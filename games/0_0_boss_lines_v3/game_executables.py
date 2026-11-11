"""Boss Lines v3 game actions, in the order of the proposal's section 6.

One spin = opening board -> loop of steps (1)-(8) ->
step (9) chests -> Treasure if the stage was cleared.

  (1) Bonus only: Scatters add free spins and are darkened.
  (2) Replace (reserved) fires while it can.
  (3) Enhance, Upgrade, Transform (reserved) fire in that order.
  (4) Connected Wilds roll their event, in cell-priority order.
  (5) Lines pay: base x sum(Enhance) x Wild multiplier x Global.
  (6) Connected basic symbols (every copy on the board), connected Wilds and
      darkened Scatters are destroyed and deal damage; refill; back to (1).
      If (1)-(6) did nothing -> (7).
  (7) Every weapon fires in cell order; refill; back to (1). Nothing -> (8).
  (8) One reserved Destroy fires; refill; back to (1). Nothing -> (9).
  (9) Chests of bosses killed this spin open left to right; then Treasure if
      every boss of the stage is dead.
"""

import math
import random

from game_calculations import GameCalculations
from game_config import ENDLESS
from game_events import emit, pos, boss_state_event, board_cells_event, chest_name
from src.calculations.statistics import get_random_outcome


def round_half_up(x: float) -> int:
    """Nearest integer, .5 rounds up (Python's round() is banker's rounding)."""
    return int(math.floor(x + 0.5))


class GameExecutables(GameCalculations):
    """Boss, power, weapon, chest and Treasure logic."""

    # =========================================================================
    # Per-spin state
    # =========================================================================
    def draw_bag(self) -> float:
        """Money bag value (x bet): chest_bag_value_weights, else the tier's coin table without coins below 1x."""
        table = self.weights("chest_bag_value_weights") or self.weights("coin_value_weights")
        return get_random_outcome({float(v): w for v, w in table.items() if float(v) >= 1 and w > 0})

    def bag_kind(self, v) -> str:
        """pinch 1-4x / small 5-15x / large 20-50x / chest 100x+ (designer 2026-10-31)."""
        for top, name in self.config.bag_kinds:
            if v <= top:
                return name
        return self.config.bag_kinds[-1][1]

    def reset_tumble(self, cause: str) -> None:
        """Clear the collected Wild multis and boss multis (tumble mode)."""
        if self.tumble_wild or self.tumble_boss or getattr(self, "tumble_acc", 0):
            emit(self, "tumbleReset", cause=cause)
        self.tumble_wild, self.tumble_boss, self.tumble_acc = 0, [], 0

    def tumble_scope(self) -> str:
        """When the tumble multi resets: "spin" (Normal, base, Heroic), "stage" (Super), "bonus" (Epic)."""
        return self.weights("tumble_reset_scope") if self.in_bonus else "spin"

    def tumble_spin_part(self) -> float:
        """tumble_combine "add": this spin's sum(Wild multis) (1 if none) x product(chest multis); 0 if neither."""
        if not self.tumble_wild and not self.tumble_boss:
            return 0
        f = max(1, self.tumble_wild)
        for m in self.tumble_boss:
            f *= m
        return f

    def tumble_factor(self) -> float:
        """Sum of the collected Wild multis (1 if none), times each boss multi, left to right.
        tumble_combine "add": this spin's part + the Global accumulated earlier in the reset scope (at least 1)."""
        cap = self.weights("tumble_factor_cap")
        if isinstance(cap, dict):  # per stage {stage: cap}
            cap = cap.get(self.stage, cap.get(str(self.stage), 0))
        if self.config.tumble_combine == "add":
            part = self.tumble_spin_part()
            if self.weights("tumble_acc_rule") == "if2x" and part < 2:
                f = max(1, part)  # Super: the accumulated Global joins only a spin with its own >= 2x
            else:
                f = max(1, getattr(self, "tumble_acc", 0) + part)
        else:
            f = max(1, self.tumble_wild)
            for m in self.tumble_boss:
                f *= m
        return min(f, cap) if cap else f

    def settle_tumble(self) -> None:
        """Tumble mode, spin end: (the spin's line pay + its chest coins) x the tumble multi."""
        base, self.tumble_base = self.tumble_base, 0.0
        add = self.config.tumble_combine == "add"
        f = self.tumble_factor()
        if base > 0 and not self.wincap_triggered:
            paid = self.award(base * f)
            emit(self, "tumbleWin", base=round(base, 4), wildSum=self.tumble_wild, bossMults=list(self.tumble_boss),
                 multi=f, paid=round(paid, 4), **({"globalBefore": self.tumble_acc} if add else {}))
        if add:  # this spin's part joins the accumulated Global; the next spin collects afresh
            part = self.tumble_spin_part()
            if self.weights("tumble_acc_rule") == "if2x" and part < 2:
                part = 0  # Super: a spin without its own >= 2x leaves the accumulated Global as it is
            if part:
                self.tumble_acc += part
                emit(self, "globalAccumulated", added=part, total=self.tumble_acc)
            self.tumble_wild, self.tumble_boss = 0, []

    def begin_spin(self) -> None:
        self.tumble_base = 0.0
        self.chain_passes = 0
        if self.config.tumble_multi and self.tumble_scope() == "spin":
            self.reset_tumble("spin")
        elif self.config.tumble_combine == "add":  # Wild / chest multis are collected per spin (settled into tumble_acc)
            self.tumble_wild, self.tumble_boss = 0, []
        self.enhance = [[0] * 5 for _ in range(6)]
        self.wild_mult = {}
        self.power_wilds = set()  # cells turned into Wild by the Transform power this spin
        self.darkened = set()
        self.spin_had_scatter = False
        for b in self.bosses:
            b["killed_this_spin"] = False
            b["chest_opened"] = False

    def note_cap(self, name: str) -> None:
        """A safety cap was hit (should be rare; counted for tuning reports)."""
        self.cap_hits[name] = self.cap_hits.get(name, 0) + 1
        emit(self, "safetyCap", cap=name)

    def stage_label(self):
        if self.stage is None:
            return None
        return "endless" if self.stage == ENDLESS else self.stage

    def is_final_bonus_spin(self) -> bool:
        return self.in_bonus and self.free_spins_left <= 0 and not self.spin_had_scatter

    # =========================================================================
    # Bosses
    # =========================================================================
    def _roll_hp(self, spec, stage=None) -> int:
        """HP from lo..hi in hp_round steps. Uniform, or tilted by tier_hp_tilt[tier] (designer 2026-10-26: the
        HP rule and range are the same for every Bonus tier, only how often each value comes up differs):
        weight of the i-th of n values = 1 + t x (2i / (n - 1) - 1); t = +1 favours the top, -1 the bottom."""
        step = self.config.hp_round
        # (lo, hi) = every hp_round step in between; more than 2 values = exactly these (rule 3, 2026-11-02: stage 5
        # is 90/95/100/110/120)
        values = list(range(spec[0], spec[1] + 1, step)) if len(spec) == 2 else list(spec)
        table = self.weights("stage_hp_weights") if stage is not None else None
        table = table.get(stage, table.get(str(stage))) if table else None
        if table:
            pool = {int(k): w for k, w in table.items() if int(k) in values and w > 0}
            if pool:
                return get_random_outcome(pool)
        key = self.bonus_tier if getattr(self, "in_bonus", False) else ("heroic" if getattr(self, "heroic", False) else None)
        t = self.config.tier_hp_tilt.get(key, 0)
        if not t or len(values) < 2:
            return random.choice(values)
        n = len(values)
        return random.choices(values, weights=[max(0.0, 1 + t * (2 * i / (n - 1) - 1)) for i in range(n)])[0]

    def _roll_chest(self, stage, guaranteed: bool = True) -> str:
        """Chest tier for one boss. guaranteed=False (see stage_min_chest_count) = the stage minimum chest does not
        apply, the draw starts from the lowest chest."""
        order = self.config.chest_order
        base = order.index(self.config.stage_min_chest[stage]) if guaranteed else 0
        table = self.config.stage_chest_weights.get(self.bonus_tier, {}).get(stage) if getattr(self, "in_bonus", False) else None
        if table:  # own chest odds for this tier + stage; the stage minimum chest still holds
            pool = {c: w for c, w in table.items() if order.index(c) >= base and w > 0}
            if pool:
                return get_random_outcome(pool)
        k = get_random_outcome({i: w for i, w in enumerate(self.weights("chest_tier_step_weights"))})
        return order[min(base + k, len(order) - 1)]

    def spawn_stage(self, stage) -> None:
        """Fresh bosses for `stage` (0-5 or ENDLESS); None = no bosses."""
        self.stage = stage
        self.stage_cleared = False
        self.bosses = []
        if self.config.tumble_multi and getattr(self, "in_bonus", False) and self.tumble_scope() == "stage":
            self.reset_tumble("stage")
        if stage is None:
            return
        if stage == ENDLESS:
            if self.last_endless_hp is None:
                hp = self._roll_hp(self.config.stage_hp_range[ENDLESS], ENDLESS)
            else:
                hp = self.last_endless_hp + random.choice(self.weights("endless_hp_step_choices"))  # per tier via tier_weights
            self.last_endless_hp = hp
            zones = self.config.endless_zone
        else:
            zones = self.config.boss_zones
        n_min = self.config.stage_min_chest_count
        if isinstance(n_min, dict):  # per stage, e.g. stage 5 / Endless: every boss (designer 2026-10-29)
            n_min = n_min.get(stage, n_min.get(str(stage), 3))
        sure = set(random.sample(list(zones), n_min)) if n_min < len(zones) else set(zones)
        chest_set = None
        if self.config.chest_rule == "v4":  # rule 3: the stage's fixed chest set, shuffled over the bosses
            sets = self.config.stage_chest_sets
            key = "heroic" if getattr(self, "heroic", False) else stage
            chest_set = list(sets.get(key, sets.get(str(key), ["dong"] * 3)))
            random.shuffle(chest_set)
        for i, (bid, zone) in enumerate(zones.items()):
            if stage != ENDLESS:
                hp = self._roll_hp(self.config.stage_hp_range[stage], stage)
                hp += self.config.boss_hp_offset.get(bid, {}).get(stage, 0)
                if stage >= 1:
                    cut = self.weights("hp_cut_weights")
                    if cut and all(isinstance(v, dict) for v in cut.values()):  # per stage {stage: {cut: w}} (2026-11-01)
                        cut = cut.get(stage, cut.get(str(stage))) or {0: 1}
                    hp -= get_random_outcome({int(k): w for k, w in cut.items()})
            self.bosses.append({"id": bid, "zone": zone, "hp": hp, "hp_max": hp, "alive": True,
                                "chest": chest_set[i % len(chest_set)] if chest_set else self._roll_chest(stage, bid in sure),
                                "killed_this_spin": False,
                                "chest_opened": False})
        boss_state_event(self)

    def boss_for_col(self, c: int):
        for b in self.bosses:
            if c in b["zone"]:
                return b
        return None

    def _kill(self, b, reason: str) -> None:
        b["alive"] = False
        b["hp"] = 0
        b["killed_this_spin"] = True
        emit(self, "bossDefeated", boss=b["id"], reason=reason, chest=chest_name(self, b["chest"]))
        if self.bosses and all(not x["alive"] for x in self.bosses):
            self.stage_cleared = True

    def deal_damage(self, hits, step: str, last_hit: bool = True) -> None:
        """One damage step. `hits` = [(col, row, damage)]. Damage is summed per
        boss; each damaged boss then rolls Last hit (if allowed) and the boss
        drop ONCE for this step (QUESTIONS.md Q11)."""
        per_boss = {}
        for c, r, dmg in hits:
            b = self.boss_for_col(c)
            if b is None or not b["alive"] or dmg <= 0:
                continue
            per_boss.setdefault(b["id"], [b, 0])[1] += dmg
        if not per_boss:
            return
        cfg = self.config
        for b, dmg in per_boss.values():
            dmg = round_half_up(dmg)
            b["hp"] = max(0, b["hp"] - dmg)
            emit(self, "bossDamage", boss=b["id"], damage=dmg, hp=b["hp"], step=step)
            if b["hp"] <= 0:
                self._kill(b, "damage")
            elif last_hit:
                chance = self.weights("last_hit_base") + self.weights("last_hit_scale") * (1 - b["hp"] / b["hp_max"])
                if self.is_final_bonus_spin():
                    chance *= self.weights("last_hit_final_spin_mult")
                if step == "arrow":
                    chance *= cfg.arrow_last_hit_mult
                if random.random() < chance:
                    self._kill(b, "lastHit")
            self._boss_drop(b)
        boss_state_event(self)

    def _boss_drop(self, b) -> None:
        if random.random() >= self.weights("boss_drop_chance"):
            return
        kind = get_random_outcome(self.weights("boss_drop_weights"))
        if kind == "power":
            p = self.pick_power()
            if p is not None:
                self.reserve[p] += 1
                emit(self, "bossDrop", boss=b["id"], kind="power", power=p)
            return
        cells = [(c, r) for c in b["zone"] for r in range(5) if self.is_basic(self.board[c][r])]
        if cells:
            c, r = random.choice(cells)
            self.board[c][r] = self.make_symbol("W")
            emit(self, "bossDrop", boss=b["id"], kind="wild", position=pos(self, c, r))

    # =========================================================================
    # Destroy / refill
    # =========================================================================
    def destroy_cells(self, cells, lit_cells=()) -> None:
        """Empty `cells` (None) and drop their Enhance factor; mark lit_cells."""
        for c, r in cells:
            self.board[c][r] = None
            self.enhance[c][r] = 0
            getattr(self, "power_wilds", set()).discard((c, r))
        new = [x for x in lit_cells if x not in self.lit]
        self.lit.update(lit_cells)
        if new:  # client: these cells now light up (Treasure plays on lit cells)
            emit(self, "litCells", cells=[pos(self, c, r) for c, r in sorted(new)])

    def chain_block_roll(self) -> bool:
        """chain_block: should this refill be forced to connect nothing?"""
        cb = self.weights("chain_block") if getattr(self, "in_bonus", False) else None
        spec = cb.get(self.stage, cb.get(str(self.stage))) if cb else None
        if not spec:
            return False
        thr, step = spec
        extra = getattr(self, "chain_passes", 0) - thr
        return extra > 0 and random.random() < min(1.0, step * extra)

    def refill(self) -> list:
        """Fill every empty cell in place, in cell-priority order."""
        filled = []
        for c, r in self.all_cells():
            if self.board[c][r] is None:
                self.board[c][r] = self.draw_symbol_for(c, r)
                filled.append((c, r))
        if filled and self.chain_block_roll():
            for _ in range(50):  # redraw the refilled cells until nothing connects
                if not self.evaluate_lines():
                    emit(self, "chainBlock", passes=self.chain_passes)
                    break
                for c, r in filled:
                    self.board[c][r] = self.draw_symbol_for(c, r)
        if filled:
            board_cells_event(self, "refill", filled)
            # display-only Wilds appear on the opening board only (designer 2026-10-25), never on refills
            self.skin_cells -= set(filled)
        return filled

    def mark_wild_skins(self, cells) -> None:
        """Display-only Wilds (wild_skin_chance): pick cells of already-winning lines among `cells` where a
        Wild would leave every line win unchanged, and emit them. Own RNG: the game's draws are untouched.
        Never in Heroic (designer 2026-10-22): every Heroic Wild is real and always fires an event / multiplier.
        Called for the opening board of a spin only (designer 2026-10-25: not on refills)."""
        self.skin_cells = set()
        chance = self.weights("wild_skin_chance")  # per tier via tier_weights (designer 2026-10-28)
        if isinstance(chance, dict):  # per stage {stage: chance} (designer 2026-10-29: fewer lit cells early)
            chance = chance.get(self.stage, chance.get(str(self.stage), 0.0))
        if chance <= 0 or getattr(self, "heroic", False):
            return
        wins = self.evaluate_lines()
        if not wins:
            return
        sig = lambda ws: sorted((w["meta"]["lineIndex"], w["symbol"], w["kind"], w["win"]) for w in ws)
        base = sig(wins)
        fresh = set(cells)
        rng = self.skin_rng
        skins = []
        bias = self.weights("wild_skin_lit_bias") if self.in_bonus else 0  # designer 2026-10-29
        for w in wins:
            ch = chance
            if bias:  # lines already mostly lit are likelier to show a display Wild (fewer new lit cells)
                cells = [(p["reel"], p["row"]) for p in w["positions"]]
                frac = sum(x in self.lit for x in cells) / len(cells)
                ch = min(1.0, chance * ((1 - bias) + bias * 2 * frac))
            if rng.random() >= ch:
                continue
            cand = [(p["reel"], p["row"]) for p in w["positions"]
                    if (p["reel"], p["row"]) in fresh and self.is_basic(self.board[p["reel"]][p["row"]])
                    and (p["reel"], p["row"]) not in skins]
            rng.shuffle(cand)
            for c, r in cand:
                real = self.board[c][r]
                self.board[c][r] = self.create_symbol("W")
                same = sig(self.evaluate_lines()) == base
                self.board[c][r] = real
                if same:
                    skins.append((c, r))
                    break
        self.skin_cells = set(skins)  # only the fresh board's skins; all are destroyed in the coming connect
        if skins:
            emit(self, "wildSkin", cells=[{**pos(self, c, r), "symbol": self.board[c][r].name} for c, r in skins])

    # =========================================================================
    # Powers
    # =========================================================================
    def pick_power(self, new_only: bool = False):
        """Random power whose reserve is below the cap (None if all are full). new_only: only powers with nothing
        in reserve (chest gifts, designer 2026-10-29: a power already stored never drops from a chest)."""
        cap = 1 if new_only else self.config.power_reserve_cap
        open_ = {p: w for p, w in self.weights("power_pick_weights").items()
                 if w > 0 and self.reserve[p] < cap}
        by_alive = self.weights("destroy_weight_by_alive")
        if by_alive and "destroy" in open_:
            n = sum(1 for b in getattr(self, "bosses", []) if b["alive"])
            open_["destroy"] *= by_alive.get(n, by_alive.get(str(n), 1))
            if open_["destroy"] <= 0:
                del open_["destroy"]
        return get_random_outcome(open_) if open_ else None

    def _basic_names_on_board(self):
        return sorted({self.board[c][r].name for c, r in self.all_cells() if self.is_basic(self.board[c][r])})

    def power_enhance(self) -> None:
        names = self._basic_names_on_board()
        if not names:
            return
        name = random.choice(names)
        f = get_random_outcome(self.weights("enhance_factor_weights"))
        cells = [(c, r) for c, r in self.all_cells() if self.board[c][r].name == name]
        for c, r in cells:
            self.enhance[c][r] += f
        emit(self, "powerActivated", power="enhance", symbol=name, factor=f,
             cells=[pos(self, c, r) for c, r in cells])

    def _win_signature(self):
        """(number of winning lines, cells in winning lines) of the current board."""
        wins = self.evaluate_lines()
        return len(wins), sum(len(w["positions"]) for w in wins)

    def power_shuffle_doc(self) -> None:
        """Document rule 3: every cell not in a winning line (Scatter stays) is shuffled; the shuffle must give a new
        line or a longer one if it can (shuffle_tries random tries, best kept); every shuffled cell gets a Shuffle
        Multiplier (kept in the cell's Enhance slot: added up per line, gone when the cell is destroyed)."""
        connected = {(p["reel"], p["row"]) for w in self.evaluate_lines() for p in w["positions"]}
        cells = [(c, r) for c, r in self.all_cells()
                 if (c, r) not in connected and self.board[c][r] is not None and not self.is_scatter(self.board[c][r])]
        syms = [self.board[c][r] for c, r in cells]
        base = self._win_signature()
        best, best_sig = None, None
        for _ in range(max(1, self.config.shuffle_tries)):
            order = syms[:]
            random.shuffle(order)
            for (c, r), s in zip(cells, order):
                self.board[c][r] = s
            sig = self._win_signature()
            if best_sig is None or sig > best_sig:
                best, best_sig = order, sig
            if sig > base:
                break
        for (c, r), s in zip(cells, best):
            self.board[c][r] = s
        mults = []
        for c, r in cells:
            f = get_random_outcome(self.weights("shuffle_mult_weights"))
            self.enhance[c][r] += f
            mults.append({**pos(self, c, r), "factor": f})
        board_cells_event(self, "powerActivated", cells, power="shuffle", mults=mults,
                          improved=bool(best_sig and best_sig > base))

    def power_shuffle(self) -> None:
        if self.config.shuffle_rule == "doc":
            return self.power_shuffle_doc()
        """Rule 3 (2026-11-02): the basic symbols swap places at random (Wild, weapons, Scatter stay), then 1-3 basic
        cells get a multi (kept in the cell's Enhance slot: added up per line, gone when the cell is destroyed)."""
        cells = [(c, r) for c, r in self.all_cells() if self.is_basic(self.board[c][r])]
        syms = [self.board[c][r] for c, r in cells]
        random.shuffle(syms)
        for (c, r), s in zip(cells, syms):
            self.board[c][r] = s
        n = min(len(cells), get_random_outcome(self.weights("shuffle_cell_count_weights")))
        mults = []
        for c, r in random.sample(cells, n):
            f = get_random_outcome(self.weights("shuffle_mult_weights"))
            self.enhance[c][r] += f
            mults.append({**pos(self, c, r), "factor": f})
        board_cells_event(self, "powerActivated", cells, power="shuffle", mults=mults)

    def power_upgrade(self) -> None:
        names = self._basic_names_on_board()
        if not names:
            return
        name = random.choice(names)
        target = get_random_outcome(self.weights("upgrade_target_weights"))
        cells = [(c, r) for c, r in self.all_cells() if self.board[c][r].name == name]
        for c, r in cells:
            self.board[c][r] = self.make_symbol(target)  # Enhance stays with the cell
        board_cells_event(self, "powerActivated", cells, power="upgrade", fromSymbol=name, toSymbol=target)

    def power_transform(self) -> None:
        skip_w = self.config.transform_skips_weapons
        cand = [(c, r) for c, r in self.all_cells()
                if not self.is_wild(self.board[c][r]) and not (skip_w and self.is_weapon(self.board[c][r]))
                and (self.in_bonus or not self.is_scatter(self.board[c][r]))]
        n = min(len(cand), random.randint(*self.weights("transform_count_range")))
        cells = random.sample(cand, n)
        for c, r in cells:
            self.board[c][r] = self.make_symbol("W")
            self.board[c][r].flash = False  # designer 2026-11-01: a Wild made by a power never flashes
        self.power_wilds.update(cells)
        board_cells_event(self, "powerActivated", cells, power="transform")

    def _replace_eligible(self):
        """Basic-symbol cells whose symbol is NOT present in at least 2 of the
        first 3 columns."""
        cols = [{self.board[c][r].name for r in range(5) if self.is_basic(self.board[c][r])} for c in range(3)]
        ok = {n for n in self.config.basic_symbols if sum(n in s for s in cols) >= 2}
        return [(c, r) for c, r in self.all_cells()
                if self.is_basic(self.board[c][r]) and self.board[c][r].name not in ok]

    def power_replace(self) -> bool:
        cells = self._replace_eligible()
        if not cells:
            return False
        allowed = self.allowed_basic_symbols()
        for c, r in cells:
            old = self.board[c][r].name
            choices = [s for s in allowed if s != old] or allowed
            self.board[c][r] = self.make_symbol(random.choice(choices))
        board_cells_event(self, "powerActivated", cells, power="replace")
        return True

    def power_destroy(self) -> None:
        """Every symbol except Wild is destroyed (step 8). Paying symbols
        deal damage (Q13) but are not lit; destroyed weapons are lit."""
        cells, hits = [], []
        for c, r in self.all_cells():
            s = self.board[c][r]
            if s is None or self.is_wild(s) or (self.is_scatter(s) and not self.in_bonus):
                continue
            cells.append((c, r))
            if self.is_basic(s) and self.config.destroy_deals_damage:
                hits.append((c, r, self.config.symbol_damage[s.name]))
        emit(self, "powerActivated", power="destroy", cells=[pos(self, c, r) for c, r in cells])
        self.destroy_cells(cells)
        self.deal_damage(hits, "destroy")

    def allowed_basic_symbols(self):
        removed = self.config.stage_removed_lows.get(self.stage, 0) if self.stage is not None else 0
        return self.config.low_symbols[removed:] + self.config.high_symbols

    # =========================================================================
    # Wild events (step 4)
    # =========================================================================
    def weights(self, name: str) -> dict:
        """Tunable config value `name` (weight table or scalar), overridden per Bonus
        tier (and for the Treasure hunt feature spin, key "treasure_hunt") by
        config.tier_weights; key "heroic" = the Heroic feature spin."""
        key = self.bonus_tier if self.in_bonus else ("treasure_hunt" if self.treasure_hunt else ("heroic" if self.heroic else None))
        table = self.config.tier_weights.get(key, {}).get(name) if key else None
        return table if table is not None else getattr(self.config, name)

    def draw_coin(self, min_value: float, min_tier: str = None, table: dict = None) -> float:
        """Coin value >= min_value (and >= min_tier's lowest value), from `table` or the coin table."""
        if getattr(self, "force_wincap", False):
            return 25000
        if self.in_bonus and self.bonus_tier == "epic" and not self.epic_opening:
            min_value = max(min_value, self.config.epic_min_coin)  # N6
        if min_tier is not None:
            min_value = max(min_value, self.config.coin_tiers[min_tier][0])
        excl = self.config.coin_excluded_values
        pool = {v: w for v, w in (table or self.weights("coin_value_weights")).items() if v >= min_value and v not in excl}
        if not pool and table:  # an own table with nothing at this minimum falls back to the coin table
            return self.draw_coin(min_value)
        return get_random_outcome(pool)

    def current_min_coin(self) -> float:
        if self.treasure_hunt and not self.in_bonus:  # a Bonus entered from Treasure hunt uses stage minimums
            return self.config.treasure_hunt_min_coin
        tier = self.config.tier_stage_min_coin.get(self.bonus_tier, {}) if self.in_bonus else {}
        return tier.get(self.stage, self.config.stage_min_coin.get(self.stage, 0.2))

    def wild_events(self, wins) -> bool:
        connected = {(p["reel"], p["row"]) for w in wins for p in w["positions"]
                     if self.is_wild(self.board[p["reel"]][p["row"]])}
        acted = False
        chance = 1.0 if (self.heroic or getattr(self, "force_wincap", False)) else self.weights("wild_event_chance")
        group = [] if self.heroic else None  # Heroic: every Wild of the pass fires at once, one grouped event
        def out(**data):
            if group is None:
                emit(self, "wildEvent", **data)
            else:
                group.append(data)
        power_chance = (self.weights("power_wild_event_chance")
                        if self.in_bonus and not getattr(self, "force_wincap", False) else None)
        if self.weights("wild_multi_weights") and not getattr(self, "force_wincap", False):
            # designer 2026-10-29: no Wild events any more. Every Wild carries its multiplier from the moment it
            # appears (mostly 1x); connecting, it multiplies its lines and drops a power with a small chance.
            drop = self.weights("wild_power_drop_chance")
            for cell in [x for x in self.all_cells() if x in connected]:
                c, r = cell
                f = getattr(self.board[c][r], "prize", 0) or 1
                if f > 1 and self.config.tumble_multi:  # collected into the tumble multi (summed)
                    self.tumble_wild += f
                    out(event="collect", position=pos(self, c, r), factor=f, total=self.tumble_wild)
                    acted = True
                elif f > 1:
                    self.wild_mult[cell] = f
                    out(event="multiplier", position=pos(self, c, r), factor=f)
                    acted = True
                flash = getattr(self.board[c][r], "flash", False)
                if flash or (drop and random.random() < drop):  # flashing Wild: a power, for sure (if room)
                    p = self.pick_power()
                    if p is not None:
                        self.reserve[p] += 1
                        out(event="power", position=pos(self, c, r), power=p)
                        acted = True
            if group:
                emit(self, "wildEvents", wilds=group)
            return acted
        for cell in [x for x in self.all_cells() if x in connected]:
            # designer 2026-10-22: in a Bonus, a Wild made by the Transform power fires an event only this often
            ch = power_chance if power_chance is not None and cell in getattr(self, "power_wilds", ()) else chance
            if random.random() >= ch:
                continue
            weights = dict(self.weights("wild_event_weights"))
            if getattr(self, "force_wincap", False):
                weights = {"coin": 1}
            if self.pick_power() is None:
                weights.pop("power", None)
            kind = get_random_outcome(weights)
            acted = True
            c, r = cell
            if kind == "multiplier":
                f = get_random_outcome(self.weights("wild_mult_weights"))
                self.wild_mult[cell] = f
                out(event="multiplier", position=pos(self, c, r), factor=f)
            elif kind == "coin":
                v = self.draw_coin(max(self.current_min_coin(), self.weights("wild_coin_min_value")),
                                   table=self.weights("wild_coin_value_weights"))
                g = self.global_factor() if self.config.wild_coin_uses_global else 1
                paid = self.award(v * g)
                out(event="coin", position=pos(self, c, r), value=v, globalMult=g, paid=paid)
            else:
                p = self.pick_power()
                self.reserve[p] += 1
                out(event="power", position=pos(self, c, r), power=p)
            if self.wincap_triggered:
                break
        if group:
            emit(self, "wildEvents", wilds=group)
        return acted

    # =========================================================================
    # Steps (1)-(6)
    # =========================================================================
    def step_scatters(self) -> bool:
        if not self.in_bonus:
            return False
        new = [(c, r) for c, r in self.all_cells()
               if self.is_scatter(self.board[c][r]) and (c, r) not in self.darkened]
        if not new:
            return False
        self.darkened.update(new)
        self.free_spins_left += len(new)
        self.spin_had_scatter = True
        emit(self, "scatterCollected", cells=[pos(self, c, r) for c, r in new], added=len(new),
             freeSpinsLeft=self.free_spins_left)
        return True

    def step_reserved_powers(self) -> bool:
        acted = False
        while self.reserve["replace"] > 0 and self._replace_eligible():
            self.reserve["replace"] -= 1
            self.power_replace()
            acted = True
        for name, fn in (("enhance", self.power_enhance), ("upgrade", self.power_upgrade),
                         ("transform", self.power_transform)):
            while self.reserve[name] > 0:
                self.reserve[name] -= 1
                fn()
                acted = True
        return acted

    def step_connect(self) -> bool:
        """Steps (4)-(6) for one pass. Returns True if anything connected."""
        wins = self.evaluate_lines()
        if not wins:
            return False
        self.chain_passes = getattr(self, "chain_passes", 0) + 1  # chain_block bookkeeping
        self.wild_events(wins)
        if self.wincap_triggered:
            return True
        self.pay_lines(wins)
        if self.wincap_triggered:
            return True
        names = {w["symbol"] for w in wins if w["symbol"] in self.config.basic_symbols}
        wild_cells = {(p["reel"], p["row"]) for w in wins for p in w["positions"]
                      if self.is_wild(self.board[p["reel"]][p["row"]])}
        cells, hits = [], []
        for c, r in self.all_cells():
            s = self.board[c][r]
            if (self.is_basic(s) and s.name in names) or (c, r) in wild_cells:
                cells.append((c, r))
                dmg = self.config.symbol_damage[s.name]
                if (c, r) in self.skin_cells and self.config.wild_skin_damage is not None:
                    dmg = self.config.wild_skin_damage  # a display-only Wild deals Wild damage
                hits.append((c, r, dmg))
        dark = [cell for cell in self.darkened if self.is_scatter(self.board[cell[0]][cell[1]])]
        emit(self, "destroy", cause="connect", cells=[pos(self, c, r) for c, r in cells],
             scatters=[pos(self, c, r) for c, r in dark])
        if self.config.lit_rule == "lines":  # only the winning lines' cells (Wilds too) + collected Scatters
            lit_wins = wins
            mode = self.weights("lit_wild_lines_only")
            if mode == "cells":  # rule 4 (2026-11-02): only the connected Wild cells (display Wilds too)
                win_cells = {(p["reel"], p["row"]) for w in wins for p in w["positions"]}
                lit_wins = []
                wild_lit = [x for x in self.all_cells() if x in wild_cells or (x in self.skin_cells and x in win_cells)]
            elif mode:  # designer 2026-10-28 trial: only lines with a Wild light up ("real": display Wilds don't count)
                skins = set() if mode == "real" else self.skin_cells
                lit_wins = [w for w in wins if any((p["reel"], p["row"]) in wild_cells
                                                   or (p["reel"], p["row"]) in skins for p in w["positions"])]
            lit = list(dict.fromkeys((p["reel"], p["row"]) for w in lit_wins for p in w["positions"])) + dark
            if mode == "cells":
                lit = wild_lit + dark
        else:
            lit = [(c, r) for c, r in cells if (c, r) not in wild_cells]  # basic symbols only
        self.destroy_cells(cells + dark, lit_cells=lit)
        self.darkened.clear()
        self.wild_mult.clear()
        self.deal_damage(hits, "connect")
        self.refill()
        return True

    def run_cycle(self) -> bool:
        """Repeat passes of steps (1)-(6) until a pass does nothing. Returns
        True if any pass acted."""
        any_act = False
        while not self.wincap_triggered and self.actions < self.config.max_actions_per_spin:
            self.actions += 1
            a1 = self.step_scatters()
            a2 = self.step_reserved_powers() if self.config.action_order != "doc" else False
            a3 = self.step_connect()
            if not (a1 or a2 or a3):
                break
            any_act = True
            if self.actions >= self.config.max_actions_per_spin:
                self.note_cap("actions")
            if self.darkened and not a3:
                # Bonus Scatters darkened without a connection this pass are
                # still destroyed in step (6).
                cells = [cell for cell in self.darkened if self.is_scatter(self.board[cell[0]][cell[1]])]
                emit(self, "destroy", cause="scatter", cells=[], scatters=[pos(self, c, r) for c, r in cells])
                self.destroy_cells(cells, lit_cells=cells if self.config.lit_rule == "lines" else ())
                self.darkened.clear()
                self.refill()
        return any_act

    # =========================================================================
    # Step (7): weapons
    # =========================================================================
    def _weapon_targets(self, c, r, name):
        cfg = self.config

        def hit(s):  # N1: any symbol, except Scatter outside Bonus; other weapons are spared (designer 2026-10-21)
            return (s is not None and (self.in_bonus or not self.is_scatter(s))
                    and not (cfg.weapons_spare_weapons and self.is_weapon(s)))

        if name == "BM":
            area = [(cc, rr) for cc in range(c - 1, c + 2) for rr in range(r - 1, r + 2)
                    if 0 <= cc < 6 and 0 <= rr < 5 and (cc, rr) != (c, r)]
            return [x for x in area if hit(self.board[x[0]][x[1]])]
        if name == "SW":
            return [(cc, r) for cc in range(6) if cc != c and hit(self.board[cc][r])]
        if name == "LT":
            names = self._basic_names_on_board()
            if not names:
                return []
            pick = random.choice(names)
            return [(cc, rr) for cc, rr in self.all_cells() if self.board[cc][rr] is not None
                    and self.board[cc][rr].name == pick]
        return []

    def arrow_damage(self, b) -> int:
        if self.config.arrow_rule == "table":
            vals = self.weights("arrow_damage_values")
            lo, hi = self.config.arrow_hp_range
            lvl = min(1.0, max(0.0, (b["hp_max"] - lo) / (hi - lo)))
            ratio = b["hp"] / b["hp_max"] if b["hp_max"] else 0
            t = self.weights("arrow_tilt_max") * (2 * lvl - 1) + self.weights("arrow_tilt_ratio") * (2 * ratio - 1)
            t = max(-1.0, min(1.0, t))
            n = len(vals)
            return random.choices(vals, weights=[max(0.0, 1 + t * (2 * i / (n - 1) - 1)) for i in range(n)])[0]
        k = random.choice(self.weights("arrow_k_choices"))
        dmg = self.config.arrow_base + b["hp_max"] * k
        if self.stage == ENDLESS:
            dmg /= self.config.arrow_endless_divisor
        return round_half_up(dmg)

    def _weapon_lit(self, c, r) -> list:
        """lit_rule "lines": a weapon that fires lights its own cell."""
        return [(c, r)] if self.config.lit_rule == "lines" else []

    def step_weapons(self) -> bool:
        weapons = [(c, r) for c, r in self.all_cells() if self.is_weapon(self.board[c][r])]
        if not weapons:
            return False
        for c, r in weapons:
            if self.wincap_triggered:
                break
            sym = self.board[c][r]
            if sym is None or not self.is_weapon(sym):
                continue
            name = sym.name
            if name == "AR":
                b = self.boss_for_col(c)
                dmg = self.arrow_damage(b) if (b is not None and b["alive"]) else 0
                emit(self, "weapon", weapon="arrow", position=pos(self, c, r), damage=dmg,
                     boss=b["id"] if b else None)
                self.destroy_cells([(c, r)], lit_cells=self._weapon_lit(c, r))
                if dmg:
                    self.deal_damage([(c, r, dmg)], "arrow")
                continue
            factor = sym.prize or 1
            targets = self._weapon_targets(c, r, name)
            hits = [(tc, tr, self.config.symbol_damage[self.board[tc][tr].name] * factor) for tc, tr in targets
                    if self.board[tc][tr].name in self.config.symbol_damage]  # only paying symbols deal damage
            if self.config.weapon_self_damage:
                hits.append((c, r, self.config.weapon_self_damage))  # the weapon's own cell (designer 2026-10-21)
            emit(self, "weapon", weapon={"BM": "bomb", "SW": "sword", "LT": "lightning"}[name],
                 position=pos(self, c, r), factor=factor, cells=[pos(self, tc, tr) for tc, tr in targets])
            # nothing destroyed by a weapon lights its cell; a destroyed weapon never fires
            self.destroy_cells(targets + [(c, r)], lit_cells=self._weapon_lit(c, r))
            self.deal_damage(hits, name)
        self.refill()
        return True

    # =========================================================================
    # Full action loop (1)-(8)
    # =========================================================================
    def fire_powers_doc(self) -> bool:
        """Section 8 step 8: each reserved power fires once, in the order Upgrade, Transform, Replace, Shuffle; the
        screen is held between them (no connect / destroy in between)."""
        acted = False
        for name, fn in (("upgrade", self.power_upgrade), ("transform", self.power_transform),
                         ("replace", self.power_replace), ("shuffle", self.power_shuffle)):
            if self.reserve.get(name, 0) <= 0 or self.wincap_triggered:
                continue
            if name == "replace" and not self._replace_eligible():
                continue  # nothing to replace: it stays in reserve
            self.reserve[name] -= 1
            fn()
            acted = True
        return acted

    def resolve_actions_doc(self) -> None:
        """Section 8 order: (1)-(5) lines until nothing connects, (6) weapons, (7) open the chests of killed bosses
        left to right, (8) Upgrade/Transform/Replace/Shuffle, (9) Destroy; each acting step goes back to (1)."""
        self.actions = 0
        while not self.wincap_triggered and self.actions < self.config.max_actions_per_spin:
            self.run_cycle()
            if self.wincap_triggered:
                break
            if self.step_weapons():
                continue
            self.open_chests()
            if self.wincap_triggered:
                break
            if self.fire_powers_doc():
                continue
            if self.reserve["destroy"] > 0:
                self.reserve["destroy"] -= 1
                self.power_destroy()
                self.refill()
                continue
            break

    def resolve_actions(self) -> None:
        if self.config.action_order == "doc":
            return self.resolve_actions_doc()
        self.actions = 0
        while not self.wincap_triggered and self.actions < self.config.max_actions_per_spin:
            self.run_cycle()
            if self.wincap_triggered:
                break
            if self.step_weapons():
                continue
            if self.reserve.get("shuffle", 0) > 0:  # rule 3: Shuffle fires once the weapons are done
                self.reserve["shuffle"] -= 1
                self.power_shuffle()
                continue
            if self.reserve["destroy"] > 0:
                self.reserve["destroy"] -= 1
                self.power_destroy()
                self.refill()
                continue
            break

    # =========================================================================
    # Step (9): chests
    # =========================================================================
    def open_chest_v4(self, b) -> None:
        """Rule 3 (2026-11-02): tier up while the upgrade roll hits (up to chest_open_upgrade_max times, never past red),
        then one money bag of the chest's own
        kind, plus independently a power and a chest multi (Bonus / Heroic only)."""
        cfg = self.config
        tier, upgraded, order = b["chest"], None, cfg.chest_order_v4
        ups, cap = 0, cfg.chest_open_upgrade_max  # designer 2026-11-02: a chest may go up several times
        while (order.index(tier) < len(order) - 1 and (cap is None or ups < cap)
               and random.random() < self.weights("chest_open_upgrade_chance").get(tier, 0)):
            tier = upgraded = order[order.index(tier) + 1]
            ups += 1
        gifts = []
        v = get_random_outcome({float(k): w for k, w in self.weights("chest_tier_bags")[tier].items() if w > 0})
        if getattr(self, "force_wincap", False):
            v = 25000.0
        bag = cfg.chest_tier_bag_names.get(tier, self.bag_kind(v))
        if cfg.tumble_multi:
            self.tumble_base += v
            gifts.append({"kind": "bag", "bag": bag, "value": v, "pending": True})
        else:
            gifts.append({"kind": "bag", "bag": bag, "value": v, "paid": self.award(v)})
        got_power = False
        if (self.in_bonus or getattr(self, "heroic", False)) and not self.wincap_triggered:
            if random.random() < self.weights("chest_gift_power_chance").get(tier, 0):
                p = self.pick_power(new_only=cfg.chest_power_new_only)
                if p is not None:  # no room: the power is simply lost (the bag was already given)
                    self.reserve[p] += 1
                    got_power = True
                    gifts.append({"kind": "power", "power": p})
            if cfg.tumble_multi and random.random() < self.weights("chest_gift_multi_chance").get(tier, 0):
                cap = cfg.chest_multi_cap.get(tier, 10)
                m = get_random_outcome({v: w for v, w in self.band_table("chest_multi_weights").items() if v <= cap})
                self.tumble_boss.append(m)
                gifts.append({"kind": "multi", "factor": m, "bossMults": list(self.tumble_boss)})
        extra = 0
        if got_power and self.in_bonus and self.free_spins_left <= 0 and not cfg.chest_power_immediate:
            self.free_spins_left += 1
            extra = 1
        b["chest_opened"] = True
        emit(self, "chestOpened", boss=b["id"], chest=chest_name(self, b["chest"]), upgradedTo=chest_name(self, upgraded),
             gifts=gifts, extraSpin=extra, freeSpinsLeft=self.free_spins_left if self.in_bonus else None)

    def open_chest(self, b) -> None:
        cfg = self.config
        if cfg.chest_rule == "v4":
            return self.open_chest_v4(b)
        tier = b["chest"]
        upgraded = None
        order = cfg.chest_order
        if random.random() < self.weights("chest_upgrade_chance") and order.index(tier) < len(order) - 1:
            higher = order[order.index(tier) + 1:]
            w = self.weights("chest_upgrade_tier_weights")  # designer 2026-10-29: fewer upgrades straight to diamond
            pool = {c: w.get(c, 0) for c in higher} if w else {}
            upgraded = get_random_outcome(pool) if sum(pool.values()) > 0 else random.choice(higher)
            tier = upgraded
        n = get_random_outcome(self.weights("chest_gift_count_weights")[tier])
        kinds = []
        gifts_ok = self.in_bonus or getattr(self, "heroic", False)  # designer 2026-10-30: Heroic chests too
        mchance = self.weights("chest_gift_multi_chance").get(tier, 0) if (gifts_ok and cfg.tumble_multi) else 0
        pch = self.weights("chest_gift_power_chance")[tier] if (self.in_bonus or (gifts_ok and cfg.tumble_multi)) else 0
        for _ in range(n):
            x = random.random()
            if x < pch:
                kinds.append("power")
            elif x < pch + mchance:
                kinds.append("multi")  # boss multi (designer 2026-10-30)
            else:
                kinds.append("coin")
        sure = tier in cfg.chest_sure_coin_tiers  # these chests always hold a coin (designer 2026-10-29: diamond only)
        if sure and "coin" not in kinds:
            kinds[0] = "coin"
        g = self.global_factor()
        gifts, got_power = [], False
        for kind in kinds:
            if kind == "multi":
                cap = cfg.chest_multi_cap.get(tier, 10)
                m = get_random_outcome({v: w for v, w in self.band_table("chest_multi_weights").items() if v <= cap})
                self.tumble_boss.append(m)
                gifts.append({"kind": "multi", "factor": m, "bossMults": list(self.tumble_boss)})
                continue
            if kind == "power":
                p = self.pick_power(new_only=cfg.chest_power_new_only)
                if p is not None:
                    self.reserve[p] += 1
                    got_power = True
                    gifts.append({"kind": "power", "power": p})
                    continue
                if not cfg.chest_power_overflow_to_coin:
                    continue
            if cfg.chest_bags:  # designer 2026-10-31: chest coins are money bags, >= 1x, no stage / chest floor
                v = self.draw_bag()
                bag = self.bag_kind(v)
                if cfg.tumble_multi:
                    self.tumble_base += v
                    gifts.append({"kind": "bag", "bag": bag, "value": v, "pending": True})
                    continue
                paid = self.award(v)
                gifts.append({"kind": "bag", "bag": bag, "value": v, "paid": paid})
                if self.wincap_triggered:
                    break
                continue
            mode = cfg.chest_coin_min
            if mode == "tier" or (mode == "sure_only" and sure):
                v = self.draw_coin(0, min_tier=tier)
                sure = False  # "sure_only": only the guaranteed coin keeps the chest tier's floor
            else:
                v = self.draw_coin(self.current_min_coin())
            if cfg.tumble_multi:  # designer 2026-10-30: chest coins join the spin's line pay, x the tumble multi
                self.tumble_base += v
                gifts.append({"kind": "coin", "value": v, "pending": True})
                continue
            paid = self.award(v * g)
            gifts.append({"kind": "coin", "value": v, "globalMult": g, "paid": paid})
            if self.wincap_triggered:
                break
        extra = 0
        if got_power and self.in_bonus and self.free_spins_left <= 0 and not cfg.chest_power_immediate:
            self.free_spins_left += 1
            extra = 1
        b["chest_opened"] = True
        emit(self, "chestOpened", boss=b["id"], chest=chest_name(self, b["chest"]), upgradedTo=chest_name(self, upgraded), gifts=gifts,
             extraSpin=extra, freeSpinsLeft=self.free_spins_left if self.in_bonus else None)

    def open_chests(self) -> None:
        for b in self.bosses:  # boss1 -> boss3 = left to right
            if b["killed_this_spin"] and not b["chest_opened"] and not self.wincap_triggered:
                self.open_chest(b)

    # =========================================================================
    # Treasure
    # =========================================================================
    def _treasure_cell(self, kind, min_coin):
        cfg = self.config
        names = {"coin": "TC", "magnet": "TM", "clover": "TV", "golden": "TV", "star": "TS",
                 "global": "TG", "scatter": "SC"}
        if kind == "coin":
            v = self.draw_coin(min_coin, table=self.stage_coin_table())
        elif kind == "star":
            v = self.draw_coin(min_coin, table=self.weights("star_value_weights"))
        elif kind == "magnet":
            v = 0.0
        elif kind == "clover":
            v = get_random_outcome(self.weights("clover_factor_weights"))
        elif kind == "golden":
            v = get_random_outcome(self.weights("golden_factor_weights"))
        elif kind == "global":
            v = get_random_outcome(self.weights("global_factor_weights"))
        else:
            v = 0
        sym = self.make_symbol(names[kind])
        sym.prize = v
        return sym

    def stage_coin_table(self):
        """Treasure coin weights of the stage just cleared (stage_coin_value_weights[tier][stage]), else None
        (the tier's coin table). Lets each stage's Treasure pay its own amount (designer 2026-10-25)."""
        if not self.in_bonus:
            return None
        return self.config.stage_coin_value_weights.get(self.bonus_tier, {}).get(self.stage)

    def roll_treasure_kind(self, weights) -> str:
        return get_random_outcome(weights)

    def _treasure_values(self, cells, kinds):
        return [(x, self.board[x[0]][x[1]].prize) for x in cells
                if kinds.get(x) in ("coin", "magnet") and self.board[x[0]][x[1]] is not None]

    def _treasure_maxwin_check(self, cells, kinds) -> bool:
        """N2: stop with Maxwin as soon as the Treasure, if collected now, would
        reach 25,000x (also covers a single Maxwin coin on the board)."""
        g = self.global_factor()
        total = sum(v for _, v in self._treasure_values(cells, kinds)) * g
        if self.win_manager.running_bet_win + total >= self.config.wincap:
            emit(self, "treasureMaxwin", value=round(total, 2))
            self.award(total)
            return True
        return False

    def run_treasure(self, cells, min_coin) -> float:
        """Treasure on `cells` (Proposal section 6, Treasure steps 1-7)."""
        cfg = self.config
        cells = [x for x in self.all_cells() if x in set(cells)]
        if not cells:
            return 0.0
        start_win = self.win_manager.running_bet_win
        emit(self, "treasureStart", cells=[pos(self, c, r) for c, r in cells])
        kinds = {}
        for c, r in cells:
            self.board[c][r] = None
        first = True
        used_magnets, used_clovers = set(), set()
        rounds = 0
        while True:
            rounds += 1
            if rounds > cfg.treasure_max_rounds:
                self.note_cap("treasure_rounds")
                break
            # (1)/(2) symbols appear on empty lit cells
            new = []
            round_mult = self.weights("treasure_round_kind_mult")
            for c, r in [x for x in cells if self.board[x[0]][x[1]] is None]:
                weights = dict(self.weights("treasure_kind_weights"))
                for k, ms in round_mult.items():  # e.g. Clover held back in the first round(s)
                    if k in weights:
                        weights[k] *= ms[min(rounds - 1, len(ms) - 1)]
                if self.no_scatter_spin or (cfg.treasure_scatter_capped and not self.scatter_allowed(c, r)):
                    weights.pop("scatter", None)
                if sum(1 for x in cells if kinds.get(x) == "coin") < cfg.magnet_min_coins:
                    weights.pop("magnet", None)
                kind = self.roll_treasure_kind(weights)
                self.board[c][r] = self._treasure_cell(kind, min_coin)
                kinds[(c, r)] = kind
                new.append((c, r))
            if first and new and not any(kinds[x] == "coin" for x in new):
                c, r = random.choice(new)
                self.board[c][r] = self._treasure_cell("coin", min_coin)
                kinds[(c, r)] = "coin"
            first = False
            n_sc = 0
            for c, r in new:
                if kinds[(c, r)] == "global":
                    self.global_mult += self.board[c][r].prize  # Q21: collected on appearance
                elif kinds[(c, r)] == "scatter":
                    n_sc += 1
            if n_sc and self.in_bonus:
                self.free_spins_left += n_sc
                self.spin_had_scatter = True
            emit(self, "treasureSymbols", cells=[
                {**pos(self, c, r), "kind": kinds[(c, r)], "value": self.board[c][r].prize,
                 **({"coin": self.coin_label(self.board[c][r].prize)} if kinds[(c, r)] == "coin" else {})}
                for c, r in new], globalMult=self.global_factor(), addedSpins=n_sc if self.in_bonus else 0)
            if self._treasure_maxwin_check(cells, kinds):
                return self.win_manager.running_bet_win - start_win
            # (3) Stars, in cell order: add to every coin and magnet, then the Star
            # turns into a coin with its own value (N3, answered 2026-10-07)
            for c, r in [x for x in cells if kinds.get(x) == "star"]:
                v = self.board[c][r].prize
                hit = [x for x, _ in self._treasure_values(cells, kinds)]
                for x in hit:
                    self.board[x[0]][x[1]].prize += v
                self.board[c][r] = self.make_symbol("TC")
                self.board[c][r].prize = v
                kinds[(c, r)] = "coin"
                emit(self, "treasureStar", position=pos(self, c, r), value=v, cells=[pos(self, *x) for x in hit],
                     becomesCoin=True)
            # (4) Clovers, simultaneous: each target x product of covering clovers
            clovers = [x for x in cells if kinds.get(x) == "clover" and x not in used_clovers]
            if clovers:
                mult = {}
                for c, r in clovers:
                    f = self.board[c][r].prize
                    for cc in range(c - 1, c + 2):
                        for rr in range(r - 1, r + 2):
                            if (cc, rr) != (c, r) and kinds.get((cc, rr)) in cfg.clover_hits:
                                mult[(cc, rr)] = mult.get((cc, rr), 1) * f
                for (cc, rr), f in mult.items():
                    self.board[cc][rr].prize *= f
                emit(self, "treasureClover", clovers=[{**pos(self, c, r), "factor": self.board[c][r].prize}
                                                       for c, r in clovers],
                     cells=[{**pos(self, c, r), "factor": f} for (c, r), f in mult.items()])
                used_clovers.update(clovers)  # N10: stays on the board, inactive
                if self.weights("treasure_clover_vanishes"):  # Proposal step 2: the cell empties and refills
                    for x in clovers:
                        self.board[x[0]][x[1]] = None
                        kinds.pop(x, None)
                        used_clovers.discard(x)  # a new Clover landing here later fires again
            # (5) Golden clovers, one after another: x every reward cell on the board
            for c, r in [x for x in cells if kinds.get(x) == "golden" and x not in used_clovers]:
                f = self.board[c][r].prize
                hit = [x for x, _ in self._treasure_values(cells, kinds)]
                for x in hit:
                    self.board[x[0]][x[1]].prize *= f
                used_clovers.add((c, r))  # N10: stays on the board, inactive
                emit(self, "treasureGoldenClover", position=pos(self, c, r), factor=f,
                     cells=[pos(self, *x) for x in hit])
                if self.weights("treasure_clover_vanishes"):
                    self.board[c][r] = None
                    kinds.pop((c, r), None)
                    used_clovers.discard((c, r))
            if self._treasure_maxwin_check(cells, kinds):
                return self.win_manager.running_bet_win - start_win
            # (6) next magnet in cell order; then back to (2)
            magnet = next((x for x in cells if kinds.get(x) == "magnet" and x not in used_magnets), None)
            if magnet is None:
                break
            used_magnets.add(magnet)
            mc, mr = magnet
            taken = [x for x, _ in self._treasure_values(cells, kinds) if x != magnet]
            gained = sum(self.board[x[0]][x[1]].prize for x in taken)
            self.board[mc][mr].prize += gained
            for x in taken:
                self.board[x[0]][x[1]] = None
                kinds.pop(x, None)
                used_magnets.discard(x)
            emit(self, "treasureMagnet", position=pos(self, mc, mr), collected=gained,
                 value=self.board[mc][mr].prize, cells=[pos(self, c, r) for c, r in taken])
        # (7) collect every reward on the board x Global
        total = sum(v for _, v in self._treasure_values(cells, kinds))
        g = self.global_factor()
        paid = self.award(total * g)
        emit(self, "treasureEnd", total=round(total, 4), globalMult=g, paid=round(paid, 4))
        self.record({"kind": "treasure", "symbol": "treasure", "gametype": self.gametype})
        return paid

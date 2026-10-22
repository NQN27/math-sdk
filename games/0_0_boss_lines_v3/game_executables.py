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
from game_events import emit, pos, boss_state_event, board_cells_event
from src.calculations.statistics import get_random_outcome


def round_half_up(x: float) -> int:
    """Nearest integer, .5 rounds up (Python's round() is banker's rounding)."""
    return int(math.floor(x + 0.5))


class GameExecutables(GameCalculations):
    """Boss, power, weapon, chest and Treasure logic."""

    # =========================================================================
    # Per-spin state
    # =========================================================================
    def begin_spin(self) -> None:
        self.enhance = [[0] * 5 for _ in range(6)]
        self.wild_mult = {}
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
    def _roll_hp(self, lo: int, hi: int) -> int:
        step = self.config.hp_round
        return random.choice(list(range(lo, hi + 1, step)))

    def _roll_chest(self, stage) -> str:
        order = self.config.chest_order
        base = order.index(self.config.stage_min_chest[stage])
        k = get_random_outcome({i: w for i, w in enumerate(self.weights("chest_tier_step_weights"))})
        return order[min(base + k, len(order) - 1)]

    def spawn_stage(self, stage) -> None:
        """Fresh bosses for `stage` (0-5 or ENDLESS); None = no bosses."""
        self.stage = stage
        self.stage_cleared = False
        self.bosses = []
        if stage is None:
            return
        if stage == ENDLESS:
            if self.last_endless_hp is None:
                hp = self._roll_hp(*self.config.stage_hp_range[ENDLESS])
            else:
                hp = self.last_endless_hp + random.choice(self.config.endless_hp_step_choices)
            self.last_endless_hp = hp
            zones = self.config.endless_zone
        else:
            zones = self.config.boss_zones
        for bid, zone in zones.items():
            if stage != ENDLESS:
                hp = self._roll_hp(*self.config.stage_hp_range[stage])
                hp += self.config.boss_hp_offset.get(bid, {}).get(stage, 0)
            self.bosses.append({"id": bid, "zone": zone, "hp": hp, "hp_max": hp, "alive": True,
                                "chest": self._roll_chest(stage), "killed_this_spin": False,
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
        emit(self, "bossDefeated", boss=b["id"], reason=reason, chest=b["chest"])
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
        decay = self.config.lit_decay.get(self.bonus_tier if self.in_bonus else ("heroic" if self.heroic else None))
        for cell in lit_cells:
            if decay and cell not in self.lit:
                if random.random() >= decay["decay"] ** max(0, len(self.lit) + 1 - decay["free"]):
                    continue
            self.lit.add(cell)

    def lit_steer_cfg(self):
        return self.config.lit_steer.get(self.bonus_tier if self.in_bonus else ("heroic" if self.heroic else None))

    def lit_steer_accepts(self) -> bool:
        """lit_steer (designer 2026-10-22): every connected cell still lights (rule unchanged), but a board whose
        connections would light many NEW cells is kept only with chance decay ** max(0, lit + new - free), so
        connections lean onto cells that are already lit. True = keep this board."""
        st = self.lit_steer_cfg()
        if not st:
            return True
        new = {(p["reel"], p["row"]) for w in self.evaluate_lines() for p in w["positions"]} - self.lit
        if not new:
            return True
        return random.random() < st["decay"] ** max(0, len(self.lit) + len(new) - st["free"])

    def refill(self) -> list:
        """Fill every empty cell in place, in cell-priority order."""
        filled = []
        for c, r in self.all_cells():
            if self.board[c][r] is None:
                self.board[c][r] = self.draw_symbol_for(c, r)
                filled.append((c, r))
        st = self.lit_steer_cfg() if filled else None
        for _ in range(st["tries"] - 1 if st else 0):  # lit_steer: redraw the new symbols a few times
            if self.lit_steer_accepts():
                break
            for c, r in filled:
                self.board[c][r] = self.draw_symbol_for(c, r)
        if filled:
            board_cells_event(self, "refill", filled)
            self.mark_wild_skins(filled)
        return filled

    def mark_wild_skins(self, cells) -> None:
        """Display-only Wilds (wild_skin_chance): pick cells of already-winning lines among `cells` where a
        Wild would leave every line win unchanged, and emit them. Own RNG: the game's draws are untouched.
        Never in Heroic (designer 2026-10-22): every Heroic Wild is real and always fires an event / multiplier."""
        self.skin_cells = set()
        chance = self.config.wild_skin_chance
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
        for w in wins:
            if rng.random() >= chance:
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
    def pick_power(self):
        """Random power whose reserve is below the cap (None if all are full)."""
        open_ = {p: w for p, w in self.weights("power_pick_weights").items()
                 if w > 0 and self.reserve[p] < self.config.power_reserve_cap}
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
        cand = [(c, r) for c, r in self.all_cells()
                if not self.is_wild(self.board[c][r]) and not self.is_weapon(self.board[c][r])
                and (self.in_bonus or not self.is_scatter(self.board[c][r]))]
        n = min(len(cand), random.randint(*self.weights("transform_count_range")))
        cells = random.sample(cand, n)
        for c, r in cells:
            self.board[c][r] = self.make_symbol("W")
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
        pool = {v: w for v, w in (table or self.weights("coin_value_weights")).items() if v >= min_value}
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
        for cell in [x for x in self.all_cells() if x in connected]:
            if random.random() >= chance:
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
            lit = list(dict.fromkeys((p["reel"], p["row"]) for w in wins for p in w["positions"])) + dark
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
            a2 = self.step_reserved_powers()
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
    def resolve_actions(self) -> None:
        self.actions = 0
        while not self.wincap_triggered and self.actions < self.config.max_actions_per_spin:
            self.run_cycle()
            if self.wincap_triggered:
                break
            if self.step_weapons():
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
    def open_chest(self, b) -> None:
        cfg = self.config
        tier = b["chest"]
        upgraded = None
        order = cfg.chest_order
        if random.random() < self.weights("chest_upgrade_chance") and order.index(tier) < len(order) - 1:
            upgraded = random.choice(order[order.index(tier) + 1:])
            tier = upgraded
        n = get_random_outcome(self.weights("chest_gift_count_weights")[tier])
        kinds = []
        for _ in range(n):
            if self.in_bonus and random.random() < self.weights("chest_gift_power_chance")[tier]:
                kinds.append("power")
            else:
                kinds.append("coin")
        if order.index(tier) >= order.index("vang") and "coin" not in kinds:
            kinds[0] = "coin"
        g = self.global_factor()
        gifts, got_power = [], False
        for kind in kinds:
            if kind == "power":
                p = self.pick_power()
                if p is not None:
                    self.reserve[p] += 1
                    got_power = True
                    gifts.append({"kind": "power", "power": p})
                    continue
                if not cfg.chest_power_overflow_to_coin:
                    continue
            v = self.draw_coin(0, min_tier=tier)
            paid = self.award(v * g)
            gifts.append({"kind": "coin", "value": v, "globalMult": g, "paid": paid})
            if self.wincap_triggered:
                break
        extra = 0
        if got_power and self.in_bonus and self.free_spins_left <= 0:
            self.free_spins_left += 1
            extra = 1
        b["chest_opened"] = True
        emit(self, "chestOpened", boss=b["id"], chest=b["chest"], upgradedTo=upgraded, gifts=gifts,
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
            v = self.draw_coin(min_coin)
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

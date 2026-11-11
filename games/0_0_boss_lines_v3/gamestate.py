"""Boss Lines v3 spin flow.

Bet modes (Proposal section 4):
  base / ante : stage-0 boss fight, Bonus by 3/4/5 Scatter at the end.
  feature     : 500x, randomly Heroic spin (stage-5 bosses, no Endless, no
                Scatter, >=5 Wild/weapon, every connected Wild fires an
                event) or Treasure hunt (no bosses, whole board is Treasure;
                its Scatters can trigger Bonus).
  buy3 / buy4 : forced >=3 / >=4 Scatter opening board.
"""

import random

from game_override import GameStateOverride
from game_config import ENDLESS
from game_events import emit, boss_state_event, pos, reveal
from src.calculations.statistics import get_random_outcome


class GameState(GameStateOverride):
    """Simulation entry points."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.floor_rerolls = 0  # Bonus re-runs under bonus_min_total_win (reject mode) for this book
        self.repeat = True
        while self.repeat:
            self.reset_book()
            cond = self.get_current_distribution_conditions()
            self.force_wincap = bool(cond["force_wincap"])
            if self.betmode == "feature":
                self.run_feature_spin(cond)
            else:
                self.run_base_spin(cond)
            self.evaluate_finalwin()
            self.check_repeat()
        self.imprint_wins()

    def run_freespin(self):
        raise NotImplementedError("Bonus runs from run_bonus(), not the SDK free-spin loop.")

    # ---------------------------------------------------------------------------
    def _guarantee_wild_or_weapon(self, minimum: int, weapons_only: bool = False) -> None:
        """Turn basic cells into Wild/weapons until the board has `minimum` of them.
        weapons_only: only weapons count and are placed (Super/Epic, designer 2026-10-07)."""
        def counts(s):
            return self.is_weapon(s) or (not weapons_only and self.is_wild(s))
        have = sum(1 for c, r in self.all_cells() if counts(self.board[c][r]))
        if have >= minimum:
            return
        cand = [(c, r) for c, r in self.all_cells() if self.is_basic(self.board[c][r])]
        random.shuffle(cand)
        for c, r in cand:
            if have >= minimum:
                break
            weights = {k: w for k, w in self.weights("guarantee_symbol_weights").items()
                       if (k == "W" and not weapons_only) or (k != "W" and self.weapon_allowed(k, c))}
            if not weights:  # no weapon may appear here (e.g. Arrow over a dead boss's column)
                continue
            self.board[c][r] = self.make_symbol(get_random_outcome(weights))
            have += 1

    def steer_weapons_to_lit(self) -> None:
        """weapon_lit_bias (Bonus only, designer 2026-10-28): each weapon of the opening board on an unlit cell
        swaps, with this chance, with a basic symbol on an already lit cell of the same column, so firing it
        lights no new cell. Same column = the column's symbols and the Arrow's boss stay the same."""
        if not self.in_bonus:
            return
        pw, pwild = self.weights("weapon_lit_bias"), self.weights("wild_lit_bias")  # wild_lit_bias: 2026-10-29
        if not (pw or pwild):
            return
        for c, r in self.all_cells():
            s = self.board[c][r]
            p = pw if self.is_weapon(s) else (pwild if self.is_wild(s) else 0)
            if not p or (c, r) in self.lit or random.random() >= p:
                continue
            spots = [rr for rr in range(5) if (c, rr) in self.lit and self.is_basic(self.board[c][rr])]
            if spots:
                rr = random.choice(spots)
                self.board[c][r], self.board[c][rr] = self.board[c][rr], self.board[c][r]

    def guarantee_multi_wilds(self, n: int) -> None:
        """Turn basic cells into Wilds carrying a >= 2x multiplier until the board has `n` of them."""
        have = sum(1 for c, r in self.all_cells() if self.is_wild(self.board[c][r]) and (self.board[c][r].prize or 1) >= 2)
        cand = [(c, r) for c, r in self.all_cells() if self.is_basic(self.board[c][r])]
        random.shuffle(cand)
        table = {k: w for k, w in self.weights("wild_multi_weights").items() if k >= 2} or {2: 1}
        for c, r in cand[:max(0, n - have)]:
            sym = self.make_symbol("W")
            sym.prize = get_random_outcome(table)
            self.board[c][r] = sym

    def guarantee_line(self) -> None:
        """Dead-spin guard "line": if the opening board connects nothing, the first 3 cells of a random payline
        (basic symbols or Wilds only) become one random allowed basic symbol."""
        if self.evaluate_lines():
            return
        lines = list(self.config.paylines.values())
        random.shuffle(lines)
        sym = random.choice(self.allowed_basic_symbols())
        for rows in lines:
            cells = [(c, rows[c]) for c in range(3)]
            if all(self.is_basic(self.board[c][r]) or self.is_wild(self.board[c][r]) for c, r in cells):
                for c, r in cells:
                    if self.is_basic(self.board[c][r]):
                        self.board[c][r] = self.make_symbol(sym)
                return

    def play_one_spin(self, reel, force_scatters=None, min_wild_weapon=0, min_weapons=0, sure_line=False,
                      min_multi_wilds=0) -> None:
        """Opening board -> steps (1)-(9) -> Treasure. (Hold and Spin removed by the designer 2026-10-07.)"""
        self.begin_spin()
        self.draw_board(reel, force_scatters)
        if min_wild_weapon:
            self._guarantee_wild_or_weapon(min_wild_weapon)
        if min_weapons:
            self._guarantee_wild_or_weapon(min_weapons, weapons_only=True)
        if sure_line:
            self.guarantee_line()
        if min_multi_wilds:
            self.guarantee_multi_wilds(min_multi_wilds)
        self.steer_weapons_to_lit()
        reveal(self)
        self.mark_wild_skins(list(self.all_cells()))
        self.resolve_actions()
        if not self.wincap_triggered:
            self.open_chests()
        loops = 0
        while (self.config.chest_power_immediate and self.config.action_order != "doc" and not self.wincap_triggered
               and loops < 20
               and any(v > 0 for v in self.reserve.values())):
            # designer 2026-10-30: chest powers act in the same spin (they may connect, kill and open more chests)
            loops += 1
            emit(self, "chestPowersResolve", reserve=dict(self.reserve))
            before = dict(self.reserve)
            self.resolve_actions()
            if not self.wincap_triggered:
                self.open_chests()
            if self.reserve == before:  # nothing could fire
                break
        if self.config.tumble_multi:
            self.settle_tumble()  # after the chests: their boss multis count for this spin
        if not self.wincap_triggered and self.stage_cleared:
            self.run_treasure(self.treasure_cells(), self.current_min_coin())
            if self.in_bonus and self.bonus_tier in self.config.lit_reset_after_treasure_tiers:
                self.lit = set()  # designer 2026-10-23: the next stage lights up from scratch
                emit(self, "litReset", cause="treasure")
        self.emit_spin_end()

    def play_dead_heroic_spin(self) -> None:
        """A Heroic spin built to pay 0 (heroic_dead_spin_chance), chosen uniformly among all natural
        combinations that do not connect: a natural HERO board (weapons re-drawn from the reel as basic
        symbols) plus the guaranteed Wilds on uniformly random cells, rejected and redrawn until no payline
        pays (~2.5% of tries are accepted, ~20 ms). With heroic_dead_symbol_tries > 1 a Wild placement is
        kept for that many symbol redraws first. Nothing connects, nothing fires, no boss is hit."""
        self.begin_spin()
        tries = self.config.heroic_dead_symbol_tries
        for _ in range(100000):
            wilds = None
            for _ in range(tries):  # >1: keep the Wild cells and redraw only the basic symbols around them
                self.draw_board("HERO")
                for c, r in self.all_cells():
                    while not self.is_basic(self.board[c][r]):
                        self.board[c][r] = self.draw_symbol_for(c, r)
                if wilds is None:
                    wilds = self.dead_heroic_wild_cells()
                for c, r in wilds:
                    self.board[c][r] = self.make_symbol("W")
                if not self.evaluate_lines():
                    break
            else:
                continue
            break
        else:
            raise RuntimeError("could not build a dead Heroic board")
        reveal(self)
        self.resolve_actions()
        self.emit_spin_end()

    def dead_heroic_wild_cells(self) -> list:
        """Cells for the guaranteed Wilds of a dead Heroic board: uniform, or weighted by column with
        heroic_dead_wild_col_weights (left-side Wilds connect far more often, so a dead board would
        otherwise show them mostly in columns 4-6)."""
        cells, n = list(self.all_cells()), self.config.heroic_min_wild_or_weapon
        col_w = self.config.heroic_dead_wild_col_weights
        if not col_w:
            return random.sample(cells, n)
        picked = []
        for _ in range(n):
            left = [x for x in cells if x not in picked]
            picked.append(random.choices(left, weights=[col_w[c] for c, _ in left])[0])
        return picked

    def win_levels(self, amount: float) -> list:
        return [name for bound, name in self.config.win_levels if amount >= bound]

    def emit_spin_end(self) -> None:
        spin_win = round(self.win_manager.spin_win, 2)
        emit(self, "spinEnd", spinWin=spin_win, totalWin=round(self.win_manager.running_bet_win, 2),
             stageCleared=self.stage_cleared, winLevels=self.win_levels(spin_win))

    def treasure_cells(self) -> set:
        """Lit cells (all cells in Epic), minus cells now holding a Scatter (Q28)."""
        cells = set(self.all_cells()) if self.bonus_tier == "epic" else set(self.lit)
        if self.config.treasure_skips_scatter_cells:
            cells = {x for x in cells if not self.is_scatter(self.board[x[0]][x[1]])}
        return cells

    def epic_opening_treasure(self) -> None:
        """Epic Bonus starts with a Treasure on every cell, as if stage 2 had
        just been cleared (N5: stage 2's coin minimum; Epic's no-Dong rule
        does not apply here)."""
        self.win_manager.reset_spin_win()
        self.begin_spin()
        self.draw_board(self.stage_reel())
        reveal(self)
        self.epic_opening = True
        emit(self, "epicOpeningTreasure")
        self.run_treasure(self.treasure_cells(), self.config.stage_min_coin[self.config.epic_opening_treasure_stage])
        self.epic_opening = False
        self.emit_spin_end()
        self.win_manager.update_gametype_wins(self.gametype)

    def scatter_tier(self):
        n = min(self.scatter_count(), self.config.max_scatters_on_board)
        return self.config.scatter_to_tier.get(n), n

    def maybe_enter_bonus(self, cond) -> None:
        tier, n = self.scatter_tier()
        if tier is None or self.wincap_triggered:
            return
        if cond["force_freegame"] or self.betmode == "feature":
            self.triggered_freegame = True
            self.record({"kind": n, "symbol": "scatter", "gametype": self.gametype})
            trigger_cells = {(c, r) for c, r in self.all_cells() if self.is_scatter(self.board[c][r])}
            self.run_bonus(tier, trigger_cells)
        else:
            self.accidental_bonus = True  # keep Bonus out of the non-freegame fences

    # ---------------------------------------------------------------------------
    def run_base_spin(self, cond) -> None:
        self.gametype = self.config.basegame_type
        reel = get_random_outcome(cond["reel_weights"][self.gametype])
        force = get_random_outcome(cond["scatter_triggers"]) if cond["force_freegame"] else None
        self.spawn_stage(0)
        self.play_one_spin(reel, force_scatters=force)
        self.win_manager.update_gametype_wins(self.gametype)
        self.maybe_enter_bonus(cond)

    def run_feature_spin(self, cond) -> None:
        self.gametype = self.config.basegame_type
        feature = "heroic" if random.random() < self.config.feature_heroic_chance else "treasure_hunt"
        if feature == "heroic":
            self.heroic = True
            self.no_scatter_spin = True
            emit(self, "featureSpin", feature="heroic")
            self.spawn_stage(5)
            if self.config.heroic_line_mult_weights:
                self.line_mult = get_random_outcome(self.config.heroic_line_mult_weights)
                emit(self, "heroicLineMult", mult=self.line_mult)
            if random.random() < self.config.heroic_dead_spin_chance:
                self.play_dead_heroic_spin()
            else:
                self.play_one_spin("HERO", min_wild_weapon=self.config.heroic_min_wild_or_weapon)
        else:
            self.treasure_hunt = True
            emit(self, "featureSpin", feature="treasureHunt")
            self.spawn_stage(None)
            self.begin_spin()
            self.draw_board("BR0")
            reveal(self)
            self.run_treasure(self.all_cells(), self.current_min_coin())
            self.emit_spin_end()
        self.win_manager.update_gametype_wins(self.gametype)
        if self.treasure_hunt:
            self.maybe_enter_bonus(cond)
        cost = next(bm.get_cost() for bm in self.config.bet_modes if bm.get_name() == "feature")
        if self.win_manager.running_bet_win > self.config.feature_big_win_ratio * cost:
            emit(self, "featureBigWin", feature=feature, win=round(self.win_manager.running_bet_win, 2),
                 threshold=round(self.config.feature_big_win_ratio * cost, 2))
        self.record({"feature": feature})  # optimizer fences: Heroic / Treasure hunt means exact
        if self.wincap_triggered:
            self.record({"maxwin_feature": feature})

    def bonus_min_win_topup(self, tier: str) -> None:
        """Designer 2026-10-08: a tier's Bonus pays at least bonus_min_total_win[tier]
        (Epic 600x). The shortfall is paid at Bonus end as its own event."""
        floor = self.config.bonus_min_total_win.get(tier, 0)
        won = self.win_manager.freegame_wins
        if not floor or self.wincap_triggered or won >= floor:
            return
        limit = self.config.bonus_min_total_win_rerolls
        if (self.config.bonus_min_total_win_mode == "reject" and (limit is None or getattr(self, "floor_rerolls", 0) < limit)
                and random.random() < self.config.bonus_min_total_win_reroll_chance):
            self.bonus_below_floor = True  # thrown away and simulated again (check_repeat)
            self.floor_rerolls = getattr(self, "floor_rerolls", 0) + 1
            return
        self.win_manager.reset_spin_win()
        paid = self.award(floor - won)
        emit(self, "bonusMinWin", tier=tier, floor=floor, topUp=round(paid, 2))
        self.win_manager.update_gametype_wins(self.gametype)

    def stage_reel(self) -> str:
        """Reel for the current Bonus stage: the tier's own reels if it has them."""
        return self.config.tier_stage_reel.get(self.bonus_tier, {}).get(self.stage) or self.config.bonus_stage_reel[self.stage]

    # ---------------------------------------------------------------------------
    def run_bonus(self, tier: str, trigger_cells=()) -> None:
        cfg = self.config
        self.in_bonus = True
        self.bonus_tier = tier
        self.heroic = False
        self.treasure_hunt = False
        self.no_scatter_spin = False
        self.gametype = cfg.freegame_type
        if not cfg.base_global_into_bonus:
            self.global_mult = 0
        if cfg.tumble_multi:
            self.reset_tumble("bonus")
        self.reserve = {p: 0 for p in cfg.power_names}
        # Q25: lit cells reset, except the Scatter cells that triggered the Bonus
        self.lit = set(self.all_cells()) if tier in cfg.full_lit_tiers else set(trigger_cells)
        self.last_endless_hp = None
        spec = cfg.bonus_tiers[tier]
        self.free_spins_left = spec["spins"]
        emit(self, "bonusStart", tier=tier, freeSpins=self.free_spins_left, stage=spec["start_stage"],
             triggerCells=[pos(self, c, r) for c, r in sorted(trigger_cells)])
        if self.lit:
            emit(self, "litCells", cells=[pos(self, c, r) for c, r in sorted(self.lit)])
        self.spawn_stage(spec["start_stage"])
        if tier == "epic" and cfg.epic_opening_treasure_on:
            self.epic_opening_treasure()
        big = cfg.bonus_big_spins.get(tier)
        burst_left, bursts = 0, 0
        rescue = cfg.bonus_rescue_scatter.get(tier)
        rescues = 0
        spin_no = 0
        dead_streak = 0  # free spins in a row that paid nothing and dealt no damage (dead_spin_guard_after)
        while self.free_spins_left > 0 and not self.wincap_triggered:
            spin_no += 1
            self.free_spins_left -= 1
            self.win_manager.reset_spin_win()
            if self.stage_cleared:
                nxt = ENDLESS if self.stage in (5, ENDLESS) else self.stage + 1
                self.spawn_stage(nxt)
            emit(self, "freeSpinStart", spin=spin_no, freeSpinsLeft=self.free_spins_left,
                 stage=self.stage_label(), globalMult=self.global_factor())
            n_weapons = cfg.bonus_min_weapons.get(tier, 0)
            chance = cfg.bonus_min_weapons_chance.get(tier)
            if n_weapons and chance is not None and random.random() >= chance:
                n_weapons -= 1  # this spin guarantees one weapon fewer (designer 2026-10-21: fewer weapons)
            guard = self.weights("dead_spin_guard_after")
            sure_line = False
            if guard and dead_streak >= guard:
                mode = self.weights("dead_spin_guard_mode")
                if mode == "either":
                    mode = "line" if random.random() < 0.5 else "weapon1"
                if mode == "line":
                    sure_line = True
                else:
                    n_weapons = max(n_weapons, 1 if mode == "weapon1" else self.weights("dead_spin_guard_weapons"))
                emit(self, "deadSpinGuard", streak=dead_streak, mode=mode, weapons=n_weapons)
            reel, min_mw = self.stage_reel(), cfg.bonus_min_multi_wilds.get(tier, 0)
            if (big and burst_left == 0 and bursts < big.get("max_bursts", 1) and spin_no >= big.get("from_spin", 1)
                    and self.win_manager.freegame_wins < big["pace"] * spin_no / spec["spins"]
                    and random.random() < big.get("chance", 1.0)):
                burst_left = get_random_outcome({int(k): w for k, w in big["burst_weights"].items()})
                bursts += 1
            if burst_left > 0:
                burst_left -= 1
                kind = get_random_outcome(big["type_weights"])
                if kind == "wilds":
                    min_mw = max(min_mw, big.get("min_multi_wilds", 3))
                elif kind == "weapons":
                    n_weapons = max(n_weapons, big.get("min_weapons", 2))
                else:  # "line"
                    sure_line = True
                    min_mw = max(min_mw, 1)
                emit(self, "bigSpin", spin=spin_no, boost=kind, burstLeft=burst_left)
            force_sc = None
            if (rescue and self.free_spins_left <= rescue["spins_left"] and rescues < rescue["max"]
                    and self.win_manager.freegame_wins < rescue["below"]):
                force_sc = 1
                rescues += 1
                emit(self, "rescueScatter", spin=spin_no, won=round(self.win_manager.freegame_wins, 2))
            hp_before = sum(b["hp"] for b in self.bosses)
            self.play_one_spin(reel, force_scatters=force_sc, min_weapons=n_weapons, sure_line=sure_line,
                               min_multi_wilds=min_mw)
            dead = self.win_manager.spin_win <= 0 and sum(b["hp"] for b in self.bosses) == hp_before and not self.stage_cleared
            dead_streak = dead_streak + 1 if dead else 0
            self.win_manager.update_gametype_wins(self.gametype)
        self.bonus_min_win_topup(tier)
        # optimizer fences per tier (designer 2026-10-12: tier means exact in the published tables)
        self.record({"bonus_tier": tier})
        if self.wincap_triggered:
            self.record({"maxwin_tier": tier})
        emit(self, "bonusEnd", tier=tier, spins=spin_no,
             totalWin=round(self.win_manager.running_bet_win, 2))
        if not self.wincap_triggered:
            emit(self, "totalWin", amount=round(self.win_manager.freegame_wins, 2),
                 winLevels=self.win_levels(self.win_manager.freegame_wins))
        boss_state_event(self)
        self.in_bonus = False

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
from game_events import emit, boss_state_event
from src.events.events import reveal_event
from src.calculations.statistics import get_random_outcome


class GameState(GameStateOverride):
    """Simulation entry points."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
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
            weights = {k: w for k, w in self.config.guarantee_symbol_weights.items()
                       if (k == "W" and not weapons_only) or (k != "W" and self.weapon_allowed(k, c))}
            if not weights:  # no weapon may appear here (e.g. Arrow over a dead boss's column)
                continue
            self.board[c][r] = self.make_symbol(get_random_outcome(weights))
            have += 1

    def play_one_spin(self, reel, force_scatters=None, min_wild_weapon=0, min_weapons=0) -> None:
        """Opening board -> steps (1)-(9) -> Treasure. (Hold and Spin removed by the designer 2026-10-07.)"""
        self.begin_spin()
        self.draw_board(reel, force_scatters)
        if min_wild_weapon:
            self._guarantee_wild_or_weapon(min_wild_weapon)
        if min_weapons:
            self._guarantee_wild_or_weapon(min_weapons, weapons_only=True)
        reveal_event(self)
        self.resolve_actions()
        if not self.wincap_triggered:
            self.open_chests()
        if not self.wincap_triggered and self.stage_cleared:
            self.run_treasure(self.treasure_cells(), self.current_min_coin())
        self.emit_spin_end()

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
        self.draw_board(self.config.bonus_stage_reel[self.stage])
        reveal_event(self)
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
        if random.random() < self.config.feature_heroic_chance:
            self.heroic = True
            self.no_scatter_spin = True
            emit(self, "featureSpin", feature="heroic")
            self.spawn_stage(5)
            self.play_one_spin("HERO", min_wild_weapon=self.config.heroic_min_wild_or_weapon)
        else:
            self.treasure_hunt = True
            emit(self, "featureSpin", feature="treasureHunt")
            self.spawn_stage(None)
            self.begin_spin()
            self.draw_board("BR0")
            reveal_event(self)
            self.run_treasure(self.all_cells(), self.current_min_coin())
            self.emit_spin_end()
        self.win_manager.update_gametype_wins(self.gametype)
        if self.treasure_hunt:
            self.maybe_enter_bonus(cond)

    def bonus_min_win_topup(self, tier: str) -> None:
        """Designer 2026-10-08: a tier's Bonus pays at least bonus_min_total_win[tier]
        (Epic 600x). The shortfall is paid at Bonus end as its own event."""
        floor = self.config.bonus_min_total_win.get(tier, 0)
        won = self.win_manager.freegame_wins
        if not floor or self.wincap_triggered or won >= floor:
            return
        self.win_manager.reset_spin_win()
        paid = self.award(floor - won)
        emit(self, "bonusMinWin", tier=tier, floor=floor, topUp=round(paid, 2))
        self.win_manager.update_gametype_wins(self.gametype)

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
        self.reserve = {p: 0 for p in cfg.power_names}
        # Q25: lit cells reset, except the Scatter cells that triggered the Bonus
        self.lit = set(self.all_cells()) if tier == "epic" else set(trigger_cells)
        self.last_endless_hp = None
        spec = cfg.bonus_tiers[tier]
        self.free_spins_left = spec["spins"]
        emit(self, "bonusStart", tier=tier, freeSpins=self.free_spins_left, stage=spec["start_stage"])
        self.spawn_stage(spec["start_stage"])
        if tier == "epic":
            self.epic_opening_treasure()
        spin_no = 0
        while self.free_spins_left > 0 and not self.wincap_triggered:
            spin_no += 1
            self.free_spins_left -= 1
            self.win_manager.reset_spin_win()
            if self.stage_cleared:
                nxt = ENDLESS if self.stage in (5, ENDLESS) else self.stage + 1
                self.spawn_stage(nxt)
            emit(self, "freeSpinStart", spin=spin_no, freeSpinsLeft=self.free_spins_left,
                 stage=self.stage_label(), globalMult=self.global_factor())
            self.play_one_spin(cfg.bonus_stage_reel[self.stage],
                               min_weapons=cfg.bonus_min_weapons.get(tier, 0))
            self.win_manager.update_gametype_wins(self.gametype)
        self.bonus_min_win_topup(tier)
        emit(self, "bonusEnd", tier=tier, spins=spin_no,
             totalWin=round(self.win_manager.running_bet_win, 2))
        if not self.wincap_triggered:
            emit(self, "totalWin", amount=round(self.win_manager.freegame_wins, 2),
                 winLevels=self.win_levels(self.win_manager.freegame_wins))
        boss_state_event(self)
        self.in_bonus = False

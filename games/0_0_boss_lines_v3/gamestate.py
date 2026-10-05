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
    def _guarantee_wild_or_weapon(self, minimum: int) -> None:
        have = sum(1 for c, r in self.all_cells()
                   if self.is_wild(self.board[c][r]) or self.is_weapon(self.board[c][r]))
        if have >= minimum:
            return
        cand = [(c, r) for c, r in self.all_cells() if self.is_basic(self.board[c][r])]
        for c, r in random.sample(cand, min(len(cand), minimum - have)):
            name = random.choice(["W"] + self.config.weapon_symbols)
            self.board[c][r] = self.make_symbol(name)

    def play_one_spin(self, reel, force_scatters=None, min_wild_weapon=0, epic=False) -> None:
        """Opening board -> Hold and Spin -> steps (1)-(9) -> Treasure."""
        self.begin_spin()
        self.draw_board(reel, force_scatters)
        if min_wild_weapon:
            self._guarantee_wild_or_weapon(min_wild_weapon)
        if epic:  # the opening board must connect (checked AFTER the guarantee)
            for _ in range(200):
                if self.evaluate_lines():
                    break
                self.draw_board(reel)
                if min_wild_weapon:
                    self._guarantee_wild_or_weapon(min_wild_weapon)
            else:
                self.note_cap("epic_redraw")
                self._force_connection()
        reveal_event(self)
        if epic:
            self.hold_and_spin(force=True)
        elif not self.heroic or self.config.hold_spin_in_heroic:
            self.hold_and_spin()
        self.resolve_actions()
        if not self.wincap_triggered:
            self.open_chests()
        if not self.wincap_triggered and self.stage_cleared:
            self.run_treasure(self.treasure_cells(), self.current_min_coin())
            if self.in_bonus and self.bonus_tier != "epic" and self.config.lit_reset_after_treasure:
                self.lit = set()
        emit(self, "spinEnd", spinWin=round(self.win_manager.spin_win, 2),
             totalWin=round(self.win_manager.running_bet_win, 2), stageCleared=self.stage_cleared)

    def treasure_cells(self) -> set:
        """Lit cells (all cells in Epic), minus cells now holding a Scatter (Q28)."""
        cells = set(self.all_cells()) if self.bonus_tier == "epic" else set(self.lit)
        if self.config.treasure_skips_scatter_cells:
            cells = {x for x in cells if not self.is_scatter(self.board[x[0]][x[1]])}
        return cells

    def _force_connection(self) -> None:
        """Fallback: make line 1 open with three of one allowed symbol."""
        name = random.choice(self.allowed_basic_symbols())
        for c in range(3):
            r = self.config.paylines[1][c]
            if not (self.is_wild(self.board[c][r]) or self.is_weapon(self.board[c][r])):
                self.board[c][r] = self.make_symbol(name)

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
            self.run_bonus(tier)
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
            emit(self, "spinEnd", spinWin=round(self.win_manager.spin_win, 2),
                 totalWin=round(self.win_manager.running_bet_win, 2))
        self.win_manager.update_gametype_wins(self.gametype)
        if self.treasure_hunt:
            self.maybe_enter_bonus(cond)

    # ---------------------------------------------------------------------------
    def run_bonus(self, tier: str) -> None:
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
        self.lit = set()
        self.last_endless_hp = None
        spec = cfg.bonus_tiers[tier]
        self.free_spins_left = spec["spins"]
        emit(self, "bonusStart", tier=tier, freeSpins=self.free_spins_left, stage=spec["start_stage"])
        self.spawn_stage(spec["start_stage"])
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
                               min_wild_weapon=cfg.super_min_wild_or_weapon if tier in ("super", "epic") else 0,
                               epic=(tier == "epic"))
            self.win_manager.update_gametype_wins(self.gametype)
        emit(self, "bonusEnd", tier=tier, spins=spin_no,
             totalWin=round(self.win_manager.running_bet_win, 2))
        boss_state_event(self)
        self.in_bonus = False

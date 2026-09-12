"""Core per-simulation resolve loop.

Combines src/calculations/lines.py's payline evaluation with
src/calculations/tumble.py's Tumble.tumble_board() physical
remove-and-refill (see game_calculations.evaluate_and_explode for how the
two are bridged via the whole-board explode + boss damage rule). Phase 2
adds the Power system: immediate-group powers (Wild Multi/Global Multi/
Maxwin) activate inline as part of evaluate_and_explode's own pass; FIFO-
group powers (Extra Wild/Extra Power/Big Symbol/Mystery/Alter) are collected
into self.power_queue during evaluate_and_explode and popped/activated ONE
AT A TIME between a tumble and the next payline re-evaluation (see
activate_next_power below) - per spec: "evaluate -> explode/damage -> tumble
-> pop-and-activate-one-fifo-power-if-any -> re-evaluate", repeated until a
full pass produces no win AND the queue is empty ("static state").

Phase 3 adds: a running Scatter tally across this whole cascade (see
game_bonus.accumulate_scatter_columns, called after the initial reveal and
after every tumble below), and - once the cascade above reaches static
state - a scatter-triggered 3-tier Bonus session (see
game_bonus.run_bonus_session) for books generated under the dedicated
"freegame" criteria/Distribution (see game_config.py). Any OTHER criteria
("wincap"/"0"/"basegame") that happens to accidentally reach 3+ Scatters
instead just forces a repeat (fresh board, same book slot) rather than
running Bonus - keeping those 3 fences base-spin-only, so "freegame" is the
ONLY fence whose books ever contain a Bonus session (matches
games/0_0_boss_lines_library_backup_.../configs/math_config.json's old
"freegame fence inside base bet mode" convention - see readme.txt).

Phase 4 adds 5 feature-buy bet modes (Ante/Ultimate Power/God Mode/buy-3+/
buy-4+-scatter) - all purely additive branches gated on `self.config.
feature_spin_guarantee_power_modes` / `power_drain_all_modes` (both empty
except for the 2 named modes) and an optional `scatter_force_floor` key
(absent from every "base"/"ante" conditions dict) so this SAME run_spin
executes byte-for-byte identically for "base" as it always did - see
game_config.py's Phase 4 section / readme.txt for the full design."""

import warnings

from game_override import GameStateOverride
from src.events.events import reveal_event
from src.calculations.statistics import get_random_outcome
from game_events import scatter_tally_event


class GameState(GameStateOverride):
    """Core function handling simulation results."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            # Reset simulation variables (including a fresh stage-1 boss
            # battle + Power system + Bonus/Scatter-tally state - see
            # game_override.reset_book) and draw a new board.
            self.reset_book()
            # Phase 3 bug fix (see game_config.py's freegame_condition
            # comment / readme.txt): the dedicated "freegame" fence forces
            # its initial reveal to land exactly one of {3,4,5} Scatters via
            # the SDK's own Board.force_special_board mechanism (same one
            # the "wincap" fence already uses), rather than drawing an
            # ordinary board and rejection-sampling on a natural (and, for
            # 4/5 Scatters specifically, vanishingly rare) trigger. Every
            # OTHER criteria still draws a completely ordinary board and
            # relies on check_repeat's existing "accidental trigger -> repeat"
            # fallback if it happens to land 3+ anyway.
            distribution_conditions = self.get_current_distribution_conditions()
            if distribution_conditions["force_freegame"]:
                # Phase 4 v2: an OPTIONAL per-fence "scatter_count_weights"
                # key (absent from base/ante's own freegame_condition dicts,
                # so `.get()` returns None and this takes the exact same
                # branch as before for those) lets buy3/buy4 supply their
                # OWN exact-count weight table (92/7.6/0.4 for buy3, 95/5 for
                # buy4 - see game_config.py's buy3_scatter_count_weights/
                # buy4_scatter_count_weights) instead of base/ante's shared
                # self.config.freegame_trigger_count_weights. Both paths
                # funnel through the SAME exact-count force_special_board
                # call - see game_config.py's Phase 4 v2 comment for why the
                # old floor-and-overshoot mechanism (force_min_scatter_board)
                # was replaced rather than reused: an EXACT required tier
                # composition cannot coexist with "let it overshoot
                # naturally".
                count_weights = distribution_conditions.get("scatter_count_weights")
                if count_weights is None:
                    count_weights = self.config.freegame_trigger_count_weights
                target_count = get_random_outcome(count_weights)
                self.force_special_board("scatter", target_count)
            else:
                self.create_board_reelstrips()
            # Phase 4 (Ultimate Power/God Mode): guarantee >=N Power symbols
            # on this spin's very first reveal - a no-op for every other bet
            # mode (self.config.feature_spin_guarantee_power_modes is only
            # ever populated with "ultimatepower"/"godmode").
            if self.get_current_betmode().get_name() in self.config.feature_spin_guarantee_power_modes:
                self.guarantee_min_power_landed(self.config.feature_spin_min_power_landed)
            self.accumulate_scatter_columns()
            reveal_event(self)

            self.evaluate_and_explode()
            self.emit_tumble_win_events()
            self.emit_pass_extra_events()

            passes = 1
            while (
                (self.win_data["totalWin"] > 0 or self.power_queue)
                and not self.wincap_triggered
                and passes < self.config.max_resolve_passes
            ):
                self.tumble_game_board()
                self.accumulate_scatter_columns()
                # One FIFO power (if any) activates between this tumble and
                # the next payline evaluation - it may inject/replace board
                # symbols, which the very next evaluate_and_explode call
                # below re-evaluates from scratch, exactly like a tumble
                # refill would. Every FIFO handler mutates the board, so the
                # queue is guaranteed to drain in finite steps (bounded
                # further by max_resolve_passes as a structural safety cap,
                # same role it already played in Phase 1).
                # Phase 4 (God Mode): drain the WHOLE FIFO queue in one step
                # instead of one-at-a-time - a no-op check for every other
                # bet mode (self.config.power_drain_all_modes only ever
                # contains "godmode").
                if self.get_current_betmode().get_name() in self.config.power_drain_all_modes:
                    self.activate_all_queued_powers()
                else:
                    self.activate_next_power()
                self.evaluate_and_explode()
                self.emit_tumble_win_events()
                self.emit_pass_extra_events()
                passes += 1
            if passes >= self.config.max_resolve_passes:
                warnings.warn(
                    f"\nHit max_resolve_passes ({self.config.max_resolve_passes}) "
                    f"on sim {sim}, criteria {self.criteria} - forcing spin end.\n"
                )

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.criteria != "wincap":
                assert self.win_manager.running_bet_win < self.config.wincap, (
                    "Non-wincap criteria produced a wincap-magnitude win - "
                    "the award_win() headroom guard should make this impossible."
                )

            # --- Phase 3: Scatter/Bonus trigger check --------------------
            scatter_tally_event(self, self.scatter_columns)
            tier = self.resolve_bonus_tier()
            if tier is not None:
                if self.criteria == "freegame":
                    self.triggered_freegame = True
                    self.record({"kind": len(self.scatter_columns), "symbol": "scatter", "gametype": self.gametype})
                    self.run_bonus_session(tier)
                else:
                    # Accidental 3+ Scatter trigger outside the dedicated
                    # "freegame" fence - discard this whole book attempt and
                    # retry with a fresh board rather than let Bonus leak
                    # into "wincap"/"0"/"basegame"'s RTP budget.
                    self.repeat = True

            self.evaluate_finalwin()
            self.check_repeat()

        self.imprint_wins()

    def run_freespin(self):
        """The generic fixed-fs-count freegame loop (`while self.fs <
        self.tot_fs`) does not apply to this game's Bonus - it runs until
        Player HP is depleted instead (see game_bonus.run_bonus_session,
        called directly from run_spin above). Required by the abstract base
        class; never invoked."""
        raise NotImplementedError("Boss Lines' Bonus is a Player-HP loop (game_bonus.run_bonus_session), not a "
                                   "fixed free-spin count - run_freespin is intentionally unused.")

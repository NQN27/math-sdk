import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager
import normal_3param_matrix_test as m

# Correction: user wants HP + the RAW DEAD-SPIN RATE tested together, not
# HP + damage. Dead-spin rate = probability the initial reveal (before any
# cascade) has zero wins at all. This is mechanically different from
# chain-break severity (which only trims cascades AFTER a spin already won)
# and from damage (combat-kill-speed multiplier) - forcing MORE dead spins
# means fewer spins deal ANY damage to bosses, slowing stage progression,
# which should pull mean AND median down together (not just mean like
# damage does), while every forced-dead spin still costs the player HP via
# the unconditional counter-attack (game_bonus.py:405-407) - so whether
# total spin count actually goes UP or DOWN under this lever, combined
# with more HP, is a genuine unknown to be measured, not assumed.
#
# NOTE: this forces the outcome at the simulation level (probability
# override), NOT by editing real reel-strip files - a prior attempt to
# raise dead-spin rate via real reel-density edits ("col0 run-injection")
# made things worse and was abandoned. This is a cheap way to test the
# HYPOTHESIS first before ever touching real reels again.

_P_FORCE_DEAD = 0.0


def patched_run_one_bonus_spin_deadrate(self, both_ways):
    self.win_manager.reset_spin_win()
    self.pass_exploded_positions = []
    self.create_board_reelstrips()
    self.enforce_removed_symbols()
    self.evaluate_and_explode(both_ways=both_ways)
    if _P_FORCE_DEAD > 0 and self.win_data.get("totalWin", 0) > 0 and random.random() < _P_FORCE_DEAD:
        # Force this spin's initial reveal to whiff: zero out the win data
        # so downstream code treats it exactly like a natural dead spin
        # (no cascade, no boss damage this spin) - still runs through the
        # normal counter-attack step in run_bonus_session afterward.
        self.win_data["totalWin"] = 0
        self.win_data["wins"] = []
    self.emit_tumble_win_events()
    self.emit_pass_extra_events()

    curve = getattr(self, "_diag_active_curve", m.CURVE_LOOSE)
    passes = 1
    forced_breaks = 0
    while not self.wincap_triggered and passes < self.config.max_resolve_passes:
        has_win = self.win_data["totalWin"] > 0
        has_fifo = bool(self.power_queue)
        if has_win and self.bonus_tier == "normal":
            p = m.p_stop(curve, self.stage, passes)
            if p > 0 and random.random() < p:
                forced_breaks += 1
                break
        if has_win or has_fifo:
            self.tumble_game_board()
            self.activate_next_power()
            self.evaluate_and_explode(both_ways=both_ways)
            self.emit_tumble_win_events()
            self.emit_pass_extra_events()
            passes += 1
            continue
        if self._board_has_elixir_or_booster():
            self._activate_elixir_booster()
            self.tumble_game_board()
            self.evaluate_and_explode(both_ways=both_ways)
            self.emit_tumble_win_events()
            self.emit_pass_extra_events()
            passes += 1
            continue
        break
    if passes >= self.config.max_resolve_passes:
        if self.power_queue:
            self.power_queue = []

    self._diag_forced_breaks = getattr(self, "_diag_forced_breaks", 0) + forced_breaks
    self._diag_spin_count = getattr(self, "_diag_spin_count", 0) + 1
    self.set_end_tumble_event()
    self.win_manager.update_gametype_wins(self.gametype)


gamestate_mod.GameState.run_one_bonus_spin = patched_run_one_bonus_spin_deadrate
gamestate_mod.GameState.run_bonus_session = m.patched_run_bonus_session


def measure(n, seed_offset, tag, hp_choices, none_pct, p_force_dead):
    global _P_FORCE_DEAD
    _P_FORCE_DEAD = p_force_dead
    m._CB_MODE = "sweep4"
    rest = (100 - none_pct) / 3
    m._SWEEP4_WEIGHTS = [rest, rest, rest, none_pct]

    config = game_config_mod.GameConfig()
    config.bonus_safety_cap_spins = 150
    config.bonus_player_hp_choices = dict(config.bonus_player_hp_choices)
    config.bonus_player_hp_choices["normal"] = hp_choices
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals = []
    spins = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs._diag_spin_count = 0
            gs.run_bonus_session("normal")
            totals.append(gs.win_manager.running_bet_win)
            spins.append(gs._diag_spin_count)

    mean = sum(totals) / n
    median = statistics.median(totals)
    stdev = statistics.pstdev(totals)
    ratio = median / mean * 100 if mean > 0 else 0
    zero = 100 * sum(1 for t in totals if t == 0) / n
    mean_spins = sum(spins) / n
    median_spins = statistics.median(spins)
    print(
        f"[{tag}] hp={hp_choices[0]}.. none={none_pct}% p_dead={p_force_dead:.2f} (n={n}): "
        f"mean={mean:.2f}x median={median:.2f}x ratio={ratio:.1f}% CV={stdev/mean:.2f} "
        f"zero={zero:.2f}% | mean_spins={mean_spins:.2f} median_spins={median_spins}"
    )


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    HP200 = [200, 200, 200, 200, 200]

    # Reference target (n=50000, from CONFIRMED_CANDIDATES.md):
    # mean=80.14x median=52.80x ratio=65.9% CV=1.32 zero=0.78%
    for none_pct in (25, 40):
        for p_dead in (0.0, 0.15, 0.30, 0.45, 0.60):
            measure(n, 940000, f"hp200_none{none_pct}_pdead{int(p_dead*100)}", HP200, none_pct, p_dead)

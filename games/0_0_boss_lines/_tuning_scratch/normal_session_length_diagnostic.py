import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# User's concern: at HP75, a couple of unlucky dead spins in a row can end
# the WHOLE bonus session in just 2-3 internal spins - regardless of what
# the payout math says, that's a bad player experience (a "bonus round"
# that's over almost as soon as it started). Measure session length
# (spin_count, i.e. total internal Bonus spins per session) directly,
# rather than inferring it from payout stats, to check how common "very
# short" sessions actually are at HP75 vs a much larger HP pool.

def measure_session_lengths(n, seed_offset, hp_choices):
    config = game_config_mod.GameConfig()
    config.bonus_safety_cap_spins = 150
    config.bonus_player_hp_choices = dict(config.bonus_player_hp_choices)
    config.bonus_player_hp_choices["normal"] = hp_choices
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    lengths = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session("normal")
            # run_bonus_session tracks spin_count internally but doesn't
            # expose it - reconstruct from event log length isn't reliable
            # either, so patch it in directly (see patched version below).
    return lengths


_original_run_bonus_session = gamestate_mod.GameState.run_bonus_session


def patched_run_bonus_session(self, tier):
    self._diag_spin_count = 0
    result = _original_run_bonus_session(self, tier)
    return result


_original_run_one_bonus_spin = gamestate_mod.GameState.run_one_bonus_spin


def patched_run_one_bonus_spin(self, both_ways):
    self._diag_spin_count = getattr(self, "_diag_spin_count", 0) + 1
    return _original_run_one_bonus_spin(self, both_ways)


gamestate_mod.GameState.run_bonus_session = patched_run_bonus_session
gamestate_mod.GameState.run_one_bonus_spin = patched_run_one_bonus_spin


def measure(n, seed_offset, tag, hp_choices):
    config = game_config_mod.GameConfig()
    config.bonus_safety_cap_spins = 150
    config.bonus_player_hp_choices = dict(config.bonus_player_hp_choices)
    config.bonus_player_hp_choices["normal"] = hp_choices
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    lengths = []
    payouts = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session("normal")
            lengths.append(gs._diag_spin_count)
            payouts.append(gs.win_manager.running_bet_win)

    le2 = 100 * sum(1 for l in lengths if l <= 2) / n
    le3 = 100 * sum(1 for l in lengths if l <= 3) / n
    le5 = 100 * sum(1 for l in lengths if l <= 5) / n
    mean_len = sum(lengths) / n
    median_len = statistics.median(lengths)
    print(
        f"[{tag}] hp={hp_choices} (n={n}): spins<=2={le2:.2f}% spins<=3={le3:.2f}% "
        f"spins<=5={le5:.2f}% mean_spins={mean_len:.2f} median_spins={median_len} "
        f"mean_payout={sum(payouts)/n:.2f}x"
    )


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000

    measure(n, 900001, "hp75_current_candidate", [75, 75, 100, 100, 100])
    measure(n, 900002, "hp200_flat", [200, 200, 200, 200, 200])
    measure(n, 900003, "hp_current_prod", [50, 50, 50, 100, 100])

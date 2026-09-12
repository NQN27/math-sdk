"""Diagnose WHERE the ~25% mean drop (cascade->in-place tumble) comes from:
line-pay (cascade chain-compounding) vs reward-drop (boss-kill rate), and
how much chain depth (tumbles/spin) actually changed.
"""
import sys, random, statistics, warnings, time
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_executables as game_executables_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

_orig_award_win = gamestate_mod.GameState.award_win
_tag = {"in_reward_drop": False}
_totals = {"line": 0.0, "reward": 0.0}


def tagged_award_win(self, amount):
    result = _orig_award_win(self, amount)
    if _tag["in_reward_drop"]:
        _totals["reward"] += amount
        _tag["in_reward_drop"] = False
    else:
        _totals["line"] += amount
    return result


gamestate_mod.GameState.award_win = tagged_award_win

_orig_roll_reward_drop = gamestate_mod.GameState.roll_reward_drop


def tagged_roll_reward_drop(self, is_last_of_stage, stage):
    _tag["in_reward_drop"] = True
    return _orig_roll_reward_drop(self, is_last_of_stage, stage)


gamestate_mod.GameState.roll_reward_drop = tagged_roll_reward_drop

_orig_tumble = game_executables_mod.GameExecutables.tumble_game_board
_tumble_count = {"n": 0}


def counting_tumble(self):
    _tumble_count["n"] += 1
    return _orig_tumble(self)


game_executables_mod.GameExecutables.tumble_game_board = counting_tumble


def measure(n, seed_offset, tag, tier, inplace):
    config = game_config_mod.GameConfig()
    config.use_inplace_tumble = inplace
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals, line_totals, reward_totals, spin_counts, tumble_counts = [], [], [], [], []
    t0 = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            _totals["line"] = 0.0
            _totals["reward"] = 0.0
            _tag["in_reward_drop"] = False
            _tumble_count["n"] = 0
            gs.run_bonus_session(tier)
            totals.append(gs.win_manager.running_bet_win)
            line_totals.append(_totals["line"])
            reward_totals.append(_totals["reward"])
            spin_counts.append(gs.bonus_spin_count)
            tumble_counts.append(_tumble_count["n"])

    mean = sum(totals) / n
    median = statistics.median(totals)
    mean_line = sum(line_totals) / n
    mean_reward = sum(reward_totals) / n
    mean_spins = sum(spin_counts) / n
    mean_tumbles = sum(tumble_counts) / n
    print(f"\n=== {tag} inplace={inplace} (n={n}, {time.time()-t0:.1f}s) ===")
    print(f"mean={mean:.2f}x median={median:.2f}x ({100*median/mean:.1f}%)")
    print(f"line-pay={mean_line:.2f}x ({100*mean_line/mean:.1f}%) reward-drop={mean_reward:.2f}x ({100*mean_reward/mean:.1f}%)")
    print(f"avg spins/session={mean_spins:.2f}  avg tumbles/session={mean_tumbles:.2f}  avg tumbles/spin={mean_tumbles/mean_spins:.3f}")
    return dict(mean=mean, mean_line=mean_line, mean_reward=mean_reward, mean_spins=mean_spins, mean_tumbles=mean_tumbles)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    measure(n, 960000, "CASCADE", "super", inplace=False)
    measure(n, 960000, "INPLACE", "super", inplace=True)

"""Normal Bonus: cascade vs in-place tumble comparison on the CURRENT
production reels/config (no reel/reward changes yet) - stage-death%,
line-pay/reward-drop split, full payout bucket histogram, mean/median.
First step of the in-place re-tune (Normal Bonus first, per game designer).
"""
import sys, random, statistics, warnings, time
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
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

BUCKETS = [(0, 5), (5, 10), (10, 20), (20, 40), (40, 80), (80, 150), (150, 250), (250, 400), (400, 10**9)]


def measure(n, seed_offset, tag, inplace, config_overrides=None):
    config = game_config_mod.GameConfig()
    config.use_inplace_tumble = inplace
    if config_overrides:
        config_overrides(config)

    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    stage_death_counts = {}
    totals, line_totals, reward_totals, spin_counts = [], [], [], []
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
            gs.run_bonus_session("normal")
            totals.append(gs.win_manager.running_bet_win)
            line_totals.append(_totals["line"])
            reward_totals.append(_totals["reward"])
            spin_counts.append(gs.bonus_spin_count)
            stage_death_counts[gs.stage] = stage_death_counts.get(gs.stage, 0) + 1

    mean = sum(totals) / n
    median = statistics.median(totals)
    mean_line = sum(line_totals) / n
    mean_reward = sum(reward_totals) / n
    print(f"\n=== {tag} inplace={inplace} (n={n}, {time.time()-t0:.1f}s) ===")
    print(f"mean={mean:.2f}x median={median:.2f}x ({100*median/mean:.1f}%)")
    print(f"line-pay={mean_line:.2f}x ({100*mean_line/mean:.1f}%) reward-drop={mean_reward:.2f}x ({100*mean_reward/mean:.1f}%)")
    print(f"avg spins/session={sum(spin_counts)/n:.2f}")
    print("stage death %: " + ", ".join(f"s{s}={100*c/n:.2f}%" for s, c in sorted(stage_death_counts.items())))
    for lo, hi in BUCKETS:
        pct = 100 * sum(1 for t in totals if lo <= t < hi) / n
        label = f"{lo}-{hi}" if hi < 10**9 else f"{lo}+"
        print(f"  {label}: {pct:.2f}%")
    return dict(mean=mean, median=median, mean_line=mean_line, mean_reward=mean_reward, n=n)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    measure(n, 940000, "NORMAL_CASCADE_baseline", inplace=False)
    measure(n, 940000, "NORMAL_INPLACE_current_reels", inplace=True)

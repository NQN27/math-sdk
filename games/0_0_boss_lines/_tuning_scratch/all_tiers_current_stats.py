"""Current state of all 3 Bonus tiers (Normal/Super/Hidden), zero-override
harness (real, unmodified game_config.py) - same trusted pattern as
pure_production_percentile_check.py / normal_bonus_full_stats.py.

Targets (2026-08-13 corrected spec, see project memory):
  Normal: mean 80.13x, median 32-40x (40-50% of mean)
  Super:  mean 240.77x, median 96-120x (40-50% of mean)
  Hidden: mean 2250.00x, median 1688-1800x (75-80% of mean)
"""
import statistics
import sys
import warnings
import random
import time

sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager


def measure(tier, n, seed_offset):
    config = game_config_mod.GameConfig()
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session(tier)
            totals.append(gs.win_manager.running_bet_win)

    mean = sum(totals) / n
    median = statistics.median(totals)
    return {"tier": tier, "n": n, "mean": mean, "median": median, "median_pct_of_mean": 100 * median / mean if mean else 0, "max": max(totals)}


TARGETS = {
    "normal": {"mean": 80.13, "median_lo": 32, "median_hi": 40},
    "super": {"mean": 240.77, "median_lo": 96, "median_hi": 120},
    "hidden": {"mean": 2250.00, "median_lo": 1688, "median_hi": 1800},
}

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    for tier in ["normal", "super", "hidden"]:
        t0 = time.time()
        r = measure(tier, n, 950001 + ["normal", "super", "hidden"].index(tier))
        elapsed = time.time() - t0
        tgt = TARGETS[tier]
        print(f"\n=== {tier.upper()} (n={n}, {elapsed:.1f}s) ===")
        print(f"  mean:   {r['mean']:.2f}x   (target {tgt['mean']:.2f}x, {'OK' if abs(r['mean']-tgt['mean'])/tgt['mean'] < 0.15 else 'OFF'} - within 15%: {abs(r['mean']-tgt['mean'])/tgt['mean']*100:.1f}% diff)")
        print(f"  median: {r['median']:.2f}x  ({r['median_pct_of_mean']:.1f}% of mean, target band {tgt['median_lo']}-{tgt['median_hi']}x)")
        print(f"  max observed: {r['max']:.2f}x")

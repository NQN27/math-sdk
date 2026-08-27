"""Large-n (100000) confirmation of the committed Super Bonus fix (commit
07a11cb) against the REAL production reels/game_config.py - no overrides,
no scratch substitution. Requested by the game designer specifically
because endless mode + Power make this distribution volatile (rare,
high-impact tail events) - n=5000-10000 may not have converged.

Reports mean/median/stdev/percentiles (not just mean/median) plus the
stage-reach funnel and a resolve-pass safety hit-rate, all from ONE pass
over the same n sessions (no need for 2 separate scripts at this scale).
"""
import sys
import random
import statistics
import warnings
import time

sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

_orig_run_one_spin = gamestate_mod.GameState.run_one_bonus_spin
_counts = {"internal_spins": 0}


def hooked_run_one_spin(self, both_ways):
    _counts["internal_spins"] += 1
    return _orig_run_one_spin(self, both_ways)


gamestate_mod.GameState.run_one_bonus_spin = hooked_run_one_spin

TARGET_MEAN = 240.77
TARGET_MEDIAN_LO, TARGET_MEDIAN_HI = 96, 120


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
    seed_offset = int(sys.argv[2]) if len(sys.argv) > 2 else 995000

    config = game_config_mod.GameConfig()  # real production reels, no override
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals = []
    stage_counts = {}
    end_reasons = {}
    resolve_pass_hits = 0
    t0 = time.time()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session("super")
            totals.append(gs.win_manager.running_bet_win)
            stage_counts[gs.stage] = stage_counts.get(gs.stage, 0) + 1
            end_reasons[gs.bonus_end_reason] = end_reasons.get(gs.bonus_end_reason, 0) + 1
            if (i + 1) % 10000 == 0:
                elapsed = time.time() - t0
                running_mean = sum(totals) / len(totals)
                print(f"  progress: {i+1}/{n} sessions, {elapsed:.0f}s elapsed, running mean so far={running_mean:.2f}x", flush=True)
        for w in caught:
            if "Hit max_resolve_passes" in str(w.message):
                resolve_pass_hits += 1

    elapsed = time.time() - t0
    totals_sorted = sorted(totals)
    mean = sum(totals) / n
    median = statistics.median(totals)
    stdev = statistics.stdev(totals)

    def pct(p):
        idx = min(n - 1, int(p / 100.0 * n))
        return totals_sorted[idx]

    print(f"\n=== SUPER, real production reels, n={n} ({elapsed:.1f}s) ===")
    print(f"mean:   {mean:.2f}x   (target {TARGET_MEAN}x, {abs(mean-TARGET_MEAN)/TARGET_MEAN*100:.1f}% off)")
    print(f"median: {median:.2f}x  ({100*median/mean:.1f}% of mean, target band {TARGET_MEDIAN_LO}-{TARGET_MEDIAN_HI}x)")
    print(f"stdev:  {stdev:.2f}x  (coefficient of variation: {stdev/mean:.2f})")
    print(f"p50={pct(50):.2f}x  p75={pct(75):.2f}x  p90={pct(90):.2f}x  p95={pct(95):.2f}x  p99={pct(99):.2f}x  p99.9={pct(99.9):.2f}x")
    print(f"max: {max(totals):.2f}x   min: {min(totals):.2f}x   zero-count: {sum(1 for t in totals if t == 0)}")
    print("end_reason: " + ", ".join(f"{k}={100*v/n:.2f}%" for k, v in sorted(end_reasons.items())))
    print("stage reached: " + ", ".join(f"s{s}={100*c/n:.2f}%" for s, c in sorted(stage_counts.items())))
    total_internal_spins = _counts["internal_spins"]
    print(f"\nresolve-pass safety: {resolve_pass_hits} max_resolve_passes hits / {total_internal_spins} internal spins ({100*resolve_pass_hits/total_internal_spins:.4f}%)")


if __name__ == "__main__":
    main()

"""Normal Bonus: overall mean/median/variance plus a per-stage breakdown.

Zero-override harness (real, unmodified game_config.py) - same pattern as
pure_production_percentile_check.py (trusted baseline per this game's
CLAUDE.md), extended with stage_funnel_payout.py's clear_stage observation
hook (records max stage reached per session, no gameplay side effects) so
we can report stats per stage bucket, not just in aggregate.
"""
import statistics
import sys
import warnings
import random
import json
import time

sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

_orig_clear_stage = gamestate_mod.GameState.clear_stage
_state = {"max_stage": 1}


def hooked_clear_stage(self, stage):
    result = _orig_clear_stage(self, stage)
    _state["max_stage"] = max(_state["max_stage"], getattr(self, "stage", stage))
    return result


gamestate_mod.GameState.clear_stage = hooked_clear_stage


def var(vals, mean):
    if len(vals) < 2:
        return 0.0
    return sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)


def measure(n, seed_offset):
    config = game_config_mod.GameConfig()
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals = []
    stage_buckets = {s: [] for s in range(1, 7)}

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            _state["max_stage"] = 1
            gs.run_bonus_session("normal")
            payout = gs.win_manager.running_bet_win
            totals.append(payout)
            stage_buckets[_state["max_stage"]].append(payout)

    mean = sum(totals) / n
    median = statistics.median(totals)
    variance = var(totals, mean)
    stdev = variance ** 0.5

    result = {
        "n": n,
        "seed_offset": seed_offset,
        "overall": {
            "mean": mean,
            "median": median,
            "variance": variance,
            "stdev": stdev,
            "min": min(totals),
            "max": max(totals),
        },
        "by_max_stage_reached": {},
    }

    prev_count = n
    for s in range(1, 7):
        vals = stage_buckets[s]
        cnt = len(vals)
        entry = {"count": cnt, "pct_of_all": 100 * cnt / n}
        if cnt:
            s_mean = sum(vals) / cnt
            entry["mean"] = s_mean
            entry["median"] = statistics.median(vals)
            entry["variance"] = var(vals, s_mean)
            entry["stdev"] = entry["variance"] ** 0.5
            entry["min"] = min(vals)
            entry["max"] = max(vals)
        else:
            entry.update({"mean": 0, "median": 0, "variance": 0, "stdev": 0, "min": 0, "max": 0})
        reached_or_beyond = sum(len(stage_buckets[k]) for k in range(s, 7))
        beyond = sum(len(stage_buckets[k]) for k in range(s + 1, 7))
        entry["pct_advanced_past_this_stage_of_those_who_reached_it"] = (
            100 * beyond / reached_or_beyond if reached_or_beyond else 0
        )
        result["by_max_stage_reached"][s] = entry
        prev_count = reached_or_beyond

    return result


def print_report(result):
    o = result["overall"]
    print(f"\n=== Normal Bonus — n={result['n']} (seed_offset={result['seed_offset']}) [REAL, UNMODIFIED game_config.py] ===")
    print(f"OVERALL: mean={o['mean']:.2f}x  median={o['median']:.2f}x  variance={o['variance']:.2f}  stdev={o['stdev']:.2f}  min={o['min']:.2f}x  max={o['max']:.2f}x")
    print(f"\n{'stage':>6} {'reached %':>10} {'count':>8} {'mean':>10} {'median':>10} {'variance':>12} {'stdev':>10} {'%advance':>10}")
    for s in range(1, 7):
        e = result["by_max_stage_reached"][s]
        print(f"{s:>6} {e['pct_of_all']:>9.2f}% {e['count']:>8} {e['mean']:>9.2f}x {e['median']:>9.2f}x {e['variance']:>12.2f} {e['stdev']:>9.2f} {e['pct_advanced_past_this_stage_of_those_who_reached_it']:>9.1f}%")
    print("\n(stage bucket = MAX stage the session reached before ending; 'reached %' is share of ALL sessions ending at exactly that stage;")
    print(" '%advance' = of sessions that reached this stage, what fraction went on past it rather than ending there)")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 940101

    t0 = time.time()
    result = measure(n, seed)
    elapsed = time.time() - t0

    print_report(result)
    print(f"\n(elapsed: {elapsed:.1f}s)")

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = rf"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch\results\normal_bonus_full_stats_n{n}_{ts}.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved: {out_path}")

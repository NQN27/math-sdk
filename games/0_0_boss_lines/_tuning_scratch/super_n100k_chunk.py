"""One CHUNK of the n=100000 Super production confirmation (see
super_production_n100k_verify.py's docstring for why - endless mode + Power
volatility means the game designer wants a much larger n than 5000-10000
before trusting the mean). Run in several foreground chunks instead of one
long background process, since a single very long background call risked
being killed by environment recycling between turns (same failure class as
the Storybook dev server dying between turns, seen earlier this project).

Each chunk appends its sessions' payouts (one float per line) to
PAYOUTS_FILE and merges its stage/end-reason/resolve-pass counts into
SUMMARY_FILE (read-modify-write) - safe to call repeatedly with different
chunk_index values; nothing is lost if a later chunk fails, only that
chunk's n sessions need re-running.
"""
import sys
import os
import json
import random
import warnings
import time

sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

SCRATCH_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch"
PAYOUTS_FILE = os.path.join(SCRATCH_DIR, "super_n100k_payouts.txt")
SUMMARY_FILE = os.path.join(SCRATCH_DIR, "super_n100k_summary.json")

_orig_run_one_spin = gamestate_mod.GameState.run_one_bonus_spin
_counts = {"internal_spins": 0}


def hooked_run_one_spin(self, both_ways):
    _counts["internal_spins"] += 1
    return _orig_run_one_spin(self, both_ways)


gamestate_mod.GameState.run_one_bonus_spin = hooked_run_one_spin


def main():
    n_per_chunk = int(sys.argv[1])
    chunk_index = int(sys.argv[2])
    base_seed_offset = 995000

    config = game_config_mod.GameConfig()
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    payouts = []
    stage_counts = {}
    end_reasons = {}
    resolve_pass_hits = 0
    t0 = time.time()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for i in range(n_per_chunk):
            gs.sim = i
            gs.criteria = "freegame"
            # unique, non-overlapping stream per chunk
            random.seed((base_seed_offset + chunk_index * 100000) * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session("super")
            payouts.append(gs.win_manager.running_bet_win)
            stage_counts[gs.stage] = stage_counts.get(gs.stage, 0) + 1
            end_reasons[gs.bonus_end_reason] = end_reasons.get(gs.bonus_end_reason, 0) + 1
        for w in caught:
            if "Hit max_resolve_passes" in str(w.message):
                resolve_pass_hits += 1
    elapsed = time.time() - t0

    with open(PAYOUTS_FILE, "a") as f:
        for p in payouts:
            f.write(f"{p}\n")

    if os.path.exists(SUMMARY_FILE):
        with open(SUMMARY_FILE) as f:
            summary = json.load(f)
    else:
        summary = {"stage_counts": {}, "end_reasons": {}, "resolve_pass_hits": 0, "total_internal_spins": 0, "chunks_done": []}

    for s, c in stage_counts.items():
        summary["stage_counts"][str(s)] = summary["stage_counts"].get(str(s), 0) + c
    for k, c in end_reasons.items():
        summary["end_reasons"][k] = summary["end_reasons"].get(k, 0) + c
    summary["resolve_pass_hits"] += resolve_pass_hits
    summary["total_internal_spins"] += _counts["internal_spins"]
    summary["chunks_done"].append(chunk_index)

    with open(SUMMARY_FILE, "w") as f:
        json.dump(summary, f, indent=2)

    import statistics
    this_mean = sum(payouts) / len(payouts)
    this_median = statistics.median(payouts)
    this_stdev = statistics.stdev(payouts)
    print(f"chunk {chunk_index}: {n_per_chunk} sessions in {elapsed:.1f}s, total sessions so far={len(summary['chunks_done'])*n_per_chunk}")
    print(f"  this-chunk: mean={this_mean:.2f}x median={this_median:.2f}x ({100*this_median/this_mean:.1f}% of mean) "
          f"stdev={this_stdev:.2f}x max={max(payouts):.2f}x")
    print("  stage reached: " + ", ".join(f"s{s}={100*c/n_per_chunk:.2f}%" for s, c in sorted(stage_counts.items())))
    print("  end_reason: " + ", ".join(f"{k}={100*v/n_per_chunk:.2f}%" for k, v in sorted(end_reasons.items())))
    print(f"  resolve_pass_hits={resolve_pass_hits} / {_counts['internal_spins']} internal spins this chunk")


if __name__ == "__main__":
    main()

"""SCRATCH-ONLY, staged investigation (per game designer, 2026-08-26: "check
config (idea normal to apply for super) unlock power and endless mode just
slowly investigate it take your time") - does NOT touch any real reel CSV or
game_config.py. All reel substitutions happen in-memory via
config.read_reels_csv() on freshly-generated scratch files, exactly like the
established pattern in stage1_density_experiment.py.

Question: how much of Super's stage-2 funnel collapse (79.6% die at the very
first stage they face - see TOWORK.md) comes from Super's own Wild% taper
being ~3x lower than Normal's at the equivalent "stage since bonus start",
versus Power, versus the endless stage-6 tail? Isolate each lever instead of
changing all of them at once.

Four conditions, each building on the last:
  A) BASELINE       - real production Super: own wild% (8/7/6/5/4), Power ON
                       (35% of wild-like density), endless ON. Reference only.
  B) NORMAL_WILD     - Super's reels rebuilt using NORMAL's wild% taper
                       (23/16/10/4/2, "stages since start" aligned - Normal's
                       stage1/2/3/4/5 value reused for Super's stage2/3/4/5/6),
                       Power turned OFF (frac=0.0), endless turned OFF - the
                       closest analogue to "apply Normal's idea to Super"
                       with every Super-specific addition locked out, so the
                       Wild-density effect alone is isolated.
  C) +POWER          - same NORMAL_WILD reels, Power unlocked back to Super's
                       real 35% fraction, endless still OFF.
  D) +ENDLESS        - same as C, endless unlocked back to Super's real ON -
                       the full "Normal idea + Super's own Power/endless"
                       stack.

Super's own HP pool ([300,350,400,450]) is left UNCHANGED in every condition
- that's a separate, already-flagged lever (see TOWORK.md), not conflated
  with this Wild/Power/endless investigation.
"""
import sys
import os
import random
import statistics
import warnings
import time

sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager
import gen_stage_reels as gsr

SCRATCH_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch\super_normal_idea"
os.makedirs(SCRATCH_DIR, exist_ok=True)

# Normal's wild% taper, reindexed by "stages since bonus start" (Normal
# starts at stage1, so its own table is already in that order) and remapped
# onto Super's real stage numbers (Super starts at stage2).
NORMAL_WILD_BY_STAGES_SINCE_START = [23.0, 16.0, 10.0, 4.0, 2.0]  # normal stage 1..5
SUPER_STAGES = [2, 3, 4, 5, 6]
NORMAL_WILD_FOR_SUPER = dict(zip(SUPER_STAGES, NORMAL_WILD_BY_STAGES_SINCE_START))


def gen_variant(power_frac, tag):
    """Write Super_BM_S{2..6} scratch reels using NORMAL_WILD_FOR_SUPER's
    wild% target and the given power_frac, keeping Super's own L/H shape and
    col0-never-wild convention untouched. Returns {stage: path}."""
    paths = {}
    seed = 5001 if tag == "pow0" else 5101
    for stage in SUPER_STAGES:
        pct = NORMAL_WILD_FOR_SUPER[stage]
        other_pct = pct * 5.0 / 4.0  # col0 stays 0% wild -> other 4 cols run richer
        w_other = gsr.make_weights(gsr.NONWILD["super"]["other"], other_pct, power_frac)
        w_col0 = gsr.make_weights(gsr.NONWILD["super"]["col0"], 0.0, power_frac)
        fname = f"Super_BM_S{stage}_{tag}.csv"
        path = os.path.join(SCRATCH_DIR, fname)
        gsr.write_reel(path, w_col0, w_other, seed)
        paths[stage] = path
        seed += 1
    return paths


def measure(tag, n, seed_offset, reel_paths, endless_on):
    config = game_config_mod.GameConfig()
    if reel_paths:
        for stage, path in reel_paths.items():
            config.reels[f"Super_BM_S{stage}"] = config.read_reels_csv(path)
    config.stage6_endless_tiers = dict(config.stage6_endless_tiers)
    config.stage6_endless_tiers["super"] = endless_on

    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals = []
    end_reasons = {}
    max_stage_seen = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session("super")
            totals.append(gs.win_manager.running_bet_win)
            end_reasons[gs.bonus_end_reason] = end_reasons.get(gs.bonus_end_reason, 0) + 1
            max_stage_seen.append(gs.stage)

    mean = sum(totals) / n
    median = statistics.median(totals)
    stage_counts = {}
    for s in max_stage_seen:
        stage_counts[s] = stage_counts.get(s, 0) + 1

    print(f"\n=== {tag} (n={n}) ===")
    print(f"  mean={mean:.2f}x  median={median:.2f}x  ({100*median/mean:.1f}% of mean)  max={max(totals):.2f}x")
    print("  end_reason: " + ", ".join(f"{k}={100*v/n:.1f}%" for k, v in sorted(end_reasons.items())))
    print("  stage reached: " + ", ".join(f"s{s}={100*c/n:.1f}%" for s, c in sorted(stage_counts.items())))
    return {"tag": tag, "mean": mean, "median": median, "end_reasons": end_reasons, "stage_counts": stage_counts}


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    t0 = time.time()

    reels_pow0 = gen_variant(0.0, "pow0")
    reels_pow35 = gen_variant(0.35, "pow35")

    measure("A_BASELINE (production Super: own wild%, power ON, endless ON)",
            n, 991000, reel_paths=None, endless_on=True)

    measure("B_NORMAL_WILD (Normal's wild% taper, power OFF, endless OFF)",
            n, 991001, reel_paths=reels_pow0, endless_on=False)

    measure("C_+POWER (Normal's wild% taper, power ON=35%, endless OFF)",
            n, 991002, reel_paths=reels_pow35, endless_on=False)

    measure("D_+ENDLESS (Normal's wild% taper, power ON=35%, endless ON) = full stack",
            n, 991003, reel_paths=reels_pow35, endless_on=True)

    print(f"\ntotal elapsed: {time.time()-t0:.1f}s")

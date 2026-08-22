"""7-segment reward table redesign, per designer spec:
  seg1 [1,2]                      - pruned after stage1 clears
  seg2 [3,4]                      - pruned after stage2 clears
  seg3 [5,6,8]                    - pruned after stage3 clears
  seg4 [10,12,15,18]              - pruned after stage4 clears
  seg5 [20,25]                    - pruned after stage5 clears
  seg6 [30,35,40,50,60,80,100,120,150,180,200,250,300,350,400,500,600,800,1000]
                                   - NEVER pruned, always in the regular pool
  seg7 [1500,2000,2500,3000,4000,5000]
                                   - stage6-chest EXCLUSIVE only (never drawn
                                     on a regular kill, matching the current
                                     reward_drop_stage6_last_tiers_normal_bonus
                                     carve-out)

This replaces the old 12-regular/9-chest table (originally scaled from
production's 2.57..35.95 / 32.96..2197.78) wholesale - a genuinely new
weight table, not a rescale of the old one. Weights use a geometric-ish
decay within each segment (low value = high weight), roughly matching the
production table's own decay pattern (~1.2-1.3x per step).
"""
import json
import os
import statistics
import sys
import time
import warnings
import random

sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import final_combined_candidate as fc

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

SEG1 = {1: 150, 2: 120}
SEG2 = {3: 380, 4: 300}
SEG3 = {5: 320, 6: 260, 8: 210}
SEG4 = {10: 110, 12: 85, 15: 65, 18: 48}
SEG5 = {20: 60, 25: 44}
SEG6 = {
    30: 36, 35: 29.3, 40: 24.1, 50: 19.6, 60: 16.1, 80: 13.2, 100: 10.8,
    120: 8.8, 150: 7.2, 180: 5.0, 200: 4.1, 250: 2.0, 300: 1.7, 350: 1.4,
    400: 1.1, 500: 0.9, 600: 0.8, 800: 0.6, 1000: 0.5,
}
SEG7_CHEST = {400: 15, 500: 8, 800: 4, 1500: 0.9, 2500: 0.35, 4000: 0.12}

REGULAR_WEIGHTS = {**SEG1, **SEG2, **SEG3, **SEG4, **SEG5, **SEG6}
PRUNE_SCHEDULE = {
    1: list(SEG1), 2: list(SEG2), 3: list(SEG3), 4: list(SEG4), 5: list(SEG5), 6: [],
}


def build_config_segments(maxwin_weight):
    config = fc.game_config_mod.GameConfig()
    config.bonus_player_hp_choices["normal"] = fc.HP_POOL
    config.boss_stage_table = fc.build_scaled_boss_table(config.boss_stage_table, fc.HP_MULT)
    config.stage6_chest_natural_maxwin_weight = maxwin_weight

    config.reward_drop_weights_normal_bonus = {**REGULAR_WEIGHTS, **SEG7_CHEST}
    config.reward_drop_top_tiers_normal_bonus = set(SEG7_CHEST)
    config.reward_drop_stage6_last_tiers_normal_bonus = set(SEG7_CHEST)
    config.stage_clear_pruned_tiers = PRUNE_SCHEDULE
    return config


def measure(n, seed_offset, maxwin_weight):
    config = build_config_segments(maxwin_weight)
    gs = fc.gamestate_mod.GameState(config)
    gs.win_manager = fc.WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals = []
    buckets = {s: [] for s in range(1, 7)}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            fc._state["max_stage"] = 1
            fc._state["spins"] = 0
            fc._state["pass_count"] = 0
            fc._state["chain_block_pending"] = False
            fc._state["general_chance"] = 0.0
            fc._state["chain_break_threshold"] = 2
            fc._state["chain_break_step"] = 0.30
            gs.run_bonus_session("normal")
            t = gs.win_manager.running_bet_win
            totals.append(t)
            buckets[fc._state["max_stage"]].append(t)

    totals_sorted = sorted(totals)

    def pct(p):
        idx = min(n - 1, int(p * n))
        return totals_sorted[idx]

    mean = sum(totals) / n
    median = statistics.median(totals)
    percentiles = {p: pct(p) for p in [0.10, 0.25, 0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99, 0.995, 0.999]}

    s6_pct_frac = len(buckets[6]) / n
    chest_total_w = sum(SEG7_CHEST.values())
    p_select_given_chest = maxwin_weight / (chest_total_w + maxwin_weight)
    maxwin_rate = s6_pct_frac * p_select_given_chest
    maxwin_1_in = (1 / maxwin_rate) if maxwin_rate > 0 else float("inf")
    bucket_stats = {}
    for s in range(1, 7):
        b = buckets[s]
        bucket_stats[s] = dict(
            n=len(b), pct=100 * len(b) / n,
            mean=(sum(b) / len(b)) if b else 0,
            median=statistics.median(b) if b else 0,
            max=max(b) if b else 0,
        )

    print(f"mean={mean:.2f}x median={median:.2f}x ratio={100*median/mean:.1f}%")
    for p, v in percentiles.items():
        print(f"  p{p*100:>5.1f} = {v:>9.2f}x")
    print("bucket%: " + ", ".join(f"s{s}={bucket_stats[s]['pct']:.2f}" for s in range(1, 7)))
    for s in range(1, 7):
        st = bucket_stats[s]
        print(f"  stage {s}: mean={st['mean']:8.2f}x median={st['median']:8.2f}x max={st['max']:9.2f}x")
    print(f"max win tier (20000x, weight={maxwin_weight}/{chest_total_w:.4f} of chest pool): "
          f"P(selected|chest reached)={100*p_select_given_chest:.4f}%  "
          f"-> session-level rate = 1-in-{maxwin_1_in:.0f}")

    result = dict(n=n, seed_offset=seed_offset, mean=mean, median=median,
                  ratio=100 * median / mean if mean else 0,
                  percentiles={f"p{p*100:g}": v for p, v in percentiles.items()},
                  bucket_stats=bucket_stats, seg1=SEG1, seg2=SEG2, seg3=SEG3,
                  seg4=SEG4, seg5=SEG5, seg6=SEG6, seg7_chest=SEG7_CHEST,
                  maxwin_weight=maxwin_weight, maxwin_1_in=maxwin_1_in)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(RESULTS_DIR, f"segments_n{n}_{ts}.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nsaved -> {out_path}")
    return result


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 501001
    # Recalibrated for this segment redesign's chest pool weight (30.4, was
    # 36 in the old 9-tier table) - see maxwin_weight_solver.py's formula;
    # target stays 1-in-25000 session-level Max Win rate.
    print(f"n={n} (7-segment structural redesign candidate)")
    measure(n, seed, 0.0651)

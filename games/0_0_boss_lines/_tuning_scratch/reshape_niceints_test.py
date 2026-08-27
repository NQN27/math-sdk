"""Nice-integer tier ladder candidate, per designer request: values should
read like a normal paytable (1,2,3...10, 15,20,25...100, 150,200...1000,
1500,2000...) instead of raw decimal-scaled numbers. Weights (relative
frequency) are carried over UNCHANGED from production, just re-attached to
the new round values in the same ascending order - only face values move.

Regular 12 tiers (ascending value:weight):
  original: 2.57:400 3.85:320 4.71:260 6.42:210 7.28:170 8.99:140 10.7:110
             12.84:90 16.26:65 20.54:50 25.25:38 35.95:22
  new:      3:400    4:320    5:260    6:210    8:170    10:140   15:110
             30:90    40:65    60:50    70:38    100:22

Chest 9 tiers (ascending value:weight) - also reduced overall per "reduce
the chest" request (top ordinary tier now 15000, not 19000 - the literal
20000 Maxwin stays on the SEPARATE dedicated
config.stage6_chest_natural_maxwin_weight mechanism, untouched):
  original: 1483.2:13 1983.6:9 2465.1:6 2965.95:4 3948.3:2.2 7915.95:1.1
             14830.2:0.5 17000:0.18 19000:0.02
  new:      1000:13   1500:9   2000:6   2500:4    3000:2.2   5000:1.1
             7500:0.5    10000:0.18 15000:0.02
"""
import statistics
import sys
import warnings
import random

sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import final_combined_candidate as fc

REGULAR_MAP = {
    2.57: 3, 3.85: 4, 4.71: 5, 6.42: 6, 7.28: 8, 8.99: 10, 10.7: 15,
    12.84: 25, 16.26: 35, 20.54: 90, 25.25: 110, 35.95: 180,
}
CHEST_MAP = {
    32.96: 800, 44.08: 1200, 54.78: 1600, 65.91: 2000, 87.74: 2500,
    175.91: 4000, 329.56: 6000, 769.12: 8000, 2197.78: 12000,
}


def build_config_niceints(maxwin_weight):
    config = fc.game_config_mod.GameConfig()
    config.bonus_player_hp_choices["normal"] = fc.HP_POOL
    config.boss_stage_table = fc.build_scaled_boss_table(config.boss_stage_table, fc.HP_MULT)
    config.stage6_chest_natural_maxwin_weight = maxwin_weight

    exclusive = set(config.reward_drop_stage6_last_tiers_normal_bonus)
    regular_keys = sorted(k for k in config.reward_drop_weights_normal_bonus if k not in exclusive)

    new_weights = {}
    for k, w in config.reward_drop_weights_normal_bonus.items():
        if k in exclusive:
            new_weights[CHEST_MAP[k]] = w
        else:
            new_weights[REGULAR_MAP[k]] = w
    config.reward_drop_weights_normal_bonus = new_weights
    config.reward_drop_top_tiers_normal_bonus = {CHEST_MAP[k] for k in config.reward_drop_top_tiers_normal_bonus}
    config.reward_drop_stage6_last_tiers_normal_bonus = {
        CHEST_MAP[k] for k in config.reward_drop_stage6_last_tiers_normal_bonus
    }

    scaled_regular = sorted(REGULAR_MAP[k] for k in regular_keys)
    schedule_counts = {1: 2, 2: 2, 3: 3, 4: 2, 5: 2, 6: 0}
    pruned_tiers = {}
    idx = 0
    for stage in range(1, 7):
        cnt = schedule_counts[stage]
        pruned_tiers[stage] = scaled_regular[idx:idx + cnt]
        idx += cnt
    config.stage_clear_pruned_tiers = pruned_tiers
    return config


def measure(n, seed_offset, maxwin_weight):
    config = build_config_niceints(maxwin_weight)
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
    print(f"mean={mean:.2f}x median={median:.2f}x ratio={100*median/mean:.1f}%")
    for p in [0.10, 0.25, 0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99, 0.995, 0.999]:
        print(f"  p{p*100:>5.1f} = {pct(p):>9.2f}x")
    print("bucket%: " + ", ".join(f"s{s}={100*len(buckets[s])/n:.2f}" for s in range(1, 7)))
    for s in range(1, 7):
        b = buckets[s]
        if b:
            print(f"  stage {s}: mean={sum(b)/len(b):8.2f}x median={statistics.median(b):8.2f}x max={max(b):9.2f}x")
    return dict(mean=mean, median=median)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 501001
    print(f"n={n} (nice-integer tier ladder candidate)")
    measure(n, seed, 0.0825)

"""Iterate toward a new target percentile shape for Normal Bonus:
  p75~80x  p80~125x  p85~175x  p90~225x  p95~300x  (p99.5/p99.9 reduced from
  current 2558.76x/4520.02x)

Strategy (per designer: "reduce the chest and increase the boss"): instead
of one uniform K on all 12 regular tiers (which can't hit a mild p75 bump
AND a big p90 bump at once - they currently sit in the same stage3/4
region), apply a GRADUATED per-tier-group multiplier that lines up with the
existing stage-clear pruning groups (tiers that only become visible once
you're further into the run get a bigger boost), and reduce stage6_boost to
pull the extreme tail (p99.5/p99.9) back down.
"""
import statistics
import sys
import warnings
import random

sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import game_config as game_config_mod
import gamestate as gamestate_mod
from src.wins.win_manager import WinManager

HP_MULT = {1: 3.7, 2: 2.5, 3: 2.7, 4: 3.3, 5: 4.75, 6: 7.0}
HP_POOL = [200, 200, 200, 200, 200]
CHEST_TIER_CAP_OVERRIDE = {769.12: 17000.0, 2197.78: 19000.0}

_state = {"max_stage": 1, "spins": 0, "pass_count": 0, "chain_block_pending": False}


def build_scaled_boss_table(base_table, hp_mult):
    scaled = {}
    for stage, bosses in base_table.items():
        m = hp_mult[stage]
        scaled[stage] = {b: (dam, hp * m) for b, (dam, hp) in bosses.items()}
    return scaled


def build_config(group_k, stage6_boost, maxwin_weight):
    """group_k: dict mapping each of the 12 raw regular-tier values to its
    own multiplier (graduated by which stage-clear group they belong to)."""
    config = game_config_mod.GameConfig()
    config.bonus_player_hp_choices["normal"] = HP_POOL
    config.boss_stage_table = build_scaled_boss_table(config.boss_stage_table, HP_MULT)
    config.stage6_chest_natural_maxwin_weight = maxwin_weight

    exclusive = set(config.reward_drop_stage6_last_tiers_normal_bonus)
    regular_keys = sorted(k for k in config.reward_drop_weights_normal_bonus if k not in exclusive)

    new_weights = {}
    for k, w in config.reward_drop_weights_normal_bonus.items():
        if k in exclusive:
            new_weights[CHEST_TIER_CAP_OVERRIDE.get(k, round(k * stage6_boost, 4))] = w
        else:
            new_weights[round(k * group_k[k], 4)] = w
    config.reward_drop_weights_normal_bonus = new_weights

    config.reward_drop_top_tiers_normal_bonus = {
        CHEST_TIER_CAP_OVERRIDE.get(k, round(k * stage6_boost, 4))
        for k in config.reward_drop_top_tiers_normal_bonus
    }
    config.reward_drop_stage6_last_tiers_normal_bonus = {
        CHEST_TIER_CAP_OVERRIDE.get(k, round(k * stage6_boost, 4))
        for k in config.reward_drop_stage6_last_tiers_normal_bonus
    }

    scaled_regular = sorted(round(k * group_k[k], 4) for k in regular_keys)
    schedule_counts = {1: 2, 2: 2, 3: 3, 4: 2, 5: 2, 6: 0}
    pruned_tiers = {}
    idx = 0
    for stage in range(1, 7):
        cnt = schedule_counts[stage]
        pruned_tiers[stage] = scaled_regular[idx:idx + cnt]
        idx += cnt
    config.stage_clear_pruned_tiers = pruned_tiers
    return config


def measure(n, seed_offset, group_k, stage6_boost, maxwin_weight):
    config = build_config(group_k, stage6_boost, maxwin_weight)
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
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
            _state["max_stage"] = 1
            _state["spins"] = 0
            _state["pass_count"] = 0
            _state["chain_block_pending"] = False
            _state["general_chance"] = 0.0
            _state["chain_break_threshold"] = 2
            _state["chain_break_step"] = 0.30
            gs.run_bonus_session("normal")
            t = gs.win_manager.running_bet_win
            totals.append(t)
            buckets[_state["max_stage"]].append(t)

    totals_sorted = sorted(totals)

    def pct(p):
        idx = min(n - 1, int(p * n))
        return totals_sorted[idx]

    mean = sum(totals) / n
    median = statistics.median(totals)
    print(f"mean={mean:.2f}x median={median:.2f}x ratio={100*median/mean:.1f}%")
    for p in [0.75, 0.80, 0.85, 0.90, 0.95, 0.99, 0.995, 0.999]:
        print(f"  p{p*100:>5.1f} = {pct(p):>9.2f}x")
    print("bucket%: " + ", ".join(f"s{s}={100*len(buckets[s])/n:.2f}" for s in range(1, 7)))
    return dict(mean=mean, median=median, totals_sorted=totals_sorted)


# gamestate.py needs _state wired the same way final_combined_candidate.py
# does - patch the same hooks it uses (chain-block state machine etc.) by
# reusing its module functions directly instead of re-deriving them here.
import final_combined_candidate as fc
_state = fc._state
gamestate_mod = fc.gamestate_mod


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 501001

    REGULAR_RAW = [2.57, 3.85, 4.71, 6.42, 7.28, 8.99, 10.7, 12.84, 16.26, 20.54, 25.25, 35.95]
    # Groups match the existing stage-clear pruning boundaries:
    #   A (stage1-2 visible): 2.57 3.85 4.71 6.42
    #   B (stage3+ visible):  7.28 8.99 10.7
    #   C (stage4+ visible):  12.84 16.26
    #   D (stage5+ visible):  20.54 25.25
    #   E (stage6 visible):   35.95
    GROUP_A = [2.57, 3.85, 4.71, 6.42]
    GROUP_B = [7.28, 8.99, 10.7]
    GROUP_C = [12.84, 16.26]
    GROUP_D = [20.54, 25.25]
    GROUP_E = [35.95]

    kA = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    kB = float(sys.argv[4]) if len(sys.argv) > 4 else 1.3
    kC = float(sys.argv[5]) if len(sys.argv) > 5 else 1.9
    kD = float(sys.argv[6]) if len(sys.argv) > 6 else 2.4
    kE = float(sys.argv[7]) if len(sys.argv) > 7 else 2.6
    stage6_boost = float(sys.argv[8]) if len(sys.argv) > 8 else 30.0

    group_k = {}
    for k in GROUP_A: group_k[k] = kA
    for k in GROUP_B: group_k[k] = kB
    for k in GROUP_C: group_k[k] = kC
    for k in GROUP_D: group_k[k] = kD
    for k in GROUP_E: group_k[k] = kE

    print(f"n={n} kA={kA} kB={kB} kC={kC} kD={kD} kE={kE} stage6_boost={stage6_boost}")
    measure(n, seed, group_k, stage6_boost, 0.0825)

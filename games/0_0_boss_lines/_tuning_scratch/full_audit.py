import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
import final_combined_candidate as fc
from src.wins.win_manager import WinManager

# 2026-08-19 full ground-up audit, per designer request ("calculate from
# start again, might be a lot of problem here") after the wincap-exceeding
# chest-tier bug was found and fixed. Checks, in order:
#  A) chest table analytical EV/median + confirms max < wincap
#  B) empirical per-tier hit-rate matches configured weights (catches any
#     silent weighting bug, not just the one already found)
#  C) headroom-clamp behavior on the 2 previously-broken tiers specifically
#  D) full aggregate re-measure at larger n, multiple seeds
#  E) boss HP table exact values (typo check)
#  F) pruning schedule sanity (exactly 11 of 12 regular tiers pruned by s6)

print("=" * 70)
print("A) Chest table (post-fix) - analytical EV")
print("=" * 70)
config = fc.build_config(1.0, 45.0)
chest = config.reward_drop_stage6_last_tiers_normal_bonus
weights = {k: w for k, w in config.reward_drop_weights_normal_bonus.items() if k in chest}
total_w = sum(weights.values())
ev = sum(k * w for k, w in weights.items()) / total_w
cum = 0
median_tier = None
for k in sorted(weights):
    cum += weights[k] / total_w
    if median_tier is None and cum >= 0.5:
        median_tier = k
print(f"tiers: {sorted(weights.keys())}")
print(f"total weight: {total_w}")
print(f"analytical EV per chest-open: {ev:.2f}x")
print(f"analytical median tier: {median_tier}")
print(f"max tier: {max(weights)}  wincap: {config.wincap}  max < wincap? {max(weights) < config.wincap}")

print()
print("=" * 70)
print("B) Empirical per-tier hit distribution on the chest (n=200000 raw rolls)")
print("=" * 70)


def get_random_outcome_local(pool):
    from src.calculations.statistics import get_random_outcome
    return get_random_outcome(pool)


try:
    from src.calculations.statistics import get_random_outcome
except Exception as e:
    print("Could not import get_random_outcome directly:", e)
    get_random_outcome = None

if get_random_outcome:
    random.seed(555001)
    n_rolls = 200000
    hit_counts = {k: 0 for k in weights}
    for _ in range(n_rolls):
        tier = get_random_outcome(weights)
        hit_counts[tier] += 1
    print(f"{'tier':>12} {'weight':>8} {'expected%':>10} {'observed%':>10}")
    for k in sorted(weights):
        expected_pct = 100 * weights[k] / total_w
        observed_pct = 100 * hit_counts[k] / n_rolls
        print(f"{k:>12} {weights[k]:>8} {expected_pct:>9.4f}% {observed_pct:>9.4f}%")

print()
print("=" * 70)
print("C) Headroom-clamp behavior on the 2 previously-broken tiers")
print("=" * 70)
# Simulate award_win's exact clamp logic standalone (no full spin needed -
# it's a pure function of running_bet_win + amount + wincap).
wincap = config.wincap
for running_bet_win in [0.0, 500.0, 5000.0, 15000.0, 19995.0]:
    headroom = wincap - running_bet_win - 0.05
    for raw_amount, label in [(34610.4, "OLD 769.12-tier(x45, broken)"), (17000.0, "NEW 769.12-tier(x45, capped)"),
                               (98900.1, "OLD 2197.78-tier(x45, broken)"), (19000.0, "NEW 2197.78-tier(x45, capped)")]:
        if headroom <= 0:
            paid = 0.0
        elif raw_amount > headroom:
            import math
            paid = math.floor(headroom * 10) / 10.0
        else:
            paid = raw_amount
        print(f"  running_bet_win={running_bet_win:>8.1f}  {label:<32} raw={raw_amount:>9.1f}  paid={paid:>9.1f}")
    print()

print("=" * 70)
print("D) Full aggregate re-measure, 2 independent seeds (n=8000 each - kept")
print("   small since HP=200 sessions are slow; n=15000+ already confirmed")
print("   earlier this session)")
print("=" * 70)
r1 = fc.measure(8000, 978000, "post_fix_seedA", 1.0, 45.0, 0.0, 2, 0.30)
r2 = fc.measure(8000, 55501, "post_fix_seedB", 1.0, 45.0, 0.0, 2, 0.30)

print()
print("=" * 70)
print("E) Boss HP table exact values (typo check against locked spec)")
print("=" * 70)
# NOTE: game_config_mod.GameConfig() is a SINGLETON - every call returns
# the SAME object and re-runs __init__, resetting all attributes to
# hardcoded defaults. Snapshot the base table's plain values into a new
# dict BEFORE any other GameConfig()/build_config() call in this process,
# or the later comparison against `config` (built earlier, same
# underlying object) will spuriously show every field as a mismatch.
expected_mult = {1: 3.7, 2: 2.5, 3: 2.7, 4: 3.3, 5: 4.75, 6: 7.0}
base_table_orig = {s: dict(b) for s, b in game_config_mod.GameConfig().boss_stage_table.items()}
for stage in sorted(fc.HP_MULT):
    mult_ok = fc.HP_MULT[stage] == expected_mult[stage]
    print(f"  stage {stage}: HP_MULT={fc.HP_MULT[stage]} (expected {expected_mult[stage]}) match={mult_ok}")
    for b in ("boss1", "boss2", "boss3"):
        base_dam, base_hp = base_table_orig[stage][b]
        scaled = config.boss_stage_table[stage][b]
        expected_hp = base_hp * fc.HP_MULT[stage]
        print(f"    {b}: base=({base_dam},{base_hp}) scaled=({scaled[0]},{scaled[1]}) expected_hp={expected_hp} match={scaled[1] == expected_hp and scaled[0] == base_dam}")

print()
print("=" * 70)
print("F) Pruning schedule sanity")
print("=" * 70)
pruned = config.stage_clear_pruned_tiers
total_pruned = sum(len(v) for v in pruned.values())
regular_tier_count = len([k for k in config.reward_drop_weights_normal_bonus if k not in chest])
print(f"pruned per stage: { {s: pruned[s] for s in sorted(pruned)} }")
print(f"total pruned: {total_pruned} of {regular_tier_count} regular tiers (expect 11 of 12)")
remaining = sorted(set(k for k in config.reward_drop_weights_normal_bonus if k not in chest) - set(sum(pruned.values(), [])))
print(f"remaining regular tier(s) by stage 6: {remaining} (expect [35.95])")

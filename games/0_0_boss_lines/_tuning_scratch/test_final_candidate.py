"""Regression test suite for final_combined_candidate.py (boss curve +
reward recalibration + chain-block, the full 2026-08-19 Normal Bonus
rebalance). Run with: python test_final_candidate.py [n]

Kept intentionally fast (default n=4000) so it's cheap to re-run after any
tweak - use a larger n via argv for a final confirmation pass.
"""
import sys
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import game_config as game_config_mod
import final_combined_candidate as fc

passed = 0
failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}{' -- ' + detail if detail else ''}")


print("=== 1. Table fidelity ===")
# IMPORTANT: game_config_mod.GameConfig() is a SINGLETON (every call
# returns the SAME object, and __init__ reruns each time, resetting all
# attributes to hardcoded defaults) - confirmed via `GameConfig() is
# GameConfig()`. Capture the UNSCALED base HP values as plain
# ints/floats (copied out, not a live dict reference) BEFORE calling
# build_config, or a later fresh GameConfig() call anywhere in this
# process will silently reset build_config's scaling too, since it's
# the exact same underlying object.
_base_snapshot = game_config_mod.GameConfig().boss_stage_table
base_table = {s: dict(bosses) for s, bosses in _base_snapshot.items()}

config = fc.build_config(1.0, 45.0)
weights = config.reward_drop_weights_normal_bonus
chest = config.reward_drop_stage6_last_tiers_normal_bonus
regular = set(weights) - chest

check("no reward tier reaches/exceeds wincap", max(weights) < config.wincap,
      f"max={max(weights)} wincap={config.wincap}")
check("chest pool has exactly 9 tiers", len(chest) == 9, str(sorted(chest)))
check("regular pool has exactly 12 tiers", len(regular) == 12, str(sorted(regular)))
check("weights dict has no key collisions (21 distinct keys total)", len(weights) == 21, str(len(weights)))

total_pruned = sum(len(v) for v in config.stage_clear_pruned_tiers.values())
check("pruning schedule removes exactly 11 of 12 regular tiers", total_pruned == 11, str(total_pruned))
remaining = sorted(regular - set(sum(config.stage_clear_pruned_tiers.values(), [])))
check("exactly one regular tier (35.95) survives to stage 6", remaining == [35.95], str(remaining))

expected_hp_mult = {1: 3.7, 2: 2.5, 3: 2.7, 4: 3.3, 5: 4.75, 6: 7.0}
check("HP_MULT matches the locked spec exactly", fc.HP_MULT == expected_hp_mult, str(fc.HP_MULT))
hp_ok = True
for stage in expected_hp_mult:
    for b in ("boss1", "boss2", "boss3"):
        base_dam, base_hp = base_table[stage][b]
        dam, hp = config.boss_stage_table[stage][b]
        if dam != base_dam or abs(hp - base_hp * expected_hp_mult[stage]) > 1e-6:
            hp_ok = False
check("boss HP table = base HP x HP_MULT exactly, Dam untouched", hp_ok)
check("HP pool is [200]*5", fc.HP_POOL == [200, 200, 200, 200, 200], str(fc.HP_POOL))

print("\n=== 2. Full simulation sanity ===")
n = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
r = fc.measure(n, 991500, "test_run", 1.0, 45.0, 0.0, 2, 0.30)

check("mean payout in 60-110x band (target ~80.13x, some n-dependent noise)", 60 <= r["mean"] <= 110, f"got {r['mean']:.2f}x")
check("median/mean ratio in 30-55% band", 30 <= r["ratio"] <= 55, f"got {r['ratio']:.1f}%")
check("zero-payout rate is low (<3%)", r["zero"] < 3, f"got {r['zero']:.2f}%")
check("spins<=2% is ~0 (HP=200 removes instant death)", r["spins_le2"] < 1, f"got {r['spins_le2']:.2f}%")
check("stage6 bucket% in 0.3-4% band", 0.3 <= r["s6_pct"] <= 4, f"got {r['s6_pct']:.2f}%")
check("mean chain passes in 1.8-2.8 band", 1.8 <= r["mean_passes"] <= 2.8, f"got {r['mean_passes']:.2f}")
check("long-chain (>=4 pass) rate in 5-20% band", 5 <= r["long_chain"] <= 20, f"got {r['long_chain']:.2f}%")

print("\n=== 3. Max Win rate (standing check, reported every run) ===")
print(f"  max win tier value: {r['maxwin_value']:.0f}x")
print(f"  session-level rate: 1-in-{r['maxwin_1_in']:.0f}  (target band: 1-in-20000 to 1-in-40000)")
check("Max Win session rate falls in the target 1/20000-1/40000 band",
      20000 <= r["maxwin_1_in"] <= 40000, f"got 1-in-{r['maxwin_1_in']:.0f}")

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)

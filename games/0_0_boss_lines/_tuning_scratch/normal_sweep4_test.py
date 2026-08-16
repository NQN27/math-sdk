import sys
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch")
import normal_3param_matrix_test as m

# Test adding a literal "chain-break OFF" tier (CURVE_NONE = {}, truly
# uncapped, not just "barely touches") to the weighted pool, per user's ask
# to pull median toward 40-50x while growing max beyond 764.4x. Weight
# combos below both add a small NONE share (for max/tail) AND shift more
# weight onto the stricter STANDARD tier (to pull the bulk of the
# distribution, including median, down) - the two moves together are meant
# to widen the gap between "typical" and "rare jackpot" instead of just
# sliding the whole population up or down together like the single-tier
# sweep did. Fixed at HP125+dmg20% (same context as the best candidate so
# far) to isolate the weight-combo's effect alone.
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000

    COMBOS = [
        ("std30_ltr30_ltst30_none10", [30, 30, 30, 10]),
        ("std40_ltr25_ltst20_none15", [40, 25, 20, 15]),
        ("std25_ltr25_ltst30_none20", [25, 25, 30, 20]),
        ("std45_ltr20_ltst15_none20", [45, 20, 15, 20]),
    ]
    seed = 840000
    for tag_suffix, weights in COMBOS:
        m._SWEEP4_WEIGHTS = weights
        tag = f"sweep4_{tag_suffix}_hp125_dmg120"
        m.measure(n, seed, tag, "sweep4", [125, 125, 125, 125, 125], 1.20, save_csv=True)
        seed += 1

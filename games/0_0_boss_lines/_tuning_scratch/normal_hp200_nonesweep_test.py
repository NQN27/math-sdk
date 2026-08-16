import sys
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch")
import normal_3param_matrix_test as m

# At HP125, raising the weight on the "none"/uncapped tier specifically
# (not reshuffling std/lighter/lightest) was the one thing that reliably
# pulled ratio down (93.1%->80.9% as lightest-tier weight rose 10%->90% in
# the earlier 3-tier sweep). The HP200 test just run reshuffled std/
# lighter/lightest with none FIXED at 5-10% and got almost no movement
# (ratio stuck 95.8-100.3%) - untested: what happens if none% itself rises
# at HP200. Splits the non-none remainder evenly across std/lighter/
# lightest each time.
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000

    NONE_PCTS = [10, 25, 40, 55, 70]
    seed = 880000
    for np in NONE_PCTS:
        rest = (100 - np) / 3
        m._SWEEP4_WEIGHTS = [rest, rest, rest, np]
        tag = f"hp200_none{np}"
        m.measure(n, seed, tag, "sweep4", [200, 200, 200, 200, 200], 1.00, save_csv=True)
        seed += 1

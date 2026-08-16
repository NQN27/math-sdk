import sys
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch")
import normal_3param_matrix_test as m

# HP200 + raised "none" weight gives great shape (ratio 77-94%, CV 0.92-1.51)
# but mean overshoots badly (101-125x vs 80-85x target) at damage=100% -
# HP200 alone already provides so much survival that normal damage produces
# too much mean. Unlike every other test this session (which needed a
# damage BOOST), this needs a damage REDUCTION to pull mean back down while
# HP200 keeps the big session-length win and none% keeps the good shape.
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000

    CASES = [
        ("none25_dmg80", 25, 0.80),
        ("none25_dmg70", 25, 0.70),
        ("none40_dmg70", 40, 0.70),
        ("none40_dmg60", 40, 0.60),
        ("none55_dmg60", 55, 0.60),
        ("none55_dmg50", 55, 0.50),
    ]
    seed = 890000
    for tag, np, dmg in CASES:
        rest = (100 - np) / 3
        m._SWEEP4_WEIGHTS = [rest, rest, rest, np]
        m.measure(n, seed, f"hp200_{tag}", "sweep4", [200, 200, 200, 200, 200], dmg, save_csv=True)
        seed += 1

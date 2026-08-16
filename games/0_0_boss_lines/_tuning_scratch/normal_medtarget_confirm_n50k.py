import sys
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch")
import normal_3param_matrix_test as m

# n=50000 confirmation of the leading medtarget candidates (n=15000 showed:
# hp75+dmg0%: mean=68.32x median=40.40x CV=1.41 max=2917.5x;
# hp75+dmg30%: mean=80.84x median=54.90x CV=1.31 max=2758.1x;
# hp100+dmg0%: mean=73.03x median=45.10x CV=1.29 max=2723.9x)
# - user asked to verify these numbers are accurate/stable at larger N
# before treating them as final.
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50000

    m._SWEEP4_WEIGHTS = [35, 30, 25, 10]
    CASES = [
        ("hp75_dmg100", [75, 75, 100, 100, 100], 1.00),
        ("hp75_dmg130", [75, 75, 100, 100, 100], 1.30),
        ("hp100_dmg100", [100, 100, 100, 100, 100], 1.00),
    ]
    seed = 860000
    for tag, hp, dmg in CASES:
        m.measure(n, seed, f"confirm50k_{tag}", "sweep4", hp, dmg, save_csv=True)
        seed += 1

import sys
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch")
import normal_3param_matrix_test as m

# Chain-break "none"-weight tuning alone was already proven insufficient
# at HP200 (median pinned 94-96x across none=10..70, dmg=1.0, vs target
# ~53-55x). Damage controls kill-speed (how many stages clear before HP
# runs out / safety cap), not just a flat payout multiplier, so it might
# move median where chain-break severity couldn't. Test HP200 + best-shape
# none% (25/40/55, from the earlier sweep) x a real damage-reduction range
# to search for a combo landing within ~99% of the loved hp75+dmg30%
# numbers: mean=80.14x median=52.80x ratio=65.9% CV=1.32 zero=0.78%.
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000

    CASES = [
        ("none25_dmg70", 25, 0.70),
        ("none25_dmg55", 25, 0.55),
        ("none25_dmg40", 25, 0.40),
        ("none40_dmg60", 40, 0.60),
        ("none40_dmg45", 40, 0.45),
        ("none40_dmg35", 40, 0.35),
        ("none55_dmg50", 55, 0.50),
        ("none55_dmg35", 55, 0.35),
        ("none55_dmg25", 55, 0.25),
    ]
    seed = 930000
    for tag, np, dmg in CASES:
        rest = (100 - np) / 3
        m._SWEEP4_WEIGHTS = [rest, rest, rest, np]
        m.measure(n, seed, f"hp200_{tag}", "sweep4", [200, 200, 200, 200, 200], dmg, save_csv=True)
        seed += 1

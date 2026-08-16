import sys
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch")
import normal_3param_matrix_test as m

# Full 3-param grid: lightest-tier weight% x HP x damage together, informed
# by the two single-axis sweeps (lightest%=20 -> mean=82.52/ratio=92.6/
# CV=0.78; lightest%~77 -> mean=90.80/ratio=83.6/CV=0.90 - both mean AND
# shape improve together as lightest% rises, so the fix for "mean overshoots
# 85x at high lightest%" is to back HP/damage off slightly, not to avoid
# high lightest% at all). Standalone so it doesn't duplicate the
# still-running 6-point single-axis sweep in normal_3param_matrix_test.py's
# own __main__.
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000

    LP_GRID = [40, 55, 70]
    HP_GRID = [("hp110", [110, 110, 110, 110, 110]), ("hp125", [125, 125, 125, 125, 125])]
    DMG_GRID = [1.00, 1.05, 1.10]
    seed = 830000
    for lp in LP_GRID:
        rest = (100 - lp) / 2
        for hp_tag, hp in HP_GRID:
            for dmg in DMG_GRID:
                m._SWEEP_WEIGHTS = [rest, rest, lp]
                tag = f"grid3_lp{lp}_{hp_tag}_dmg{int(dmg*100)}"
                m.measure(n, seed, tag, "sweep", hp, dmg, save_csv=True)
                seed += 1

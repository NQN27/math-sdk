import sys
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch")
import normal_3param_matrix_test as m

# Key finding from sweep4: median is HP-driven, not CB-severity-driven (all
# 4 weight combos at HP125 gave median~75-76x regardless of curve
# strictness). To hit median 40-50x (per user's ask) while keeping the new
# big-max "none" tier AND landing mean back near 80-85x, drop HP back to
# 75-100 (known to give median ~40-44x from earlier single-lever tests)
# and use damage as the mean-compensation knob, since HP alone in that
# range won't reach 80-85x mean by itself.
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000

    m._SWEEP4_WEIGHTS = [35, 30, 25, 10]  # moderate std/lighter/lightest + 10% none
    HP_OPTIONS = [
        ("hp75", [75, 75, 100, 100, 100]),
        ("hp100", [100, 100, 100, 100, 100]),
    ]
    DMG_OPTIONS = [1.0, 1.3, 1.6, 2.0]
    seed = 850000
    for hp_tag, hp in HP_OPTIONS:
        for dmg in DMG_OPTIONS:
            tag = f"medtarget_{hp_tag}_dmg{int(dmg*100)}"
            m.measure(n, seed, tag, "sweep4", hp, dmg, save_csv=True)
            seed += 1

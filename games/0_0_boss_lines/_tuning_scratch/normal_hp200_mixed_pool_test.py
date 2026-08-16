import sys
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch")
import normal_3param_matrix_test as m

# Candidate so far uses a FLAT hp=[200]*5 pool for testing convenience, but
# production's actual convention (bonus_player_hp_choices) is always a
# MIXED pool (e.g. current prod [50,50,50,100,100]) giving session-to-
# session HP variance. Check whether a mixed pool centered on 200 changes
# the confirmed shape at all before treating flat-200 as final, since we
# haven't actually tested that this simplification is harmless.
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000

    CASES = [
        ("flat200", [200, 200, 200, 200, 200]),
        ("mixed_175_225", [175, 175, 200, 225, 225]),
        ("mixed_150_250", [150, 175, 200, 225, 250]),
        ("mixed_current_style", [150, 150, 150, 250, 250]),
    ]
    seed = 990000
    for tag, hp in CASES:
        m._SWEEP4_WEIGHTS = [20, 20, 20, 40]
        m.measure(n, seed, f"hp200_pool_{tag}", "sweep4", hp, 0.45, save_csv=True)
        seed += 1

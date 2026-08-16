import sys
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch")
import normal_3param_matrix_test as m

# User's actual design intent, stated directly: at HP75, back-to-back dead
# spins can end a WHOLE bonus session in just 2-3 internal spins - a bad
# experience regardless of what the payout math says. Wants HP=200 (so a
# session can't die that fast even on bad luck) with a STRONGER
# connection-triggered chain-break to compensate the extra mean/survival
# HP=200 buys - similar to the earlier combo_chainbreak_hp200 test, but
# redone with everything learned since (4-tier weighted pool incl. a
# "none"/uncapped tail slice) so it doesn't repeat that test's "too flat"
# failure (CV=0.55, ratio=104.5%).
# Since HP=200 alone already pushes mean way up (134.19x with zero
# chain-break), no damage bump needed here - the compensating lever is
# making the "standard"/"lighter" curves carry MORE weight (stricter cut on
# the now much-larger population of long chains) while keeping a modest
# "none" slice for the rare-jackpot tail.
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000

    WEIGHT_COMBOS = [
        ("w35_30_25_10", [35, 30, 25, 10]),
        ("w50_25_15_10", [50, 25, 15, 10]),
        ("w60_20_10_10", [60, 20, 10, 10]),
        ("w70_15_10_5", [70, 15, 10, 5]),
    ]
    seed = 870000
    for tag, weights in WEIGHT_COMBOS:
        m._SWEEP4_WEIGHTS = weights
        m.measure(n, seed, f"hp200_sweep4_{tag}", "sweep4",
                  [200, 200, 200, 200, 200], 1.00, save_csv=True)
        seed += 1

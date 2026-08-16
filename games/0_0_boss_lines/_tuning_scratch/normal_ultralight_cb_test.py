import sys
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch")
from normal_chainbreak_hp_combined_test import measure, STAGE_GROUPS_ULTRALIGHT

# Standalone run of just the ultralight-CB variants, so this doesn't
# duplicate the separately-running 7-variant creative batch (task
# bzyex2y22) which also lives in normal_chainbreak_hp_combined_test.py's
# __main__ block.
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000

    measure(n, 700050, "ultralight_cb_alone", use_chainbreak=True,
            hp_choices=[50, 50, 50, 100, 100], curve=STAGE_GROUPS_ULTRALIGHT, save_csv=True)

    measure(n, 700051, "ultralight_cb_hp75", use_chainbreak=True,
            hp_choices=[75, 75, 100, 100, 100], curve=STAGE_GROUPS_ULTRALIGHT, save_csv=True)

    measure(n, 700052, "ultralight_cb_hp100", use_chainbreak=True,
            hp_choices=[100, 100, 100, 100, 100], curve=STAGE_GROUPS_ULTRALIGHT, save_csv=True)

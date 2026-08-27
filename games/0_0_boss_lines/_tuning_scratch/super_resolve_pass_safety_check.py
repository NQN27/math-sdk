"""Safety follow-up to super_normal_idea_experiment.py's condition D (Normal's
wild% taper + Super's real 35% power fraction + endless ON) - this specific
combo (high wild% WITH Power) has never existed in production before: Normal
runs 23% wild with 0% power, Super used to run 8% wild with 35% power, but
this candidate runs 23% wild WITH 35% power for the first time. The project's
own history (gen_stage_reels.py's STAGE_WILD_PCT comment) already found that
high-wild% + power-fraction combos can push the cascade resolve loop into
max_resolve_passes territory (that's why Hidden's taper got scaled down
0.769x after measuring ~0.5-2% hit-rate at 6.5%/55%pow) - so this checks the
same thing for this new Super candidate before treating its payout numbers
as usable, not just trusting the mean/median looked good.

Reuses the exact scratch reel files super_normal_idea_experiment.py already
wrote to _tuning_scratch/super_normal_idea/ (run that script first).
"""
import sys
import os
import random
import warnings

sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

SCRATCH_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch\super_normal_idea"
SUPER_STAGES = [2, 3, 4, 5, 6]

_orig_run_one_spin = gamestate_mod.GameState.run_one_bonus_spin
_counts = {"internal_spins": 0}


def hooked_run_one_spin(self, both_ways):
    _counts["internal_spins"] += 1
    return _orig_run_one_spin(self, both_ways)


gamestate_mod.GameState.run_one_bonus_spin = hooked_run_one_spin


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000

    config = game_config_mod.GameConfig()
    for stage in SUPER_STAGES:
        path = os.path.join(SCRATCH_DIR, f"Super_BM_S{stage}_pow35.csv")
        config.reels[f"Super_BM_S{stage}"] = config.read_reels_csv(path)
    config.stage6_endless_tiers = dict(config.stage6_endless_tiers)
    config.stage6_endless_tiers["super"] = True

    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    hits = 0
    max_passes_seen_via_warning = 0
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(992000 * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session("super")
        for w in caught:
            msg = str(w.message)
            if "Hit max_resolve_passes" in msg:
                hits += 1

    total_internal_spins = _counts["internal_spins"]
    print(f"n={n} sessions, {total_internal_spins} total internal bonus spins")
    print(f"max_resolve_passes hits: {hits} ({100*hits/total_internal_spins:.3f}% of internal spins)")
    if hits == 0:
        print("SAFE at this n - zero hits observed.")
    else:
        print(f"NOT proven safe - {hits} hit(s) observed, matches the historical risk pattern.")


if __name__ == "__main__":
    main()

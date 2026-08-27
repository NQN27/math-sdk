"""Candidate 3: test whether CONCENTRATING the chest EV into a narrow value
band (instead of spreading across 6 values like Normal/Candidate 2) is
enough to produce a visible third peak against Super's dominant, smooth
line-pay background (75% of total mean, unlike Normal where reward-drop
dominates at ~72% - see super_reward_redesign_v2.py's finding: a shape-
copy of Normal's spread-out chest did NOT produce a visible bump).

Keeps Candidate 2's LOW/MID pool UNCHANGED (that part already landed
close to target: mean=249.82x/median=168.70x vs 266.84x/178.40x) - only
replaces the 6 spread chest values with a concentrated cluster around
~1000x carrying similar total chest weight, to isolate concentration as
the variable being tested.
"""
import sys, random, statistics, warnings, time
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Candidate 2's LOW/MID pool (unchanged) + a concentrated chest cluster
# replacing the old spread 239.4/299.2/478.8/897.8/1496.2/2394 values.
LOW_MID = {
    0.6: 150, 1.2: 120, 1.8: 380, 2.4: 300, 3: 320, 3.6: 260, 4.8: 210,
    6: 110, 7.2: 85, 9: 65, 10.8: 48, 12: 60, 15: 44, 18: 36,
    20.9: 29.3, 23.9: 24.1, 29.9: 19.6, 35.9: 16.1, 47.9: 13.2,
    59.9: 10.8, 71.8: 8.8, 89.8: 7.2, 107.7: 5.0, 119.7: 4.1,
    149.6: 2.0, 179.6: 1.7, 209.5: 1.4, 359.1: 0.8, 598.5: 0.5,
}
# Concentrated chest: same total weight sum as Candidate 2's chest
# (15+8+4+0.9+0.35+0.12=28.37), redistributed onto 3 nearby values around
# 900-1100x instead of spread 239-2394x.
CHEST = {900: 15, 1000: 8, 1100: 5.37}


def measure(n, seed_offset, tag, low_mid, chest):
    weights = dict(low_mid)
    weights.update(chest)
    chest_tiers = set(chest.keys())

    config = game_config_mod.GameConfig()
    config.reward_drop_weights_super_bonus = weights
    config.reward_drop_top_tiers_super_bonus = chest_tiers
    config.reward_drop_stage6_last_tiers_super_bonus = chest_tiers

    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals = []
    t0 = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session("super")
            totals.append(gs.win_manager.running_bet_win)

    mean = sum(totals) / n
    median = statistics.median(totals)
    print(f"\n=== {tag} (n={n}, {time.time()-t0:.1f}s) ===")
    print(f"mean={mean:.2f}x median={median:.2f}x ratio={100*median/mean:.1f}% max={max(totals):.2f}x")
    with open("super_cand3_payouts.txt", "w") as f:
        for t in totals:
            f.write(f"{t}\n")
    return totals


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    measure(n, 994400, "CANDIDATE_3_concentrated_chest", LOW_MID, CHEST)

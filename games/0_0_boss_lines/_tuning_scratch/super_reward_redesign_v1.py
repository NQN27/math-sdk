"""Candidate 1 for reshaping Super Bonus's reward-drop table into a
Normal-style 3-peak (LOW/MID + exclusive CHEST) shape, per the game
designer's request: "i like the mean and median but the distribution i
want it alike the normal bonus with 3 vertices."

Key finding from payout_component_split_super.py (n=8000, real production):
Super's CURRENT total mean=261.58x splits line-pay=197.12x (75.4%) vs
reward-drop=64.46x (24.6%) - the OPPOSITE ratio from what Normal's own
economy likely has (Normal's reward-drop dominates, ~72% of its 80.85x
mean, since line-pay alone is only ~23x there). This matters: the
reward-table lever can only ever move the reward-drop slice, and that
slice is much smaller relative to Super's total than it is for Normal's -
so a value-for-value copy of Normal's table onto Super, without accounting
for how much MORE OFTEN Super rolls from it (Super survives far more
spins/boss-kills per session than Normal on average), would likely
overshoot Super's mean well past 266.84x.

Step 1 (this script): plug NORMAL's exact reward_drop_weights_normal_bonus
table (same values, same weights, same top/chest tier sets) into Super's
roll_reward_drop branch, in-memory only, and measure what Super's mean/
median/shape becomes. This empirically measures the "roll-frequency
effect" (how much richer Super's reward-drop total gets from the SAME
table, purely because Super's sessions are longer) before deciding how
much to rescale values down to hit budget.
"""
import sys, random, statistics, warnings, time
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager


def measure(n, seed_offset, tag, weights, top_tiers, stage6_last_tiers):
    config = game_config_mod.GameConfig()
    config.reward_drop_weights_super_bonus = dict(weights)
    config.reward_drop_top_tiers_super_bonus = set(top_tiers)
    config.reward_drop_stage6_last_tiers_super_bonus = set(stage6_last_tiers)

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
    return totals


NORMAL_WEIGHTS = {
    1: 150, 2: 120, 3: 380, 4: 300, 5: 320, 6: 260, 8: 210,
    10: 110, 12: 85, 15: 65, 18: 48, 20: 60, 25: 44,
    30: 36, 35: 29.3, 40: 24.1, 50: 19.6, 60: 16.1, 80: 13.2,
    100: 10.8, 120: 8.8, 150: 7.2, 180: 5.0, 200: 4.1, 250: 2.0,
    300: 1.7, 350: 1.4, 600: 0.8, 1000: 0.5,
    400: 15, 500: 8, 800: 4, 1500: 0.9, 2500: 0.35, 4000: 0.12,
}
NORMAL_TOP = {400, 500, 800, 1500, 2500, 4000}
NORMAL_CHEST = {400, 500, 800, 1500, 2500, 4000}

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    measure(n, 994200, "CANDIDATE_1_normal_table_as_is_on_super", NORMAL_WEIGHTS, NORMAL_TOP, NORMAL_CHEST)

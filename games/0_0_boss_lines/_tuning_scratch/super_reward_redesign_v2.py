"""Candidate 2: Normal's exact reward-table SHAPE (weights unchanged),
values rescaled by K so Super's reward-drop component lands near its
current ~64.46x budget (preserving overall mean~261-267x/median~178-220x
depending on how the ratio comes out) - same K-rescale technique Normal's
own table went through once (2026-08-18, before the SEG1-7 redesign).

K = target_reward_drop_mean / candidate1_reward_drop_mean
  = 64.46 / (304.84 - 197.12) = 64.46 / 107.72 ~= 0.5985

Values rounded to sensible precision after scaling. top_tiers/
stage6_last_tiers rescaled by the same K (they reference VALUES not
indices - same caution documented in game_config.py's own K=4.28 history).
"""
import sys, random, statistics, warnings, time
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

NORMAL_WEIGHTS = {
    1: 150, 2: 120, 3: 380, 4: 300, 5: 320, 6: 260, 8: 210,
    10: 110, 12: 85, 15: 65, 18: 48, 20: 60, 25: 44,
    30: 36, 35: 29.3, 40: 24.1, 50: 19.6, 60: 16.1, 80: 13.2,
    100: 10.8, 120: 8.8, 150: 7.2, 180: 5.0, 200: 4.1, 250: 2.0,
    300: 1.7, 350: 1.4, 600: 0.8, 1000: 0.5,
    400: 15, 500: 8, 800: 4, 1500: 0.9, 2500: 0.35, 4000: 0.12,
}
NORMAL_CHEST = {400, 500, 800, 1500, 2500, 4000}

K = 0.5985


def rescale(weights, chest, k):
    new_weights = {}
    for v, w in weights.items():
        new_v = round(v * k, 1)
        if new_v == int(new_v):
            new_v = int(new_v)
        new_weights[new_v] = new_weights.get(new_v, 0) + w  # merge on collision, same as Normal's own history
    new_chest = set()
    for v in chest:
        new_v = round(v * k, 1)
        if new_v == int(new_v):
            new_v = int(new_v)
        new_chest.add(new_v)
    return new_weights, new_chest


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
    with open("super_cand2_payouts.txt", "w") as f:
        for t in totals:
            f.write(f"{t}\n")
    return totals


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    w, chest = rescale(NORMAL_WEIGHTS, NORMAL_CHEST, K)
    print("rescaled weights:", w)
    print("rescaled chest tiers:", sorted(chest))
    measure(n, 994300, f"CANDIDATE_2_normal_shape_K={K}", w, chest, chest)

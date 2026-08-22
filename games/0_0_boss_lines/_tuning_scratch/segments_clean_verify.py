"""Clean, zero-contamination re-verification of reshape_segments_test.py's
7-segment reward-drop table (the design the user accepted). Applies ONLY the
reward-table/weights/pruned-tiers/maxwin-weight config changes on a real,
UNMODIFIED GameConfig() - real bonus_player_hp_choices ([50,50,50,100,100]
for Normal, untouched), real unscaled boss_stage_table, NO monkeypatch of
create_board_reelstrips/tumble_board (so no scratch-only chain-break), NO
run_one_bonus_spin override. Pure `run_bonus_session("normal")`, exactly the
real production code path.
"""
import json
import statistics
import sys
import warnings
import random

sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

SEG1 = {1: 150, 2: 120}
SEG2 = {3: 380, 4: 300}
SEG3 = {5: 320, 6: 260, 8: 210}
SEG4 = {10: 110, 12: 85, 15: 65, 18: 48}
SEG5 = {20: 60, 25: 44}
SEG6 = {
    30: 36, 35: 29.3, 40: 24.1, 50: 19.6, 60: 16.1, 80: 13.2, 100: 10.8,
    120: 8.8, 150: 7.2, 180: 5.0, 200: 4.1, 250: 2.0, 300: 1.7, 350: 1.4,
    400: 1.1, 500: 0.9, 600: 0.8, 800: 0.6, 1000: 0.5,
}
SEG7_CHEST = {400: 15, 500: 8, 800: 4, 1500: 0.9, 2500: 0.35, 4000: 0.12}
REGULAR_WEIGHTS = {**SEG1, **SEG2, **SEG3, **SEG4, **SEG5, **SEG6}
PRUNE_SCHEDULE = {1: list(SEG1), 2: list(SEG2), 3: list(SEG3), 4: list(SEG4), 5: list(SEG5), 6: []}

_original_clear_stage = gamestate_mod.GameState.clear_stage


def patched_clear_stage(self, stage):
    self._diag_max_stage = max(getattr(self, "_diag_max_stage", 1), stage)
    result = _original_clear_stage(self, stage)
    self._diag_max_stage = max(getattr(self, "_diag_max_stage", 1), getattr(self, "stage", stage))
    return result


gamestate_mod.GameState.clear_stage = patched_clear_stage


def build_config(maxwin_weight):
    config = game_config_mod.GameConfig()
    # deliberately NOT touching bonus_player_hp_choices or boss_stage_table -
    # real production values stay exactly as shipped.
    config.reward_drop_weights_normal_bonus = {**REGULAR_WEIGHTS, **SEG7_CHEST}
    config.reward_drop_top_tiers_normal_bonus = set(SEG7_CHEST)
    config.reward_drop_stage6_last_tiers_normal_bonus = set(SEG7_CHEST)
    config.stage_clear_pruned_tiers = PRUNE_SCHEDULE
    config.stage6_chest_natural_maxwin_weight = maxwin_weight
    return config


def measure(n, seed_offset, maxwin_weight):
    config = build_config(maxwin_weight)
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals, max_stages = [], []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs._diag_max_stage = 1
            gs.run_bonus_session("normal")
            totals.append(gs.win_manager.running_bet_win)
            max_stages.append(gs._diag_max_stage)

    mean = sum(totals) / n
    median = statistics.median(totals)
    ratio = 100 * median / mean if mean > 0 else 0
    sorted_t = sorted(totals)

    def pct(p):
        return sorted_t[min(n - 1, int(p * n))]

    s6_rate = 100 * sum(1 for s in max_stages if s >= 6) / n

    result = {
        "n": n, "seed_offset": seed_offset, "maxwin_weight": maxwin_weight,
        "mean": round(mean, 4), "median": round(median, 4), "ratio": round(ratio, 2),
        "stage6_reach_pct": round(s6_rate, 3),
        "percentiles": {f"p{p*100:g}": round(pct(p), 2) for p in
                         [0.10, 0.25, 0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99, 0.995, 0.999]},
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 950001
    mw = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0651
    measure(n, seed, mw)

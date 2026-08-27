"""Re-tune Normal Bonus reward-drop shape (LOW/MID scale 'a', CHEST/TOP scale
'b') against the REAL, unmodified production config - no HP_POOL/HP_MULT
override of any kind (bonus_player_hp_choices/boss_stage_table exactly as
shipped in game_config.py). This corrects the earlier shape-redesign session,
which measured its "final" shape numbers under a fake HP_POOL=[200]*5 +
massively-scaled boss table that was never actually shipped - see
project_boss_lines_normal_bonus_shape_done.md's 2026-08-22 correction.

a scales the 12 regular (LOW/MID) tier VALUES, b scales the 9 stage6-chest
(CHEST/TOP) tier VALUES - same technique as the original redesign, just
measured on the real, correct baseline this time. Weights are left untouched
(only values move) - same convention as final_combined_candidate.py's
build_config(K, stage6_boost).
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

_original_clear_stage = gamestate_mod.GameState.clear_stage


def patched_clear_stage(self, stage):
    self._diag_max_stage = max(getattr(self, "_diag_max_stage", 1), stage)
    result = _original_clear_stage(self, stage)
    self._diag_max_stage = max(getattr(self, "_diag_max_stage", 1), getattr(self, "stage", stage))
    return result


gamestate_mod.GameState.clear_stage = patched_clear_stage


def build_config(a, b):
    config = game_config_mod.GameConfig()
    base = config.reward_drop_weights_normal_bonus
    exclusive = set(config.reward_drop_stage6_last_tiers_normal_bonus)
    new_weights = {}
    remap = {}
    for k, w in base.items():
        nk = round(k * (b if k in exclusive else a), 4)
        new_weights[nk] = w
        remap[k] = nk
    config.reward_drop_weights_normal_bonus = new_weights
    config.reward_drop_top_tiers_normal_bonus = {remap[k] for k in config.reward_drop_top_tiers_normal_bonus}
    config.reward_drop_stage6_last_tiers_normal_bonus = {remap[k] for k in config.reward_drop_stage6_last_tiers_normal_bonus}
    return config


def measure(n, seed_offset, a, b, tag):
    config = build_config(a, b)
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
    s6_mask = [t for t, s in zip(totals, max_stages) if s >= 6]
    s6_rate = 100 * len(s6_mask) / n
    avg_if_s6 = sum(s6_mask) / len(s6_mask) if s6_mask else 0
    result = {
        "tag": tag, "a": a, "b": b, "n": n,
        "mean": round(mean, 4), "median": round(median, 4), "ratio": round(ratio, 2),
        "stage6_reach_pct": round(s6_rate, 2), "avg_if_stage6": round(avg_if_s6, 2),
    }
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    n = int(sys.argv[1])
    seed_offset = int(sys.argv[2])
    a = float(sys.argv[3])
    b = float(sys.argv[4])
    tag = sys.argv[5] if len(sys.argv) > 5 else f"a{a}_b{b}"
    measure(n, seed_offset, a, b, tag)

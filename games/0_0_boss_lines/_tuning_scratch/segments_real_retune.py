"""Retune the SEG1-7-style Normal Bonus table against REAL production
settings (real HP pool, real unscaled boss table, no chain-break, no
monkeypatch). Keeps the segment/chest STRUCTURE (nice-integer style, chest
as an exclusive second peak) but exposes 3 independent scale factors so the
real-conditions mean/shape can actually be hit:
  r = scale on seg1-5 values (the "early/mid" regular-pool population)
  s = scale on seg6 values (the "big tail" regular-pool population, 30-1000)
  b = scale on chest values (the stage6-exclusive second peak)
Weights are untouched throughout - only values move, same convention as
every other retune in this project.
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
CHEST = {400: 15, 500: 8, 800: 4, 1500: 0.9, 2500: 0.35, 4000: 0.12}
LOWMID = {**SEG1, **SEG2, **SEG3, **SEG4, **SEG5}

_original_clear_stage = gamestate_mod.GameState.clear_stage


def patched_clear_stage(self, stage):
    self._diag_max_stage = max(getattr(self, "_diag_max_stage", 1), stage)
    result = _original_clear_stage(self, stage)
    self._diag_max_stage = max(getattr(self, "_diag_max_stage", 1), getattr(self, "stage", stage))
    return result


gamestate_mod.GameState.clear_stage = patched_clear_stage


def build_config(r, s, b, maxwin_weight):
    config = game_config_mod.GameConfig()
    regular = {}
    remap = {}
    for k, w in LOWMID.items():
        nk = round(k * r, 4)
        regular[nk] = w
        remap[k] = nk
    for k, w in SEG6.items():
        nk = round(k * s, 4)
        regular[nk] = w
        remap[k] = nk
    chest = {}
    for k, w in CHEST.items():
        nk = round(k * b, 4)
        chest[nk] = w
        remap[k] = nk

    config.reward_drop_weights_normal_bonus = {**regular, **chest}
    config.reward_drop_top_tiers_normal_bonus = set(chest)
    config.reward_drop_stage6_last_tiers_normal_bonus = set(chest)
    config.stage_clear_pruned_tiers = {
        1: [remap[k] for k in SEG1], 2: [remap[k] for k in SEG2],
        3: [remap[k] for k in SEG3], 4: [remap[k] for k in SEG4],
        5: [remap[k] for k in SEG5], 6: [],
    }
    config.stage6_chest_natural_maxwin_weight = maxwin_weight
    return config


def measure(n, seed_offset, r, s, b, maxwin_weight, tag):
    config = build_config(r, s, b, maxwin_weight)
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

    s6_rate = 100 * sum(1 for x in max_stages if x >= 6) / n
    result = {
        "tag": tag, "r": r, "s": s, "b": b, "n": n,
        "mean": round(mean, 4), "median": round(median, 4), "ratio": round(ratio, 2),
        "stage6_reach_pct": round(s6_rate, 2),
        "p75": round(pct(0.75), 2), "p90": round(pct(0.90), 2), "p99": round(pct(0.99), 2),
    }
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    n = int(sys.argv[1])
    seed = int(sys.argv[2])
    r = float(sys.argv[3])
    s = float(sys.argv[4])
    b = float(sys.argv[5])
    mw = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0651
    tag = sys.argv[7] if len(sys.argv) > 7 else f"r{r}_s{s}_b{b}"
    measure(n, seed, r, s, b, mw, tag)

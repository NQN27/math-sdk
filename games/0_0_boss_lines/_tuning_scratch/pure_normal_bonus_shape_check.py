"""Pure production ground truth for Normal Bonus, WITH stage-reach tracking,
to check whether the shipped bonus_player_hp_choices/boss_stage_table (as
literally written in game_config.py right now) reproduces the validated
shape-redesign numbers (mean=85.00x, median=30.60x, ratio=36.0%,
avg-payout-if-stage6+=243.6x) or diverges from them.

Same no-monkeypatch-of-game-logic philosophy as pure_production_diagnostic.py:
only a clear_stage wrapper to observe max stage reached (does not change
behavior). No HP_POOL/HP_MULT override of any kind - literal unmodified
GameConfig().
"""
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


def measure(n, seed_offset):
    config = game_config_mod.GameConfig()
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals = []
    max_stages = []
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
    stage6_mask = [t for t, s in zip(totals, max_stages) if s >= 6]
    stage_dist = {s: 100 * sum(1 for x in max_stages if x == s) / n for s in range(1, 7)}
    avg_if_s6 = sum(stage6_mask) / len(stage6_mask) if stage6_mask else 0
    print(f"n={n} seed_offset={seed_offset}")
    print(f"mean={mean:.4f}x  median={median:.4f}x  ratio={ratio:.1f}%")
    print("stage reached distribution: " + ", ".join(f"s{s}={stage_dist[s]:.2f}%" for s in range(1, 7)))
    print(f"stage6+ reach rate: {100*len(stage6_mask)/n:.2f}%  avg-payout-if-stage6+={avg_if_s6:.2f}x")
    return mean, median, ratio


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    measure(n, 920001)

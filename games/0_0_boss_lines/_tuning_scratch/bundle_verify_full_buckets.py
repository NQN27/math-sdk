"""Full-bundle verification with the per-stage bucket breakdown (% of
sessions / mean / median / max, keyed by max-stage-reached) that the user's
accepted overnight session reported, so it can be compared bucket-by-bucket
instead of just overall mean/percentiles. Real, UNMODIFIED game_config.py -
chain-block/HP=200/boss table/SEG1-7 reward table are all now shipped
production code, so no overrides are applied here at all."""
import json
import statistics
import sys
import warnings
import random
from collections import defaultdict

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
    by_stage = defaultdict(list)
    maxwin_hits = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs._diag_max_stage = 1
            gs.run_bonus_session("normal")
            total = gs.win_manager.running_bet_win
            totals.append(total)
            by_stage[gs._diag_max_stage].append(total)
            if getattr(gs, "wincap_triggered", False):
                maxwin_hits += 1

    mean = sum(totals) / n
    median = statistics.median(totals)
    ratio = 100 * median / mean if mean > 0 else 0
    sorted_t = sorted(totals)

    def pct(p):
        return sorted_t[min(n - 1, int(p * n))]

    result = {
        "n": n, "seed_offset": seed_offset,
        "mean": round(mean, 2), "median": round(median, 2), "ratio": round(ratio, 2),
        "percentiles": {f"p{p*100:g}": round(pct(p), 2) for p in
                         [0.10, 0.25, 0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99, 0.995, 0.999]},
        "buckets": {},
        "maxwin_hits": maxwin_hits,
        "maxwin_1_in": (n / maxwin_hits) if maxwin_hits else None,
    }
    for stage in sorted(by_stage):
        vals = by_stage[stage]
        result["buckets"][stage] = {
            "pct_sessions": round(100 * len(vals) / n, 2),
            "mean": round(sum(vals) / len(vals), 2),
            "median": round(statistics.median(vals), 2),
            "max": round(max(vals), 2),
            "count": len(vals),
        }
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 990001
    measure(n, seed)

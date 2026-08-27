"""A/B isolation test: does chain-block or the chest/reward-table cause the
stage-6 reach-rate shortfall (measured 1.42% vs target 1.86%)? Runs the SAME
seeds through the real, unmodified game_config.py twice - once with
chain-block exactly as shipped, once with chain_block_step forced to 0.0
(cleanly disables the reactive mechanic: chance = min(1, 0*(extra+1)) = 0
always, so _maybe_apply_chain_block's roll never succeeds and no column is
ever forced dead - everything else, including the reward table/chest/maxwin
weight, stays byte-identical). If the OFF run's stage-6 reach rate recovers
to ~1.86%, chain-block is the cause; if it's still ~1.4%, the chest/reward
table (or something else) is."""
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


def measure(n, seed_offset, chain_block_step, tag, chain_block_threshold=2):
    config = game_config_mod.GameConfig()
    config.chain_block_step = chain_block_step  # 0.0 = fully disabled, else real shipped value
    config.chain_block_threshold = chain_block_threshold
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
    sorted_t = sorted(totals)

    def pct(p):
        return sorted_t[min(n - 1, int(p * n))]

    result = {
        "tag": tag, "n": n, "chain_block_step": chain_block_step, "chain_block_threshold": chain_block_threshold,
        "mean": round(mean, 2), "median": round(median, 2),
        "p95": round(pct(0.95), 2), "p99": round(pct(0.99), 2), "p99.5": round(pct(0.995), 2),
        "maxwin_hits": maxwin_hits,
        "stage_reach_pct": {s: round(100 * len(v) / n, 2) for s, v in sorted(by_stage.items())},
        "stage_mean": {s: round(sum(v) / len(v), 2) for s, v in sorted(by_stage.items())},
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 995001
    step = float(sys.argv[3]) if len(sys.argv) > 3 else 0.30
    tag = sys.argv[4] if len(sys.argv) > 4 else ("ON" if step > 0 else "OFF")
    threshold = int(sys.argv[5]) if len(sys.argv) > 5 else 2
    measure(n, seed, step, tag, threshold)

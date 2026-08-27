"""Split running_bet_win into reward-drop cash vs line-pay cash, to find out
how much of the Python mean (~84-86x) comes from each source - directly
answering whether the JS demo's missing line-pay mechanic explains the
45.37x vs 84.36x gap on its own, per advisor's measure-before-you-build
guidance.

Hooks GameState.on_boss_defeated (whichever ancestor actually defines it -
setting the attribute on the GameState subclass itself overrides for all
instances regardless of MRO) to snapshot running_bet_win before/after the
reward-drop's award_win call happens inside it; the delta is reward cash.
Everything else added to running_bet_win this session is line-pay (+ any
Wild/Global Multi scaling, though production's Normal-tier reels (BM_Reels_S1-6)
contain zero PWM/PGM/PMX symbols, confirmed via grep, so for Normal Bonus
specifically those multipliers are always inert - effective_global_mult()
always returns 1, no wild_multi_rolls ever populated).
"""
import json
import os
import statistics
import sys
import time
import warnings
import random

sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import reshape_segments_test as seg

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

fc = seg.fc
gs_cls = fc.gamestate_mod.GameState
_orig_on_boss_defeated = gs_cls.on_boss_defeated

_reward_cash_this_session = {"v": 0.0}


def _patched_on_boss_defeated(self, boss_id):
    before = self.win_manager.running_bet_win
    _orig_on_boss_defeated(self, boss_id)
    after = self.win_manager.running_bet_win
    _reward_cash_this_session["v"] += (after - before)


gs_cls.on_boss_defeated = _patched_on_boss_defeated


def measure_split(n, seed_offset, maxwin_weight):
    config = seg.build_config_segments(maxwin_weight)
    gs = fc.gamestate_mod.GameState(config)
    gs.win_manager = fc.WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals = []
    reward_cash = []
    line_cash = []

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            fc._state["max_stage"] = 1
            fc._state["spins"] = 0
            fc._state["pass_count"] = 0
            fc._state["chain_block_pending"] = False
            fc._state["general_chance"] = 0.0
            fc._state["chain_break_threshold"] = 2
            fc._state["chain_break_step"] = 0.30
            _reward_cash_this_session["v"] = 0.0
            gs.run_bonus_session("normal")
            total = gs.win_manager.running_bet_win
            rc = _reward_cash_this_session["v"]
            totals.append(total)
            reward_cash.append(rc)
            line_cash.append(total - rc)

    def stats(arr):
        return dict(mean=sum(arr) / len(arr), median=statistics.median(arr))

    result = dict(
        n=n, seed_offset=seed_offset,
        total=stats(totals), reward_cash=stats(reward_cash), line_cash=stats(line_cash),
        reward_frac_of_mean=stats(reward_cash)["mean"] / stats(totals)["mean"],
        line_frac_of_mean=stats(line_cash)["mean"] / stats(totals)["mean"],
    )
    print(json.dumps(result, indent=2))
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(RESULTS_DIR, f"cash_split_n{n}_{ts}.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nsaved -> {out_path}")
    return result


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 501001
    measure_split(n, seed, 0.0651)

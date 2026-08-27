"""Pure production ground-truth mean payout for a Normal Bonus session.

Same no-monkeypatch philosophy as pure_production_diagnostic.py (no
chain-break, no run_one_bonus_spin override, no config value/weight
rescaling of any kind) - just a totally unmodified GameConfig() +
GameState.run_bonus_session("normal") called directly, exactly the real
production code path. This measures win_manager.running_bet_win instead of
spin/stage counters, to answer "what does the reward_drop_weights_normal_bonus
table plus real session mechanics actually average, right now, on disk."
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


def measure(n, seed_offset):
    config = game_config_mod.GameConfig()
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session("normal")
            totals.append(gs.win_manager.running_bet_win)

    mean = sum(totals) / n
    median = statistics.median(totals)
    ratio = 100 * median / mean if mean > 0 else 0
    zero_pct = 100 * sum(1 for t in totals if t == 0) / n
    p95 = statistics.quantiles(totals, n=100)[94]
    p99 = statistics.quantiles(totals, n=100)[98]
    print(f"n={n} seed_offset={seed_offset}")
    print(f"mean={mean:.4f}x  median={median:.4f}x  ratio={ratio:.1f}%")
    print(f"p95={p95:.2f}x  p99={p99:.2f}x  max={max(totals):.2f}x  zero%={zero_pct:.2f}")
    return mean


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30000
    means = [measure(n, seed) for seed in (910001, 910002, 910003)]
    print(f"\n3-seed means: {[round(m,3) for m in means]}  avg={sum(means)/len(means):.4f}x")

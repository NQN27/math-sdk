"""Full-bundle verification (real, unmodified game_config.py - chain-block,
HP=200, boss table, SEG1-7 reward table are all now shipped production code)
with Max Win trigger rate included, per this project's standing "always
report Max Win rate" convention."""
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
    maxwin_hits = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session("normal")
            totals.append(gs.win_manager.running_bet_win)
            if getattr(gs, "wincap_triggered", False):
                maxwin_hits += 1

    mean = sum(totals) / n
    median = statistics.median(totals)
    ratio = 100 * median / mean if mean > 0 else 0
    sorted_t = sorted(totals)

    def pct(p):
        return sorted_t[min(n - 1, int(p * n))]

    print(f"n={n} seed_offset={seed_offset}  [REAL, UNMODIFIED game_config.py, chain-block ON]")
    print(f"mean={mean:.2f}x median={median:.2f}x ratio={ratio:.1f}%")
    for p in [0.10, 0.25, 0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99, 0.995, 0.999]:
        print(f"  p{p*100:>5.1f} = {pct(p):>9.2f}x")
    if maxwin_hits > 0:
        print(f"maxwin: {maxwin_hits}/{n} sessions = 1-in-{n/maxwin_hits:.2f}")
    else:
        print(f"maxwin: 0/{n} sessions (need larger n to observe; target ~1-in-23509)")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 940001
    measure(n, seed)

"""Sanity + comparison test for the experimental in-place tumble mechanic
(game_config.use_inplace_tumble, game_executables._tumble_board_in_place).

1. Sanity: run both base spins and a Bonus session with it ON, confirm no
   crashes, board size stays correct, wins still evaluate.
2. Comparison: measure Super Bonus mean/median/hit-rate with it OFF vs ON,
   same seeds, to see the real distributional impact of the mechanic swap.
"""
import sys, random, statistics, warnings, time
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager


def sanity_check():
    print("=== SANITY CHECK (use_inplace_tumble=True) ===")
    config = game_config_mod.GameConfig()
    config.use_inplace_tumble = True
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(200):
            gs.sim = i
            gs.criteria = "0"
            gs.reset_book()
            gs.run_spin(i)
            for reel in gs.board:
                assert len(reel) == 5, f"board column size broke: {len(reel)}"
        print(f"200 base spins OK, no crashes, board size held at 5 every time.")

        for i in range(200):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(600000 + i)
            gs.reset_book()
            gs.run_bonus_session("super")
            for reel in gs.board:
                assert len(reel) == 5, f"board column size broke: {len(reel)}"
        print(f"200 Super Bonus sessions OK, no crashes, board size held at 5 every time.")


def measure(n, seed_offset, tag, tier, inplace):
    config = game_config_mod.GameConfig()
    config.use_inplace_tumble = inplace
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals, spin_counts = [], []
    t0 = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session(tier)
            totals.append(gs.win_manager.running_bet_win)
            spin_counts.append(gs.bonus_spin_count)

    mean = sum(totals) / n
    median = statistics.median(totals)
    print(f"\n=== {tag} inplace={inplace} (n={n}, {time.time()-t0:.1f}s) ===")
    print(f"mean={mean:.2f}x median={median:.2f}x ({100*median/mean:.1f}%)")
    print(f"avg spins/session={sum(spin_counts)/n:.2f}")
    buckets = [(0, 5), (5, 10), (10, 20), (0, 10)]
    for lo, hi in buckets:
        pct = 100 * sum(1 for t in totals if lo <= t < hi) / n
        print(f"  {lo}-{hi}x: {pct:.2f}%")


if __name__ == "__main__":
    sanity_check()
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    measure(n, 970000, "CASCADE_baseline", "super", inplace=False)
    measure(n, 970000, "INPLACE_test", "super", inplace=True)

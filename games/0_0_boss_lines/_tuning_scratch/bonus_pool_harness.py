import sys, os, random

sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
os.chdir(r"D:\Stake Engine\math-sdk")

from gamestate import GameState
from game_config import GameConfig
from src.wins.win_manager import WinManager

config = GameConfig()
gs = GameState(config)
mode_max_win = config.bet_modes[0].get_wincap()
gs.win_manager = WinManager(config.basegame_type, config.freegame_type, mode_max_win)
gs.betmode = "base"


def measure_tier(tier_name, n=3000):
    totals = []
    for i in range(n):
        gs.sim = i
        gs.criteria = "freegame"
        random.seed(i + 1)
        gs.reset_book()
        gs.run_bonus_session(tier_name)
        totals.append(gs.win_manager.running_bet_win)
    avg = sum(totals) / len(totals)
    totals.sort()
    median = totals[len(totals) // 2]
    return avg, median, max(totals)


if __name__ == "__main__":
    import sys as _sys
    n = int(_sys.argv[1]) if len(_sys.argv) > 1 else 3000
    for tier in ["normal", "super", "hidden"]:
        avg, median, mx = measure_tier(tier, n)
        print(f"{tier}: avg={avg:.2f} median={median:.2f} max={mx:.2f} (n={n})")

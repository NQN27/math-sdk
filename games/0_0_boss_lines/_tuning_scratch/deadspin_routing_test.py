import sys, random
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager
from src.calculations.lines import Lines


def measure(chance, n, seed_offset):
    config = game_config_mod.GameConfig()
    config.deadspin_force_chance = dict(config.deadspin_force_chance)
    config.deadspin_force_chance["base"] = chance
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"
    gs.gametype = config.basegame_type

    dead = 0
    fallbacks_seen = 0
    for i in range(n):
        gs.sim = i
        gs.criteria = "freegame"  # irrelevant here, just needs a value
        random.seed(seed_offset * 1000003 + i + 1)
        gs.reset_book()
        gs.create_board_reelstrips()
        wd = Lines.get_lines(gs.board, config)
        if wd["totalWin"] <= 0:
            dead += 1
    fallbacks_seen = getattr(gs, "_deadspin_route_fallback_count", 0)
    print(f"chance={chance}: deadspin rate = {100*dead/n:.2f}% (n={n}), fallbacks={fallbacks_seen}")
    return dead / n


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    p0 = measure(0.0, n, 111)
    p1 = measure(0.3, n, 222)
    p2 = measure(0.6, n, 333)
    predicted1 = 1 - (1 - p0) * (1 - 0.3) ** 3
    predicted2 = 1 - (1 - p0) * (1 - 0.6) ** 3
    print(f"\nbaseline p0={p0*100:.2f}%")
    print(f"predicted @0.3 (naive 1-(1-p0)(1-0.3)^3) = {predicted1*100:.2f}% vs measured {p1*100:.2f}%")
    print(f"predicted @0.6 (naive 1-(1-p0)(1-0.6)^3) = {predicted2*100:.2f}% vs measured {p2*100:.2f}%")

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
SDK = os.path.dirname(os.path.dirname(GAME))
for p in (SDK, GAME):
    if p not in sys.path:
        sys.path.insert(0, p)

from gamestate import GameState  # noqa: E402
from game_config import GameConfig  # noqa: E402
from src.wins.win_manager import WinManager  # noqa: E402


@pytest.fixture(scope="session")
def cfg():
    return GameConfig()


@pytest.fixture
def gs(cfg):
    g = GameState(cfg)
    g.betmode = "base"
    g.criteria = "basegame"
    g.win_manager = WinManager(cfg.basegame_type, cfg.freegame_type, cfg.wincap)
    g.reset_book()
    g.begin_spin()
    g.reel_name = "BR0"
    return g


def set_board(gs, rows):
    """rows: 5 strings/lists of 6 symbol names, top row first."""
    grid = [r.split() if isinstance(r, str) else r for r in rows]
    gs.board = [[gs.make_symbol(grid[r][c]) for r in range(5)] for c in range(6)]
    gs.enhance = [[0] * 5 for _ in range(6)]
    gs.get_special_symbols_on_board()

import sys
sys.path.insert(0, r"D:\Stake Engine\math-sdk"); sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines_v2")
import gamestate as G, game_config as C
from src.calculations.lines import Lines
cfg = C.GameConfig(); gs = G.GameState(cfg)
def board(line):  # payline 1 = row 0 across; other rows filler L1/L2 alternating so no other wins
    b=[[gs.create_symbol("L1" if (r+ro)%2 else "L2") for ro in range(5)] for r in range(6)]
    for r,n in enumerate(line): b[r][0]=gs.create_symbol(n)
    return b
def line1(names):
    d=Lines.get_lines(board(names),cfg); return [(w["meta"]["lineIndex"],w["symbol"],w["kind"],w["win"]) for w in d["wins"] if w["meta"]["lineIndex"]==1]
for name,l in {"W W W H3 H4 L1":["W","W","W","H3","H4","L1"],
               "H2 W H2 H2 H2 L1":["H2","W","H2","H2","H2","L1"],
               "H5x6":["H5"]*6,"W W W W W W":["W"]*6,"W H4 W W H5 L1":["W","H4","W","W","H5","L1"]}.items():
    print(name, line1(l))

import sys, random, warnings, collections
sys.path.insert(0, r"D:\Stake Engine\math-sdk"); sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines_v2")
import gamestate as G, game_config as C
from src.wins.win_manager import WinManager
cfg=C.GameConfig(); gs=G.GameState(cfg)
gs.win_manager=WinManager(cfg.basegame_type,cfg.freegame_type,cfg.bet_modes[0].get_wincap()); gs.betmode="base"
N=int(sys.argv[1]); crit=sys.argv[2] if len(sys.argv)>2 else "basegame"
cleared=0; tot=[]; kills=collections.Counter(); scat=collections.Counter()
orig=G.GameState.resolve_bonus_tier
def p(self):
    global cleared
    kills[len(self.stage_defeat_order)]+=1
    scat[len(self.scatter_columns)]+=1
    if self.base_bosses_cleared: cleared+=1
    return orig(self)
G.GameState.resolve_bonus_tier=p
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for i in range(N):
        gs.criteria=crit
        gs.run_spin(i)
        tot.append(gs.win_manager.running_bet_win)
print("attempts",sum(kills.values()),"cleared",cleared,"rate",round(cleared/max(1,sum(kills.values())),4),"kills",dict(kills),"scat",dict(scat))
print("mean win",round(sum(tot)/len(tot),3))

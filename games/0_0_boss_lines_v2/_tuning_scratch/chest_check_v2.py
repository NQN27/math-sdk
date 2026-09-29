import sys, random, collections
sys.path.insert(0, r"D:\Stake Engine\math-sdk"); sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines_v2")
import gamestate as G, game_config as C
cfg=C.GameConfig(); gs=G.GameState(cfg); gs.criteria="freegame"
N=100000
for stage in range(1,6):
    for last in (False,True):
        ch=collections.Counter(); ms=[]
        for _ in range(N):
            t,a=gs.roll_chest_drop(last,stage); ch[gs.last_chest_type if a else "none"]+=1; ms.append(a)
        print(stage,"last" if last else "    ",{k:round(100*v/N,2) for k,v in sorted(ch.items())},"min",min(ms),"mean",round(sum(ms)/N,2),"max",max(ms))

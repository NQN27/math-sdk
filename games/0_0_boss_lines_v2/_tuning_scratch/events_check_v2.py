import sys, random, warnings, collections, json
sys.path.insert(0, r"D:\Stake Engine\math-sdk"); sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines_v2")
import gamestate as G, game_config as C
from src.wins.win_manager import WinManager
cfg=C.GameConfig(); gs=G.GameState(cfg)
gs.win_manager=WinManager(cfg.basegame_type,cfg.freegame_type,cfg.bet_modes[0].get_wincap()); gs.betmode="base"
cnt=collections.Counter(); ex={}; guns=[]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for i in range(150):
        gs.sim=i; gs.criteria="freegame"; random.seed(i+1); gs.reset_book(); gs.run_bonus_session(sys.argv[1] if len(sys.argv)>1 else "normal")
        for ev in gs.book.events:
            t=ev["type"]; k=t+(":"+ev["powerType"] if t=="powerActivated" else "")
            cnt[k]+=1; ex.setdefault(k,ev)
            if t=="gunActivated": guns+=ev["guns"]
print(dict(cnt))
for k in ("powerActivated:wild_multi","powerActivated:upgrade","powerActivated:extra_wild"):
    if k in ex: print(k, json.dumps(ex[k])[:300])
print("guns", collections.Counter(g["kind"] for g in guns), [g["damage"] for g in guns[:15]])

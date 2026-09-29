import sys, random, warnings, collections
sys.path.insert(0, r"D:\Stake Engine\math-sdk"); sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines_v2")
import gamestate as G, game_config as C
from src.wins.win_manager import WinManager
cfg=C.GameConfig(); gs=G.GameState(cfg)
N=int(sys.argv[1]) if len(sys.argv)>1 else 60
for mode in ("base","ante","ultimatepower","godmode","buy3","buy4"):
    bm=[m for m in cfg.bet_modes if m.get_name()==mode][0]
    gs.win_manager=WinManager(cfg.basegame_type,cfg.freegame_type,bm.get_wincap()); gs.betmode=mode
    crits=[d._criteria for d in bm.get_distributions()] if hasattr(bm.get_distributions()[0],"_criteria") else []
    errs=0; tot=[]; ev=collections.Counter(); first=None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for crit in (["basegame"] if mode in("base","ante") else []) + (["freegame"] if mode in("buy3","buy4","base") else []) + (["basegame"] if mode in("ultimatepower","godmode") else []):
            for i in range(N):
                gs.criteria=crit
                try:
                    gs.run_spin(i); tot.append(gs.win_manager.running_bet_win)
                    for e in gs.book.events:
                        if e["type"]=="coinPhase": ev["full" if e["fullBoard"] else "coin"]+=1
                        if e["type"]=="bonusTrigger": ev["bonus"]+=1
                except Exception as x:
                    errs+=1
                    if first is None:
                        import traceback; first=traceback.format_exc()
    print(mode,"n",len(tot),"errs",errs,"mean",round(sum(tot)/max(1,len(tot)),2),dict(ev))
    if first: print(first[-600:])

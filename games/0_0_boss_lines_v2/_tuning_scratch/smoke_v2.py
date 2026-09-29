import sys, random, warnings, statistics, traceback
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines_v2")
import gamestate as G, game_config as C
from src.wins.win_manager import WinManager
cfg = C.GameConfig(); gs = G.GameState(cfg)
mx = cfg.bet_modes[0].get_wincap()
gs.win_manager = WinManager(cfg.basegame_type, cfg.freegame_type, mx); gs.betmode = "base"
print("game_id", cfg.game_id, "reels", cfg.num_reels, [len(cfg.reels["BR0"][i]) for i in range(1)] if isinstance(cfg.reels["BR0"], list) else "")
for tier in ("normal", "super", "hidden"):
    tot = []; err = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(int(sys.argv[1]) if len(sys.argv) > 1 else 100):
            gs.sim = i; gs.criteria = "freegame"; random.seed(i + 1); gs.reset_book()
            try:
                gs.run_bonus_session(tier); tot.append(gs.win_manager.running_bet_win)
            except Exception:
                err += 1
                if err == 1: traceback.print_exc()
    print(tier, "ok", len(tot), "err", err, "mean", round(sum(tot)/max(1,len(tot)), 2), "median", round(statistics.median(tot), 2) if tot else None)

import sys, os, random, math
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

CAP_THRESH = 19000.0

def measure_tier(tier_name, n):
    totals = []
    for i in range(n):
        gs.sim = i
        gs.criteria = "freegame"
        random.seed(i + 1)
        gs.reset_book()
        gs.run_bonus_session(tier_name)
        totals.append(gs.win_manager.running_bet_win)
    n = len(totals)
    mean = sum(totals) / n
    var = sum((x - mean) ** 2 for x in totals) / (n - 1)
    se = math.sqrt(var / n)
    capped = [x for x in totals if x >= CAP_THRESH]
    uncapped = [x for x in totals if x < CAP_THRESH]
    p_cap = len(capped) / n
    mean_uncapped = (sum(uncapped) / len(uncapped)) if uncapped else 0.0
    contrib_cap = (sum(capped) / n)
    totals.sort()
    median = totals[n // 2]
    return {
        "tier": tier_name, "n": n, "mean": mean, "se": se, "median": median,
        "max": totals[-1], "p_cap": p_cap, "n_cap": len(capped),
        "mean_uncapped": mean_uncapped, "contrib_cap": contrib_cap,
    }

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    tiers = sys.argv[2:] if len(sys.argv) > 2 else ["normal", "super", "hidden"]
    for tier in tiers:
        r = measure_tier(tier, n)
        print(
            f"{r['tier']}: mean={r['mean']:.2f} +/- {r['se']:.2f} (SE)  median={r['median']:.2f}  max={r['max']:.2f}  "
            f"P(>=19000)={r['p_cap']*100:.3f}% (n_cap={r['n_cap']})  "
            f"mean_uncapped={r['mean_uncapped']:.2f}  contrib_from_capped={r['contrib_cap']:.2f}  n={r['n']}"
        )

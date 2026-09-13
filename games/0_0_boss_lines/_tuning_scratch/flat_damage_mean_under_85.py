import sys, random, statistics
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
from gamestate import GameState
from game_config import GameConfig
from src.wins.win_manager import WinManager

# 2026-09-14: push flat-damage Normal Bonus's mean under 85 without
# disturbing median (~33, confirmed good by the user). Abandoned boosting
# 1-8 tiers (the historically reliable cascade-era lever) - it barely moved
# mean and dragged median down, the opposite of what was wanted. Cutting
# 100-250 tier weights (doesn't govern median, which is dominated by the
# much-more-frequent 1-8/10-80 tiers) plus a further chest-value cut worked:
# mean 95.28 -> 83.62, median 33.31 -> 33.45 (n=20000).


def measure(n, seed_offset, tag):
    config = GameConfig()
    config.use_flat_damage["normal"] = True

    gs = GameState(config)
    mode_max_win = config.bet_modes[0].get_wincap()
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, mode_max_win)
    gs.betmode = "base"

    totals, maxwin_raws = [], []
    for i in range(n):
        gs.sim = i
        gs.criteria = "freegame"
        random.seed(seed_offset * 1000003 + i + 1)
        gs.reset_book()
        gs.run_bonus_session("normal")
        raw = gs.win_manager.running_bet_win
        if raw >= mode_max_win:
            maxwin_raws.append(raw)
        else:
            totals.append(raw)

    totals.sort()
    n_clean = len(totals)

    def pct(p):
        k = (n_clean - 1) * p
        f = int(k)
        c = min(f + 1, n_clean - 1)
        return totals[f] + (totals[c] - totals[f]) * (k - f)

    print(f"\n=== {tag} (n={n}) ===")
    print(f"maxwin hits={len(maxwin_raws)}")
    print(f"mean={sum(totals)/n_clean:.2f}x median={statistics.median(totals):.2f}x")
    for name, p in [("p50", .5), ("p75", .75), ("p85", .85), ("p90", .9),
                    ("p95", .95), ("p99", .99), ("p99.5", .995), ("p99.9", .999)]:
        print(f"{name}={pct(p):.2f}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    measure(n, 999300, "flat-damage current config (production values)")

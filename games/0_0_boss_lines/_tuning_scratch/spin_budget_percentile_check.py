import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Check the current committed use_spin_budget["normal"] config (whatever it
# is on disk right now - chain-block/deadspin/last-hit/spin_budget_initial
# all read live from game_config.py, no overrides here) against the target
# percentile table given: p5=2x p10=5x p20=10x p30=15x p40=21x p50=30x
# p60=42x p70=60x p75=85x p80=120x p85=170x p90=250x p95=500x p99=1500x
# p99.5=2500x.

TARGET = {
    5: 2, 10: 5, 20: 10, 30: 15, 40: 21, 50: 30, 60: 42, 70: 60,
    75: 85, 80: 120, 85: 170, 90: 250, 95: 500, 99: 1500, 99.5: 2500,
}


def measure(n, tier, seed_offset):
    config = game_config_mod.GameConfig()
    config.use_spin_budget[tier] = True
    gs = gamestate_mod.GameState(config)
    mode_max_win = config.bet_modes[0].get_wincap()
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, mode_max_win)
    gs.betmode = "base"

    totals = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session(tier)
            totals.append(gs.win_manager.running_bet_win)

    sorted_totals = sorted(totals)

    def pctl(p):
        idx = min(len(sorted_totals) - 1, int(len(sorted_totals) * p / 100))
        return sorted_totals[idx]

    print(f"\n=== {tier} spin-budget (n={n}) ===")
    print(f"mean={sum(totals)/n:.2f}x median={statistics.median(totals):.2f}x")
    print(f"{'p':<6}{'measured':<12}{'target':<10}{'diff%'}")
    for p, tgt in TARGET.items():
        m = pctl(p)
        diff = 100 * (m - tgt) / tgt
        print(f"p{p:<5}{m:<12.2f}{tgt:<10}{diff:+.1f}%")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    measure(n, "normal", 271828)

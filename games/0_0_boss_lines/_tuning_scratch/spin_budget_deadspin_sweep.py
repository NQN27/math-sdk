import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Re-check the 30/33/35% deadspin candidates at a larger n (n=2000 showed
# non-monotonic mean across them - 30%->89.80, 33%->98.44, 35%->80.33 -
# likely sampling noise given this project's repeated cliff/noise history).
# Config otherwise fixed at its current committed state: chain-block
# threshold=1/step=0.80, last-hit per-pass-aggregated scale=2%/base=0.5%.


def measure(n, deadspin_pct, seed_offset):
    config = game_config_mod.GameConfig()
    config.use_spin_budget["normal"] = True
    config.bonus_stage_deadspin_chance["normal"] = {s: deadspin_pct for s in range(1, 7)}
    gs = gamestate_mod.GameState(config)
    mode_max_win = config.bet_modes[0].get_wincap()
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, mode_max_win)
    gs.betmode = "base"

    totals, spin_counts = [], []
    stage_end = {}
    end_reasons = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session("normal")
            totals.append(gs.win_manager.running_bet_win)
            spin_counts.append(gs.bonus_spin_count)
            stage_end[gs.stage] = stage_end.get(gs.stage, 0) + 1
            end_reasons[gs.bonus_end_reason] = end_reasons.get(gs.bonus_end_reason, 0) + 1

    mean_total = sum(totals) / n
    median_total = statistics.median(totals)
    mean_spins = sum(spin_counts) / n
    print(f"\n=== deadspin={deadspin_pct*100:.0f}% (n={n}) ===")
    print(f"mean={mean_total:.2f}x median={median_total:.2f}x ratio={100*median_total/mean_total:.1f}%")
    print(f"avg spins/session={mean_spins:.2f}")
    print("stage-end %:", {k: round(100 * v / n, 2) for k, v in sorted(stage_end.items())})
    print("end_reason %:", {k: round(100 * v / n, 2) for k, v in sorted(end_reasons.items())})


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    for pct in (0.30, 0.33, 0.35):
        measure(n, pct, 314159)

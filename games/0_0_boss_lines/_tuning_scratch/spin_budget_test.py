import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Sanity + first measurement pass for the new use_spin_budget mechanic
# (2026-09-16, replaces Player-HP/counterattack with a fixed spin budget +
# per-stage-clear top-up). Reports avg spins/session, session mean/median,
# stage-death%, safety_cap-hit rate (should be ~0 - a non-zero rate here
# would mean the budget/grant combo lets sessions run away) and end_reason
# breakdown (to confirm "spins_depleted" is actually the dominant reason,
# not an accidental never-taken path).


def measure(n, tier, seed_offset, deadspin_pct=None, chain_step=None):
    config = game_config_mod.GameConfig()
    config.use_spin_budget[tier] = True
    # NOTE: GameConfig.__init__ re-runs (resetting every attribute to its
    # file default) on EVERY GameConfig() call, even though __new__ returns
    # the same cached singleton instance - any override must be applied
    # AFTER this specific construction, not before it in the caller, or it
    # gets silently wiped out right here.
    if deadspin_pct is not None:
        config.bonus_stage_deadspin_chance[tier] = {s: deadspin_pct for s in range(1, 7)}
    if chain_step is not None:
        config.spin_budget_chain_block_step[tier] = chain_step
    gs = gamestate_mod.GameState(config)
    mode_max_win = config.bet_modes[0].get_wincap()
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, mode_max_win)
    gs.betmode = "base"

    session_totals, spin_counts = [], []
    stage_end = {}
    end_reasons = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session(tier)
            session_totals.append(gs.win_manager.running_bet_win)
            spin_counts.append(gs.bonus_spin_count)
            stage_end[gs.stage] = stage_end.get(gs.stage, 0) + 1
            end_reasons[gs.bonus_end_reason] = end_reasons.get(gs.bonus_end_reason, 0) + 1

    mean_total = sum(session_totals) / n
    median_total = statistics.median(session_totals)
    mean_spins = sum(spin_counts) / n

    print(f"\n=== SPIN-BUDGET {tier} (n={n}) ===")
    print(f"deadspin={config.bonus_stage_deadspin_chance.get(tier, {})} "
          f"chain_step={config.spin_budget_chain_block_step[tier]}")
    print(f"initial={config.spin_budget_initial[tier]} per_stage_clear={config.spin_budget_per_stage_clear[tier]}")
    print(f"session total: mean={mean_total:.2f}x median={median_total:.2f}x ratio={100*median_total/mean_total:.1f}%")
    print(f"avg spins/session={mean_spins:.2f} (min={min(spin_counts)} max={max(spin_counts)})")
    print("stage-end %:", {k: round(100 * v / n, 2) for k, v in sorted(stage_end.items())})
    print("end_reason %:", {k: round(100 * v / n, 2) for k, v in sorted(end_reasons.items())})


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    tier = sys.argv[2] if len(sys.argv) > 2 else "normal"
    deadspin_pct = float(sys.argv[3]) if len(sys.argv) > 3 else None
    chain_step = float(sys.argv[4]) if len(sys.argv) > 4 else None
    measure(n, tier, 771000, deadspin_pct=deadspin_pct, chain_step=chain_step)

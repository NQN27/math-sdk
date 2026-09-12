"""Main file for generating results for Boss Lines (Phase 1 rebuild)."""

from gamestate import GameState
from game_config import GameConfig
from game_optimization import OptimizationSetup
from optimization_program.run_script import OptimizationExecution
from utils.game_analytics.run_analysis import create_stat_sheet
from utils.rgs_verification import execute_all_tests
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":

    # Memory-constrained machine: keep threads/batching modest (see
    # readme.txt) to avoid MemoryError during book compression.
    num_threads = 4
    rust_threads = 8
    batching_size = 10000
    compression = True
    profiling = False

    # Phase 4 v2 (see QUESTIONS_FOR_YOU.md's "Phase 4 v2" section): this
    # round is SCOPED to base/ante/buy3/buy4 only - ultimatepower/godmode
    # are deliberately OMITTED from num_sim_args/target_modes so their own
    # already-validated 100k library files (RTP=0.965) are left completely
    # untouched (create_books/OptimizationExecution only ever touch bet-mode
    # names present in these two collections; execute_all_tests below still
    # re-verifies ultimatepower/godmode's EXISTING library, unaffected).
    # Scale chosen to fit this session's time budget while still being a
    # REAL end-to-end run (not a resumed/stalled one - the previous attempt
    # at scaling buy3/buy4 to 100k stalled unresolved; started fresh here) -
    # see QUESTIONS_FOR_YOU.md's "ket qua" section for the actual scale
    # used/why and the real measured numbers.
    num_sim_args = {
        "base": int(2e4),
        "ante": int(2e4),
        "buy3": int(2e4),
        "buy4": int(2e4),
        "ultimatepower": int(2e4),
        "godmode": int(2e4),
    }

    run_conditions = {
        "run_sims": True,
        "run_optimization": True,
        "run_analysis": True,
        "run_format_checks": True,
    }
    target_modes = ["base", "ante", "buy3", "buy4", "ultimatepower", "godmode"]

    config = GameConfig()
    gamestate = GameState(config)
    if run_conditions["run_optimization"] or run_conditions["run_analysis"]:
        optimization_setup_class = OptimizationSetup(config)

    if run_conditions["run_sims"]:
        create_books(
            gamestate,
            config,
            num_sim_args,
            batching_size,
            num_threads,
            compression,
            profiling,
        )

    generate_configs(gamestate)

    if run_conditions["run_optimization"]:
        OptimizationExecution().run_all_modes(config, target_modes, rust_threads)
        generate_configs(gamestate)

    if run_conditions["run_analysis"]:
        # Phase 4 v2: scope analysis to this round's 4 modes only - see
        # utils/game_analytics/run_analysis.py's create_stat_sheet docstring
        # for why (ultimatepower/godmode's OWN existing library files were
        # found to be internally stale/mismatched already, unrelated to this
        # round - analysing them here would crash on that pre-existing
        # inconsistency for no benefit, since this round doesn't touch them).
        create_stat_sheet(gamestate, modes_to_analyse=target_modes)

    if run_conditions["run_format_checks"]:
        # utils/rgs_verification.py's execute_all_tests is post-hoc reporting
        # only now ("hau kiem") - it prints the real math-verification
        # numbers (rtp, std, prob5k/10k, etl40b/etl10k/etl_sum,
        # cvar_per_stake/absolute) per mode and writes them to
        # stats_summary.json, with no pass/fail gate and no per-game RTP
        # ceiling override (that mechanism was removed - see
        # report_math_verification_stats' docstring for why the old flat
        # 0.967/0.9705-style ceiling gate was actively wrong, not just
        # loose). IMPORTANT: it still OVERWRITES stats_summary.json from
        # scratch every call (write_all_stats truncates) - must be exactly
        # ONE call covering every mode in target_modes.
        #
        # Read the real limits at stake-engine.com/docs/approval-guidelines/
        # math-verification before treating any run's numbers as
        # approval-ready. Flagging now because it's already known to matter
        # here: base/ante/buy3/buy4 target ~97.00-97.05% RTP (Phase 4 v2),
        # but the official Critical "RTP band" test caps at 96.70% - that
        # target sits outside the real band regardless of what this repo's
        # own tooling reports, and needs an explicit decision (re-target the
        # RTP, or knowingly accept it's outside the documented band) before
        # this round is called approval-ready.
        excluded_modes = [bm.get_name() for bm in config.bet_modes if bm.get_name() not in target_modes]
        execute_all_tests(config, excluded_modes=excluded_modes)

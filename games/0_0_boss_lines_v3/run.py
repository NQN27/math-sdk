"""Generate books (and later optimize/analyse) for Boss Lines v3.

Optimization/analysis/format checks stay OFF until the game is tuned: the
RTP splits in game_optimization.py are placeholders, and the paytable's
non-0.10 values (QUESTIONS.md Q3) would fail the RGS format check.
"""

from gamestate import GameState
from game_config import GameConfig
from game_optimization import OptimizationSetup
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":
    num_threads = 4
    rust_threads = 8
    batching_size = 1000
    compression = True
    profiling = False

    num_sim_args = {"base": 2000, "ante": 2000, "feature": 1000, "buy3": 1000, "buy4": 1000, "random_bonus": 1000}
    run_conditions = {
        "run_sims": True,
        "run_optimization": False,
        "run_analysis": False,
        "run_format_checks": False,
    }
    target_modes = list(num_sim_args.keys())

    config = GameConfig()
    gamestate = GameState(config)
    OptimizationSetup(config)

    if run_conditions["run_sims"]:
        create_books(gamestate, config, num_sim_args, batching_size, num_threads, compression, profiling)
    generate_configs(gamestate)

    if run_conditions["run_optimization"]:
        from optimization_program.run_script import OptimizationExecution

        OptimizationExecution().run_all_modes(config, target_modes, rust_threads)
        generate_configs(gamestate)
    if run_conditions["run_analysis"]:
        from utils.game_analytics.run_analysis import create_stat_sheet

        create_stat_sheet(gamestate, custom_keys=[{"symbol": "scatter"}])
    if run_conditions["run_format_checks"]:
        from utils.rgs_verification import execute_all_tests

        execute_all_tests(config)

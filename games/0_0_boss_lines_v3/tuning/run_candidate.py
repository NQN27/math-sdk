"""Books + optimizer for a tuning candidate WITHOUT writing it into game_config.py.

usage: python tuning/run_candidate.py OVERRIDES.json [mode=sims ...] [--no-opt | --opt-only]
  e.g. python tuning/run_candidate.py tuning/overrides/f3.json base=20000 buy3=10000
Applies the override file to the GameConfig singleton (same rules as tune_harness.py, incl. _reel_specs),
then runs create_books (1 thread, low RAM), generate_configs and the Rust optimizer for the listed modes.
Output goes to library/ (git-ignored). The reel CSVs in reels/ are NOT rewritten.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
SDK = os.path.dirname(os.path.dirname(GAME))
for p in (SDK, GAME, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

DEFAULT_SIMS = {"base": 20000, "ante": 20000, "feature": 10000, "buy3": 10000, "buy4": 10000, "random_bonus": 10000}

if __name__ == "__main__":
    args = sys.argv[1:]
    run_opt = "--no-opt" not in args
    run_books = "--opt-only" not in args  # reuse the books already in library/
    args = [a for a in args if a not in ("--no-opt", "--opt-only")]
    overrides = json.load(open(args[0]))
    sims = {k: int(v) for k, v in (a.split("=") for a in args[1:])} or dict(DEFAULT_SIMS)

    # stale optimized lookups from an older run would be published instead of this run's books
    pub = os.path.join(GAME, "library", "publish_files")
    for f in os.listdir(pub) if os.path.isdir(pub) and run_books else []:
        if f.startswith("lookUpTable_") and f.endswith("_0.csv"):
            os.remove(os.path.join(pub, f))
    os.chdir(SDK)
    import tune_harness
    gamestate, config = tune_harness._setup(overrides)
    from game_optimization import OptimizationSetup, plan_summary
    from src.state.run_sims import create_books
    from src.write_data.write_configs import generate_configs

    OptimizationSetup(config)
    print(json.dumps(plan_summary(config), indent=1, default=str))
    if run_books:
        create_books(gamestate, config, sims, batch_size=1000, threads=1, compress=True, profiling=False)
    generate_configs(gamestate)  # writes math_config.json (the optimizer's fences) from this run's setup
    if run_opt:
        from optimization_program.run_script import OptimizationExecution
        OptimizationExecution().run_all_modes(config, list(sims), 4)
        generate_configs(gamestate)
    print("done", list(sims))

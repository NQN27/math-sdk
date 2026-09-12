"""In-place tumble re-tune for Normal Bonus, stage 1 first. Isolates a
single stage's wild% via a fixed seed keyed to (stage, pct) - same
cliff-avoidance pattern used for Super's funnel reshape - so an unchanged
stage's reel content stays byte-identical between candidates.
"""
import sys, os, random, statistics, warnings, time
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager
import gen_stage_reels as gsr

SCRATCH_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch\normal_inplace_reels"
os.makedirs(SCRATCH_DIR, exist_ok=True)

BUCKETS = [(0, 5), (5, 10), (10, 20), (20, 40), (40, 80), (80, 150), (150, 250), (250, 400), (400, 10**9)]


def gen_reels(wild_pct, tag):
    paths = {}
    for stage, pct in wild_pct.items():
        pfrac = gsr.POWER_FRAC_OF_WILD["normal"]
        col0_wild = gsr.COL0_GETS_WILD["normal"]
        other_pct = pct if col0_wild else pct * 5.0 / 4.0
        w_other = gsr.make_weights(gsr.NONWILD["normal"]["other"], other_pct, pfrac)
        w_col0 = gsr.make_weights(gsr.NONWILD["normal"]["col0"], pct if col0_wild else 0.0, pfrac)
        seed = 7000 + stage * 1000 + int(round(pct * 10))
        fname = f"BM_Reels_S{stage}_{tag}.csv"
        path = os.path.join(SCRATCH_DIR, fname)
        gsr.write_reel(path, w_col0, w_other, seed)
        paths[stage] = path
    return paths


def measure(n, seed_offset, tag, wild_pct):
    reel_paths = gen_reels(wild_pct, tag.replace(" ", "_"))
    config = game_config_mod.GameConfig()
    config.use_inplace_tumble = True
    for stage, path in reel_paths.items():
        config.reels[f"BM_Reels_S{stage}"] = config.read_reels_csv(path)

    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    stage_death_counts = {}
    totals = []
    t0 = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session("normal")
            totals.append(gs.win_manager.running_bet_win)
            stage_death_counts[gs.stage] = stage_death_counts.get(gs.stage, 0) + 1

    mean = sum(totals) / n
    median = statistics.median(totals)
    print(f"\n=== {tag} (n={n}, {time.time()-t0:.1f}s) wild%={wild_pct} ===")
    print(f"mean={mean:.2f}x median={median:.2f}x ({100*median/mean:.1f}%)")
    print("stage death %: " + ", ".join(f"s{s}={100*c/n:.2f}%" for s, c in sorted(stage_death_counts.items())))
    for lo, hi in BUCKETS:
        pct = 100 * sum(1 for t in totals if lo <= t < hi) / n
        label = f"{lo}-{hi}" if hi < 10**9 else f"{lo}+"
        print(f"  {label}: {pct:.2f}%")
    return {"mean": mean, "median": median, "stage_death_counts": stage_death_counts, "n": n}


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    # s1=27.5/s2=16 (default) already matches both targets closely. Now vary
    # s3 (currently 18.43% vs target 14.85%, too hard - ease it) keeping
    # s1/s2 fixed.
    # s3=12.0 locked in. s5 currently 1.39% vs target 3.95% (too easy) -
    # lower its wild% (opposite direction from s1-s3) to make it harder.
    for s5v in (1.0, 0.5, 1.5):
        wp = {1: 27.5, 2: 16.0, 3: 12.0, 4: 4.0, 5: s5v, 6: 1.0}
        measure(n, 941000, f"INPLACE_s5_{s5v}", wp)

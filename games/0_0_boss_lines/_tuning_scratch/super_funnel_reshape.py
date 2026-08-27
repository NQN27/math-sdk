"""Iterate Super's per-stage Wild% taper (and stage6_dam_escalation) toward
the game designer's explicit target shape:
  stage-death %: s2~10%, s3~30%, s4~35%, s5~20%, s6~5%
  stage-6 endless clear-chance: P(clear loop N) = max(5%, 25% - N*0.5%)

Reels are regenerated in-memory (scratch dir) via gen_stage_reels' own
weight-building functions - real reel CSVs untouched until a final
candidate is chosen and applied.
"""
import sys, os, random, statistics, warnings, time
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager
import gen_stage_reels as gsr

SCRATCH_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch\super_funnel_reshape_reels"
os.makedirs(SCRATCH_DIR, exist_ok=True)


def gen_reels(wild_pct, tag):
    paths = {}
    seed = 6001 if tag not in globals().get("_seed_cache", {}) else None
    seed = hash(tag) % 100000 + 6000
    for stage, pct in wild_pct.items():
        pfrac = gsr.POWER_FRAC_OF_WILD["super"]
        other_pct = pct * 5.0 / 4.0
        w_other = gsr.make_weights(gsr.NONWILD["super"]["other"], other_pct, pfrac)
        w_col0 = gsr.make_weights(gsr.NONWILD["super"]["col0"], 0.0, pfrac)
        fname = f"Super_BM_S{stage}_{tag}.csv"
        path = os.path.join(SCRATCH_DIR, fname)
        gsr.write_reel(path, w_col0, w_other, seed)
        paths[stage] = path
        seed += 1
    return paths


def measure(n, seed_offset, tag, wild_pct, dam_escalation=1.20):
    reel_paths = gen_reels(wild_pct, tag.replace(" ", "_"))
    config = game_config_mod.GameConfig()
    for stage, path in reel_paths.items():
        config.reels[f"Super_BM_S{stage}"] = config.read_reels_csv(path)
    config.stage6_dam_escalation = dict(config.stage6_dam_escalation)
    config.stage6_dam_escalation["super"] = dam_escalation

    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    stage_death_counts = {}
    loop_counts = {}
    stage6_sessions = 0
    totals = []
    t0 = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session("super")
            totals.append(gs.win_manager.running_bet_win)
            stage_death_counts[gs.stage] = stage_death_counts.get(gs.stage, 0) + 1
            if gs.stage == 6:
                stage6_sessions += 1
                lc = gs.stage6_loop_count
                loop_counts[lc] = loop_counts.get(lc, 0) + 1

    mean = sum(totals) / n
    median = statistics.median(totals)
    print(f"\n=== {tag} (n={n}, {time.time()-t0:.1f}s) wild%={wild_pct} escalation={dam_escalation} ===")
    print(f"payout: mean={mean:.2f}x median={median:.2f}x ({100*median/mean:.1f}%)")
    print("stage death %: " + ", ".join(f"s{s}={100*c/n:.2f}% (target {t})" for (s,c), t in
          zip(sorted(stage_death_counts.items()), [10,30,35,20,5])))
    print(f"stage-6 reached: {stage6_sessions} ({100*stage6_sessions/n:.2f}%, target ~5%)")
    if stage6_sessions:
        max_lc = max(loop_counts.keys())
        for k in range(min(max_lc + 2, 4)):
            reached_k = sum(c for lc, c in loop_counts.items() if lc >= k)
            if reached_k == 0:
                break
            cleared_k = reached_k - loop_counts.get(k, 0)
            target = max(5.0, 25.0 - k * 0.5)
            print(f"  attempt #{k+1}: reached={reached_k}, cleared={100*cleared_k/reached_k:.1f}% (target~{target:.1f}%)")
    return {"mean": mean, "median": median, "stage_death_counts": stage_death_counts,
            "stage6_sessions": stage6_sessions, "n": n}


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    # Candidate 1: shift wild% earlier-weighted (cut s2/s3, boost s4/s5),
    # bump s6 slightly to help first-attempt clear rate.
    cand1 = {2: 18.0, 3: 11.0, 4: 14.0, 5: 7.0, 6: 3.0}
    measure(n, 998100, "CAND1_shift_earlier", cand1)

"""Comprehensive baseline for the requested Super Bonus re-tune:
  - per-stage death % (target: s2~10%, s3~30%, s4~35%, s5~20%, s6~5%)
  - stage-6 endless-loop clear-chance curve (target: P(clear loop N) =
    max(5%, 25% - N*0.5%), N = loops already cleared going into this
    attempt)
  - line-pay vs reward-drop (boss-kill) payout split
  - overall payout distribution (mean/median/stdev)

One simulation pass, all stats collected together (no need to re-run per
metric). Baseline = current committed game_config.py, no overrides.
"""
import sys, random, statistics, warnings, time
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

_orig_award_win = gamestate_mod.GameState.award_win
_tag = {"in_reward_drop": False}
_totals = {"line": 0.0, "reward": 0.0}


def tagged_award_win(self, amount):
    result = _orig_award_win(self, amount)
    if _tag["in_reward_drop"]:
        _totals["reward"] += amount
        _tag["in_reward_drop"] = False
    else:
        _totals["line"] += amount
    return result


gamestate_mod.GameState.award_win = tagged_award_win

_orig_roll_reward_drop = gamestate_mod.GameState.roll_reward_drop


def tagged_roll_reward_drop(self, is_last_of_stage, stage):
    _tag["in_reward_drop"] = True
    return _orig_roll_reward_drop(self, is_last_of_stage, stage)


gamestate_mod.GameState.roll_reward_drop = tagged_roll_reward_drop


def measure(n, seed_offset, tag, config_overrides=None):
    config = game_config_mod.GameConfig()
    if config_overrides:
        config_overrides(config)

    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    stage_death_counts = {}
    loop_counts = {}
    stage6_sessions = 0
    totals, line_totals, reward_totals = [], [], []
    t0 = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            _totals["line"] = 0.0
            _totals["reward"] = 0.0
            _tag["in_reward_drop"] = False
            gs.run_bonus_session("super")
            totals.append(gs.win_manager.running_bet_win)
            line_totals.append(_totals["line"])
            reward_totals.append(_totals["reward"])
            stage_death_counts[gs.stage] = stage_death_counts.get(gs.stage, 0) + 1
            if gs.stage == 6:
                stage6_sessions += 1
                lc = gs.stage6_loop_count
                loop_counts[lc] = loop_counts.get(lc, 0) + 1

    mean = sum(totals) / n
    median = statistics.median(totals)
    stdev = statistics.stdev(totals)
    mean_line = sum(line_totals) / n
    mean_reward = sum(reward_totals) / n

    print(f"\n=== {tag} (n={n}, {time.time()-t0:.1f}s) ===")
    print(f"payout: mean={mean:.2f}x median={median:.2f}x ({100*median/mean:.1f}% of mean) stdev={stdev:.2f}x")
    print(f"split: line-pay={mean_line:.2f}x ({100*mean_line/mean:.1f}%) reward-drop={mean_reward:.2f}x ({100*mean_reward/mean:.1f}%)")
    print("stage death %: " + ", ".join(f"s{s}={100*c/n:.2f}%" for s, c in sorted(stage_death_counts.items())))

    print(f"stage-6 reached: {stage6_sessions} ({100*stage6_sessions/n:.2f}%)")
    if stage6_sessions:
        print("stage-6 endless clear-chance curve:")
        # survivors going INTO attempt k (0-indexed loop count k-1... see below)
        max_lc = max(loop_counts.keys())
        for k in range(max_lc + 2):
            reached_k = sum(c for lc, c in loop_counts.items() if lc >= k)
            died_at_k = loop_counts.get(k, 0)
            if reached_k == 0:
                break
            cleared_k = reached_k - died_at_k
            target = max(5.0, 25.0 - k * 0.5)
            print(f"  attempt #{k+1} (loops_cleared_going_in={k}): reached={reached_k}, "
                  f"cleared={cleared_k} ({100*cleared_k/reached_k:.2f}%, target~{target:.1f}%), "
                  f"died={died_at_k} ({100*died_at_k/reached_k:.2f}%)")
    return {
        "mean": mean, "median": median, "stdev": stdev,
        "mean_line": mean_line, "mean_reward": mean_reward,
        "stage_death_counts": stage_death_counts, "loop_counts": loop_counts,
        "stage6_sessions": stage6_sessions, "n": n,
    }


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    measure(n, 997500, "BASELINE_current_committed")

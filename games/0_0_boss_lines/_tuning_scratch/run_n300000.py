"""Big n=300000 instrumented run of the current Normal Bonus candidate
(final_combined_candidate.build_config(1.0, 45.0), with the real
stage6_chest_natural_maxwin_weight now calibrated to 0.0825 - see
final_combined_candidate.py's 2026-08-21 correction note).

Captures per-session gameplay+payout data (not just the final total) so any
follow-up question about the shape/mechanics can be answered from the CSV
without re-running the sim. Output goes to run_n300000/ (a real project
folder, not a temp dir):
  - sessions.csv        one row per session
  - config_snapshot.txt exact config values this run used
  - summary.txt         aggregate stats computed after the run
"""
import csv
import os
import random
import statistics
import sys
import time
import warnings

sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import final_combined_candidate as fc
from src.wins.win_manager import WinManager

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_n300000")
os.makedirs(OUT_DIR, exist_ok=True)

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300000
SEED_OFFSET = int(sys.argv[2]) if len(sys.argv) > 2 else 900001

config = fc.build_config(1.0, 45.0)
gs = fc.gamestate_mod.GameState(config)
gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
gs.betmode = "base"

MAXWIN_VALUE = int(config.wincap)

# Hook roll_reward_drop directly, since it returns (tier, amount) right
# before award_win's clamp is applied - exactly the stage6-chest roll info
# we need, with no reconstruction required (run_bonus_session doesn't
# otherwise expose it).
_orig_roll_reward_drop = fc.gamestate_mod.GameState.roll_reward_drop
_last_chest_roll = {"tier": None, "stage6_chest": False}


def hooked_roll_reward_drop(self, is_last_of_stage, stage):
    tier, amount = _orig_roll_reward_drop(self, is_last_of_stage, stage)
    is_stage6_chest = stage == self.config.max_stage and is_last_of_stage
    if is_stage6_chest:
        _last_chest_roll["tier"] = tier
        _last_chest_roll["stage6_chest"] = True
    return tier, amount


fc.gamestate_mod.GameState.roll_reward_drop = hooked_roll_reward_drop

rows = []
t0 = time.time()
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for i in range(N):
        gs.sim = i
        gs.criteria = "freegame"
        seed = SEED_OFFSET * 1000003 + i + 1
        random.seed(seed)
        gs.reset_book()
        fc._state["max_stage"] = 1
        fc._state["spins"] = 0
        fc._state["pass_count"] = 0
        fc._state["chain_block_pending"] = False
        fc._state["general_chance"] = 0.0
        fc._state["chain_break_threshold"] = 2
        fc._state["chain_break_step"] = 0.30
        _last_chest_roll["tier"] = None
        _last_chest_roll["stage6_chest"] = False

        gs.run_bonus_session("normal")

        total = gs.win_manager.running_bet_win
        max_stage = fc._state["max_stage"]
        spins = fc._state["spins"]
        pass_count = fc._state["pass_count"]
        chest_tier = _last_chest_roll["tier"]
        stage6_reached = max_stage == 6
        maxwin_fired = chest_tier == MAXWIN_VALUE

        rows.append((
            i, seed, total, spins, max_stage, pass_count,
            int(stage6_reached), chest_tier if chest_tier is not None else "",
            int(maxwin_fired), int(total == 0),
        ))

        if (i + 1) % 10000 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (N - (i + 1)) / rate
            print(f"  {i+1}/{N}  elapsed={elapsed:.0f}s  eta={eta:.0f}s", flush=True)

elapsed = time.time() - t0
print(f"\nsimulation done: n={N} in {elapsed:.1f}s ({N/elapsed:.1f} sessions/s)")

sessions_csv = os.path.join(OUT_DIR, "sessions.csv")
with open(sessions_csv, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow([
        "session_id", "seed", "total_payout", "spins", "max_stage",
        "chain_pass_count", "stage6_reached", "stage6_chest_tier",
        "maxwin_fired", "is_zero",
    ])
    w.writerows(rows)
print(f"wrote {sessions_csv} ({len(rows)} rows)")

# ---- config snapshot ----
snap_path = os.path.join(OUT_DIR, "config_snapshot.txt")
chest = config.reward_drop_stage6_last_tiers_normal_bonus
chest_weights = {k: v for k, v in config.reward_drop_weights_normal_bonus.items() if k in chest}
regular_weights = {k: v for k, v in config.reward_drop_weights_normal_bonus.items() if k not in chest}
with open(snap_path, "w") as f:
    f.write(f"run: n={N} seed_offset={SEED_OFFSET}\n")
    f.write(f"HP_MULT: {fc.HP_MULT}\n")
    f.write(f"HP_POOL: {fc.HP_POOL}\n")
    f.write(f"wincap: {config.wincap}\n")
    f.write(f"stage6_chest_natural_maxwin_weight: {config.stage6_chest_natural_maxwin_weight}\n")
    f.write(f"chain_break_threshold: 2   chain_break_step: 0.30\n")
    f.write(f"\nregular reward tiers (12): {sorted(regular_weights.items())}\n")
    f.write(f"\nstage6 chest tiers (9, weight): {sorted(chest_weights.items())}\n")
    f.write(f"\nstage_clear_pruned_tiers: {config.stage_clear_pruned_tiers}\n")
    f.write(f"\nboss_stage_table: {config.boss_stage_table}\n")
print(f"wrote {snap_path}")

# ---- summary stats ----
totals = [r[2] for r in rows]
spins_list = [r[3] for r in rows]
buckets = {s: [] for s in range(1, 7)}
for r in rows:
    buckets[r[4]].append(r[2])
totals_sorted = sorted(totals)


def pct(p):
    idx = min(N - 1, int(p * N))
    return totals_sorted[idx]


mean = sum(totals) / N
median = statistics.median(totals)
n_maxwin = sum(r[8] for r in rows)
n_stage6 = sum(r[6] for r in rows)

summary_path = os.path.join(OUT_DIR, "summary.txt")
with open(summary_path, "w") as f:
    f.write(f"n={N}  elapsed={elapsed:.1f}s\n\n")
    f.write(f"mean={mean:.2f}x  median={median:.2f}x  ratio={100*median/mean:.2f}%\n")
    f.write(f"zero%={100*sum(1 for t in totals if t==0)/N:.3f}%\n")
    f.write(f"mean spins={sum(spins_list)/N:.2f}\n\n")
    f.write("percentiles:\n")
    for p in [0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 0.995, 0.999, 0.9999]:
        f.write(f"  p{p*100:>6.2f} = {pct(p):>10.2f}x\n")
    f.write(f"  max observed = {totals_sorted[-1]:.2f}x\n\n")
    f.write("bucket (max stage reached) breakdown:\n")
    for s in range(1, 7):
        b = buckets[s]
        if not b:
            f.write(f"  stage {s}: 0 sessions\n")
            continue
        f.write(f"  stage {s}: n={len(b):>6} ({100*len(b)/N:5.2f}%)  mean={sum(b)/len(b):9.2f}x  "
                f"median={statistics.median(b):9.2f}x  min={min(b):8.2f}x  max={max(b):9.2f}x\n")
    f.write(f"\nstage6 chest reached: {n_stage6}/{N} ({100*n_stage6/N:.4f}%)\n")
    f.write(f"maxwin tier ({MAXWIN_VALUE}x) fired: {n_maxwin}/{N}")
    if n_maxwin > 0:
        f.write(f"  (1-in-{N/n_maxwin:.0f}, observed)\n")
    else:
        f.write("  (0 observed this run)\n")
print(f"wrote {summary_path}")
print(open(summary_path).read())

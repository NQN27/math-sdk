import sys, os, random, statistics, warnings, csv
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager
import gen_stage_reels as gsr

OUT_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch"
N_ROWS = gsr.N_ROWS  # 307

# --- Experiment: does injecting periodic RUNS of a repeated symbol into
# col0 (the anchor column - every payline win is anchored there, per
# game_config.py's paytable comment) reduce the "dead reveal" rate (no win
# at all on a spin) without blowing out the mean, at the cost of somewhat
# shorter average cascade chains? User's hypothesis: smoothing the gap
# between deadspin-rate and average-chain-length should feel better to a
# player even if peak chain length drops a bit.
#
# Mechanism: instead of drawing all N_ROWS=307 col0 cells i.i.d. (current
# production gen_stage_reels.py behavior), intersperse short RUNS of
# `run_len` consecutive identical cells (symbol drawn weighted from the
# same col0 shape, so no bias introduced beyond what naturally exists -
# L1's weight=65 is already dominant, so most runs land on L1/L2) at random
# gaps of `gap_range` i.i.d. cells apart. This raises the local
# correlation/consistency of col0 without changing its overall weighted
# symbol-frequency (each run's symbol is still drawn proportional to the
# existing weights).


def build_column_with_runs(weights, n, rng, run_len=3, gap_range=(5, 15)):
    names = list(weights.keys())
    wts = list(weights.values())
    col = []
    while len(col) < n:
        gap = rng.randint(*gap_range)
        for _ in range(min(gap, n - len(col))):
            col.append(rng.choices(names, weights=wts, k=1)[0])
        if len(col) >= n:
            break
        sym = rng.choices(names, weights=wts, k=1)[0]
        for _ in range(min(run_len, n - len(col))):
            col.append(sym)
    return col[:n]


def write_test_reel(path, w_col0, w_other, seed, run_len, gap_range):
    rng = random.Random(seed)
    cols = [build_column_with_runs(w_col0, N_ROWS, rng, run_len, gap_range)]
    for _ in range(4):
        cols.append(gsr.build_column(w_other, N_ROWS, rng))
    with open(path, "w", newline="") as f:
        for r in range(N_ROWS):
            f.write(",".join(cols[c][r] for c in range(5)) + "\n")


# --- Chain-length instrumentation (same monkeypatch as normal_chain_diagnostic.py) ---
_original_evaluate = gamestate_mod.GameState.evaluate_and_explode
_original_run_one_bonus_spin = gamestate_mod.GameState.run_one_bonus_spin


def _patched_evaluate(self, *a, **kw):
    self._diag_pass_count = getattr(self, "_diag_pass_count", 0) + 1
    return _original_evaluate(self, *a, **kw)


def _patched_run_one_bonus_spin(self, both_ways):
    self._diag_pass_count = 0
    result = _original_run_one_bonus_spin(self, both_ways)
    if not hasattr(self, "_diag_spin_chain_lengths"):
        self._diag_spin_chain_lengths = []
    self._diag_spin_chain_lengths.append(self._diag_pass_count)
    return result


gamestate_mod.GameState.evaluate_and_explode = _patched_evaluate
gamestate_mod.GameState.run_one_bonus_spin = _patched_run_one_bonus_spin


def measure(n, seed_offset, tag, use_test_reel, save_csv=False):
    config = game_config_mod.GameConfig()
    config.bonus_safety_cap_spins = 150
    if use_test_reel:
        test_reel_id = "BM_Reels_S1_col0runtest"
        config.reels = dict(config.reels)
        config.reels[test_reel_id] = config.read_reels_csv(
            os.path.join(OUT_DIR, "BM_Reels_S1_col0runtest.csv")
        )
        config.bonus_tier_stage_reel = {
            t: dict(d) for t, d in config.bonus_tier_stage_reel.items()
        }
        config.bonus_tier_stage_reel["normal"][1] = test_reel_id

    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals = []
    spin1_chain = []
    spin1_chain_zero = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs._diag_spin_chain_lengths = []
            gs.run_bonus_session("normal")
            payout = gs.win_manager.running_bet_win
            totals.append(payout)
            chains = gs._diag_spin_chain_lengths
            if chains:
                spin1_chain.append(chains[0])
                if payout == 0:
                    spin1_chain_zero.append(chains[0])

    if save_csv:
        with open(f"{OUT_DIR}\\{tag}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["payout_multiplier"])
            for t in totals:
                w.writerow([t])

    mean = sum(totals) / n
    median = statistics.median(totals)
    stdev = statistics.pstdev(totals)
    se = stdev / (n ** 0.5)
    ratio = median / mean * 100 if mean > 0 else 0
    under5 = 100 * sum(1 for t in totals if t < 5) / n
    zero = 100 * sum(1 for t in totals if t == 0) / n
    dead_reveal_rate = 100 * sum(1 for c in spin1_chain if c == 1) / len(spin1_chain)
    mean_chain1 = statistics.mean(spin1_chain)
    print(
        f"[{tag}] (n={n}): mean={mean:.2f}x (+/-{1.96*se:.2f}) median={median:.2f}x "
        f"ratio={ratio:.1f}% CV={stdev/mean:.2f} under5x={under5:.2f}% zero={zero:.2f}% "
        f"spin1-dead-reveal-rate={dead_reveal_rate:.2f}% spin1-mean-chain={mean_chain1:.2f}"
    )
    return mean, median


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000

    # Build the test reel's col0/other weights matching Normal stage-1's
    # current production profile exactly (23% wild), so the ONLY thing
    # under test is col0's run-injection structure.
    pct = gsr.STAGE_WILD_PCT["normal"][1]  # 23.0
    pfrac = gsr.POWER_FRAC_OF_WILD["normal"]  # 0.0
    w_col0 = gsr.make_weights(gsr.NONWILD["normal"]["col0"], pct, pfrac)
    w_other = gsr.make_weights(gsr.NONWILD["normal"]["other"], pct, pfrac)

    run_len = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    gap_lo = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    gap_hi = int(sys.argv[4]) if len(sys.argv) > 4 else 15

    write_test_reel(
        os.path.join(OUT_DIR, "BM_Reels_S1_col0runtest.csv"),
        w_col0, w_other, seed=90001, run_len=run_len, gap_range=(gap_lo, gap_hi),
    )

    measure(n, 111222, "normal_col0_baseline", use_test_reel=False, save_csv=True)
    measure(n, 111333, f"normal_col0_runtest_len{run_len}_gap{gap_lo}-{gap_hi}", use_test_reel=True, save_csv=True)

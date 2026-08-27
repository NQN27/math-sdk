import sys, random, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# SCRATCH-ONLY experiment (per game designer, 2026-08-18: "just try it, only
# testing, don't apply") - does a very light, ISOLATED stage-1 wild-density
# cut (23% -> 22%, stage 1 only, stages 2-6 completely untouched) narrow the
# spin#1 connect-rate cliff (82% -> ~55%+ at stage 2) without collapsing the
# payout floor the way the historical 23->19 cut did? Swaps config.reels
# in-memory only via read_reels_csv on a scratch CSV - never touches the
# real games/0_0_boss_lines/reels/BM_Reels_S1.csv.

SCRATCH_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch\stage1_experiment"

_orig_create_board = gamestate_mod.GameState.create_board_reelstrips
_orig_evaluate = gamestate_mod.GameState.evaluate_and_explode

_state = {"is_first_pass": True, "stage_at_draw": 1}
_rows = []  # (stage, connected)


def hooked_create_board(self):
    _state["is_first_pass"] = True
    _state["stage_at_draw"] = getattr(self, "stage", 1)
    return _orig_create_board(self)


def hooked_evaluate(self, both_ways=False):
    result = _orig_evaluate(self, both_ways=both_ways)
    if _state["is_first_pass"]:
        _state["is_first_pass"] = False
        _rows.append((_state["stage_at_draw"], self.win_data.get("totalWin", 0) > 0))
    return result


gamestate_mod.GameState.create_board_reelstrips = hooked_create_board
gamestate_mod.GameState.evaluate_and_explode = hooked_evaluate


def measure(n, seed_offset, tag, stage1_variant_pct):
    config = game_config_mod.GameConfig()
    if stage1_variant_pct is not None:
        path = f"{SCRATCH_DIR}\\BM_Reels_S1_wild{int(stage1_variant_pct)}.csv"
        config.reels["BM_Reels_S1"] = config.read_reels_csv(path)
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    _rows.clear()
    totals = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session("normal")
            totals.append(gs.win_manager.running_bet_win)

    by_stage = {}
    for stage, connected in _rows:
        by_stage.setdefault(stage, [0, 0])
        by_stage[stage][0] += 1
        if connected:
            by_stage[stage][1] += 1

    mean = sum(totals) / n
    import statistics
    median = statistics.median(totals)
    ratio = median / mean * 100 if mean > 0 else 0
    zero = 100 * sum(1 for t in totals if t == 0) / n

    print(f"\n=== {tag} (n={n}, stage1_wild%={stage1_variant_pct}) ===")
    print(f"payout: mean={mean:.2f}x median={median:.2f}x ratio={ratio:.1f}% zero={zero:.2f}%")
    print("connect-rate by stage: " + ", ".join(
        f"s{s}={100*by_stage[s][1]/by_stage[s][0]:.2f}%" for s in sorted(by_stage)
    ))


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    # Reproduce the real 23% first as a sanity check. NOTE: this is NOT
    # verified byte-identical to the real BM_Reels_S1.csv - gen_stage_reels.py
    # increments its seed per file written across all tiers in dict order, so
    # stage 1 only gets seed=777 if it happens to be first in that order.
    # Measured mean=81.91x here vs baseline=82.16x (0.3% apart) - close
    # enough to be a fair sanity check, but not proven identical.
    measure(n, 998000, "stage1_wild=23%_(reproduction_of_real)", 23.0)
    measure(n, 998001, "stage1_wild=22%_(light_cut_test)", 22.0)
    measure(n, 998002, "baseline_unmodified_config", None)

import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# REAL chain-damping (2026-08-18, per designer request to actually try this
# for real this time - NOT the old fictional "chain-break" weighted-pool
# patch from normal_3param_matrix_test.py, which never existed in real game
# code). Mechanism: reuses the EXACT same real, RGS-safe
# _route_column_force_deadspin method the game already uses for initial-
# reveal dead-spin routing, but calls it on tumble.tumble_board's OUTPUT
# (the refilled board) once a spin's pass count crosses a threshold, with a
# probability that escalates per extra pass ("giam dan xac suat connect tiep
# sau moi pass" - gradually reduce continued-connect probability after each
# pass, the designer's original framing of this idea). Since
# _route_column_force_deadspin redraws a column from a genuine new random
# pick BEFORE the next evaluate_and_explode call decides whether this
# refilled board wins - i.e. before that pass's outcome is evaluated, not
# overriding an already-decided one - this respects the same RGS-replay-
# determinism constraint as the initial-reveal mechanism.
#
# SCRATCH ONLY - monkeypatches tumble_board/evaluate_and_explode; does not
# touch the real src/calculations/tumble.py or game_executables.py.

_orig_create_board = gamestate_mod.GameState.create_board_reelstrips
_orig_evaluate = gamestate_mod.GameState.evaluate_and_explode
_orig_tumble = gamestate_mod.GameState.tumble_board

_state = {"pass_count": 0, "chain_break_threshold": 2, "chain_break_step": 0.0, "general_chance": 0.0}
_all_pass_counts = []


def patched_create_board(self):
    if _state["pass_count"] > 0:
        _all_pass_counts.append(_state["pass_count"])
    _state["pass_count"] = 0

    _orig_create_board(self)

    if not getattr(self, "in_bonus", False):
        return
    chance = _state["general_chance"]
    if chance <= 0:
        return
    routed_any = False
    for col in (1, 2, 3):
        if random.random() < chance:
            routed_any = True
            self._route_column_force_deadspin(col)
    if routed_any:
        self.get_special_symbols_on_board()


def patched_evaluate(self, both_ways=False):
    result = _orig_evaluate(self, both_ways=both_ways)
    if self.win_data.get("totalWin", 0) > 0:
        _state["pass_count"] += 1
    return result


def patched_tumble(self):
    result = _orig_tumble(self)
    if not getattr(self, "in_bonus", False):
        return result
    threshold = _state["chain_break_threshold"]
    step = _state["chain_break_step"]
    extra_passes = _state["pass_count"] - threshold
    if extra_passes < 0 or step <= 0:
        return result
    chance = min(1.0, step * (extra_passes + 1))
    routed_any = False
    for col in (1, 2, 3):
        if random.random() < chance:
            routed_any = True
            self._route_column_force_deadspin(col)
    if routed_any:
        self.get_special_symbols_on_board()
    return result


gamestate_mod.GameState.create_board_reelstrips = patched_create_board
gamestate_mod.GameState.evaluate_and_explode = patched_evaluate
gamestate_mod.GameState.tumble_board = patched_tumble


def measure(n, seed_offset, tag, hp_choices, general_chance, chain_break_threshold, chain_break_step):
    config = game_config_mod.GameConfig()
    config.bonus_player_hp_choices["normal"] = hp_choices
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    _all_pass_counts.clear()
    totals, spins_list = [], []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            _state["pass_count"] = 0
            _state["general_chance"] = general_chance
            _state["chain_break_threshold"] = chain_break_threshold
            _state["chain_break_step"] = chain_break_step
            gs.run_bonus_session("normal")
            if _state["pass_count"] > 0:
                _all_pass_counts.append(_state["pass_count"])
                _state["pass_count"] = 0
            totals.append(gs.win_manager.running_bet_win)

    counts = _all_pass_counts
    total_spins = len(counts)
    mean_passes = sum(counts) / total_spins
    dist = {}
    for c in counts:
        dist[c] = dist.get(c, 0) + 1
    long_chain = sum(v for k, v in dist.items() if k >= 4)
    mean_p = sum(totals) / n
    median_p = statistics.median(totals)
    ratio = median_p / mean_p * 100 if mean_p > 0 else 0

    print(f"\n=== {tag} (n={n}) hp={hp_choices} gd={general_chance:.2f} "
          f"cb_threshold={chain_break_threshold} cb_step={chain_break_step:.2f} ===")
    print(f"chain: mean_passes={mean_passes:.2f} median={statistics.median(counts)} max={max(counts)} "
          f">=4pass={100*long_chain/total_spins:.2f}%")
    print(f"payout: mean={mean_p:.2f}x median={median_p:.2f}x ratio={ratio:.1f}%")
    return dict(tag=tag, mean_passes=mean_passes, long_chain_pct=100*long_chain/total_spins, mean_p=mean_p, ratio=ratio)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    # First: isolate chain-damping alone (baseline HP, no general deadspin)
    # to find threshold/step that lands mean_passes~2.5-2.6, >=4pass~10-20%.
    CANDIDATES = [
        ("baseline_no_damping", [50, 50, 50, 100, 100], 0.0, 99, 0.0),
        ("cb_t2_s010", [50, 50, 50, 100, 100], 0.0, 2, 0.10),
        ("cb_t2_s015", [50, 50, 50, 100, 100], 0.0, 2, 0.15),
        ("cb_t2_s020", [50, 50, 50, 100, 100], 0.0, 2, 0.20),
        ("cb_t3_s015", [50, 50, 50, 100, 100], 0.0, 3, 0.15),
        ("cb_t3_s025", [50, 50, 50, 100, 100], 0.0, 3, 0.25),
    ]
    for i, (tag, hp, gd, th, step) in enumerate(CANDIDATES):
        measure(n, 991000 + i, tag, hp, gd, th, step)

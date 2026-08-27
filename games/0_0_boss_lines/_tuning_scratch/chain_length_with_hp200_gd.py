import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Chain length (tumble-cascade passes per winning spin) under the candidate
# HP=200 + general_deadspin_chance combo, vs current production baseline -
# does throttling connect frequency (the general dead-spin lever) change
# how LONG a chain runs once a spin does connect? Combines chain_length_
# diagnostic.py's instrumentation with general_deadspin_sweep.py's patch in
# a single script (importing both separately would clobber each other's
# create_board_reelstrips monkeypatch).

_orig_create_board = gamestate_mod.GameState.create_board_reelstrips
_orig_evaluate = gamestate_mod.GameState.evaluate_and_explode

_spin_passes = {"count": 0}
_all_pass_counts = []
_state = {"general_chance": 0.0}


def combined_create_board(self):
    if _spin_passes["count"] > 0:
        _all_pass_counts.append(_spin_passes["count"])
    _spin_passes["count"] = 0

    _orig_create_board(self)

    # Same general dead-spin branch as general_deadspin_sweep.py - applies
    # on every in-bonus spin (real production only forces this for base
    # game spins and the single post-stage-clear grace spin).
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


def combined_evaluate(self, both_ways=False):
    result = _orig_evaluate(self, both_ways=both_ways)
    if self.win_data.get("totalWin", 0) > 0:
        _spin_passes["count"] += 1
    return result


gamestate_mod.GameState.create_board_reelstrips = combined_create_board
gamestate_mod.GameState.evaluate_and_explode = combined_evaluate


def measure(n, seed_offset, tag, hp_choices, general_chance):
    config = game_config_mod.GameConfig()
    config.bonus_player_hp_choices["normal"] = hp_choices
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    _all_pass_counts.clear()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            _spin_passes["count"] = 0
            _state["general_chance"] = general_chance
            gs.run_bonus_session("normal")
            if _spin_passes["count"] > 0:
                _all_pass_counts.append(_spin_passes["count"])
                _spin_passes["count"] = 0

    counts = _all_pass_counts
    total_spins = len(counts)
    mean_passes = sum(counts) / total_spins
    dist = {}
    for c in counts:
        dist[c] = dist.get(c, 0) + 1
    print(f"\n=== {tag} (n={n} sessions, {total_spins} winning spins) hp={hp_choices} gd={general_chance:.2f} ===")
    print(f"mean passes-per-winning-spin: {mean_passes:.2f}, median: {statistics.median(counts)}, max: {max(counts)}")
    long_chain = sum(v for k, v in dist.items() if k >= 4)
    print(f">=4-pass chains: {100*long_chain/total_spins:.2f}% of winning spins")
    single_pass = dist.get(1, 0)
    print(f"single-pass (no chain): {100*single_pass/total_spins:.2f}% of winning spins")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50000
    measure(n, 994500, "baseline_current_prod", [50, 50, 50, 100, 100], 0.0)
    measure(n, 994501, "hp200_gd65_candidate", [200, 200, 200, 200, 200], 0.65)

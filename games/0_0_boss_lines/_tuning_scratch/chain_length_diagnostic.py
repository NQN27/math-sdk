import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# How long is a single spin's cascade in REAL, pure production (no chain-
# break patch - that mechanic doesn't exist in game_bonus.py/game_
# executables.py, confirmed earlier this session)? "Chain length" here =
# number of winning evaluate_and_explode passes within ONE spin (1 = just
# the initial reveal connects and then stops, no further tumble; 2+ = the
# tumble refill ALSO won, extending the cascade further).

_orig_evaluate = gamestate_mod.GameState.evaluate_and_explode
_orig_create_board = gamestate_mod.GameState.create_board_reelstrips

_spin_passes = {"count": 0}
_all_pass_counts = []


def counted_create_board(self):
    if _spin_passes["count"] > 0:
        _all_pass_counts.append(_spin_passes["count"])
    _spin_passes["count"] = 0
    return _orig_create_board(self)


def counted_evaluate(self, both_ways=False):
    result = _orig_evaluate(self, both_ways=both_ways)
    if self.win_data.get("totalWin", 0) > 0:
        _spin_passes["count"] += 1
    return result


gamestate_mod.GameState.create_board_reelstrips = counted_create_board
gamestate_mod.GameState.evaluate_and_explode = counted_evaluate


def measure(n, seed_offset, tag):
    config = game_config_mod.GameConfig()
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
    print(f"\n=== {tag} (n={n} sessions, {total_spins} winning spins measured) ===")
    print(f"mean passes-per-winning-spin: {mean_passes:.2f}, median: {statistics.median(counts)}, max: {max(counts)}")
    print("chain-length distribution (passes : % of winning spins):")
    for c in sorted(dist):
        print(f"  {c:>3}: {100*dist[c]/total_spins:5.2f}%")
    long_chain = sum(v for k, v in dist.items() if k >= 4)
    print(f">=4-pass chains: {100*long_chain/total_spins:.2f}% of winning spins")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    measure(n, 995000, "current_production_chain_length")

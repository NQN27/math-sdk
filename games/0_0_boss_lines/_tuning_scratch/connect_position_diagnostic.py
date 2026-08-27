import sys, random, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Does "connect" (>0 win on the INITIAL reveal of a spin) cluster at spin
# position 1-2 of a session, then fizzle to mostly-dead later spins? This is
# a different question from chain length (passes within one spin) - it's
# about WHICH spin-index in the session sequence tends to connect at all.
# Candidate cause: bonus_tier_stage_reel's per-stage Wild/Power tapering -
# stage 1's reel may simply be much richer than stage 4-6's, and most
# sessions are still on an early stage during their first couple of spins.

_orig_create_board = gamestate_mod.GameState.create_board_reelstrips
_orig_evaluate = gamestate_mod.GameState.evaluate_and_explode

_state = {"spin_idx": 0, "is_first_pass": True, "initial_connect": None}
# rows: (spin_index_in_session, stage_at_draw, connected_bool)
_rows = []


def hooked_create_board(self):
    _state["spin_idx"] += 1
    _state["is_first_pass"] = True
    _state["initial_connect"] = None
    _state["stage_at_draw"] = getattr(self, "stage", 1)
    return _orig_create_board(self)


def hooked_evaluate(self, both_ways=False):
    result = _orig_evaluate(self, both_ways=both_ways)
    if _state["is_first_pass"]:
        _state["is_first_pass"] = False
        connected = self.win_data.get("totalWin", 0) > 0
        _rows.append((_state["spin_idx"], _state["stage_at_draw"], connected))
    return result


gamestate_mod.GameState.create_board_reelstrips = hooked_create_board
gamestate_mod.GameState.evaluate_and_explode = hooked_evaluate


def measure(n, seed_offset, tag):
    config = game_config_mod.GameConfig()
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    _rows.clear()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            _state["spin_idx"] = 0
            gs.run_bonus_session("normal")

    by_pos = {}
    for spin_idx, stage, connected in _rows:
        by_pos.setdefault(spin_idx, [0, 0])
        by_pos[spin_idx][0] += 1
        if connected:
            by_pos[spin_idx][1] += 1

    print(f"\n=== {tag} (n={n} sessions, {len(_rows)} spins total) ===")
    print("spin position in session : connect-rate (n spins at that position)")
    for pos in sorted(by_pos)[:15]:
        total, hits = by_pos[pos]
        print(f"  spin #{pos:>2}: {100*hits/total:5.2f}%  (n={total})")

    by_stage = {}
    for spin_idx, stage, connected in _rows:
        by_stage.setdefault(stage, [0, 0])
        by_stage[stage][0] += 1
        if connected:
            by_stage[stage][1] += 1
    print("connect-rate by STAGE (regardless of spin position):")
    for s in sorted(by_stage):
        total, hits = by_stage[s]
        print(f"  stage {s}: {100*hits/total:5.2f}%  (n={total})")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    measure(n, 997000, "connect_position")

import sys, random, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import final_combined_candidate as fc
from src.wins.win_manager import WinManager

# Re-run of connect_position_diagnostic.py's check (spin-position and
# per-stage connect-rate) against the NEW final combined candidate, to
# verify the earlier-fixed "action clusters in spin 1, then fizzles"
# complaint doesn't come back under the redesigned difficulty curve.

_orig_create_board = fc.gamestate_mod.GameState.create_board_reelstrips
_orig_evaluate = fc.gamestate_mod.GameState.evaluate_and_explode

_pos_state = {"spin_idx": 0, "is_first_pass": True}
_rows = []


def hooked_create_board(self):
    _pos_state["spin_idx"] += 1
    _pos_state["is_first_pass"] = True
    _pos_state["stage_at_draw"] = getattr(self, "stage", 1)
    return fc.patched_create_board(self)


def hooked_evaluate(self, both_ways=False):
    result = _orig_evaluate(self, both_ways=both_ways)
    if _pos_state["is_first_pass"]:
        _pos_state["is_first_pass"] = False
        connected = self.win_data.get("totalWin", 0) > 0
        _rows.append((_pos_state["spin_idx"], _pos_state["stage_at_draw"], connected))
    return result


fc.gamestate_mod.GameState.create_board_reelstrips = hooked_create_board
fc.gamestate_mod.GameState.evaluate_and_explode = hooked_evaluate


def measure(n, seed_offset):
    config = fc.build_config(1.0, 45.0)
    gs = fc.gamestate_mod.GameState(config)
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
            _pos_state["spin_idx"] = 0
            fc._state["max_stage"] = 1
            fc._state["pass_count"] = 0
            fc._state["chain_block_pending"] = False
            fc._state["general_chance"] = 0.0
            fc._state["chain_break_threshold"] = 2
            fc._state["chain_break_step"] = 0.30
            gs.run_bonus_session("normal")

    by_pos = {}
    for spin_idx, stage, connected in _rows:
        by_pos.setdefault(spin_idx, [0, 0])
        by_pos[spin_idx][0] += 1
        if connected:
            by_pos[spin_idx][1] += 1

    print(f"\n=== connect_position (n={n} sessions, {len(_rows)} spins total) [NEW final candidate] ===")
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
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    measure(n, 971000)

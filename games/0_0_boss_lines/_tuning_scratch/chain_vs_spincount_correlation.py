import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Does long chain length actually EXPLAIN the <=2-spin sessions, or is it
# really just the small HP pool (50 for stages 1-3) being 1-2 unconditional
# counter-attacks from hp_depleted regardless of chain length? Correlate
# per-SESSION max chain length against spin_count/end_reason on the same
# run, pure production, before designing any chain-damping mechanic.

_orig_evaluate = gamestate_mod.GameState.evaluate_and_explode
_orig_create_board = gamestate_mod.GameState.create_board_reelstrips
_orig_run_one_bonus_spin = gamestate_mod.GameState.run_one_bonus_spin

_spin_passes = {"count": 0}
_session_max_chain = {"val": 0}


def counted_create_board(self):
    if _spin_passes["count"] > _session_max_chain["val"]:
        _session_max_chain["val"] = _spin_passes["count"]
    _spin_passes["count"] = 0
    return _orig_create_board(self)


def counted_evaluate(self, both_ways=False):
    result = _orig_evaluate(self, both_ways=both_ways)
    if self.win_data.get("totalWin", 0) > 0:
        _spin_passes["count"] += 1
    return result


def counted_run_one_bonus_spin(self, both_ways):
    self._diag_spin_count = getattr(self, "_diag_spin_count", 0) + 1
    return _orig_run_one_bonus_spin(self, both_ways)


gamestate_mod.GameState.create_board_reelstrips = counted_create_board
gamestate_mod.GameState.evaluate_and_explode = counted_evaluate
gamestate_mod.GameState.run_one_bonus_spin = counted_run_one_bonus_spin


def measure(n, seed_offset, tag):
    config = game_config_mod.GameConfig()
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    rows = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs._diag_spin_count = 0
            _spin_passes["count"] = 0
            _session_max_chain["val"] = 0
            gs.run_bonus_session("normal")
            if _spin_passes["count"] > _session_max_chain["val"]:
                _session_max_chain["val"] = _spin_passes["count"]
            rows.append((gs._diag_spin_count, _session_max_chain["val"], getattr(gs, "bonus_end_reason", "?")))

    le2 = [r for r in rows if r[0] <= 2]
    gt2 = [r for r in rows if r[0] > 2]
    print(f"\n=== {tag} (n={n}) ===")
    print(f"sessions with spin_count<=2: {len(le2)} ({100*len(le2)/n:.2f}%)")
    print(f"  mean max_chain_length: {sum(r[1] for r in le2)/len(le2):.2f}  "
          f"(vs {sum(r[1] for r in gt2)/max(1,len(gt2)):.2f} for spin_count>2)")
    print(f"  end_reason breakdown: hp_depleted={100*sum(1 for r in le2 if r[2]=='hp_depleted')/len(le2):.1f}%, "
          f"stage_cleared={100*sum(1 for r in le2 if r[2]=='stage_cleared')/len(le2):.1f}%")
    chain_ge4 = [r for r in rows if r[1] >= 4]
    chain_lt4 = [r for r in rows if r[1] < 4]
    print(f"sessions with max_chain>=4 (n={len(chain_ge4)}): mean spin_count={sum(r[0] for r in chain_ge4)/max(1,len(chain_ge4)):.2f}")
    print(f"sessions with max_chain<4  (n={len(chain_lt4)}): mean spin_count={sum(r[0] for r in chain_lt4)/max(1,len(chain_lt4)):.2f}")
    # among the <=2-spin sessions, how many NEVER had a chain>=4 at all?
    le2_no_long_chain = sum(1 for r in le2 if r[1] < 4)
    print(f"of the <=2-spin sessions, {100*le2_no_long_chain/len(le2):.1f}% had NO chain>=4 at all "
          f"(i.e. would still end in <=2 spins even with long chains fully suppressed)")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    measure(n, 996000, "chain_vs_spincount")

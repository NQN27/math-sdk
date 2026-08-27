import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Designer's idea (2026-08-18): instead of raising HP and cutting reward-
# table K to compensate, raise HP (more spins needed to grind through) AND
# apply Controlled Deadspin Routing (the SAME real, already-shipped
# _route_column_force_deadspin mechanism used for base game + the post-
# stage-clear grace spin - RGS-safe, redraws a column's stop BEFORE reveal)
# on a GENERAL chance across EVERY bonus spin, not just the grace spin.
# Rationale: more spins that produce zero connect => more spins needed to
# deal the same total damage => longer sessions (the actual ask: "more
# spin") AND fewer winning spins overall => naturally suppresses BOTH
# line-pay and reward-drop frequency without touching the reward table's
# values at all - a genuinely different lever than the K-rescale/HP-only
# sweeps tried so far. SCRATCH ONLY - monkeypatches create_board_reelstrips
# to add a new branch; does not touch the real game_executables.py.

_orig_create_board = gamestate_mod.GameState.create_board_reelstrips
_orig_run_one_spin = gamestate_mod.GameState.run_one_bonus_spin
_orig_clear_stage = gamestate_mod.GameState.clear_stage

_state = {"spins": 0, "max_stage": 1, "general_chance": 0.0}


def patched_create_board(self):
    _orig_create_board(self)
    # _orig_create_board already handles: base game deadspin_force_chance,
    # and the grace-spin (grace_deadspin_pending) case, consuming that flag.
    # This adds a THIRD, independent chance for every OTHER in-bonus spin
    # (i.e. any spin where grace_deadspin_pending was NOT the trigger).
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


def hooked_run_one_spin(self, *a, **k):
    _state["spins"] += 1
    return _orig_run_one_spin(self, *a, **k)


def hooked_clear_stage(self, *a, **k):
    result = _orig_clear_stage(self, *a, **k)
    _state["max_stage"] = max(_state["max_stage"], getattr(self, "stage", 1))
    return result


gamestate_mod.GameState.create_board_reelstrips = patched_create_board
gamestate_mod.GameState.run_one_bonus_spin = hooked_run_one_spin
gamestate_mod.GameState.clear_stage = hooked_clear_stage


def measure(n, seed_offset, tag, hp_choices, general_chance):
    config = game_config_mod.GameConfig()
    config.bonus_player_hp_choices["normal"] = hp_choices
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals, spins_list, s6_reach = [], [], []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            _state["spins"] = 0
            _state["max_stage"] = 1
            _state["general_chance"] = general_chance
            gs.run_bonus_session("normal")
            totals.append(gs.win_manager.running_bet_win)
            spins_list.append(_state["spins"])
            s6_reach.append(_state["max_stage"] >= 6)

    mean = sum(totals) / n
    median = statistics.median(totals)
    ratio = median / mean * 100 if mean > 0 else 0
    zero = 100 * sum(1 for t in totals if t == 0) / n
    spins_le2 = 100 * sum(1 for s in spins_list if s <= 2) / n
    mean_spins = sum(spins_list) / n
    s6_pct = 100 * sum(s6_reach) / n

    print(f"\n=== {tag} (n={n}) hp={hp_choices} general_deadspin_chance={general_chance:.2f} ===")
    print(f"mean={mean:.2f}x median={median:.2f}x ratio={ratio:.1f}% zero={zero:.2f}%")
    print(f"spins: mean={mean_spins:.2f} spins<=2={spins_le2:.2f}% | stage6 reach={s6_pct:.2f}%")
    return dict(tag=tag, mean=mean, median=median, ratio=ratio, spins_le2=spins_le2, s6_pct=s6_pct, mean_spins=mean_spins)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    CANDIDATES = [
        ("baseline_current_prod", [50, 50, 50, 100, 100], 0.0),
        ("hp200_flat_gd00", [200, 200, 200, 200, 200], 0.0),
        ("hp200_flat_gd15", [200, 200, 200, 200, 200], 0.15),
        ("hp200_flat_gd30", [200, 200, 200, 200, 200], 0.30),
        ("hp200_flat_gd45", [200, 200, 200, 200, 200], 0.45),
        ("hp200_flat_gd60", [200, 200, 200, 200, 200], 0.60),
    ]
    results = [measure(n, 999700 + i, tag, hp, gd) for i, (tag, hp, gd) in enumerate(CANDIDATES)]

    print("\n=== SUMMARY ===")
    for r in results:
        print(f"{r['tag']:>20}: mean={r['mean']:.2f}x median={r['median']:.2f}x ratio={r['ratio']:.1f}%"
              f" spins<=2={r['spins_le2']:.2f}% s6reach={r['s6_pct']:.2f}% mean_spins={r['mean_spins']:.2f}")

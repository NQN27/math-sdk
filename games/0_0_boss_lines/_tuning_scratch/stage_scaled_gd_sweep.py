import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Designer's idea (2026-08-19): make general_deadspin_chance a function of
# self.stage instead of a flat constant, so later stages (where the
# stage-to-stage survival rate was measured to climb from 62% at stage1->2
# up to 82-90% at stage5->6) get MORE suppression - restoring a properly
# narrowing funnel instead of relying on a single flat gd value that can't
# fix both the early game (spins<=2%) and late game (stage6 overshoot) at
# once. gd_by_stage is a dict {stage: chance}, looked up via self.stage at
# the moment create_board_reelstrips fires for that spin.

_orig_create_board = gamestate_mod.GameState.create_board_reelstrips
_orig_run_one_spin = gamestate_mod.GameState.run_one_bonus_spin
_orig_clear_stage = gamestate_mod.GameState.clear_stage

_state = {"spins": 0, "max_stage": 1, "gd_by_stage": {}}


def patched_create_board(self):
    _orig_create_board(self)
    if not getattr(self, "in_bonus", False):
        return
    stage = getattr(self, "stage", 1)
    chance = _state["gd_by_stage"].get(stage, 0.0)
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


def measure(n, seed_offset, tag, hp_choices, gd_by_stage):
    config = game_config_mod.GameConfig()
    config.bonus_player_hp_choices["normal"] = hp_choices
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals, spins_list, max_stages, end_reasons = [], [], [], []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            _state["spins"] = 0
            _state["max_stage"] = 1
            _state["gd_by_stage"] = gd_by_stage
            gs.run_bonus_session("normal")
            totals.append(gs.win_manager.running_bet_win)
            spins_list.append(_state["spins"])
            max_stages.append(_state["max_stage"])
            end_reasons.append(getattr(gs, "bonus_end_reason", "?"))

    mean = sum(totals) / n
    median = statistics.median(totals)
    ratio = median / mean * 100 if mean > 0 else 0
    zero = 100 * sum(1 for t in totals if t == 0) / n
    spins_le2 = 100 * sum(1 for s in spins_list if s <= 2) / n
    mean_spins = sum(spins_list) / n
    stage_dist = {s: 100 * sum(1 for x in max_stages if x == s) / n for s in range(1, 7)}
    clear_pct = 100 * sum(1 for r in end_reasons if r == "stage_cleared") / n

    print(f"\n=== {tag} (n={n}) hp={hp_choices} gd_by_stage={gd_by_stage} ===")
    print(f"mean={mean:.2f}x median={median:.2f}x ratio={ratio:.1f}% zero={zero:.2f}%")
    print(f"spins: mean={mean_spins:.2f} spins<=2={spins_le2:.2f}%")
    print("max stage reached: " + ", ".join(f"s{s}={stage_dist[s]:.2f}%" for s in range(1, 7)))
    print(f"full-clear rate (stage_cleared): {clear_pct:.2f}%")
    return dict(tag=tag, mean=mean, median=median, ratio=ratio, spins_le2=spins_le2,
                s6_pct=stage_dist[6], clear_pct=clear_pct, mean_spins=mean_spins)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    CANDIDATES = [
        ("baseline", [50, 50, 50, 100, 100], {}),
        ("hp200_flat_gd", [200, 200, 200, 200, 200], {1: 0.65, 2: 0.65, 3: 0.65, 4: 0.65, 5: 0.65, 6: 0.65}),
        ("hp200_ramp_gd_A", [200, 200, 200, 200, 200], {1: 0.55, 2: 0.60, 3: 0.65, 4: 0.70, 5: 0.75, 6: 0.80}),
        ("hp200_ramp_gd_B", [200, 200, 200, 200, 200], {1: 0.50, 2: 0.55, 3: 0.60, 4: 0.68, 5: 0.78, 6: 0.85}),
        ("hp200_ramp_gd_C", [200, 200, 200, 200, 200], {1: 0.45, 2: 0.50, 3: 0.58, 4: 0.65, 5: 0.75, 6: 0.85}),
    ]
    for i, (tag, hp, gd_map) in enumerate(CANDIDATES):
        measure(n, 990500 + i, tag, hp, gd_map)

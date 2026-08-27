import sys, random, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# What does the payout DISTRIBUTION look like specifically among sessions
# that reach stage 6 (not just the mean/median)? Buckets the payout of
# stage-6-reaching sessions into ranges and reports % of that subset in
# each range, for baseline vs the HP=200+general-deadspin candidates.

_orig_create_board = gamestate_mod.GameState.create_board_reelstrips
_orig_clear_stage = gamestate_mod.GameState.clear_stage

_state = {"max_stage": 1, "general_chance": 0.0}

BUCKETS = [
    (0, 0, "= 0x"),
    (0.01, 25, "0-25x"),
    (25, 50, "25-50x"),
    (50, 100, "50-100x"),
    (100, 200, "100-200x"),
    (200, 300, "200-300x"),
    (300, 500, "300-500x"),
    (500, 1000, "500-1000x"),
    (1000, 2500, "1000-2250x (max win)"),
    (2250, float("inf"), ">2250x (should be ~0)"),
]


def patched_create_board(self):
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


def hooked_clear_stage(self, stage):
    result = _orig_clear_stage(self, stage)
    _state["max_stage"] = max(_state["max_stage"], getattr(self, "stage", stage))
    return result


gamestate_mod.GameState.create_board_reelstrips = patched_create_board
gamestate_mod.GameState.clear_stage = hooked_clear_stage


def bucket_of(v):
    if v == 0:
        return BUCKETS[0][2]
    for lo, hi, label in BUCKETS[1:]:
        if lo < v <= hi:
            return label
    return BUCKETS[-1][2]


def measure(n, seed_offset, tag, hp_choices, general_chance):
    config = game_config_mod.GameConfig()
    config.bonus_player_hp_choices["normal"] = hp_choices
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    s6_payouts = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            _state["max_stage"] = 1
            _state["general_chance"] = general_chance
            gs.run_bonus_session("normal")
            if _state["max_stage"] >= 6:
                s6_payouts.append(gs.win_manager.running_bet_win)

    cnt = len(s6_payouts)
    print(f"\n=== {tag} (n={n} sessions, {cnt} reached stage 6 = {100*cnt/n:.2f}%) hp={hp_choices} gd={general_chance:.2f} ===")
    counts = {label: 0 for _, _, label in BUCKETS}
    for v in s6_payouts:
        counts[bucket_of(v)] += 1
    for _, _, label in BUCKETS:
        c = counts[label]
        print(f"  {label:>22}: {100*c/cnt:5.2f}%  (n={c})")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    measure(n, 992500, "baseline_current_prod", [50, 50, 50, 100, 100], 0.0)
    measure(n, 992501, "hp200_gd60", [200, 200, 200, 200, 200], 0.60)
    measure(n, 992502, "hp200_gd65", [200, 200, 200, 200, 200], 0.65)

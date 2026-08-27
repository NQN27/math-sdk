import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Per-stage funnel: for each candidate, bucket sessions by their FINAL max
# stage reached (1-6) and report what fraction of sessions land in each
# bucket plus that bucket's average/median payout. Answers "why is stage-6
# clear rate so high" by showing exactly where the funnel narrows (or fails
# to narrow) stage-by-stage, rather than just the single stage6-reach%
# number measured so far.

_orig_create_board = gamestate_mod.GameState.create_board_reelstrips
_orig_clear_stage = gamestate_mod.GameState.clear_stage

_state = {"max_stage": 1, "general_chance": 0.0}


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


def measure(n, seed_offset, tag, hp_choices, general_chance):
    config = game_config_mod.GameConfig()
    config.bonus_player_hp_choices["normal"] = hp_choices
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    buckets = {s: [] for s in range(1, 7)}
    end_reasons_by_stage = {s: {} for s in range(1, 7)}
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
            ms = _state["max_stage"]
            buckets[ms].append(gs.win_manager.running_bet_win)
            r = getattr(gs, "bonus_end_reason", "?")
            end_reasons_by_stage[ms][r] = end_reasons_by_stage[ms].get(r, 0) + 1

    print(f"\n=== {tag} (n={n}) hp={hp_choices} gd={general_chance:.2f} ===")
    prev_count = n
    for s in range(1, 7):
        vals = buckets[s]
        cnt = len(vals)
        pct = 100 * cnt / n
        pct_of_prev_reaching = 100 * cnt / prev_count if prev_count else 0
        mean_p = sum(vals) / cnt if cnt else 0
        median_p = statistics.median(vals) if cnt else 0
        reasons = ", ".join(f"{k}={100*v/cnt:.1f}%" for k, v in sorted(end_reasons_by_stage[s].items())) if cnt else "-"
        print(f"  stage {s} bucket: {pct:5.2f}% of all sessions ({cnt:>6}) | mean={mean_p:8.2f}x median={median_p:7.2f}x | end: {reasons}")
        # "survival rate" = fraction of sessions that reached stage s that
        # went on past it (i.e. didn't end AT stage s) - approximated as
        # (sessions with max_stage > s) / (sessions with max_stage >= s)
        reached_or_beyond = sum(len(buckets[k]) for k in range(s, 7))
        beyond = sum(len(buckets[k]) for k in range(s + 1, 7))
        if reached_or_beyond:
            print(f"    -> of sessions that reached stage {s}, {100*beyond/reached_or_beyond:.1f}% advanced past it")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    measure(n, 993500, "baseline_current_prod", [50, 50, 50, 100, 100], 0.0)
    measure(n, 993501, "hp200_gd60", [200, 200, 200, 200, 200], 0.60)
    measure(n, 993502, "hp200_gd65", [200, 200, 200, 200, 200], 0.65)

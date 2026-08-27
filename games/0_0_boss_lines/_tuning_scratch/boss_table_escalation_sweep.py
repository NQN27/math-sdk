import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Structural difficulty-curve rebalance (2026-08-19, per designer): current
# boss_stage_table's Dam/HP escalation is TOO GENTLE relative to how fast
# the player's own damage output grows over a session - measured stage-to-
# stage survival rate actually INCREASES with depth (62%->82% at baseline),
# which is why stage6 gets reached far too often (~22%). Designer wants
# stage6 reach down to ~1-2%, achieved by making stages themselves properly
# harder (not by throttling connects via gd, which was shown to wreck ratio/
# zero-payout instead). This sweeps an HP-only escalation multiplier per
# stage (Dam left at base table values, to avoid reopening the "dies within
# 1-2 spins" problem HP=200 already fixed) to find how much steepening is
# needed. HP multiplier is applied ON TOP of the existing boss_hp_reroll/
# +-25% variance mechanism, via roll_stage_bosses's base table lookup.

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


def build_scaled_table(base_table, hp_mult_by_stage):
    scaled = {}
    for stage, bosses in base_table.items():
        mult = hp_mult_by_stage.get(stage, 1.0)
        scaled[stage] = {b: (dam, hp * mult) for b, (dam, hp) in bosses.items()}
    return scaled


def measure(n, seed_offset, tag, hp_choices, hp_mult_by_stage, general_chance=0.0):
    config = game_config_mod.GameConfig()
    config.bonus_player_hp_choices["normal"] = hp_choices
    config.boss_stage_table = build_scaled_table(config.boss_stage_table, hp_mult_by_stage)
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    buckets = {s: [] for s in range(1, 7)}
    totals, spins_list = [], []
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
            buckets[_state["max_stage"]].append(gs.win_manager.running_bet_win)
            totals.append(gs.win_manager.running_bet_win)

    mean = sum(totals) / n
    median = statistics.median(totals)
    ratio = median / mean * 100 if mean > 0 else 0
    zero = 100 * sum(1 for t in totals if t == 0) / n

    print(f"\n=== {tag} (n={n}) hp_mult={hp_mult_by_stage} hp_pool={hp_choices} gd={general_chance:.2f} ===")
    print(f"mean={mean:.2f}x median={median:.2f}x ratio={ratio:.1f}% zero={zero:.2f}%")
    prev_count = n
    for s in range(1, 7):
        cnt = len(buckets[s])
        pct = 100 * cnt / n
        reached_or_beyond = sum(len(buckets[k]) for k in range(s, 7))
        beyond = sum(len(buckets[k]) for k in range(s + 1, 7))
        adv = 100 * beyond / reached_or_beyond if reached_or_beyond else 0
        print(f"  stage {s}: {pct:5.2f}% of sessions | advanced past it: {adv:5.1f}%")
    return dict(tag=tag, mean=mean, ratio=ratio, zero=zero, s6_pct=100*len(buckets[6])/n)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    HP = [200, 200, 200, 200, 200]
    CANDIDATES = [
        ("baseline_no_escalation", {}),
        ("mild_escalation", {2: 1.1, 3: 1.25, 4: 1.45, 5: 1.7, 6: 2.0}),
        ("strong_escalation", {2: 1.2, 3: 1.5, 4: 1.9, 5: 2.5, 6: 3.5}),
        ("very_strong_escalation", {2: 1.3, 3: 1.7, 4: 2.3, 5: 3.5, 6: 5.5}),
    ]
    for i, (tag, mult) in enumerate(CANDIDATES):
        measure(n, 988000 + i, tag, HP, mult)

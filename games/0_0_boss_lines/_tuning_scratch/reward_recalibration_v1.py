import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Reward-side recalibration for the new (monotonic, stage6~1-2%) boss
# difficulty curve. Two changes on top of the validated boss_stage_table
# HP-multiplier curve:
#
# 1. Fix stage_clear_pruned_tiers' documented no-op for Normal tier - it
#    references the SHARED table's original-scale keys (1,2,3,5,...), which
#    never match Normal's own rescaled keys (2.57,3.85,...). Replaces it
#    with a Normal-tier-specific schedule pruning the regular (non-exclusive
#    -chest) pool's 11 tiers progressively, 2/2/3/2/2 per stage (same COUNTS
#    as the old shared-table schedule, just correct keys) - so later stages'
#    kills draw from a pool with a rising floor.
# 2. Multiply ONLY the stage6-exclusive tiers (top_tiers + stage6_last_tiers)
#    by a separate STAGE6_BOOST factor, independent of the regular-pool K,
#    since stage6 is now ~1.7% reach (was ~22%) and needs a much bigger
#    single prize to preserve its contribution to the overall mean.
#
# K (regular pool scale) and STAGE6_BOOST are swept together against the
# NEW boss curve to re-target mean~80.13x, ratio~40-50%.

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


def build_scaled_boss_table(base_table, hp_mult_by_stage):
    scaled = {}
    for stage, bosses in base_table.items():
        mult = hp_mult_by_stage.get(stage, 1.0)
        scaled[stage] = {b: (dam, hp * mult) for b, (dam, hp) in bosses.items()}
    return scaled


HP_MULT = {1: 4.0, 2: 3.0, 3: 3.2, 4: 4.0, 5: 6.0, 6: 9.0}
HP_POOL = [200, 200, 200, 200, 200]


def build_config(K, stage6_boost):
    config = game_config_mod.GameConfig()
    config.bonus_player_hp_choices["normal"] = HP_POOL
    config.boss_stage_table = build_scaled_boss_table(config.boss_stage_table, HP_MULT)

    exclusive = set(config.reward_drop_stage6_last_tiers_normal_bonus)
    regular_keys = sorted(k for k in config.reward_drop_weights_normal_bonus if k not in exclusive)

    new_weights = {}
    for k, w in config.reward_drop_weights_normal_bonus.items():
        if k in exclusive:
            new_weights[round(k * stage6_boost, 4)] = w
        else:
            new_weights[round(k * K, 4)] = w
    config.reward_drop_weights_normal_bonus = new_weights
    config.reward_drop_top_tiers_normal_bonus = {
        round(k * stage6_boost, 4) for k in config.reward_drop_top_tiers_normal_bonus
    }
    config.reward_drop_stage6_last_tiers_normal_bonus = {
        round(k * stage6_boost, 4) for k in config.reward_drop_stage6_last_tiers_normal_bonus
    }

    # Normal-tier-aware progressive pruning (fixes the documented no-op) -
    # same 2/2/3/2/2 counts as the old shared-table schedule, applied to
    # Normal's own regular-pool tiers (rescaled by K), lowest-value-first.
    scaled_regular = sorted(round(k * K, 4) for k in regular_keys)
    schedule_counts = {1: 2, 2: 2, 3: 3, 4: 2, 5: 2, 6: 0}
    pruned_tiers = {}
    idx = 0
    for stage in range(1, 7):
        cnt = schedule_counts[stage]
        pruned_tiers[stage] = scaled_regular[idx:idx + cnt]
        idx += cnt
    config.stage_clear_pruned_tiers = pruned_tiers

    return config


def measure(n, seed_offset, tag, K, stage6_boost, general_chance=0.0):
    config = build_config(K, stage6_boost)
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    buckets = {s: [] for s in range(1, 7)}
    totals = []
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

    print(f"\n=== {tag} (n={n}) K={K} stage6_boost={stage6_boost} gd={general_chance:.2f} ===")
    print(f"mean={mean:.2f}x median={median:.2f}x ratio={ratio:.1f}% zero={zero:.2f}%")
    print("bucket%: " + ", ".join(f"s{s}={100*len(buckets[s])/n:.2f}" for s in range(1, 7)))
    s6 = buckets[6]
    if s6:
        print(f"  s6-subset: mean={sum(s6)/len(s6):.2f}x median={statistics.median(s6):.2f}x")
    return dict(tag=tag, mean=mean, median=median, ratio=ratio, zero=zero,
                s6_pct=100*len(buckets[6])/n)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    # NOTE: config.reward_drop_weights_normal_bonus loaded from GameConfig()
    # is ALREADY the K=4.28-rescaled production table from earlier this
    # session - K/stage6_boost here are ADDITIONAL multipliers on top of
    # that, not absolute scale from tier-value-1. Start near 1.0 for K.
    measure(n, 984000, "K1.0_boost1_pruningfix_only", 1.0, 1.0)
    measure(n, 984001, "K1.0_boost8", 1.0, 8.0)
    measure(n, 984002, "K1.0_boost13", 1.0, 13.0)
    measure(n, 984003, "K1.3_boost13", 1.3, 13.0)

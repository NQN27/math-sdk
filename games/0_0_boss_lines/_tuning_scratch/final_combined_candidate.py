import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# FULL combined candidate: new boss_stage_table difficulty curve (monotonic
# bucket%, stage6~1-2%) + reward recalibration (pruning fix + stage6 boost)
# + validated chain-block (threshold=2/step=0.30/pending-retry) + a small
# flat general_deadspin_chance as a minor supporting lever only (NOT the
# primary funnel-narrowing tool - that's now the boss curve).
#
# All pieces individually validated in isolation this session:
#  - boss_table_escalation_sweep.py: difficulty curve
#  - reward_recalibration_v1.py: pruning fix + K + stage6_boost
#  - chain_block_pending_mechanism.py: chain-block w/ deferred retry
#  - general_deadspin_sweep.py: flat gd (used sparingly here)
# This script layers all four onto one GameConfig/GameState for a single,
# fully-combined measurement - the real end-to-end candidate.

_orig_create_board = gamestate_mod.GameState.create_board_reelstrips
_orig_evaluate = gamestate_mod.GameState.evaluate_and_explode
_orig_tumble = gamestate_mod.GameState.tumble_board
_orig_clear_stage = gamestate_mod.GameState.clear_stage
_orig_run_one_spin = gamestate_mod.GameState.run_one_bonus_spin

_state = {
    "pass_count": 0, "chain_block_pending": False,
    "chain_break_threshold": 2, "chain_break_step": 0.30,
    "general_chance": 0.0, "max_stage": 1, "spins": 0,
}
_all_pass_counts = []


def try_block_columns(self):
    cols = [1, 2, 3]
    random.shuffle(cols)
    for col in cols:
        before = getattr(self, "_deadspin_route_fallback_count", 0)
        self._route_column_force_deadspin(col)
        after = getattr(self, "_deadspin_route_fallback_count", 0)
        if after == before:
            return True
    return False


def patched_create_board(self):
    if _state["pass_count"] > 0:
        _all_pass_counts.append(_state["pass_count"])
    _state["pass_count"] = 0
    _state["chain_block_pending"] = False

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


def patched_evaluate(self, both_ways=False):
    result = _orig_evaluate(self, both_ways=both_ways)
    if self.win_data.get("totalWin", 0) > 0:
        _state["pass_count"] += 1
    return result


def patched_tumble(self):
    result = _orig_tumble(self)
    if not getattr(self, "in_bonus", False):
        return result
    was_pending = _state["chain_block_pending"]
    threshold = _state["chain_break_threshold"]
    step = _state["chain_break_step"]
    extra = _state["pass_count"] - threshold
    newly_triggered = extra >= 0 and step > 0 and random.random() < min(1.0, step * (extra + 1))
    if not was_pending and not newly_triggered:
        return result
    if try_block_columns(self):
        _state["chain_block_pending"] = False
        self.get_special_symbols_on_board()
    else:
        _state["chain_block_pending"] = True
    return result


def hooked_clear_stage(self, stage):
    result = _orig_clear_stage(self, stage)
    _state["max_stage"] = max(_state["max_stage"], getattr(self, "stage", stage))
    return result


def hooked_run_one_spin(self, *a, **k):
    _state["spins"] += 1
    return _orig_run_one_spin(self, *a, **k)


gamestate_mod.GameState.create_board_reelstrips = patched_create_board
gamestate_mod.GameState.evaluate_and_explode = patched_evaluate
gamestate_mod.GameState.tumble_board = patched_tumble
gamestate_mod.GameState.clear_stage = hooked_clear_stage
gamestate_mod.GameState.run_one_bonus_spin = hooked_run_one_spin


def build_scaled_boss_table(base_table, hp_mult_by_stage):
    scaled = {}
    for stage, bosses in base_table.items():
        mult = hp_mult_by_stage.get(stage, 1.0)
        scaled[stage] = {b: (dam, hp * mult) for b, (dam, hp) in bosses.items()}
    return scaled


HP_MULT = {1: 3.7, 2: 2.5, 3: 2.7, 4: 3.3, 5: 4.75, 6: 7.0}
HP_POOL = [200, 200, 200, 200, 200]



# 2026-08-19 bugfix: raw k*stage6_boost pushes the top 2 of the chest's 9
# tiers (769.12, 2197.78) past config.wincap=20000 (34610.4x, 98900.1x) -
# award_win's real headroom clamp made this harmless mathematically (the
# 83x mean already measured this correctly), but the table itself was
# nonsensical: those 2 tiers could never pay their nominal face value,
# making them silently indistinguishable from "hit the cap". Explicit
# override, keyed by the PRE-boost production value, caps just these two -
# the other 7 chest tiers are untouched.
#
# 2026-08-20: kept 19000 (not a literal 20000) deliberately - real sessions
# reach the chest with only ~405-615x accumulated (empirically measured via
# maxwin_weight_solver.py, n=20000), so headroom there is ~19385-19595x.
# A literal-20000 tier would ALWAYS get clamped down to that odd headroom
# value (e.g. 19412.35x) instead of ever paying a clean number. Fixing the
# face value at 19000 (safely below the observed headroom floor) means it
# reliably pays its exact face value with no clamp variance.
CHEST_TIER_CAP_OVERRIDE = {769.12: 17000.0, 2197.78: 19000.0}

# 2026-08-21 CORRECTION: this used to also carry a designer-requested
# Max Win frequency boost on the 2197.78/19000 tier's WEIGHT
# (CHEST_TIER_WEIGHT_OVERRIDE = {2197.78: 0.0825}). Reverted - discovered
# game_executables.py's roll_reward_drop already has a SEPARATE, dedicated,
# real production mechanism for exactly this purpose:
# config.stage6_chest_natural_maxwin_weight, which adds a literal
# maxwin_tier=int(config.wincap)=20000 into the stage6-chest pool at
# roll-time (not stored in reward_drop_weights_normal_bonus itself) -
# default 0.00000796, docstring literally says "pending final
# calibration". That's the correct/intended lever, not this ordinary
# tier's weight - see STAGE6_NATURAL_MAXWIN_WEIGHT below. This tier
# (19000) is left at its real production weight (0.02), value-capped only
# to stop it being unpayable.
CHEST_TIER_WEIGHT_OVERRIDE = {}

# Designer-requested Max Win frequency: 1-in-25000 sessions (closest value
# to the preferred 1-in-20000 that still keeps this mechanism's RTP share
# under 1% of the ~83x mean). Solved analytically against the REAL
# production mechanism described above: w = pool_weight_base *
# p_select_needed / (1 - p_select_needed), where p_select_needed =
# target_rate / P(chest reached), pool_weight_base = 36 (the 9 unmodified
# ordinary chest tiers' weight sum). P(chest reached) was calibrated via a
# 60000-session/3-seed run to a stable 1.748% (range 1.65-1.87%) - an
# earlier single-seed n=20000 draw of 1.095% was a noisy outlier. Paid
# amount is headroom-clamped same as any other award (~19385-19595x, never
# a clean 20000 - see CHEST_TIER_CAP_OVERRIDE note above for why).
STAGE6_NATURAL_MAXWIN_WEIGHT = 0.0825


def _boosted_or_capped(k, stage6_boost):
    return CHEST_TIER_CAP_OVERRIDE.get(k, round(k * stage6_boost, 4))


def build_config(K, stage6_boost):
    config = game_config_mod.GameConfig()
    config.bonus_player_hp_choices["normal"] = HP_POOL
    config.boss_stage_table = build_scaled_boss_table(config.boss_stage_table, HP_MULT)
    config.stage6_chest_natural_maxwin_weight = STAGE6_NATURAL_MAXWIN_WEIGHT

    exclusive = set(config.reward_drop_stage6_last_tiers_normal_bonus)
    regular_keys = sorted(k for k in config.reward_drop_weights_normal_bonus if k not in exclusive)

    new_weights = {}
    for k, w in config.reward_drop_weights_normal_bonus.items():
        if k in exclusive:
            new_weights[_boosted_or_capped(k, stage6_boost)] = CHEST_TIER_WEIGHT_OVERRIDE.get(k, w)
        else:
            new_weights[round(k * K, 4)] = w
    config.reward_drop_weights_normal_bonus = new_weights
    config.reward_drop_top_tiers_normal_bonus = {
        _boosted_or_capped(k, stage6_boost) for k in config.reward_drop_top_tiers_normal_bonus
    }
    config.reward_drop_stage6_last_tiers_normal_bonus = {
        _boosted_or_capped(k, stage6_boost) for k in config.reward_drop_stage6_last_tiers_normal_bonus
    }

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


def measure(n, seed_offset, tag, K, stage6_boost, general_chance, chain_threshold, chain_step):
    config = build_config(K, stage6_boost)
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    _all_pass_counts.clear()
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
            _state["spins"] = 0
            _state["pass_count"] = 0
            _state["chain_block_pending"] = False
            _state["general_chance"] = general_chance
            _state["chain_break_threshold"] = chain_threshold
            _state["chain_break_step"] = chain_step
            gs.run_bonus_session("normal")
            if _state["pass_count"] > 0:
                _all_pass_counts.append(_state["pass_count"])
                _state["pass_count"] = 0
            buckets[_state["max_stage"]].append(gs.win_manager.running_bet_win)
            totals.append(gs.win_manager.running_bet_win)
            spins_list.append(_state["spins"])

    mean = sum(totals) / n
    median = statistics.median(totals)
    ratio = median / mean * 100 if mean > 0 else 0
    zero = 100 * sum(1 for t in totals if t == 0) / n
    mean_spins = sum(spins_list) / n
    spins_le2 = 100 * sum(1 for s in spins_list if s <= 2) / n
    counts = _all_pass_counts
    mean_passes = sum(counts) / len(counts) if counts else 0
    long_chain = 100 * sum(1 for c in counts if c >= 4) / len(counts) if counts else 0
    s6_pct = 100 * len(buckets[6]) / n

    # Standing Max Win check (designer wants this reported on every test
    # run, not just when asked). "Max win tier" = game_executables.py's
    # REAL dedicated maxwin_tier mechanism (int(config.wincap)=20000,
    # inserted into the stage6-chest pool at roll-time via
    # config.stage6_chest_natural_maxwin_weight - not stored in
    # reward_drop_weights_normal_bonus itself). Selection is a pure weight
    # ratio (P(selected|chest) = w/(chest_total_w+w)), independent of the
    # session's accumulated total, so this is exact - no extra simulation
    # needed beyond the chest-reach rate already measured above.
    chest = config.reward_drop_stage6_last_tiers_normal_bonus
    chest_weights = {k: w for k, w in config.reward_drop_weights_normal_bonus.items() if k in chest}
    chest_total_w = sum(chest_weights.values())
    maxwin_value = int(config.wincap)
    maxwin_w = config.stage6_chest_natural_maxwin_weight
    p_select_given_chest = maxwin_w / (chest_total_w + maxwin_w) if (chest_total_w + maxwin_w) else 0
    maxwin_rate = (s6_pct / 100) * p_select_given_chest
    maxwin_1_in = (1 / maxwin_rate) if maxwin_rate > 0 else float("inf")

    print(f"\n=== {tag} (n={n}) K={K} boost={stage6_boost} gd={general_chance:.2f} "
          f"cb_th={chain_threshold} cb_step={chain_step:.2f} ===")
    print(f"mean={mean:.2f}x median={median:.2f}x ratio={ratio:.1f}% zero={zero:.2f}%")
    print(f"spins: mean={mean_spins:.2f} spins<=2={spins_le2:.2f}%")
    print(f"chain: mean_passes={mean_passes:.2f} >=4pass={long_chain:.2f}%")
    print("bucket%: " + ", ".join(f"s{s}={100*len(buckets[s])/n:.2f}" for s in range(1, 7)))
    print(f"max win tier ({maxwin_value:.0f}x, weight={maxwin_w}/{chest_total_w:.4f} of chest pool): "
          f"P(selected|chest reached)={100*p_select_given_chest:.4f}%  "
          f"-> session-level rate = 1-in-{maxwin_1_in:.0f}")
    return dict(tag=tag, mean=mean, median=median, ratio=ratio, zero=zero,
                s6_pct=s6_pct, spins_le2=spins_le2,
                mean_passes=mean_passes, long_chain=long_chain,
                maxwin_value=maxwin_value, maxwin_rate=maxwin_rate, maxwin_1_in=maxwin_1_in)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    # K=0.72/boost=64.0 confirmed at n=5000 (reward_recalibration_v1.py):
    # mean=78.35x median=36.94x ratio=47.2% s6=1.52% - now layering in the
    # validated chain-block (threshold=2/step=0.30/pending) to see the
    # combined effect (chain-block alone cut mean ~25% in isolation testing
    # against the OLD boss curve - may need a K/boost nudge to compensate).
    measure(n, 978000, "combined_full", 1.0, 45.0, 0.0, 2, 0.30)

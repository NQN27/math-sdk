import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Chain Block with PENDING/deferred retry (2026-08-19, per designer request).
# Same purpose as Controlled Deadspin Routing (game_executables.py's
# _route_column_force_deadspin), reused as-is - column content is genuinely
# re-picked from a pre-filtered valid-position list BEFORE the next
# evaluate_and_explode decides that pass's outcome, so it's RGS-safe the
# same way the shipped mechanism is. What's NEW here is the deferred-retry
# behavior the designer asked for:
#
#   - Once a pass's chain-length trigger condition fires ("we want to block
#     the chain now"), try columns 1,2,3 in turn. _route_column_force_
#     deadspin can genuinely fail for a column (returns with no re-route)
#     when EVERY candidate position at some row would still touch a Wild/
#     Power symbol in the neighboring column - there is nothing safe to
#     draw. The shipped mechanism just silently gives up in that case
#     (counted in self._deadspin_route_fallback_count).
#   - Instead of giving up, this sets chain_block_pending=True and RETRIES
#     on every subsequent pass (checking all 3 columns again, since the
#     board has changed each tumble) until at least one column succeeds -
#     "co gang de khien cho chain gan nhat co kha nang bi block sau do kich
#     hoat block" (try to make the nearest blockable chain get blocked).
#     Consumed (cleared) the instant any column succeeds.
#
# Detects per-column success/failure by snapshotting self._deadspin_route_
# fallback_count before/after each call (the real method's own visibility
# counter) - no changes to the real method itself.

_orig_create_board = gamestate_mod.GameState.create_board_reelstrips
_orig_evaluate = gamestate_mod.GameState.evaluate_and_explode
_orig_tumble = gamestate_mod.GameState.tumble_board

_state = {
    "pass_count": 0,
    "chain_block_pending": False,
    "chain_break_threshold": 2,
    "chain_break_step": 0.0,
    "general_chance": 0.0,
    "attempts": 0,
    "successes": 0,
    "deferred_saves": 0,   # times a pending block eventually succeeded on a LATER pass
    "never_delivered": 0,  # pending block still unresolved when the spin/session ended
}
_all_pass_counts = []


def try_block_columns(self):
    """Try columns 1,2,3 in a shuffled order; return True on first success."""
    cols = [1, 2, 3]
    random.shuffle(cols)
    for col in cols:
        before = getattr(self, "_deadspin_route_fallback_count", 0)
        self._route_column_force_deadspin(col)
        after = getattr(self, "_deadspin_route_fallback_count", 0)
        if after == before:
            return True  # succeeded - board content actually changed
    return False


def patched_create_board(self):
    if _state["pass_count"] > 0:
        _all_pass_counts.append(_state["pass_count"])
    if _state["chain_block_pending"]:
        _state["never_delivered"] += 1
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

    was_already_pending = _state["chain_block_pending"]
    threshold = _state["chain_break_threshold"]
    step = _state["chain_break_step"]
    extra_passes = _state["pass_count"] - threshold
    newly_triggered = extra_passes >= 0 and step > 0 and random.random() < min(1.0, step * (extra_passes + 1))

    if not was_already_pending and not newly_triggered:
        return result

    _state["attempts"] += 1
    success = try_block_columns(self)
    if success:
        _state["successes"] += 1
        if was_already_pending:
            _state["deferred_saves"] += 1
        _state["chain_block_pending"] = False
        self.get_special_symbols_on_board()
    else:
        _state["chain_block_pending"] = True  # defer to next pass

    return result


gamestate_mod.GameState.create_board_reelstrips = patched_create_board
gamestate_mod.GameState.evaluate_and_explode = patched_evaluate
gamestate_mod.GameState.tumble_board = patched_tumble


def measure(n, seed_offset, tag, hp_choices, general_chance, chain_break_threshold, chain_break_step):
    config = game_config_mod.GameConfig()
    config.bonus_player_hp_choices["normal"] = hp_choices
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    _all_pass_counts.clear()
    _state["attempts"] = 0
    _state["successes"] = 0
    _state["deferred_saves"] = 0
    _state["never_delivered"] = 0
    totals = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            _state["pass_count"] = 0
            _state["chain_block_pending"] = False
            _state["general_chance"] = general_chance
            _state["chain_break_threshold"] = chain_break_threshold
            _state["chain_break_step"] = chain_break_step
            gs.run_bonus_session("normal")
            if _state["pass_count"] > 0:
                _all_pass_counts.append(_state["pass_count"])
                _state["pass_count"] = 0
            totals.append(gs.win_manager.running_bet_win)

    counts = _all_pass_counts
    total_spins = len(counts)
    mean_passes = sum(counts) / total_spins
    dist = {}
    for c in counts:
        dist[c] = dist.get(c, 0) + 1
    long_chain = sum(v for k, v in dist.items() if k >= 4)
    mean_p = sum(totals) / n
    median_p = statistics.median(totals)
    ratio = median_p / mean_p * 100 if mean_p > 0 else 0

    print(f"\n=== {tag} (n={n}) hp={hp_choices} gd={general_chance:.2f} "
          f"cb_threshold={chain_break_threshold} cb_step={chain_break_step:.2f} [PENDING-RETRY] ===")
    print(f"chain: mean_passes={mean_passes:.2f} median={statistics.median(counts)} max={max(counts)} "
          f">=4pass={100*long_chain/total_spins:.2f}%")
    print(f"payout: mean={mean_p:.2f}x median={median_p:.2f}x ratio={ratio:.1f}%")
    block_success_rate = 100 * _state["successes"] / _state["attempts"] if _state["attempts"] else 0
    print(f"block attempts={_state['attempts']} immediate_or_eventual_success_rate={block_success_rate:.1f}% "
          f"deferred_saves={_state['deferred_saves']} never_delivered(session/spin ended still pending)={_state['never_delivered']}")
    return dict(tag=tag, mean_passes=mean_passes, long_chain_pct=100*long_chain/total_spins, mean_p=mean_p, ratio=ratio)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    CANDIDATES = [
        ("cb_t2_s015_pending", [50, 50, 50, 100, 100], 0.0, 2, 0.15),
        ("cb_t2_s020_pending", [50, 50, 50, 100, 100], 0.0, 2, 0.20),
        ("cb_t2_s025_pending", [50, 50, 50, 100, 100], 0.0, 2, 0.25),
    ]
    for i, (tag, hp, gd, th, step) in enumerate(CANDIDATES):
        measure(n, 989000 + i, tag, hp, gd, th, step)

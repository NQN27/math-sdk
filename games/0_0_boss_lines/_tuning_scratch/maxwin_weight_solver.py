import sys, random, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import final_combined_candidate as fc
from src.wins.win_manager import WinManager

# Solve for stage6_chest_natural_maxwin_weight to hit a target
# session-level Max Win frequency, using the REAL running_bet_win
# accumulated by each session right before its stage-6 chest opens (not
# the naive "assume it always pays the full 20000x" assumption - a chest
# that opens late in a long, already-lucrative session has much less
# headroom left, so a real weight-sweep needs the true pre-chest total
# distribution to get an accurate hit-rate/EV estimate).
#
# Key fact: which tier gets SELECTED depends only on the weight ratio
# w/(36+w) - totally independent of the session's accumulated total.
# Only the PAID AMOUNT (via award_win's headroom clamp) depends on the
# pre-chest total. So: run the real sim ONCE to collect the pre-chest
# total for every session that reaches the chest, then solve for w
# analytically against that real empirical distribution - no need to
# re-run the (slow) full simulation per candidate w.

_orig_on_boss_defeated = fc.gamestate_mod.GameState.on_boss_defeated
_pre_chest_totals = []


def hooked_on_boss_defeated(self, boss_id):
    is_stage6_chest = (
        getattr(self, "in_bonus", False)
        and self.bonus_tier == "normal"
        and self.stage == self.config.max_stage
        and len(self.stage_defeat_order) == 2  # about to become the 3rd/last kill
    )
    if is_stage6_chest:
        _pre_chest_totals.append(self.win_manager.running_bet_win)
    return _orig_on_boss_defeated(self, boss_id)


fc.gamestate_mod.GameState.on_boss_defeated = hooked_on_boss_defeated


def collect(n, seed_offset):
    config = fc.build_config(1.0, 45.0)
    gs = fc.gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"
    _pre_chest_totals.clear()
    totals = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            fc._state["max_stage"] = 1
            fc._state["spins"] = 0
            fc._state["pass_count"] = 0
            fc._state["chain_block_pending"] = False
            fc._state["general_chance"] = 0.0
            fc._state["chain_break_threshold"] = 2
            fc._state["chain_break_step"] = 0.30
            gs.run_bonus_session("normal")
            totals.append(gs.win_manager.running_bet_win)
    return list(_pre_chest_totals), totals


def analyze_for_weight(pre_chest_totals, n_total, wincap, chest_pool_weight, w):
    """P(maxwin_tier SELECTED | chest reached) is exact and independent of
    the session's accumulated total (pure weight ratio). What that
    selection actually PAYS depends on award_win's headroom clamp against
    each session's real pre-chest total - reported separately so "1-in-N
    hits the mechanic" and "1-in-N actually gets ~20000x" don't get
    conflated."""
    import math
    p_select = w / (chest_pool_weight + w)
    paid_amounts = []
    for pre in pre_chest_totals:
        headroom = wincap - pre - 0.05
        paid = 0.0 if headroom <= 0 else math.floor(min(20000.0, headroom) * 10) / 10.0
        paid_amounts.append(paid)
    ev = p_select * sum(paid_amounts) / n_total
    select_rate = p_select * len(pre_chest_totals) / n_total
    near_full_count = sum(1 for p in paid_amounts if p >= 19000)
    near_full_rate = p_select * near_full_count / n_total
    paid_amounts.sort()
    return dict(
        p_select=p_select, select_rate=select_rate, ev=ev,
        near_full_rate=near_full_rate,
        paid_median=paid_amounts[len(paid_amounts) // 2] if paid_amounts else 0,
        paid_min=paid_amounts[0] if paid_amounts else 0,
    )


def solve_for_weight(pre_chest_totals, n_total, wincap, chest_pool_weight, target_rate):
    """Solve w so P(maxwin_tier SELECTED per session) == target_rate. This
    is an exact closed form (selection is a pure weight ratio, independent
    of accumulated totals) - no search needed."""
    p_chest = len(pre_chest_totals) / n_total
    if target_rate >= p_chest:
        raise ValueError(f"target_rate {target_rate} unreachable - chest itself is only reached {p_chest:.5f} of sessions")
    p_select_needed = target_rate / p_chest
    w = chest_pool_weight * p_select_needed / (1 - p_select_needed)
    return w


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    target_rate = float(sys.argv[2]) if len(sys.argv) > 2 else 1 / 25000
    pre_chest, totals = collect(n, 61001)
    print(f"n={n}, sessions reaching stage6 chest: {len(pre_chest)} ({100*len(pre_chest)/n:.3f}%)")
    if pre_chest:
        pre_chest_sorted = sorted(pre_chest)
        print(f"pre-chest total distribution: min={pre_chest_sorted[0]:.1f} "
              f"p25={pre_chest_sorted[len(pre_chest_sorted)//4]:.1f} "
              f"median={pre_chest_sorted[len(pre_chest_sorted)//2]:.1f} "
              f"p75={pre_chest_sorted[3*len(pre_chest_sorted)//4]:.1f} "
              f"max={pre_chest_sorted[-1]:.1f}")

    w = solve_for_weight(pre_chest, n, 20000.0, 36.0, target_rate)
    result = analyze_for_weight(pre_chest, n, 20000.0, 36.0, w)
    print(f"\nsolved weight for target SELECTION rate 1/{1/target_rate:.0f}: w={w:.6f}")
    print(f"  -> P(maxwin_tier selected | chest reached) = {100*result['p_select']:.4f}%")
    print(f"  -> P(maxwin_tier selected per session, i.e. 'the mechanic fires') = 1/{1/result['select_rate']:.0f}")
    print(f"  -> of those selections, paid amount: min={result['paid_min']:.1f}x median={result['paid_median']:.1f}x")
    print(f"  -> P(session actually gets a near-full ~20000x payout, >=19000x paid) = "
          f"1/{1/result['near_full_rate']:.0f}" if result['near_full_rate'] > 0 else "  -> near-full payout rate: 0 in this sample")
    print(f"  -> EV contribution to mean: {result['ev']:.4f}x  (as % of mean~80.13x: {100*result['ev']/80.13:.3f}%)")

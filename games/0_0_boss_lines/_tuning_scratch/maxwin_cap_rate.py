import sys, random, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import final_combined_candidate as fc
from src.wins.win_manager import WinManager

# What fraction of sessions actually hit (or land very close to) the
# 20000x wincap ceiling via NORMAL play (not the dedicated "wincap"
# criteria book)? award_win's headroom clamp means a session can only ever
# get there by accumulating close to 20000x total across line-pay + every
# boss-kill reward-drop in one session - tracked here via
# self.power_clamp_events (incremented every time ANY award actually got
# clamped) and by thresholding the final running_bet_win directly.

CAP_THRESHOLD = 19999.0  # "effectively hit the cap" - true max achievable is 19999.9-19999.95


def measure_cap_rate(n, seed_offset):
    config = fc.build_config(1.0, 45.0)
    gs = fc.gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    hit_cap = 0
    any_clamp_event = 0
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
            gs.power_clamp_events = 0
            gs.run_bonus_session("normal")
            total = gs.win_manager.running_bet_win
            totals.append(total)
            if total >= CAP_THRESHOLD:
                hit_cap += 1
            if getattr(gs, "power_clamp_events", 0) > 0:
                any_clamp_event += 1

    totals.sort()
    print(f"\n=== n={n} seed_offset={seed_offset} ===")
    print(f"sessions with total >= {CAP_THRESHOLD}x (effectively hit the wincap ceiling): "
          f"{hit_cap}/{n} = {100*hit_cap/n:.4f}%")
    print(f"sessions where AT LEAST ONE award got clamped at all (any_clamp_event>0): "
          f"{any_clamp_event}/{n} = {100*any_clamp_event/n:.4f}%")
    print(f"top 5 totals this run: {totals[-5:]}")
    return hit_cap, any_clamp_event, n


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    a = measure_cap_rate(n, 44201)
    b = measure_cap_rate(n, 44202)
    total_hit = a[0] + b[0]
    total_n = a[2] + b[2]
    print(f"\ncombined: {total_hit}/{total_n} = {100*total_hit/total_n:.4f}% hit the cap threshold")

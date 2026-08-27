import sys, random, statistics
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Verify the Bonus "grace spin" deadspin routing (1) doesn't crash across a
# full session, (2) actually raises the dead-rate specifically of grace
# spins (not all spins), and (3) measure the net effect on mean spins/
# payout so the designer can judge the chosen default.

_orig_create_board = gamestate_mod.GameState.create_board_reelstrips
_orig_evaluate = gamestate_mod.GameState.evaluate_and_explode

pending_grace = {"flag": None}
grace_dead_counts = {True: [0, 0], False: [0, 0]}  # was_grace -> [dead_count, total_count]


def spy_create_board(self):
    pending_grace["flag"] = bool(getattr(self, "in_bonus", False) and getattr(self, "grace_deadspin_pending", False))
    return _orig_create_board(self)


def spy_evaluate(self, both_ways=False):
    result = _orig_evaluate(self, both_ways=both_ways)
    # Only tag the FIRST evaluate_and_explode of a spin (the initial reveal,
    # right after create_board_reelstrips) - later passes within the same
    # spin are tumble continuations, not a fresh "was this spin's opening
    # reveal dead" measurement.
    if getattr(self, "in_bonus", False) and pending_grace["flag"] is not None:
        was_grace = pending_grace["flag"]
        pending_grace["flag"] = None
        is_dead = self.win_data.get("totalWin", 0) <= 0
        grace_dead_counts[was_grace][1] += 1
        if is_dead:
            grace_dead_counts[was_grace][0] += 1
    return result


gamestate_mod.GameState.create_board_reelstrips = spy_create_board
gamestate_mod.GameState.evaluate_and_explode = spy_evaluate


def measure(n, seed_offset, tag, bonus_grace_chance):
    config = game_config_mod.GameConfig()
    config.bonus_grace_deadspin_chance = bonus_grace_chance
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    spins, totals = [], []
    grace_dead_counts[True][:] = [0, 0]
    grace_dead_counts[False][:] = [0, 0]

    for i in range(n):
        gs.sim = i
        gs.criteria = "freegame"
        random.seed(seed_offset * 1000003 + i + 1)
        gs.reset_book()
        gs.run_bonus_session("normal")
        spins.append(gs.bonus_spin_count)
        totals.append(gs.win_manager.running_bet_win)

    mean_spins = sum(spins) / n
    median_spins = statistics.median(spins)
    mean_payout = sum(totals) / n
    median_payout = statistics.median(totals)
    gd, gt = grace_dead_counts[True]
    ngd, ngt = grace_dead_counts[False]
    print(f"{tag}:")
    print(f"  mean_spins={mean_spins:.2f} median_spins={median_spins} "
          f"mean_payout={mean_payout:.2f}x median_payout={median_payout:.2f}x")
    print(f"  grace-spin dead-rate: {100*gd/max(1,gt):.2f}% (n={gt})  |  "
          f"non-grace-spin dead-rate: {100*ngd/max(1,ngt):.2f}% (n={ngt})")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    measure(n, 444000, "grace_chance=0.0 (OFF, current baseline)", 0.0)
    measure(n, 444001, "grace_chance=0.65 (proposed default)", 0.65)
    measure(n, 444002, "grace_chance=1.0 (max, for reference)", 1.0)

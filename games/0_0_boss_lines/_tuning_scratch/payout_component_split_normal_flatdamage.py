import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Line-pay vs boss-kill reward-drop split for Normal Bonus, both under the
# production cascade/random-damage system and the flat-damage experiment -
# same tagging technique as payout_component_split_tier.py, extended with a
# use_flat_damage toggle so both systems can be measured with one script.

_orig_award_win = gamestate_mod.GameState.award_win
_tag = {"in_reward_drop": False}
_totals = {"line": 0.0, "reward": 0.0}


def tagged_roll_reward_drop(self, is_last_of_stage, stage):
    _tag["in_reward_drop"] = True
    return _orig_roll_reward_drop(self, is_last_of_stage, stage)


_orig_roll_reward_drop = gamestate_mod.GameState.roll_reward_drop
gamestate_mod.GameState.roll_reward_drop = tagged_roll_reward_drop


def tagged_award_win_v2(self, amount):
    result = _orig_award_win(self, amount)
    if _tag["in_reward_drop"]:
        _totals["reward"] += amount
        _tag["in_reward_drop"] = False
    else:
        _totals["line"] += amount
    return result


gamestate_mod.GameState.award_win = tagged_award_win_v2


def measure(n, seed_offset, tag, use_flat=False):
    config = game_config_mod.GameConfig()
    if use_flat:
        config.use_flat_damage["normal"] = True
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    line_totals, reward_totals, session_totals, spin_counts = [], [], [], []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            _totals["line"] = 0.0
            _totals["reward"] = 0.0
            _tag["in_reward_drop"] = False
            gs.run_bonus_session("normal")
            line_totals.append(_totals["line"])
            reward_totals.append(_totals["reward"])
            session_totals.append(gs.win_manager.running_bet_win)
            spin_counts.append(gs.bonus_spin_count)

    mean_line = sum(line_totals) / n
    mean_reward = sum(reward_totals) / n
    mean_total = sum(session_totals) / n
    median_total = statistics.median(session_totals)
    mean_spins = sum(spin_counts) / n
    print(f"\n=== {tag} (n={n}) ===")
    print(f"line-pay mean:    {mean_line:.2f}x  ({100*mean_line/mean_total:.1f}% of total)")
    print(f"reward-drop mean: {mean_reward:.2f}x  ({100*mean_reward/mean_total:.1f}% of total)")
    print(f"session total: mean={mean_total:.2f}x median={median_total:.2f}x "
          f"ratio={100*median_total/mean_total:.1f}%  avg_spins/session={mean_spins:.2f}")
    print(f"line-pay per spin: {mean_line/mean_spins:.3f}x")
    print(f"(line+reward = {mean_line+mean_reward:.2f}x, sanity check vs total {mean_total:.2f}x)")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    which = sys.argv[2] if len(sys.argv) > 2 else "both"
    if which in ("default", "both"):
        measure(n, 995500, "PRODUCTION (cascade, use_flat_damage=False)", use_flat=False)
    if which in ("flat", "both"):
        measure(n, 995500, "FLAT-DAMAGE (use_flat_damage=True, current tuned state)", use_flat=True)

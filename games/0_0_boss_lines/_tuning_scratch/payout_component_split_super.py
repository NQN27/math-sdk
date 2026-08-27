import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Same decomposition as payout_component_split.py (Normal), applied to
# Super - needed before redesigning reward_drop_weights_super_bonus into a
# Normal-style 3-peak (LOW/MID + exclusive CHEST) shape while preserving
# Super's current mean=266.84x/median=178.40x: the reward table can only
# ever move the reward-drop component, so we need to know how much of the
# current total is the FIXED line-pay floor before sizing the redesign.

_orig_award_win = gamestate_mod.GameState.award_win
_tag = {"in_reward_drop": False}
_totals = {"line": 0.0, "reward": 0.0}


def tagged_award_win(self, amount):
    result = _orig_award_win(self, amount)
    if _tag["in_reward_drop"]:
        _totals["reward"] += amount
        _tag["in_reward_drop"] = False
    else:
        _totals["line"] += amount
    return result


gamestate_mod.GameState.award_win = tagged_award_win

_orig_roll_reward_drop = gamestate_mod.GameState.roll_reward_drop


def tagged_roll_reward_drop(self, is_last_of_stage, stage):
    _tag["in_reward_drop"] = True
    return _orig_roll_reward_drop(self, is_last_of_stage, stage)


gamestate_mod.GameState.roll_reward_drop = tagged_roll_reward_drop


def measure(n, seed_offset, tag):
    config = game_config_mod.GameConfig()
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    line_means, reward_means, session_totals = [], [], []
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
            gs.run_bonus_session("super")
            line_means.append(_totals["line"])
            reward_means.append(_totals["reward"])
            session_totals.append(gs.win_manager.running_bet_win)

    mean_line = sum(line_means) / n
    mean_reward = sum(reward_means) / n
    mean_total = sum(session_totals) / n
    median_total = statistics.median(session_totals)
    print(f"\n=== {tag} (n={n}) ===")
    print(f"line-pay mean:    {mean_line:.2f}x  ({100*mean_line/mean_total:.1f}% of total)")
    print(f"reward-drop mean: {mean_reward:.2f}x  ({100*mean_reward/mean_total:.1f}% of total)")
    print(f"session total: mean={mean_total:.2f}x median={median_total:.2f}x "
          f"ratio={100*median_total/mean_total:.1f}%")
    print(f"(line+reward = {mean_line+mean_reward:.2f}x, sanity check vs total {mean_total:.2f}x)")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    measure(n, 994100, "super_current_production_split")

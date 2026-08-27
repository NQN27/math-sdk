import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Discriminating check (2026-08-18, per advisor): is Super's ~5.5% ratio (at
# any reward-table K) caused by table SHAPE, or by a bimodal session-length
# split (s1=33.58% die immediately, s6=29.95% sail through, s2-s5 thin)? If
# non-s6 sessions draw near-zero reward-drop, the cause is length/HP-driven
# (same lever as Normal's fix), not a shape problem - a K-rescale or shape
# redesign of the reward table can't fix that.

_orig_award_win = gamestate_mod.GameState.award_win
_orig_roll_reward_drop = gamestate_mod.GameState.roll_reward_drop
_orig_clear_stage = gamestate_mod.GameState.clear_stage
_tag = {"in_reward_drop": False}
_totals = {"line": 0.0, "reward": 0.0}
_state = {"max_stage": 1}


def tagged_roll_reward_drop(self, is_last_of_stage, stage):
    _tag["in_reward_drop"] = True
    return _orig_roll_reward_drop(self, is_last_of_stage, stage)


def tagged_award_win(self, amount):
    result = _orig_award_win(self, amount)
    if _tag["in_reward_drop"]:
        _totals["reward"] += amount
        _tag["in_reward_drop"] = False
    else:
        _totals["line"] += amount
    return result


def hooked_clear_stage(self, stage):
    result = _orig_clear_stage(self, stage)
    _state["max_stage"] = max(_state["max_stage"], getattr(self, "stage", stage))
    return result


gamestate_mod.GameState.roll_reward_drop = tagged_roll_reward_drop
gamestate_mod.GameState.award_win = tagged_award_win
gamestate_mod.GameState.clear_stage = hooked_clear_stage

_orig_init = game_config_mod.GameConfig.__init__


def scaled_init(self, K):
    _orig_init(self)
    if K != 1.0:
        self.reward_drop_weights_super_bonus = {
            round(k * K, 4): w for k, w in self.reward_drop_weights_super_bonus.items()
        }
        self.reward_drop_top_tiers_super_bonus = {round(k * K, 4) for k in self.reward_drop_top_tiers_super_bonus}
        self.reward_drop_stage6_last_tiers_super_bonus = {
            round(k * K, 4) for k in self.reward_drop_stage6_last_tiers_super_bonus
        }


def measure(n, seed_offset, tag, K=1.0):
    config = game_config_mod.GameConfig.__new__(game_config_mod.GameConfig)
    scaled_init(config, K)
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    rows = []
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
            _state["max_stage"] = 1
            gs.run_bonus_session("super")
            rows.append((_totals["line"], _totals["reward"], gs.win_manager.running_bet_win, _state["max_stage"] >= 6))

    s6 = [r for r in rows if r[3]]
    non_s6 = [r for r in rows if not r[3]]

    def summarize(label, subset):
        if not subset:
            print(f"  {label}: (empty)")
            return
        n_ = len(subset)
        mean_line = sum(r[0] for r in subset) / n_
        mean_reward = sum(r[1] for r in subset) / n_
        totals = [r[2] for r in subset]
        mean_total = sum(totals) / n_
        median_total = statistics.median(totals)
        print(f"  {label} (n={n_}, {100*n_/n:.1f}% of sessions): "
              f"line={mean_line:.2f}x reward={mean_reward:.2f}x total_mean={mean_total:.2f}x "
              f"total_median={median_total:.2f}x")

    print(f"\n=== {tag} K={K} (n={n}) ===")
    summarize("stage6-reach", s6)
    summarize("non-stage6", non_s6)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    measure(n, 997500, "super_split_by_s6reach", K=0.121)

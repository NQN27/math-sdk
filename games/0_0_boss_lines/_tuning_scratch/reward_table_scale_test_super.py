import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Super-tier analog of reward_table_scale_test.py (2026-08-18). Super's
# reward_drop_weights_super_bonus is a known PLACEHOLDER - an exact,
# unscaled copy of the base shared reward_drop_weights table (values 1..
# 20000) - never redesigned for Super's own HP pool (300-450) or 240.77x
# mean target. Measured: current mean=1181-1244x (n=8-15k), reward-drop
# component alone = 1141.55x (91.8% of total), line-pay = 102.38x (fixed
# baseline, unaffected by reward-table scaling since it's a separate award_
# win() source entirely). To reach target: reward_mean_target ~=
# 240.77 - 102.38 = 138.4x => K ~= 138.4 / 1141.55 ~= 0.121. This script
# brackets/confirms that K. HP/damage/weights UNTOUCHED - pure value rescale,
# same proof-of-shape-preservation as the Normal-tier K=4.28 fix. NOT applied
# to production - proposal/measurement only, pending designer review.

_orig_init = game_config_mod.GameConfig.__init__


def scaled_init(self, K):
    _orig_init(self)
    self.reward_drop_weights_super_bonus = {
        round(k * K, 4): w for k, w in self.reward_drop_weights_super_bonus.items()
    }
    self.reward_drop_top_tiers_super_bonus = {
        round(k * K, 4) for k in self.reward_drop_top_tiers_super_bonus
    }
    self.reward_drop_stage6_last_tiers_super_bonus = {
        round(k * K, 4) for k in self.reward_drop_stage6_last_tiers_super_bonus
    }


def measure_scaled(n, seed_offset, tag, K):
    config = game_config_mod.GameConfig.__new__(game_config_mod.GameConfig)
    scaled_init(config, K)
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"
    return _run(gs, config, n, seed_offset, tag, K)


def _run(gs, config, n, seed_offset, tag, K):
    spins, totals = [], []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs._diag_spin_count = 0
            gs.run_bonus_session("super")
            totals.append(gs.win_manager.running_bet_win)
    mean = sum(totals) / n
    median = statistics.median(totals)
    ratio = median / mean * 100 if mean > 0 else 0
    zero = 100 * sum(1 for t in totals if t == 0) / n
    sorted_t = sorted(totals)

    def pct(p):
        return sorted_t[min(n - 1, int(p * n))]

    print(f"\n=== {tag} (n={n}) K={K} [Super reward-table scale, HP/dmg UNTOUCHED] ===")
    print(f"mean={mean:.2f}x median={median:.2f}x ratio={ratio:.1f}% zero={zero:.2f}%")
    print(f"percentiles: p75={pct(.75):.1f}x p90={pct(.9):.1f}x p95={pct(.95):.1f}x p99={pct(.99):.1f}x max={sorted_t[-1]:.1f}x")
    return dict(tag=tag, mean=mean, median=median, ratio=ratio)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    for K in (0.10, 0.121, 0.14):
        measure_scaled(n, 996000 + int(K * 1000), f"K={K}", K)

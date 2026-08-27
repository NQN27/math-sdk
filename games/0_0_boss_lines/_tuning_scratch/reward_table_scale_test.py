import sys
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
import pure_production_full_measure as ppfm

# Instead of touching HP pool (which distorts the median/mean ratio away
# from the 40-50% target band - see pure_production_sweep(2).py), scale the
# Normal-bonus reward-drop table's tier VALUES by a constant K, leaving
# weights/HP/damage untouched entirely. Because roll_reward_drop draws once
# per boss-kill from this exact table and sums across a session, multiplying
# every tier value by K multiplies every possible session total by exactly
# K (deterministically, not just in expectation) - so mean AND median scale
# together and the ratio is provably unchanged. top_tiers/stage6_last_tiers
# reference tier VALUES (not indices), so they must be re-keyed by the same
# K or the "reserved for last boss" / "stage-6 chest exclusivity" checks
# silently stop matching anything.

_orig_init = game_config_mod.GameConfig.__init__


def scaled_init(self, K):
    _orig_init(self)
    self.reward_drop_weights_normal_bonus = {
        round(k * K, 4): w for k, w in self.reward_drop_weights_normal_bonus.items()
    }
    self.reward_drop_top_tiers_normal_bonus = {
        round(k * K, 4) for k in self.reward_drop_top_tiers_normal_bonus
    }
    self.reward_drop_stage6_last_tiers_normal_bonus = {
        round(k * K, 4) for k in self.reward_drop_stage6_last_tiers_normal_bonus
    }


def measure_scaled(n, seed_offset, tag, K):
    config = game_config_mod.GameConfig.__new__(game_config_mod.GameConfig)
    scaled_init(config, K)
    gs = gamestate_mod.GameState(config)
    from src.wins.win_manager import WinManager
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"
    return _run(gs, config, n, seed_offset, tag)


def _run(gs, config, n, seed_offset, tag):
    import random, statistics, warnings
    spins, max_stages, end_reasons, totals = [], [], [], []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs._diag_spin_count = 0
            gs._diag_max_stage = 1
            gs.run_bonus_session("normal")
            spins.append(gs._diag_spin_count)
            max_stages.append(gs._diag_max_stage)
            end_reasons.append(getattr(gs, "bonus_end_reason", "?"))
            totals.append(gs.win_manager.running_bet_win)
    mean = sum(totals) / n
    median = statistics.median(totals)
    ratio = median / mean * 100 if mean > 0 else 0
    zero = 100 * sum(1 for t in totals if t == 0) / n
    print(f"\n=== {tag} (n={n}) K={K} [reward-table scale, HP/dmg UNTOUCHED] ===")
    print(f"mean={mean:.2f}x median={median:.2f}x ratio={ratio:.1f}% zero={zero:.2f}%")
    mean_spins = sum(spins) / n
    print(f"spins: mean={mean_spins:.2f} median={statistics.median(spins)}")
    return dict(tag=tag, mean=mean, median=median, ratio=ratio)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    for K in (4.28,):
        measure_scaled(n, 993000 + int(K * 100), f"K={K}", K)

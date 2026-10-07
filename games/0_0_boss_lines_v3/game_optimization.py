"""Optimizer setup for Boss Lines v3.

PLACEHOLDER RTP splits: the structure (one entry per bet mode and fence) is
final, the numbers are not - they get set in the tuning phase once the raw
game distribution is close to target.
"""

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructConditions,
    ConstructFenceBias,
    verify_optimization_input,
)

TARGET = 0.967  # 96.7% RTP for every bet mode (designer, 2026-10-07)


def wincap_rtp(cfg):
    """RTP (fraction of cost) each mode spends on 25,000x wins, from the tier mix and
    the per-tier Max Win rates (designer 2026-10-08). A flat 0.001 would let the
    optimizer push Epic's Max Win rate far below its 1% target."""
    cap = cfg.wincap
    p_mix = {}
    for mode, mix in cfg.tier_mix.items():
        tot = sum(mix.values())
        p_mix[mode] = sum(w / tot * cfg.tier_maxwin_rate[cfg.scatter_to_tier[n]] for n, w in mix.items())
    cost = {bm.get_name(): bm.get_cost() for bm in cfg.bet_modes}
    out = {
        "buy3": p_mix["buy3"] * cap / cost["buy3"],
        "buy4": p_mix["buy4"] * cap / cost["buy4"],
        "base": p_mix["buy3"] * cap / 200 / cost["base"],    # Bonus 1 in 200 base spins
        "ante": p_mix["buy3"] * cap / 40 / cost["ante"],     # Bonus 1 in 40 ante spins
        "feature": cfg.feature_maxwin_rate * cap / cost["feature"],
    }
    return {k: round(v, 5) for k, v in out.items()}


def _params(test_spins):
    return ConstructParameters(
        num_show=5000, num_per_fence=10000, min_m2m=4, max_m2m=8, pmb_rtp=1.0, sim_trials=5000,
        test_spins=test_spins, test_weights=[0.3, 0.4, 0.3], score_type="rtp",
    ).return_dict()


class OptimizationSetup:
    def __init__(self, game_config):
        self.game_config = game_config
        caps = {bm.get_name(): bm.get_wincap() for bm in game_config.bet_modes}
        wc = wincap_rtp(game_config)
        self.wincap_rtp = wc
        opt = {}
        # Proposal: Ante spin = 5x the rate of 3+ Scatter -> 1/5 of base's hit rate.
        # A triggered Bonus pays the buy3 tier mix mean (96.7x base bets). rtp is a
        # fraction of the mode's cost (optimizer: hr = avg_win / rtp / cost), so
        # base: 96.7/200 = 0.4835 (half of 0.967); ante (cost 3): 96.7/(40*3) = 0.80583.
        # Same base-game part in both: 0.4825 x base bet. (2026-10-07, replaces 0.30 placeholder)
        bonus_hr = {"base": 200, "ante": 40}
        bonus_mean = 96.7
        for mode in ("base", "ante"):
            cost = {bm.get_name(): bm.get_cost() for bm in game_config.bet_modes}[mode]
            # the Bonus share includes its Max Win part, which lives in the wincap fence
            bonus_rtp = round(bonus_mean / (bonus_hr[mode] * cost) - wc[mode], 5)
            opt[mode] = {
                "conditions": {
                    "wincap": ConstructConditions(rtp=wc[mode], av_win=caps[mode],
                                                  search_conditions=caps[mode]).return_dict(),
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    "freegame": ConstructConditions(rtp=bonus_rtp, hr=bonus_hr[mode],
                                                    search_conditions={"symbol": "scatter"}).return_dict(),
                    "basegame": ConstructConditions(hr=3.5, rtp=round(TARGET - bonus_rtp - wc[mode], 5)).return_dict(),
                },
                "scaling": ConstructScaling([]).return_dict(),
                "parameters": _params([50, 100, 200]),
                "distribution_bias": ConstructFenceBias(applied_criteria=["basegame"], bias_ranges=[(2.0, 3.0)],
                                                        bias_weights=[0.5]).return_dict(),
            }
        opt["feature"] = {
            "conditions": {
                "wincap": ConstructConditions(rtp=wc["feature"], av_win=caps["feature"],
                                              search_conditions=caps["feature"]).return_dict(),
                "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                "basegame": ConstructConditions(rtp=round(TARGET - wc["feature"], 5), hr="x").return_dict(),
            },
            "scaling": ConstructScaling([]).return_dict(),
            "parameters": _params([10, 20, 50]),
            # No bias (2026-10-08): pushing mass into 500-1500x fought the tuned Heroic/Treasure hunt shapes.
            "distribution_bias": ConstructFenceBias(applied_criteria=[], bias_ranges=[], bias_weights=[]).return_dict(),
        }
        for mode in ("buy3", "buy4"):
            opt[mode] = {
                "conditions": {
                    "wincap": ConstructConditions(rtp=wc[mode], av_win=caps[mode],
                                                  search_conditions=caps[mode]).return_dict(),
                    "freegame": ConstructConditions(rtp=round(TARGET - wc[mode], 5), hr="x").return_dict(),
                },
                "scaling": ConstructScaling([]).return_dict(),
                "parameters": _params([10, 20, 50]),
                # No bias (2026-10-08): the designer's percentile spec (p60 <= 0.5 m, p75 <= 0.9 m per tier) is
                # built into the books; a 100-300x bias would undo it (Bonus tier p75 is ~64x).
                "distribution_bias": ConstructFenceBias(applied_criteria=[], bias_ranges=[], bias_weights=[]).return_dict(),
            }
        self.game_config.opt_params = opt
        verify_optimization_input(self.game_config, self.game_config.opt_params)

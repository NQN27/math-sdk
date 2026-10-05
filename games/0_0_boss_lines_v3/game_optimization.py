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

TARGET = 0.97
WINCAP_RTP = 0.001


def _params(test_spins):
    return ConstructParameters(
        num_show=5000, num_per_fence=10000, min_m2m=4, max_m2m=8, pmb_rtp=1.0, sim_trials=5000,
        test_spins=test_spins, test_weights=[0.3, 0.4, 0.3], score_type="rtp",
    ).return_dict()


class OptimizationSetup:
    def __init__(self, game_config):
        self.game_config = game_config
        caps = {bm.get_name(): bm.get_wincap() for bm in game_config.bet_modes}
        opt = {}
        # Proposal: Ante spin = 5x the rate of 3+ Scatter -> 1/5 of base's hit rate.
        bonus_hr = {"base": 200, "ante": 40}
        for mode in ("base", "ante"):
            bonus_rtp = 0.30
            opt[mode] = {
                "conditions": {
                    "wincap": ConstructConditions(rtp=WINCAP_RTP, av_win=caps[mode],
                                                  search_conditions=caps[mode]).return_dict(),
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    "freegame": ConstructConditions(rtp=bonus_rtp, hr=bonus_hr[mode],
                                                    search_conditions={"symbol": "scatter"}).return_dict(),
                    "basegame": ConstructConditions(hr=3.5, rtp=TARGET - bonus_rtp - WINCAP_RTP).return_dict(),
                },
                "scaling": ConstructScaling([]).return_dict(),
                "parameters": _params([50, 100, 200]),
                "distribution_bias": ConstructFenceBias(applied_criteria=["basegame"], bias_ranges=[(2.0, 3.0)],
                                                        bias_weights=[0.5]).return_dict(),
            }
        opt["feature"] = {
            "conditions": {
                "wincap": ConstructConditions(rtp=WINCAP_RTP, av_win=caps["feature"],
                                              search_conditions=caps["feature"]).return_dict(),
                "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                "basegame": ConstructConditions(rtp=TARGET - WINCAP_RTP, hr="x").return_dict(),
            },
            "scaling": ConstructScaling([]).return_dict(),
            "parameters": _params([10, 20, 50]),
            "distribution_bias": ConstructFenceBias(applied_criteria=["basegame"], bias_ranges=[(500.0, 1500.0)],
                                                    bias_weights=[0.3]).return_dict(),
        }
        for mode in ("buy3", "buy4"):
            opt[mode] = {
                "conditions": {
                    "wincap": ConstructConditions(rtp=WINCAP_RTP, av_win=caps[mode],
                                                  search_conditions=caps[mode]).return_dict(),
                    "freegame": ConstructConditions(rtp=TARGET - WINCAP_RTP, hr="x").return_dict(),
                },
                "scaling": ConstructScaling([]).return_dict(),
                "parameters": _params([10, 20, 50]),
                "distribution_bias": ConstructFenceBias(applied_criteria=["freegame"], bias_ranges=[(100.0, 300.0)],
                                                        bias_weights=[0.3]).return_dict(),
            }
        self.game_config.opt_params = opt
        verify_optimization_input(self.game_config, self.game_config.opt_params)

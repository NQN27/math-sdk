"""Optimizer setup for Boss Lines v3.

Designer 2026-10-12 (tuning/targets/mode_targets_2026-10-12.csv): every tier mean must be EXACT in the
published tables, not only each mode's RTP. So every bet mode gets one fence per tier, found through the
force records written by the game:
  {"bonus_tier": t}    every Bonus session of tier t           (gamestate.run_bonus)
  {"maxwin_tier": t}   that session hit the 25,000x Max Win
  {"feature": f}       Feature spin type, f = heroic | treasure_hunt
  {"maxwin_feature": f}
A fence fixes its books' total weight (hr) and its average win (rtp), so
  tier mean = (non-Max-Win fence avg) * (1 - mw) + 25,000 * mw   is exact by construction.
Max Win fences come first (the optimizer gives each book to the first fence that matches). A tier whose
expected Max Win books are too few for its own fence (MIN_MW_PROB) keeps its Max Win books inside the
tier fence instead; its mean is still exact, only its Max Win rate is then free.
rtp = fraction of the mode cost; hr = 1 / probability per round.
"""

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructConditions,
    ConstructFenceBias,
    verify_optimization_input,
)

TARGET = 0.967  # 96.7% RTP for every bet mode (designer, 2026-10-07)
MIN_MW_PROB = 2e-5  # below this per-round Max Win probability a separate Max Win fence would be empty
TIER_ORDER = ("epic", "super", "bonus")  # rarest first; the last tier present is named "freegame"


def _params(test_spins):
    return ConstructParameters(
        num_show=5000, num_per_fence=10000, min_m2m=4, max_m2m=8, pmb_rtp=1.0, sim_trials=5000,
        test_spins=test_spins, test_weights=[0.3, 0.4, 0.3], score_type="rtp",
    ).return_dict()


def _no_bias():
    return ConstructFenceBias(applied_criteria=[], bias_ranges=[], bias_weights=[]).return_dict()


def tier_fences(cfg, prob, cost, extra_per_book=0.0, pooled_wincap=False):
    """Fence plan [(name, rtp, hr, search)] for tiers entered with probability prob[t] per round.
    extra_per_book: x-bet added to every tier book (the trigger spin's share of the designer's gap)."""
    cap = cfg.wincap
    tiers = [t for t in TIER_ORDER if prob.get(t, 0) > 0]
    plan, mw_fences, pooled = [], [], 0.0
    for t in tiers:
        p, mw = prob[t], cfg.tier_maxwin_rate[t]
        if pooled_wincap:
            pooled += p * mw * cap / cost
        elif p * mw >= MIN_MW_PROB:
            mw_fences.append((t, p * mw * cap / cost, 1 / (p * mw), {"maxwin_tier": t}))
    for i, (t, rtp, hr, search) in enumerate(mw_fences):
        plan.append(("wincap" if i == 0 else f"wincap_{t}", rtp, hr, search))
    for t in tiers:
        p, mw, m = prob[t], cfg.tier_maxwin_rate[t], cfg.tier_mean_targets[t] + extra_per_book
        own_mw = pooled_wincap or p * mw >= MIN_MW_PROB  # Max Win books already taken by a Max Win fence
        if own_mw:
            rtp, hr = p * (m - mw * cap) / cost, 1 / (p * (1 - mw))
        else:
            rtp, hr = p * m / cost, 1 / p
        plan.append((t, rtp, hr, {"bonus_tier": t}))
    return plan, pooled


def _conditions(plan, rename_last_tier="freegame"):
    """ConstructConditions per fence; the last tier fence takes the name the bet mode's distributions use."""
    last_tier = [n for n, *_ in plan if not n.startswith("wincap")][-1]
    out = {}
    for name, rtp, hr, search in plan:
        key = rename_last_tier if name == last_tier else name
        out[key] = ConstructConditions(rtp=round(rtp, 7), hr=round(hr, 4), search_conditions=search).return_dict()
    return out


def _close(conds, last_key):
    """Put the rounding residual on one fence so the fences add up to TARGET exactly."""
    total = sum(c["rtp"] for c in conds.values())
    conds[last_key]["rtp"] = round(conds[last_key]["rtp"] + TARGET - total, 7)
    return conds


def plan_summary(cfg):
    """{mode: {fence: (rtp, hr, avg_win_x_bet)}} for reports/tests."""
    out = {}
    cost = {bm.get_name(): bm.get_cost() for bm in cfg.bet_modes}
    for mode, conds in cfg.opt_params.items():
        out[mode] = {k: (c["rtp"], c.get("hr"), (c["rtp"] * cost[mode] * c["hr"]) if c.get("hr") not in (None, "x") else None)
                     for k, c in conds["conditions"].items()}
    return out


class OptimizationSetup:
    def __init__(self, game_config):
        cfg = self.game_config = game_config
        cap = cfg.wincap
        cost = {bm.get_name(): bm.get_cost() for bm in cfg.bet_modes}
        caps = {bm.get_name(): bm.get_wincap() for bm in cfg.bet_modes}
        opt = {}

        # ---- buy modes (buy3, buy4, Random Bonus): forced 3/4/5 Scatters, tier mix from the designer table ------------------------
        for mode in ("buy3", "buy4", "random_bonus"):
            mix = cfg.tier_mix[mode]
            tot = sum(mix.values())
            prob = {cfg.scatter_to_tier[n]: w / tot for n, w in mix.items()}
            gap = TARGET * cost[mode] - sum(p * cfg.tier_mean_targets[t] for t, p in prob.items())
            plan, _ = tier_fences(cfg, prob, cost[mode], extra_per_book=gap)
            conds = _conditions(plan)
            opt[mode] = {
                "conditions": _close(conds, "freegame"),
                "scaling": ConstructScaling([]).return_dict(),
                "parameters": _params([10, 20, 50]),
                # No bias: the tier shapes are tuned into the books (designer curves).
                "distribution_bias": _no_bias(),
            }

        # ---- base / ante: natural trigger rates per tier from the designer table -------------------------
        for mode in ("base", "ante"):
            prob = cfg.tier_trigger_rate[mode]
            plan, pooled = tier_fences(cfg, prob, cost[mode], pooled_wincap=True)
            conds = {"wincap": ConstructConditions(rtp=round(pooled, 7), av_win=caps[mode],
                                                   search_conditions=caps[mode]).return_dict(),
                     "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict()}
            conds.update(_conditions(plan))
            # base game proper (line wins, Treasure at stage 0) pays the rest - the designer's "gap"
            conds["basegame"] = ConstructConditions(hr=3.5, rtp=0.0).return_dict()
            opt[mode] = {
                "conditions": _close(conds, "basegame"),
                "scaling": ConstructScaling([]).return_dict(),
                "parameters": _params([50, 100, 200]),
                "distribution_bias": ConstructFenceBias(applied_criteria=["basegame"], bias_ranges=[(2.0, 3.0)],
                                                        bias_weights=[0.5]).return_dict(),
            }

        # ---- Feature: Heroic / Treasure hunt, each mean exact -------------------------------------------
        p_h = cfg.feature_heroic_chance
        share = {"heroic": p_h, "treasure_hunt": 1 - p_h}
        conds, mw_named = {}, False
        for f in ("heroic", "treasure_hunt"):
            p, mw = share[f], cfg.feature_maxwin_rates[f]
            if p * mw >= MIN_MW_PROB:
                key = "wincap" if not mw_named else f"wincap_{f}"
                mw_named = True
                conds[key] = ConstructConditions(rtp=round(p * mw * cap / cost["feature"], 7), hr=round(1 / (p * mw), 4),
                                                 search_conditions={"maxwin_feature": f}).return_dict()
        z = cfg.feature_zero_share["heroic"]
        conds["0"] = ConstructConditions(rtp=0, hr=round(1 / (share["heroic"] * z), 4), search_conditions=0).return_dict()
        for f, key in (("heroic", "heroic"), ("treasure_hunt", "basegame")):
            p, mw, m = share[f], cfg.feature_maxwin_rates[f], cfg.feature_mean_targets[f]
            zero = cfg.feature_zero_share[f]
            own_mw = p * mw >= MIN_MW_PROB
            nonzero = 1 - zero - (mw if own_mw else 0)
            rtp = p * (m - (mw * cap if own_mw else 0)) / cost["feature"]
            conds[key] = ConstructConditions(rtp=round(rtp, 7), hr=round(1 / (p * nonzero), 4),
                                             search_conditions={"feature": f}).return_dict()
        assert "wincap" in conds, "Feature needs a wincap fence (its distributions force Max Win books)"
        opt["feature"] = {
            "conditions": _close(conds, "basegame"),
            "scaling": ConstructScaling([]).return_dict(),
            "parameters": _params([10, 20, 50]),
            "distribution_bias": _no_bias(),
        }

        self.game_config.opt_params = opt
        verify_optimization_input(self.game_config, self.game_config.opt_params)

import random
import os

N_ROWS = 307
REELS_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\reels"

POWER_RATIOS = {"PXW": 28.0, "PMY": 25.0, "PAL": 15.0, "PBS": 14.0, "PWM": 10.0, "PGM": 6.0, "PXP": 1.99}
POWER_RATIO_SUM = sum(POWER_RATIOS.values())

# True original non-wild (L1-L5/H1-H4/EL/BO) shapes, recovered from
# _tuning_scratch/gen_bm_reels.py / gen_super_bm.py / gen_up_reels.py's
# BASELINE dicts with their own wild-like keys (W/PWM/PGM/...) stripped out -
# these are the foundations we scale, never touching L/H relative
# proportions directly (a prior tuning pass found shifting L->H concentration
# lowers average payout in this whole-board-explode/cascade mechanic - see
# gen_bm_reels.py's "WRONG DIRECTION FOUND" comment - so only the AMOUNT of
# wild-like weight changes per stage, never the L/H shape itself).
NONWILD = {
    "normal": {
        "other": {"L1": 65, "L2": 52, "L3": 53, "L4": 41, "L5": 34, "H1": 22, "H2": 17, "H3": 8, "H4": 7, "BO": 3, "EL": 3},
        "col0":  {"L1": 65, "L2": 52, "L3": 54, "L4": 42, "L5": 35, "H1": 22, "H2": 17, "H3": 7, "H4": 7, "BO": 3, "EL": 3},
    },
    "super": {
        "other": {"L1": 62, "L2": 50, "L3": 52, "L4": 40, "L5": 32, "H1": 22, "H2": 17, "H3": 7, "H4": 7, "EL": 3, "BO": 3},
        "col0":  {"L1": 65, "L2": 53, "L3": 54, "L4": 42, "L5": 35, "H1": 22, "H2": 16, "H3": 7, "H4": 7, "EL": 3, "BO": 3},
    },
    "hidden": {
        "other": {"L1": 74, "L2": 60, "L3": 61, "L4": 47, "L5": 40, "H1": 7, "H2": 5, "H3": 2, "H4": 2, "EL": 2, "BO": 2},
        "col0":  {"L1": 76, "L2": 61, "L3": 62, "L4": 48, "L5": 40, "H1": 7, "H2": 5, "H3": 2, "H4": 2, "EL": 2, "BO": 2},
    },
}

# Confirmed Tier x Stage taper table (total wild-like %) and fixed %Power-of-wild per tier.
STAGE_WILD_PCT = {
    # Normal: hard-tuned 2026-08-14/15 (was a flat 10/9/8/7/6/5 decay).
    # Front-loading stage 1-2 and crushing stage 4-6 was found necessary
    # to raise Normal Bonus's median (driven almost entirely by ordinary
    # line-win income - see game_config.reward_drop_weights_normal_bonus's
    # comment for the full channel-decoupling breakdown) while still
    # suppressing how often a session reaches the stage-6 chest.
    #
    # CLIFF FOUND: this response is NOT smooth. An initial steep taper of
    # 24/17/10/4/2/1 measured a ~101x pure-line-win floor (compression->
    # infinity). Trimming stage1/2 down to 19/13 - a modest-looking cut -
    # collapsed that floor to ~22x, a ~78% drop from one small change: an
    # all-or-nothing threshold in the whole-board-explode cascade
    # mechanic, not a proportional response. Bisected between the two
    # points (22/15 -> ~41x, 23/16 -> ~66-79x) and LOCKED at 23/16,
    # landing the floor safely under the 80.13x target with headroom for
    # the reward table (see game_config.py) to add the rest. Cascade-
    # safety (max_resolve_passes hit rate) at this taper is measured
    # directly against the final on-disk reels+reward-table combo rather
    # than assumed from an earlier smaller/different-seed check - see
    # scratchpad for the current measurement.
    "normal": {1: 23.0, 2: 16.0, 3: 10.0, 4: 4.0, 5: 2.0, 6: 1.0},
    "super":  {2: 8.0, 3: 7.0, 4: 6.0, 5: 5.0, 6: 4.0},
    # Revised DOWN from the original 6.5/5.5/4.5/3.5 proposal: empirical
    # testing (pass_count_sweep.py) found hidden's Both-Ways pay + 55%
    # power-fraction combination pushes resolve-pass counts into the
    # heavy tail hard enough to occasionally hit max_resolve_passes (300) -
    # measured hit-rate ~0.5-2% at 6.5%/55%pow on stage 3, vs 0% (max
    # observed pass count 134 across 1200 sims / 2 reel-generation seeds)
    # at 5.0%/55%pow - not a risk super/normal share (super's peak stage
    # tops out at 14 passes even at its full 8%/35%pow target, no Both
    # Ways). Scaled the whole hidden curve down proportionally (x0.769) to
    # keep the same taper SHAPE while landing stage 3 in the verified-safe
    # zone.
    "hidden": {3: 4.0, 4: 3.5, 5: 3.0, 6: 2.5},
}
POWER_FRAC_OF_WILD = {"normal": 0.0, "super": 0.35, "hidden": 0.55}
# col0 stays permanently Wild/Power-free for super/hidden (established pattern
# in gen_super_bm.py/gen_up_reels.py's BASELINE_COL0 - no W/Power key at all);
# normal's col0 DOES carry wild, same target % as its other columns.
COL0_GETS_WILD = {"normal": True, "super": False, "hidden": False}

TIER_FILE_PREFIX = {"normal": "BM_Reels", "super": "Super_BM", "hidden": "UP_Reels"}


def make_weights(nonwild_shape, target_wild_pct, power_frac):
    if target_wild_pct <= 0:
        return dict(nonwild_shape)
    nonwild_sum = sum(nonwild_shape.values())
    total_weight = nonwild_sum / (1 - target_wild_pct / 100.0)
    wild_weight = total_weight - nonwild_sum
    power_weight = wild_weight * power_frac
    plain_w_weight = wild_weight - power_weight
    out = dict(nonwild_shape)
    if plain_w_weight > 1e-9:
        out["W"] = plain_w_weight
    for k, r in POWER_RATIOS.items():
        w = power_weight * (r / POWER_RATIO_SUM)
        if w > 1e-9:
            out[k] = w
    return out


def build_column(weights, n, rng):
    names = list(weights.keys())
    wts = list(weights.values())
    return rng.choices(names, weights=wts, k=n)


def write_reel(path, w_col0, w_other, seed):
    rng = random.Random(seed)
    cols = [build_column(w_col0, N_ROWS, rng)]
    for _ in range(4):
        cols.append(build_column(w_other, N_ROWS, rng))
    with open(path, "w", newline="") as f:
        for r in range(N_ROWS):
            f.write(",".join(cols[c][r] for c in range(5)) + "\n")


def main():
    seed = 777
    written = []
    for tier, stages in STAGE_WILD_PCT.items():
        prefix = TIER_FILE_PREFIX[tier]
        pfrac = POWER_FRAC_OF_WILD[tier]
        col0_wild = COL0_GETS_WILD[tier]
        for stage, pct in stages.items():
            # target `pct` is the OVERALL 5-column average. When col0 is
            # forced to 0% wild (super/hidden), the other 4 columns must run
            # richer (x5/4) so the 5-column average still lands on `pct`.
            other_pct = pct if col0_wild else pct * 5.0 / 4.0
            w_other = make_weights(NONWILD[tier]["other"], other_pct, pfrac)
            w_col0 = make_weights(NONWILD[tier]["col0"], pct if col0_wild else 0.0, pfrac)
            fname = f"{prefix}_S{stage}.csv"
            path = os.path.join(REELS_DIR, fname)
            write_reel(path, w_col0, w_other, seed)
            written.append((tier, stage, fname, pct))
            seed += 1

    for tier, stage, fname, pct in written:
        print(f"{tier} stage{stage}: wrote {fname} (target wild={pct}%)")


if __name__ == "__main__":
    main()

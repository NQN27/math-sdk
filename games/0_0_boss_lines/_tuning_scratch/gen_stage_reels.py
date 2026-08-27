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
    # Super: REPLACED 2026-08-26 (was 8/7/6/5/4, hard-tuned independently of
    # Normal and never revisited when the 2026-08-19 shared boss_stage_table
    # rebalance made Super's first stage (2) noticeably tougher than
    # Normal's first stage (1)). Root-caused Super's 79-80% stage-2 death
    # rate (see TOWORK.md's "Super-tier Bonus is badly UNDER target" entry)
    # almost entirely to this taper being ~3x lower than Normal's at the
    # equivalent "stages since bonus start" - not a joint HP+Wild% problem
    # as first hypothesized. Reuses NORMAL's own taper values directly
    # (23/16/10/4/2, Normal's stage1-5 mapped onto Super's stage2-6), power
    # fraction and HP pool both left exactly as they were - isolated via a
    # 4-condition in-memory A/B (_tuning_scratch/super_normal_idea_experiment.py,
    # confirmed at n=8000: mean 28.45x -> 206.12x, stage-2 death 80.0% ->
    # 3.4%, vs the 240.77x target). Cascade-safety re-checked for this
    # SPECIFIC combination (23% wild + Super's existing 35% power fraction,
    # a combo that never existed before - Normal only ever ran high-wild%
    # WITHOUT power) via
    # _tuning_scratch/super_resolve_pass_safety_check.py: zero
    # max_resolve_passes hits across 113,999 internal spins at n=10000 - not
    # a risk here despite the "CLIFF FOUND"/hidden-taper history above
    # warning that high-wild%+power combos CAN blow up resolve-pass counts.
    # RE-TUNED 2026-08-28 (was 23/16/10/4/2, the "reuse Normal's taper"
    # candidate from 2026-08-26 above) - that candidate fixed the funnel
    # collapse but concentrated death almost entirely at stage 4 (45.98%
    # vs a requested 35%) with stage2/3 far too safe (4.76%/13.83% vs a
    # requested 10%/30%). Game designer specified an explicit target shape
    # (stage-death%: s2~10, s3~30, s4~35, s5~20, s6~5) plus a stage-6
    # endless clear-chance curve (~25% decaying by 0.5pp/loop, floor 5% -
    # see game_config.stage6_dam_escalation["super"]). Reached via iterative
    # single-lever empirical tuning (_tuning_scratch/super_funnel_reshape.py)
    # - confirmed real reel-content-seed sensitivity along the way (a
    # harness bug initially re-randomized every stage's reel on every
    # candidate, even unchanged ones - fixed by keying the generation seed
    # to (stage, target%) instead of the candidate label) and a genuine
    # HP-depletion coupling effect (hardening an early stage costs
    # survivors more HP for every LATER stage too, not just its own -
    # confirmed by holding downstream reel content byte-identical across
    # two tests and still seeing s5 shift when only s4 changed). s5's own
    # wild% was found to NOT meaningfully control its death rate in
    # isolation (tested at 5/7/8.5/11%, no monotonic response - survivors
    # reaching s5 are already too HP-depleted for its own density to
    # matter) - what actually closed most of s5's gap was
    # booster_damage_multiplier["super"]=3.0 (see game_config.py), not a
    # further wild% change. Final measured funnel (n=15000, against the
    # SCRATCH-harness seed - see the seed warning below):
    # s2=10.17%, s3=28.09%, s4=34.43%, s5=18.20%,
    # s6-reach=9.11% (target 5% - the one persistent gap, not fully
    # closed). Payout: mean=232.50x, median=107.30x (46.2% of mean, now
    # inside the original 40-50% target band). See TOWORK.md for the full
    # candidate-by-candidate history.
    #
    # *** SEED WARNING (2026-08-28) - do NOT regenerate Super's reels by
    # running this file's main() and expect to reproduce the numbers
    # above. *** main()'s running-seed-counter lands Super's 5 files on
    # seed 783-787 (Normal's 6 files come first in this dict) - measured
    # DIRECTLY at n=15000 against those exact seeds: mean=304.43x,
    # median=115.50x (37.9% of mean, BELOW the 40-50% target band), stage
    # funnel s2=19.21%/s3=24.20%/s4=28.45%/s5=15.96%/s6=12.18% - a real,
    # substantially different result from the one this taper was actually
    # validated and shipped against, purely from reel-CONTENT seed
    # (aggregate wild% identical) - the same cliff-sensitivity class
    # documented elsewhere in this file. The reels actually on disk right
    # now were generated with seed = 6000 + stage*1000 + round(pct*10)
    # (see _tuning_scratch/super_funnel_reshape.py's gen_reels()) and
    # copied in directly, NOT produced by this file's main(). If you need
    # to regenerate Super's reels for any reason, use that same formula
    # (or re-derive and re-verify a new one against a real harness at
    # n>=15000) rather than assuming main()'s natural sequence reproduces
    # the validated state.
    "super":  {2: 18.0, 3: 13.0, 4: 10.0, 5: 8.5, 6: 3.0},
    # Revised DOWN from the original 6.5/5.5/4.5/3.5 proposal: empirical
    # testing (pass_count_sweep.py) found hidden's Both-Ways pay + 55%
    # power-fraction combination pushes resolve-pass counts into the
    # heavy tail hard enough to occasionally hit max_resolve_passes (300) -
    # measured hit-rate ~0.5-2% at 6.5%/55%pow on stage 3, vs 0% (max
    # observed pass count 134 across 1200 sims / 2 reel-generation seeds)
    # at 5.0%/55%pow. Scaled the whole hidden curve down proportionally
    # (x0.769) to keep the same taper SHAPE while landing stage 3 in the
    # verified-safe zone. NOTE: the "not a risk super shares" clause this
    # comment originally had is gone - Super's own taper changed
    # significantly on 2026-08-26 (see above) and was re-verified safe
    # independently, not by reference to this hidden-specific measurement.
    "hidden": {3: 4.0, 4: 3.5, 5: 3.0, 6: 2.5},
}
POWER_FRAC_OF_WILD = {"normal": 0.0, "super": 0.35, "hidden": 0.55}
# col0 is permanently Wild/Power-free for ALL tiers - confirmed by the game
# designer (2026-08-17) that Wild may only ever appear on columns 2-5
# (1-indexed) / reel index 1-4 (0-indexed), never column 1 / reel index 0.
# CORRECTED 2026-08-17: this used to read {"normal": True, ...} - a real bug,
# not a deliberate design choice as the old comment here claimed. It made
# BM_Reels_S1-S6.csv place "W" in column 0 (verified: 72/307, 41/307, 30/307,
# 14/307, 6/307, 2/307 rows for stages 1-6 respectively), which also silently
# violates game_config.py's own paytable comment ("Wild never lands on reel/
# column 0"). Super/Hidden were already correct (False) - only Normal was
# wrong. Every Normal-tier Bonus economy number tuned earlier this project
# (CONFIRMED_CANDIDATES.md) was measured against the buggy reels and needs
# re-verification against the corrected ones.
COL0_GETS_WILD = {"normal": False, "super": False, "hidden": False}

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

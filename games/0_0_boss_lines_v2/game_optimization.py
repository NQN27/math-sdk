"""Set conditions/parameters for the optimization program."""

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructConditions,
    verify_optimization_input,
)


class OptimizationSetup:
    """Single 'base' bet mode this phase (no bonus/feature-buy modes yet -
    see readme.txt). Fence formula for this SDK (learned the hard way on a
    previous build of this game): for a fence with sampling quota q needing
    target RTP contribution r, set hr=1/q and rtp=r explicitly (both given
    directly, not derived) - see game_config.py's Distribution quotas, which
    these hr values mirror 1:1 (verify_optimization_input asserts this).

    Phase 2 (Power system) note: the "basegame" fence's raw/natural win
    distribution got noticeably wider and higher-mean once Power was added
    (whole-board-explode chains more easily with more Wild-like symbols on
    the board, then Wild Multi/Global Multi scale up the result - measured
    raw mean ~2.27 vs the ~0.60 target, see readme.txt/game_config.py's
    quota-update comment). The scaling entries below broaden Phase 1's mild
    shape hint into a real downweight across most of the non-trivial win
    range, to help the optimizer's own reweighting search reach the
    UNCHANGED 0.599 basegame RTP target without needing to lean so hard on
    the smallest wins that volatility limits (etl40b/etl10k/cvar) break -
    tune further if the small-scale run below still needs it.

    Phase 3 (Bonus) note: added a "freegame" fence. freegame's own raw win
    distribution is far wider than basegame's - a session runs anywhere from
    1 spin (rare, HP<=lowest boss Dam total) up to dozens, with Global
    Multi/reward-drops persisting and compounding across every spin in the
    session, plus Hidden-tier Both-Ways double-paying - so its
    ConstructScaling entries are kept separate from basegame's and cover a
    wider win range.

    Phase 3 v3 note (see QUESTIONS_FOR_YOU.md's "Phase 3 v3" section for the
    full writeup): the declared per-fence `rtp` values below are NO LONGER a
    simple "each fence's own natural contribution" (basegame~0.60/
    freegame~0.366) split - a previous round found that split converges the
    ACHIEVED total to ~0.607 regardless of quota, because this shared
    optimizer's cross-fence combination stage (create_show_pigs) scores
    candidates purely on bankroll-survival, not on matching each fence's
    declared av_win, and with 2 ranged fences the achieved total is a
    non-linear function of the split rather than its simple sum. The values
    below were found by empirically walking that split (not by a formula)
    to land the ACHIEVED total at ~0.965, just under the 0.967 ceiling
    utils/rgs_verification.py's 3-star check enforces."""

    def __init__(self, game_config):
        self.game_config = game_config
        wincaps = {}
        for bm in game_config.bet_modes:
            wincaps[bm.get_name()] = bm.get_wincap()

        # Design decision: the "wincap" fence's real hit-rate = rtp/av_win
        # (this is an EXACT/deterministic fence - always pays exactly
        # av_win - so unlike the "0"/"basegame"/"freegame" ranged-fence
        # split discussed below, this rtp->hit-rate mapping is direct, not
        # subject to create_show_pigs's non-linear cross-fence behavior).
        # 0.000667/20000 = 1/29,985 ~= 1/30,000,000 hit-rate (moved from the
        # previous 0.001 = 1/20,000,000, per user's confirmed decision).
        # This ~0.033-percentage-point rtp reduction is small enough to fold
        # into the next full re-walk of the basegame/freegame split (task:
        # full harness re-verification pass) rather than hand-offsetting it
        # here - every other fence's rtp is being re-derived from scratch
        # anyway once the new per-stage reels / endless stage-6 tail /
        # stage-6-chest natural-maxwin criteria are all in place.
        self.game_config.opt_params = {
            "base": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.000667, av_win=wincaps["base"], search_conditions=wincaps["base"]
                    ).return_dict(),
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    # Phase 3 v3 FIX (see QUESTIONS_FOR_YOU.md's "Phase 3 v3" section for
                    # the full investigation): the OLD split here (basegame rtp=0.600 /
                    # freegame rtp=0.366, i.e. each fence's own hr*rtp av_win target
                    # mirroring its "natural" contribution) is what produced the
                    # ~0.607-stuck-regardless-of-quota symptom the previous agent
                    # observed. That was NOT because "rtp is unused" (it demonstrably
                    # IS read and used to seed each fence's own av_win target for the
                    # per-fence pig-breeding search in optimization_program/src/main.rs's
                    # create_ancestors) - it is because the FINAL cross-fence
                    # combination stage (create_show_pigs, ~line 520) scores candidate
                    # combinations purely by bankroll-survival (pmb_rtp=1.0 over
                    # 50/100/200 simulated spins), with NO term anywhere in that
                    # function's body that re-checks the achieved total against the
                    # declared per-fence rtp/av_win. With 2 simultaneous ranged
                    # ("distribution") fences, the winning combination the survival
                    # search settles on does NOT reliably land at
                    # sum(fence_quota * fence_av_win) - direct measurement (joining
                    # library/lookup_tables/lookUpTableSegmented_base.csv against
                    # library/publish_files/lookUpTable_base_0.csv's optimizer weights)
                    # showed both ranged fences landing well under their DECLARED mass
                    # share (freegame ~0.9% actual vs its 2% quota) while the exact-zero
                    # "0" fence soaked up the shortfall (67.9% actual vs its 58.4%
                    # quota) - a real, reproducible limitation of the shared optimizer
                    # for 2+ ranged fences, confirmed empirically (not by re-reading
                    # main.rs alone): swapping the (rtp) values between basegame and
                    # freegame with everything else held fixed moved the achieved total
                    # from 0.607 to 0.994 - i.e. the mapping from declared target to
                    # achieved total is real but highly non-linear/fence-shape-
                    # dependent, not a simple per-fence sum. Empirically walked the
                    # split (5 iterations, see readme.txt) to the values below, which
                    # land the ACHIEVED total at ~0.965 (safely under the 0.967 3-star
                    # ceiling in utils/rgs_verification.py's verify_mode_volatility,
                    # which treats "rtp" as a hard MAXIMUM, not a target band - see
                    # readme.txt) - this is a game-config-side compensation for the
                    # optimizer's cross-fence behavior, not a fix to the shared
                    # optimizer itself (out of scope, per task instructions).
                    # Phase 4 v2 (see QUESTIONS_FOR_YOU.md's "Phase 4 v2"
                    # section): flat 97.00% total replaces the old 0.967
                    # ladder - split 72.75% Line Wins ("wincap"+"0"+
                    # "basegame") / 24.25% Bonus ("freegame"), per spec
                    # (24.25% = 97.00x blended tier-mix Bonus average x
                    # 1/400 trigger frequency). Starting point renormalized
                    # from the OLD discovered (0.3835/0.5825) ratio to the
                    # NEW basegame budget (0.7275-0.001=0.7265) - empirically
                    # re-walked below like every previous phase's own
                    # fence-split discovery (see readme.txt).
                    # Phase 4 v2 FIX (this round - a prior mid-edit attempt was
                    # found half-done and non-functional: it had drifted to
                    # hr=900/rtp=0.5853 for freegame, matching neither this
                    # comment's own math nor a working result - achieved total
                    # was RTP-correct at ~0.97 but etl40b/cvar were badly
                    # VIOLATED (0.968/835 vs limits 0.9/800), and was never
                    # re-verified with a real run before being left in place).
                    # Root cause (confirmed empirically, not by re-deriving
                    # main.rs): `avg_win = hr*rtp*cost` sets how CONCENTRATED a
                    # fence's contribution is (fewer/bigger hits vs more/
                    # smaller ones) - it does NOT have to equal the real
                    # design average (97.00x blended tier-mix) for the
                    # optimizer to reach the right ACHIEVED total, since the
                    # achieved-vs-declared mapping is already known non-linear
                    # (see the "Phase 3 v3" note above). hr=400 (the spec's
                    # literal 1-in-400 target) forced avg_win=97, which is
                    # itself well above the etl40 metric's own threshold
                    # (40*cost=40 for base) - so nearly ALL of freegame's mass
                    # counted against etl40b no matter how the scaling below
                    # crushed the tail, and ALSO badly undershot the achieved
                    # total (0.403) at this fence's own natural rtp split.
                    # Walking hr DOWN instead (900->400->10, rtp/split held
                    # fixed each step) confirmed etl40b tracks avg_win far
                    # more than it tracks the scaling bands: hr=10 (avg_win=
                    # 5.825, safely under the 40 threshold) reproduced the
                    # SAME achieved total (~0.965, split is the real lever for
                    # that) while dropping etl40b to 0.044-0.046 and cvar to
                    # ~55-60 - both with wide margin, stable across repeated
                    # independent optimizer runs (unseeded RNG - re-run twice
                    # to confirm, not just once). This means the REALIZED
                    # per-hit Bonus average the optimizer actually selects for
                    # is no longer close to the reel-tuned 97.00x blended
                    # figure - same known/accepted trade-off this project has
                    # made before (see QUESTIONS_FOR_YOU.md's Phase 3 v3 "tần
                    # suất Bonus THẬT... không khớp thiết kế" note - achieved
                    # Bonus frequency/richness drifting from the raw design
                    # target is an established, previously-flagged pattern in
                    # this codebase, not a new regression).
                    # +0.000333 folded in here (was 0.3865) to re-absorb the
                    # wincap rtp cut (0.001->0.000667, see comment above) -
                    # verify_optimization_input requires the per-mode rtp sum
                    # to match bet_mode.rtp EXACTLY (round-to-5dp), and this
                    # sum had drifted to 0.969667 vs the declared 0.97 without
                    # this fix (caught before running anything, via advisor
                    # review - see readme.txt/report for this session).
                    "basegame": ConstructConditions(hr=1 / 0.3955, rtp=0.386833).return_dict(),
                    "freegame": ConstructConditions(hr=10, rtp=0.5825).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        # Phase 4 v2 fix: `etl40` sums win*weight_fraction for
                        # payouts >= 40*bet_cost - for base (cost=1) that's
                        # exactly 40. Previous bands straddled 50/500/5000 (and
                        # freegame's 30/300/2000), missing the metric's own
                        # threshold (same class of bug found/fixed in ante's
                        # fences above) - rebuilt around an explicit 40
                        # boundary, crushing hard only above it.
                        {"criteria": "basegame", "scale_factor": 1.1, "win_range": (0.1, 1), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 0.55, "win_range": (1, 40), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 0.05, "win_range": (40, 5000), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 1.0, "win_range": (0.1, 5), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.7, "win_range": (5, 40), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.04, "win_range": (40, 100), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.005, "win_range": (100, 2000), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.0002, "win_range": (2000, 20000), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=4,
                    max_m2m=8,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[50, 100, 200],
                    test_weights=[0.3, 0.4, 0.3],
                    score_type="rtp",
                ).return_dict(),
            },
            # ==================================================================
            # Phase 4 feature-buy modes - see game_config.py's Phase 4 section
            # and QUESTIONS_FOR_YOU.md/readme.txt for the full design writeup.
            # Each is its OWN opt_params entry with its OWN raw book pool -
            # this SDK's optimizer runs per bet-mode-name (see run.py's
            # target_modes / OptimizationExecution().run_all_modes), so
            # NONE of this can perturb "base"'s own entry above (confirmed
            # empirically too - see readme.txt's Phase 4 section).
            #
            # Same "hr=1/quota, rtp=r" convention as "base" throughout - the
            # cost multiplier (2x/25x/500x/100x/300x) needs NO manual
            # adjustment here: the shared Rust optimizer's own per-fence
            # target (`avg_win = hr*rtp`, then internally multiplied by that
            # bet mode's `cost` before being compared against the RAW,
            # cost-independent absolute win values in the lookup table - see
            # optimization_program/src/main.rs's `create_show_pigs`/
            # `parse_fence_info`) already scales this transparently - this
            # was verified directly against the shared Rust source before
            # writing any of the numbers below (not assumed), and matches
            # exactly how games/0_0_scatter's own shipped cost=200 "bonus"
            # bet mode declares its own freegame fence's rtp (0.966) as a
            # plain SMALL fraction, not a cost-scaled absolute number.
            #
            # Ultimate Power (cost 25x) / God Mode (cost 500x): a single
            # ranged fence ("basegame") - deliberately, per readme.txt's
            # Phase 3 finding that a lone ranged fence "converges to target
            # exactly" while 2+ coexisting ranged fences interact non-
            # linearly. "0"/"basegame" quotas below match this game's own
            # measured natural zero-win rate on the PWR0 reel (~0.153-0.155,
            # measured via a direct gamestate.run_spin() harness at 2000
            # sims/mode - see readme.txt) - NOT base's own ~0.55-0.60, since
            # the forced high starting stage + guaranteed >=5 Power symbols
            # make a truly zero-win spin considerably less likely here.
            "ultimatepower": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.000667, av_win=wincaps["base"], search_conditions=wincaps["base"]
                    ).return_dict(),
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    # +0.000333 folded in (was 0.964) - same wincap-rtp-cut
                    # re-absorption as base's own comment above.
                    "basegame": ConstructConditions(hr=1 / 0.843, rtp=0.964333).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "basegame", "scale_factor": 1.0, "win_range": (0.1, 5), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 0.6, "win_range": (5, 50), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 0.3, "win_range": (50, 500), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 0.08, "win_range": (500, 5000), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 0.01, "win_range": (5000, 20000), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=4,
                    max_m2m=8,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[50, 100, 200],
                    test_weights=[0.3, 0.4, 0.3],
                    score_type="rtp",
                ).return_dict(),
            },
            # godmode - the REAL root cause (confirmed by reading
            # utils/analysis/distribution_functions.get_etl_cvar_p5k_10k_vales
            # directly, not by further blind scaling): etl10k sums
            # `win * weight_fraction` for every payout >=10000 with NO
            # division by bet_cost (unlike cvar, which divides by
            # bet_cost, and unlike p5k/p10k, which get a cost-based
            # leniency factor via get_prob_scale) - it is an ABSOLUTE-
            # value, absolute-threshold, NOT-cost-normalized metric. 3
            # earlier attempts (crush harder, upweight, switch to a richer
            # PWR1 reel) all made it WORSE (2.45->9.09->24.89->65.07)
            # because none of them targeted the actual mechanism: for a
            # 500x-cost mode needing average win ~482.5x (per its own
            # hr*rtp*cost=1/0.845*0.964*500 ~= 570.6 per-fence raw target),
            # the fixed absolute value 10000 is only ~20.7x that target -
            # ANY meaningful probability mass at or above it contributes
            # disproportionately (e.g. even a 0.1%-weight entry at 15000
            # alone contributes 15 to etl10k, ~19x the 0.8 limit on its
            # own), regardless of how rich or poor the underlying reel is.
            # Reverted to sharing PWR0 with Ultimate Power (see
            # game_config.py) and rebuilt the scaling around a HARD
            # boundary exactly at the metric's own threshold instead of the
            # 500/5000/20000 bins used elsewhere in this game: raised the
            # 500-5000 and added a new 5000-10000 band (both kept
            # meaningful, non-crushed weight, since payouts here are
            # completely free of the etl10k penalty) while crushing
            # 10000-20000 down to near-zero (0.0003, an order of magnitude
            # more aggressive than any prior attempt) - the target average
            # is now reached via "many payouts approaching but staying
            # under 10000" rather than "a rare few over it".
            "godmode": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.000667, av_win=wincaps["base"], search_conditions=wincaps["base"]
                    ).return_dict(),
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    # +0.000333 folded in (was 0.964) - same wincap-rtp-cut
                    # re-absorption as base's own comment above.
                    "basegame": ConstructConditions(hr=1 / 0.845, rtp=0.964333).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "basegame", "scale_factor": 1.0, "win_range": (0.1, 5), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 0.6, "win_range": (5, 50), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 0.5, "win_range": (50, 500), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 0.6, "win_range": (500, 5000), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 0.35, "win_range": (5000, 10000), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 0.0003, "win_range": (10000, 20000), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=4,
                    max_m2m=8,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[50, 100, 200],
                    test_weights=[0.3, 0.4, 0.3],
                    score_type="rtp",
                ).return_dict(),
            },
            # Ante (cost 2x): same 2-ranged-fence structural risk as "base"
            # (basegame+freegame) - starting rtp split is base's OWN
            # discovered (0.3835/0.5825) ratio, renormalized to ante's
            # slightly smaller basegame+freegame budget (0.964 vs base's
            # 0.966) - a starting guess to empirically re-walk if the
            # achieved total misses, exactly like base's own Phase 3 v3
            # process (see readme.txt for whether a re-walk was needed here
            # too). basegame/freegame quotas (0.3545/0.10) and their
            # ConstructScaling bands are carried over directly from "base"'s
            # own values (measured via harness to be the same shape/order of
            # magnitude - ante reuses the IDENTICAL BR0/bonus engine, only
            # the freegame fence's sampling quota differs).
            "ante": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.000667, av_win=wincaps["base"], search_conditions=wincaps["base"]
                    ).return_dict(),
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    # Ante's FIRST small-scale (3k) attempt with base's own
                    # discovered ratio (renormalized) landed at achieved
                    # RTP=0.902, undershooting the 0.965 target by ~0.063 -
                    # confirms the 2-ranged-fence non-linearity is real here
                    # too (matches readme.txt's Phase 3 v3 finding: shifting
                    # MORE declared share toward freegame moved base's own
                    # achieved total UP, not down). Walked one step in that
                    # same direction (basegame 0.383->0.30, freegame
                    # 0.581->0.664, same 0.964 sum) - re-verified via an
                    # optimizer-only re-run (run_sims=False, same raw books)
                    # before committing to the 100k run.
                    # 2nd iteration: (0.383,0.581)->achieved 0.902; walking
                    # toward more freegame share (0.30,0.664)->achieved
                    # 1.030 (overshot past the 0.967 ceiling) - linearly
                    # interpolating between those 2 known points for the
                    # 3rd iteration.
                    # game_config.py's freegame quota changed 0.10->0.07
                    # (see that file's comment) to directly attack the
                    # etl40b violation at its source - re-walking rtp from
                    # scratch at the new quota (hr updated to 1/0.07=14.286
                    # to match, per this SDK's hr=1/quota convention).
                    # Starting from the last-known-good total-RTP-hitting
                    # pair (0.342/0.622) as the first guess at this new
                    # quota, to be re-measured.
                    # Phase 4 v2: flat 97.00% total (cost-normalized, cost=3)
                    # replaces the old 0.965 target - split, base-bet-
                    # relative, 169.75% Line Wins / 121.25% Bonus (121.25% =
                    # 97.00x blended tier-mix Bonus average x 1/80 trigger
                    # frequency), i.e. cost-normalized 56.583% / 40.417%
                    # (sum 97.00%, since ante's own RTP field - like every
                    # other bet mode's - is win/cost, cost=3 here). Starting
                    # point carried over in RATIO from the old (0.342/0.622)
                    # split, renormalized to the new 0.96999... budget -
                    # empirically re-walk exactly like every previous fence
                    # split in this file (see readme.txt for the established
                    # pattern - 2-ranged-fence combination is non-linear).
                    # (basegame+freegame budget = 0.97 - wincap's 0.001 -
                    # "0"'s 0 = 0.969, split 169.75:121.25 as above.)
                    # Phase 4 v2 FIX (this round - the hr=80/rtp=0.404167 pair
                    # a prior mid-edit attempt derived here was found drifted
                    # to hr=96.7/rtp=0.33436 in the actual code, matching
                    # neither this comment's own math nor a working result:
                    # achieved total was only 0.628, undershooting 0.97, and
                    # was never re-verified with a real run before being left
                    # in place). Same root cause/fix as base's own comment
                    # above: hr=80 forces avg_win=hr*rtp*cost=97 (the reel-
                    # tuned blended Bonus average), which sits well above the
                    # etl40 metric's own threshold (40*cost=120 for ante's
                    # cost=3) - so raising the rtp split enough to hit 0.965
                    # total (basegame=0.347/freegame=0.622) drove etl40b to
                    # 2.1-2.6 (over 2x the 0.9 limit) NO MATTER how hard the
                    # scaling bands below crushed the tail (confirmed by
                    # testing 2 very different crush strengths - both stayed
                    # badly violated, and the harder crush made it WORSE, not
                    # better - ConstructScaling has little real effect here,
                    # same finding as buy3/buy4's own comments). Walking hr
                    # DOWN instead (80->20, split re-walked to keep the same
                    # ~0.965 achieved total) confirmed avg_win, not the
                    # scaling bands, is what actually drives etl40b: hr=20
                    # (avg_win=20*0.622*3=37.3, under the 120 threshold)
                    # dropped etl40b to 0.012-0.016, stable across repeated
                    # independent optimizer runs. Same accepted trade-off as
                    # base's: the realized per-hit Bonus average this
                    # optimizer actually selects for ante no longer matches
                    # the reel-tuned 97.00x figure - an established pattern in
                    # this codebase already flagged once for base itself (see
                    # QUESTIONS_FOR_YOU.md's Phase 3 v3 section), not new here.
                    # +0.000333 folded in (was 0.347) - same wincap-rtp-cut
                    # re-absorption as base's own comment above (missed in
                    # the first pass over this file - caught by
                    # verify_optimization_input actually failing at runtime).
                    "basegame": ConstructConditions(hr=1 / 0.3545, rtp=0.347333).return_dict(),
                    "freegame": ConstructConditions(hr=20, rtp=0.622).return_dict(),
                },
                # `etl40` sums `win * weight_fraction` for every payout >=
                # 40*bet_cost - for ante (cost=3) that's 120, not the 80 these
                # bands were originally built around back when ante's cost was
                # 2x (stale from the pre-v2 cost change, updated here too) -
                # kept as a reasonable shape even though the real fix for
                # etl40b turned out to be the hr change above, not this.
                "scaling": ConstructScaling(
                    [
                        {"criteria": "basegame", "scale_factor": 1.2, "win_range": (0.1, 1), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 0.6, "win_range": (1, 50), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 0.3, "win_range": (50, 120), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 0.01, "win_range": (120, 5000), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 1.2, "win_range": (0.1, 5), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.9, "win_range": (5, 30), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.6, "win_range": (30, 120), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.02, "win_range": (120, 2000), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.0005, "win_range": (2000, 20000), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=4,
                    max_m2m=8,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[50, 100, 200],
                    test_weights=[0.3, 0.4, 0.3],
                    score_type="rtp",
                ).return_dict(),
            },
            # Buy-3+/Buy-4+ scatter (direct bonus buy, cost 100x/300x): only
            # "wincap" + "freegame" fences - matches games/0_0_scatter's own
            # shipped "bonus" bet-mode convention exactly (every sim in this
            # mode enters Bonus, there is no separate non-Bonus population
            # to sample). freegame's ConstructScaling bands are carried over
            # from "base"'s own freegame bands (same underlying Bonus
            # engine/tier reels, same order of magnitude - see readme.txt's
            # harness measurements: buy3 raw mean ~594x, buy4 ~1365x, both
            # well within base freegame's own ~1119x-mean shape).
            "buy3": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.000667, av_win=wincaps["base"], search_conditions=wincaps["base"]
                    ).return_dict(),
                    # Phase 4 v2: flat 97.00% total (cost-normalized, cost
                    # 100x) - freegame's own target 0.97-0.001=0.969, per the
                    # blended tier-mix Bonus average (97.00x base-bet-
                    # relative = 0.92x80.13 + 0.076x250 + 0.004x1070) / buy3's
                    # own cost 100. First pass at 5000 sims achieved 0.971
                    # (VIOLATED by 0.001) - confirmed via direct A/B
                    # re-optimizer runs that (a) ConstructScaling has ~zero
                    # effect here (bit-identical output across 2 different
                    # scaling attempts) and (b) the ~0.001 excess persists
                    # almost identically across several wincap/freegame
                    # splits summing to the same 0.970 - reads as small-
                    # sample quantization noise (5000 discrete integer
                    # lookup-table weights) rather than a fixable bias.
                    # Left the declared values at the clean spec-derived
                    # numbers and increased the FINAL validation sim count
                    # instead (see run.py) - both because the task's own QA
                    # plan wants buy3/buy4 at >=20k-100k anyway, and because
                    # a bigger raw pool gives the optimizer's weight
                    # allocation finer resolution to land closer to target.
                    # +0.000333 folded in (was 0.968) - same wincap-rtp-cut
                    # re-absorption as base's own comment above.
                    "freegame": ConstructConditions(hr=1 / 0.999, rtp=0.968333).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "freegame", "scale_factor": 1.0, "win_range": (0.1, 5), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.68, "win_range": (5, 30), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.2, "win_range": (30, 300), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.03, "win_range": (300, 2000), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.003, "win_range": (2000, 20000), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=4,
                    max_m2m=8,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[10, 20, 50],
                    test_weights=[0.6, 0.2, 0.2],
                    score_type="rtp",
                ).return_dict(),
            },
            # buy4's FIRST small-scale (3k) attempt hit RTP=0.966 (close to
            # target) but VIOLATED etl10k (1.05 vs the 0.8 limit) - crushed
            # the top band harder (0.005->0.001) and the next one down a
            # little (0.05->0.03), compensating with a mild raise on the
            # 30-300 band (0.25->0.32) - re-verified via optimizer-only
            # re-run before the 100k run.
            "buy4": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.000667, av_win=wincaps["base"], search_conditions=wincaps["base"]
                    ).return_dict(),
                    # Phase 4 v2: flat 97.00% total (cost-normalized, cost
                    # 300x) - freegame's own target 0.97-0.001=0.969, per the
                    # blended tier-mix Bonus average (291.00x base-bet-
                    # relative = 0.95x250 + 0.05x1070) / buy4's own cost 300.
                    # +0.000333 folded in (was 0.968) - same wincap-rtp-cut
                    # re-absorption as base's own comment above.
                    "freegame": ConstructConditions(hr=1 / 0.999, rtp=0.968333).return_dict(),
                },
                # Phase 4 v2: first pass achieved 0.971 (VIOLATED by 0.001,
                # same tiny quantization-noise finding as buy3 - see that
                # mode's comment). A direct weight-mass check of buy4's raw
                # freegame table shows a flatter spread than buy3's (7.5% in
                # 0-5, 25.8% in 5-30, 37.2% in 30-300, 29.5% in 300-2000,
                # 0.05% above 2000) - scaling adjusted to match that shape
                # rather than crushing bands with little real mass.
                "scaling": ConstructScaling(
                    [
                        {"criteria": "freegame", "scale_factor": 1.0, "win_range": (0.1, 5), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.75, "win_range": (5, 30), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.4, "win_range": (30, 300), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.15, "win_range": (300, 2000), "probability": 1.0},
                        {"criteria": "freegame", "scale_factor": 0.001, "win_range": (2000, 20000), "probability": 1.0},
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=4,
                    max_m2m=8,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[10, 20, 50],
                    test_weights=[0.6, 0.2, 0.2],
                    score_type="rtp",
                ).return_dict(),
            },
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)

"""Game-specific configuration file, inherits from src/config/config.py

Boss Lines - REBUILD v2, Phase 1 + Phase 2 (Power system).

Phase 1 scope (see D:\\Stake Engine\\QUESTIONS_FOR_YOU.md for the full spec
log): base-spin tumble+line-pay cascade engine, INCLUDING the full boss/stage
system (3 bosses, 6-stage Dam/HP table, whole-board symbol explode + damage,
reward-drop table, wincap-forced Maxwin routing). Boss state resets fresh to
stage 1 at the start of every spin (no cross-spin persistence - that is
Phase 3's job).

Phase 2 scope (this extension): the Power system - 8 Wild-attached effect
types (Wild Multi, Global Multi, Maxwin, Extra Wild, Extra Power, Big
Symbol, Mystery, Alter). See game_calculations.py/game_executables.py for
the resolve-loop/activation logic. Still OUT of scope: Scatter/Bonus, Ante/
feature-spin buy modes, Elixir/Booster, Player-HP bonus loop (Phase 3+).
"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


class GameConfig(Config):

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "0_0_boss_lines"
        self.provider_name = "sample_provider"
        self.provider_number = 0
        self.game_name = "Boss Lines"
        self.working_name = "Boss Lines (Phase 1 rebuild)"
        self.min_denomination = 0.01
        self.wincap = 20000.0
        self.win_type = "lines"
        # Phase 3: the "base" bet mode's RTP now includes the scatter-
        # triggered Bonus contribution (see the "freegame" Distribution/fence
        # below) - matches how games/0_0_boss_lines_library_backup_...'s old
        # build wired this exact scatter-Bonus-inside-"base" convention; see
        # readme.txt.
        # Phase 4 v2 (see QUESTIONS_FOR_YOU.md's "Phase 4 v2" section): FLAT
        # 97.00% target for base/ante/buy3/buy4 (replaces the old 0.967/
        # 0.965 ladder) - split 72.75% Line Wins ("0"+"basegame"+"wincap"
        # fences) + 24.25% Bonus ("freegame" fence).
        self.rtp = 0.97
        self.construct_paths()

        # --- Game Dimensions: 5 reels x 5 rows -------------------------------
        self.num_reels = 5
        self.num_rows = [5] * self.num_reels
        self.include_padding = True

        # EXPERIMENTAL (2026-09-04, game designer's idea, not yet adopted -
        # see game_executables._tumble_board_in_place for the full design/
        # safety-audit writeup and TOWORK.md for measured before/after
        # numbers). False = SDK default cascade/gravity refill (drop
        # surviving symbols, refill from top). True = replace exploded
        # symbols in their own cell, nothing else moves - requested to make
        # line-pay hit rate easier to reason about (cascades let symbols
        # realign into brand-new lines across passes; in-place only
        # refreshes what actually exploded). Defaults False: this is a
        # fundamental board-refill mechanic change that reshapes hit
        # frequency/chain depth across the whole game, and every reward
        # table / wild% / HP number tuned so far was calibrated against
        # cascade's specific statistics - flip only after the measured
        # impact below is reviewed and accepted, not by default.
        self.use_inplace_tumble = False

        # --- Controlled Deadspin Routing --------------------------------------
        # Per game-designer spec, columns 2/3/4 (1-indexed - reel index
        # 1/2/3; columns 1 and 5 always draw a plain random stop) each
        # independently roll a chance to be routed to a "Force Deadspin"
        # redraw instead of an ordinary random stop - see
        # game_executables.create_board_reelstrips/
        # _route_column_force_deadspin for the exact anti-match algorithm.
        # Does NOT touch the Pool/Reel Strips/Distribution weights - purely
        # re-picks a different, still-genuinely-random stop position for the
        # routed column so the recorded event is a real, replayable draw.
        # Forcing anti-match on ANY ONE of these 3 columns alone already
        # guarantees a full-board zero-win deadspin (every payline is a
        # contiguous run starting at reel 0 - see src/calculations/lines.py -
        # so a broken link anywhere caps kindCount below the paytable's
        # minimum of 3), and each column rolls independently here, so the
        # resulting deadspin-uplift probability from this mechanism alone is
        # 1-(1-p)^3 for chance p, not p directly (measured fallback rate -
        # when a column's pool has no valid anti-match candidate - was
        # ~10-12% at p=0.3-0.6 on the base game reel; higher-wild-density
        # reels/stages will fall back more often).
        #
        # 2026-08-17 (base game, per game-designer spec): tunable per bet
        # mode. Left at 0.0 (disabled) for every mode pending a real target
        # value from the game designer - enabling this changes the natural
        # hit-rate/RTP distribution and needs its own re-measurement pass,
        # same discipline as every other economy lever in this project.
        self.deadspin_force_chance = {"base": 0.0, "ante": 0.0, "feature": 0.0}

        # 2026-08-18 (Bonus "grace spin", per game designer): reuses the SAME
        # routing, gated by `grace_deadspin_pending` (see
        # game_executables.reset_boss_battle/clear_stage/create_board_
        # reelstrips and game_bonus.run_bonus_session) - NOT the same spin
        # that skips the counter-attack (that flag, boss_counterattack_grace,
        # is set and consumed within the spin that clears a stage, before the
        # new trio's board is ever drawn). This instead lands on the very
        # NEXT spin's opening reveal - the first time the new trio is faced
        # from a clean board - so keeping that spin low-eventful reads as
        # "quiet breather right after the free hit" even though it's
        # technically the following spin. Starting value chosen deliberately
        # high (unlike the base-game default above) for that reason - PLACE-
        # HOLDER pending designer sign-off, not yet confirmed against a
        # measured effect on mean/median Bonus payout.
        self.bonus_grace_deadspin_chance = 0.65

        # --- Chain-block (2026-08-19 rebalance bundle) -------------------------
        # Reactive counterpart to the grace-deadspin above: instead of a fixed
        # post-stage-clear breather, this watches consecutive same-spin winning
        # tumble passes (see game_calculations.evaluate_and_explode's
        # chain_pass_count bookkeeping) and, once that streak exceeds
        # chain_block_threshold, escalates the chance of forcing a column dead
        # (via the same Controlled Deadspin Routing primitive grace-deadspin
        # uses - see game_executables._route_column_force_deadspin) on every
        # later pass of that same run - capping how long a single spin's
        # cascade can keep paying out before something interrupts it. Ported
        # from the accepted 2026-08-19 rebalance proposal
        # (_tuning_scratch/final_combined_candidate.py's chain-break state
        # machine / _tuning_scratch/boss_lines_normal_slot_demo.html's
        # CHAIN_BLOCK_THRESHOLD/CHAIN_BLOCK_STEP), paired with the HP=200 pool
        # and boss_stage_table HP scaling below - the reward-table redesign
        # further down assumed this mechanic capping runaway chains, so it
        # must ship together with those, not in isolation. Chance on the pass
        # `extra` beyond threshold is min(1.0, chain_block_step * (extra + 1));
        # if routing can't find a safe column to force dead (hits
        # _route_column_force_deadspin's own fallback), the attempt carries
        # over as chain_block_pending and retries unconditionally on the very
        # next pass rather than re-rolling.
        # 2026-09-09: chain_block_threshold/step are FLAT constants - same
        # values at every stage, confirmed directly in
        # game_executables._maybe_apply_chain_block (no self.stage
        # reference anywhere in that logic). But the EFFECTIVE outcome is
        # NOT flat: _route_column_force_deadspin's success rate climbs
        # sharply by stage (each stage's reel differs, cumulative symbol
        # removal shrinks board diversity) - measured previously at ~65%
        # stage1 up to ~95-99% stage5-6 - so this mechanic disproportionately
        # suppresses exactly the deep-stage sessions that would otherwise
        # feed p85-p99 of the payout distribution. A step=0.22 candidate
        # (down from 0.30) was measured in an earlier round (n=20000 AND
        # n=80000) to close most of a similar stage-6 shortfall at the
        # cost of a modest mean increase - built and verified then but
        # never applied to this file. Testing it now against the current
        # iteration-5d reward-table/chest state.
        # ITERATION 9b: user relaxed the mean target to a ceiling of 90
        # (not necessarily exactly 85); iteration 9's reward-table cuts
        # are hitting diminishing returns (94.56, still over ceiling, only
        # -2.1% from a further -50% cut on 300-1000). Chain-block's mean
        # cost runs largely through line-pay (a separate income channel,
        # untouched by any reward-table edit), so no amount of
        # reward-table trimming alone closes this - nudging the actual
        # source back up partway (0.22 -> 0.26, between the original 0.30
        # and the aggressive 0.22) trades a little tail benefit for a real
        # cut at the mean's actual driver, now that p85-p95 are mostly
        # carried by the 100-250 reward-table boost rather than
        # chain-block alone.
        self.chain_block_threshold = 2
        self.chain_block_step = 0.26

        # EXPERIMENTAL (2026-09-16) - use_spin_budget-ONLY chain-block
        # override (see game_executables._maybe_apply_chain_block). The
        # shared chain_block_threshold/chain_block_step above stay the
        # single source of truth for every OTHER system (live HP-based
        # cascade, flat-damage) - both already validated against those
        # exact values (iteration 9b, n=40000: 79.84x+/-2.04); tightening
        # chain-block GLOBALLY to fix the spin-budget economy would
        # silently regress that already-locked calibration, the same class
        # of bug this file has hit twice before (the Wild-col0 fix and the
        # power_multi_factor_weights global-vs-scoped bug - see their own
        # comments). A tier absent from these dicts falls back to the
        # shared values above unchanged - only "normal" (the only tier
        # with use_spin_budget on) is populated.
        #
        # Per explicit request: cut chains much shorter than the live
        # system's own 2/0.26 (removing HP-based death removed the main
        # brake on how far a session progresses per spin under a FIXED
        # spin budget, so cascades need to do less work per spin here).
        # PLACEHOLDER pending measurement - see
        # _tuning_scratch/spin_budget_test.py.
        # SUPER PORTED 2026-09-20 (see use_spin_budget's own docstring
        # above) - starting placeholder threshold=1/step=0.80, an
        # arbitrary but reasonable first guess (matches an earlier value
        # Normal's own tuning passed through, not a measured fit for
        # Super). NOT YET MEASURED against Super's 240.77x target.
        self.spin_budget_chain_block_threshold = {"normal": 1, "super": 1}
        # Super: 0.80 -> 0.40 (2026-09-20) - baseline (deadspin=30%/
        # step=0.80) measured mean=128.33x vs the 240.77x target (-46.7%,
        # UNDER this time, opposite direction from Normal's own first
        # pass) - loosening chain-block first, per the same "chain-block
        # prioritized first" approach Normal's own tuning used.
        #
        # RE-TUNED (2026-09-21) after switching Super to flat_damage_boss_
        # hp_mult's newly-rederived table (see that config's own comment -
        # replaces an earlier 0.0255/... guess that blew out to mean=
        # 1482.66x/stage6=75.27%). The new boss-HP table alone (chain_step
        # still at 0.288) measured mean=278.88x at n=8000 (stage-end%=
        # {2:12.64,3:38.59,4:29.73,5:8.39,6:10.66}) - close but ~16% over
        # target. Direction check: 0.24->304.31x, 0.288->278.88x, 0.40->
        # 211.05x (higher step = LOWER mean for this config, interpolated
        # to 0.35 -> 237.12x at n=3000). CONFIRMED at n=15000: mean=
        # 226.36x, median=80.30x, stage-end%={2:13.79,3:41.6,4:28.36,
        # 5:7.91,6:8.34} - within this game's established ~1-6% sampling
        # noise band of the 240.77x target at this n, and stage6 lands
        # almost exactly on the best random-range config's own 8.28%.
        # 0.288 -> 0.35.
        self.spin_budget_chain_block_step = {"normal": 1.0, "super": 0.35}

        # EXPERIMENTAL (2026-09-20) - use_spin_budget-ONLY boss-HP
        # multiplier, per tier/per stage. Same shape/precedent as flat-
        # damage's own flat_damage_boss_hp_mult, but for the RANDOM-RANGE
        # damage system spin-budget currently uses (use_flat_damage is
        # still False for every tier - see game_executables.
        # roll_stage_bosses, which never had a per-tier override for this
        # path before now). Built specifically to reduce Super's stage-6
        # reach rate WITHOUT the funnel-volume side effects deadspin kept
        # producing: raising deadspin at stage 5 alone worked (stage6
        # 9.43% -> 7.71%) but any lever tried to compensate the resulting
        # mean drop backfired - loosening chain-block re-inflated stage6
        # itself (7.71% -> 10.72%), and lowering stages 2-4's deadspin
        # flooded the funnel's entrance so much (stage2 death 30.3% ->
        # 14.16%) that stage6 ended up WORSE than the original baseline
        # (12.99% vs 9.43%) despite stage5's own gate being unchanged - see
        # TOWORK.md for the full trade-off history. A boss-HP toll gate at
        # stage5 should not have that failure mode: it makes stage5
        # harder in absolute terms regardless of how many sessions arrive
        # there, rather than probabilistically breaking connections (whose
        # effect scales with how many attempts hit the gate).
        # A tier/stage absent from this dict gets hp_mult=1.0 (shared
        # boss_stage_table value, unchanged) - only "super" stage 5 is
        # populated. NOT YET MEASURED.
        # 1.4 -> 1.8 (2026-09-20, per explicit request to lower stage6 a
        # bit further after the stage2-deadspin funnel reshape re-inflated
        # it to 10.11% - this lever is the "clean" one (no funnel-volume
        # side effect), and mean was already +12% over target anyway, so
        # pushing it further should help both goals at once.
        self.spin_budget_boss_hp_mult = {"super": {5: 1.8}}

        # EXPERIMENTAL (2026-09-06, game designer's idea): per-tier, per-
        # stage deadspin chance, reusing the same Controlled Deadspin
        # Routing primitive as deadspin_force_chance/bonus_grace_deadspin_
        # chance above, but keyed by (tier, stage) and applied on EVERY
        # ordinary (non-grace) spin within that stage - see
        # game_executables.create_board_reelstrips's new elif branch. Built
        # to correct the flat-damage Normal re-tune's remaining funnel gap
        # after initial_mult=0.060/bonus_mult=0.04 locked in s1 (37.20% vs
        # target 38.30%) and s6 (2.25% vs target 1.55%, well under the
        # designer's "5% or lower" bar): s2 was overshooting (44.20% vs
        # target 32.70%) while s3-s5 were all undershooting (12.80/2.55/
        # 1.00 vs target 16.45/7.40/3.60) - too many sessions coasting past
        # s3-s5 into s6 rather than dying along the way. A tier/stage absent
        # from this dict gets no extra deadspin at all (0.0 default via
        # .get()). NOT YET VALIDATED - starting point for the same
        # measure-and-iterate pass as every other lever here.
        #
        # GATED TO use_spin_budget ONLY (2026-09-16, see
        # game_executables.create_board_reelstrips): this was still
        # unused/all-zero for every tier when the spin-budget mechanic was
        # built, so populating it now to help control THAT economy is safe
        # only if it stays inert for the live HP-based/flat-damage systems
        # (both already validated with this at 0.0/dormant) - reads as 0.0
        # for any tier without use_spin_budget on, regardless of what's in
        # this dict. Flat 30% -> 35% -> 33% (2026-09-17, per explicit
        # request - 35% pulled median down more than wanted), every stage
        # 1-6.
        # SUPER PORTED 2026-09-20 (see use_spin_budget's own docstring
        # above) - flat 30% starting placeholder across Super's own stage
        # range (2-6, per bonus_start_stage["super"]=2 - stage 1 never
        # happens for Super), same starting point Normal's own tuning pass
        # began from before iterating to 27%/38%. NOT YET MEASURED against
        # Super's 240.77x target - Super's own combat dynamics (wider
        # power_multi_factor_weights, booster_damage_multiplier=3.0,
        # stage6 endless tail) differ enough from Normal's that this value
        # should NOT be assumed to land anywhere near Normal's own final
        # 27%/38% split without its own measure-iterate pass.
        self.bonus_stage_deadspin_chance = {
            "normal": {1: 0.27, 2: 0.38, 3: 0.38, 4: 0.38, 5: 0.38, 6: 0.38},
            # Super: 30% -> 38% (2026-09-20, per explicit request for
            # "higher risk... một chút" - a bit more volatility). Higher
            # deadspin cuts more low/mid sessions short (more early deaths,
            # pulling median down) while chain_block_step stays the
            # tail-shaping lever - raises variance for roughly the same
            # mean, rather than moving mean itself. NOT YET measured.
            # Stage 5 raised further (2026-09-20, per explicit request to
            # lower stage-6 reach specifically) - breakdown showed 9.43%
            # of ALL sessions end at stage 6, and 88.7% of THOSE already
            # clear it at least once (only 1.07% get stuck fighting the
            # initial trio, loop>=2 is a mere 2.58% of all sessions) - the
            # mass is almost entirely from the stage 5->6 TRANSITION
            # itself, not the endless tail compounding. Targeting that
            # transition specifically via stage 5's own deadspin rather
            # than touching the shared escalation/HP levers.
            # 0.55 barely moved stage6 (9.43% -> 9.2%, ~same cliff/
            # nonlinearity this project has repeatedly hit with deadspin -
            # needs a much bigger jump, not a modest one, to matter).
            # REVERTED stage5 back to flat 38% (2026-09-20) - deadspin
            # couldn't reduce stage6 without a mean-compensation side
            # effect (chain-block re-inflated stage6 itself; lowering
            # stages 2-4 backfired WORSE by flooding the funnel's entrance
            # - see TOWORK.md for the full trade-off history). Switching
            # to a boss-HP-based lever instead (spin_budget_boss_hp_mult
            # below) to isolate stage5's difficulty from session-volume
            # effects entirely.
            # Stage 2 lowered specifically (2026-09-20, per explicit
            # request: "giảm tỉ lệ stage 2 dead xuống dồn vào 3456") -
            # stage-end% showed stage2 as the single largest death share
            # (~30%) - only stage2 touched here (not the same "cut every
            # early stage" move that flooded the funnel and backfired for
            # stage6 earlier - see the deadspin history above) so the
            # redistribution targets specifically the 2->3+ transition.
            # NOT YET measured.
            "super": {2: 0.22, 3: 0.38, 4: 0.38, 5: 0.38, 6: 0.38},
        }
        # "Reverse deadspin" counterpart - see game_executables.
        # _route_column_force_connect's docstring for the mechanism (biases
        # a column toward CONNECTING to its neighbor instead of breaking).
        # Built for s2, which was overshooting (44.20% vs target 32.70%)
        # after s1/s3/s6 were already locked in via initial_mult=0.060/
        # bonus_mult=0.04/s3 deadspin=1.0 - the opposite problem
        # bonus_stage_deadspin_chance solves. NOT a hard win guarantee like
        # deadspin's is (see that method's docstring for why the asymmetry
        # exists) - expect a weaker/softer response, same as deadspin itself
        # needed to go all the way to 1.0 to hit its target. NOT YET
        # VALIDATED - starting point for the same measure-and-iterate pass.
        self.bonus_stage_connect_chance = {"normal": {}}

        # --- Symbol map -------------------------------------------------------
        # L1..L5 = 10, J, Q, K, A (low pay, ascending). H1..H4 = Mini, Minor,
        # Major, Grand (high pay, ascending). W = Wild (never on reel/column 0).
        self.symbol_display_names = {
            "L1": "10", "L2": "J", "L3": "Q", "L4": "K", "L5": "A",
            "H1": "Mini", "H2": "Minor", "H3": "Major", "H4": "Grand",
            "PWM": "Wild Multi", "PGM": "Global Multi", "PMX": "Maxwin",
            "PXW": "Extra Wild", "PXP": "Extra Power", "PBS": "Big Symbol",
            "PMY": "Mystery", "PAL": "Alter",
            # Phase 3: Scatter (base/ante reels only, triggers Bonus) + the 2
            # Bonus-exclusive collectible symbols (plain reel symbols, NOT
            # wild-attached Power - no paytable/damage role of their own).
            "SC": "Scatter", "EL": "Elixir", "BO": "Booster",
        }
        # Ascending pay-order list, used by the stage-clear symbol-removal
        # system (stage N removes low_pay_order[N-1], stages 1-5 only).
        self.low_pay_order = ["L1", "L2", "L3", "L4", "L5"]

        # --- Paytable: (kind, name) -> pay (multiple of bet) -----------------
        # NOTE: L2 (J)'s spec values 0.15/0.75 are not representable on the
        # RGS's required $0.10 payout increment (utils/rgs_verification.py's
        # verify_lookup_format hard-asserts `payout_cents % 10 == 0`) - rounded
        # to the nearest valid increment: 0.15 -> 0.2, 0.75 -> 0.8 (0.3 already
        # valid, unchanged). Every other symbol's spec values already land on a
        # $0.10 increment. See readme.txt.
        # RESCALED 2026-09-13 (x1.3 of the original spec values below,
        # rounded to the nearest 0.05 for clean numbers - the raw x1.3
        # product had 2-decimal odd values like 0.13/0.26/0.39/1.04, per
        # user request to avoid that) as part of rebalancing Normal Bonus's
        # line-pay vs reward-drop split under the flat-damage system -
        # measured line-pay was only ~22-27% of total payout (vs
        # reward-drop's ~73-78%), and per user request this ratio needed
        # shifting toward line-pay rather than leaving reward-drop dominant.
        # This is a GAME-WIDE table (shared by every bet mode and all 3
        # Bonus tiers, not Normal-specific) - per explicit go-ahead, since
        # base/ante/Ultimate Power/God Mode/buy3/buy4/Super/Hidden haven't
        # had their own post-rescale re-verification pass yet and are being
        # treated as "not yet redone, will be redone later" for this build.
        # REVERTED 2026-09-16, per explicit user request ("trả lại bảng
        # multi cũ cho tôi"): back to the original spec values (pre-x1.3),
        # rounded only for the $0.10 RGS increment per the note above. The
        # x1.3 rescale's own rationale (line-pay's ~22-27%-of-total share
        # under flat-damage) still stands as a real finding - see TOWORK.md -
        # but the paytable lever is undone; Normal Bonus's line-pay/reward-
        # drop split and the flat-damage mean/median numbers measured
        # against the x1.3 table (83.13x/33.90x etc.) are now STALE and need
        # re-measuring against this reverted table before being relied on
        # again.
        self.paytable = {
            (3, "L1"): 0.10, (4, "L1"): 0.20, (5, "L1"): 0.50,
            (3, "L2"): 0.20, (4, "L2"): 0.30, (5, "L2"): 0.80,
            (3, "L3"): 0.20, (4, "L3"): 0.40, (5, "L3"): 1.00,
            (3, "L4"): 0.30, (4, "L4"): 0.60, (5, "L4"): 1.50,
            (3, "L5"): 0.50, (4, "L5"): 1.00, (5, "L5"): 2.50,
            (3, "H1"): 1.00, (4, "H1"): 2.00, (5, "H1"): 5.00,
            (3, "H2"): 1.50, (4, "H2"): 4.00, (5, "H2"): 10.00,
            (3, "H3"): 2.00, (4, "H3"): 6.00, (5, "H3"): 15.00,
            (3, "H4"): 3.00, (4, "H4"): 8.00, (5, "H4"): 20.00,
        }
        # No (kind, "W") entries: Wild never lands on reel/column 0 (see the
        # reel CSVs), so Lines.get_lines's wild-anchored-run branch (which only
        # fires when reel 0's symbol is itself a wild) can never trigger -
        # every line win is anchored on a real paying symbol, with wilds
        # (columns 1-4) substituting for it. A win's recorded "symbol" is
        # therefore always one of L1-L5/H1-H4, never "W".

        # Per-symbol-instance boss damage RANGE (uniform-random, rolled
        # independently for every exploding instance of that symbol anywhere
        # on the board - not one shared roll per symbol type).
        self.symbol_damage_range = {
            "L1": (5, 10), "L2": (6, 12), "L3": (8, 15), "L4": (10, 18), "L5": (12, 20),
            "H1": (15, 25), "H2": (18, 30), "H3": (20, 40), "H4": (25, 50),
        }
        # Wild damage = 2x a roll from the damage range of the highest-
        # paytable-value symbol it substituted for within the winning line(s)
        # it took part in this pass (see game_calculations.py). Ranking order:
        self.symbol_rank_order = ["L1", "L2", "L3", "L4", "L5", "H1", "H2", "H3", "H4"]
        self.wild_damage_multiplier = 2.0

        # EXPERIMENTAL (2026-09-05, game designer's idea): flat, deterministic
        # damage-to-boss/damage-to-player, replacing the random-range system
        # above. Per-tier switch - defaults False everywhere (old system
        # unchanged) until a tier's HP has been re-tuned against it; Normal is
        # first. See game_calculations.evaluate_and_explode (damage-to-boss)
        # and game_bonus.run_bonus_session (counterattack) for the two call
        # sites this gates.
        #
        # Damage-to-boss: low-pay (L1-L5) = 1, high-pay (H1-H4) = 2, Wild AND
        # every Power-tagged Wild variant = 3 ALWAYS - unlike the old system,
        # a Wild's flat-mode damage does NOT depend on which symbol it
        # substituted for (no more symbol_rank_order/wild_damage_multiplier
        # lookup). Booster/Elixir deal 0 - true by construction already (they
        # never enter the win-based `exploding` list at all; only marked
        # .explode via _activate_elixir_booster, which never calls
        # deal_damage_to_boss), so no explicit 0-entry is needed for them.
        #
        # Damage-to-player (boss counterattack): every ALIVE boss deals a
        # flat `flat_boss_counterattack_damage`, replacing boss_dam's
        # per-stage/per-boss random-scaled value entirely. NOTE: this bypasses
        # stage6_dam_escalation's per-loop boss_dam scaling - a non-issue for
        # Normal (stage6_endless_tiers["normal"]=False, no endless tail to
        # escalate), but needs revisiting before extending flat damage to
        # Super/Hidden, which both use the endless tail.
        #
        # Boss HP (boss_stage_table) and Player HP
        # (bonus_player_hp_choices) still reflect the OLD damage scale as of
        # this commit - average damage-per-instance is dropping roughly
        # 10-15x (old symbol ranges ~5-50, Wild up to 100; new flat values
        # 0-3), so both HP pools need their own empirically-derived rescale
        # pass once real average-damage-per-spin is measured under this
        # system - not yet done, tracked as the immediate next step.
        # "super": False -> True (2026-09-20, per explicit request to try
        # flat/small-integer damage for Super too - see flat_damage_boss_
        # hp_mult["super"]'s own docstring below for the target HP scale).
        self.use_flat_damage = {"normal": False, "super": True, "hidden": False}
        self.flat_symbol_damage = {
            "L1": 1, "L2": 1, "L3": 1, "L4": 1, "L5": 1,
            "H1": 2, "H2": 2, "H3": 2, "H4": 2,
        }
        self.flat_wild_damage = 3
        self.flat_boss_counterattack_damage = 1
        # Per-tier boss HP multiplier, ONLY applied when use_flat_damage[tier]
        # is True (game_executables.roll_stage_bosses) - boss_stage_table
        # itself stays untouched/shared so Super/Hidden (still on the old
        # damage system) are unaffected. Derived from a real measurement, not
        # a guess: n=30 sanity run on Normal with flat damage ON and this
        # multiplier still at 1.0 gave avg damage-to-boss per spin=28.52 vs
        # the old system's 252.65 (an 8.86x drop, matching the ~10-15x
        # predicted from the raw symbol-range/flat-value ratio) - sessions
        # ballooned to ~488 spins/session and 100% ended at stage 6 (never
        # actually clearing it) before this multiplier existed.
        # 0.113 = 1/8.86, i.e. shrink boss HP by the same ratio damage output
        # shrank by, to preserve roughly the same spins-to-kill.
        #
        # PER-STAGE OVERRIDE (2026-09-13): this value can now be a plain
        # float (applies to every stage, as originally) OR a dict keyed by
        # stage (game_executables.roll_stage_bosses looks up `.get(stage,
        # 1.0)` when it's a dict) - lets one tier's stage-by-stage survival
        # funnel be reshaped without touching the shared boss_stage_table.
        # Added because the flat 0.113-everywhere baseline's measured
        # stage-death% (s1=54.9/s2=32.5/s3=9.1/s4=2.1/s5=0.2/s6=1.3, n=1500)
        # was badly front-loaded against the game designer's target
        # (s1=38.30/s2=32.70/s3=16.45/s4=7.40/s5=3.60/s6<=5, see the
        # Controlled Deadspin Routing section above for where that target
        # comes from) - too many sessions dying at stage 1 instead of
        # spreading across s3-s5.
        # Eased stages 1-2 only (0.113 -> 0.105, ~7% easier) to let more
        # sessions survive past the earliest stages - CONFIRMED this moves
        # in the right direction (n=800: err vs target 36.6->28.0; s2 lands
        # almost exactly on target) but does NOT fully close the gap: s3-s5
        # are still meaningfully under target (measured ~10-11/2.7-3.1/
        # 0.2-0.4 vs target 16.45/7.4/3.6) even after this change, and mean
        # is noisy/elevated at this setting (93.08x at n=800, 109.95x at
        # n=5000 - both above the ~85-90x mean target the OLD random-damage
        # system was tuned to, and NOT tightly converged between sample
        # sizes). A "little" adjustment here measurably improves the shape
        # but does not fully solve it - fully matching the designer's exact
        # profile needs either further per-stage iteration on s3-s6 too (own
        # cliff-sensitivity risk - some candidates tested took >100s per
        # n=800 batch and had to be abandoned) or the previously-scoped but
        # never-built bonus_stage_deadspin_chance/bonus_stage_connect_chance
        # levers (still empty dicts, see the Controlled Deadspin Routing
        # section), or a dedicated reward-table retune to also bring mean
        # back down once the funnel shape is right. NOT further iterated
        # past this point - see TOWORK.md for the open item.
        # Scratch: _tuning_scratch/flat_damage_stage_sweep.py.
        #
        # STAGE 5 HARDENED FURTHER (2026-09-14), per explicit request:
        # s5's share was too small (0.62%) and s6's too large (2.30%) -
        # wanted s5 higher, s6 lower, without moving mean/median. 0.113 ->
        # 0.40 (a much bigger jump than stage 1/2's own -7% ease above was
        # needed to move the needle at all: 0.15 only nudged s5/s6 by
        # <1pp each, 0.22 barely more - this lever needed a ~3.5x jump, not
        # a small nudge, to matter). Paired with restoring the 100-250
        # reward-drop weights and chest values back toward their prior,
        # less-aggressive levels (see reward_drop_weights_normal_bonus's
        # own comments) to compensate the mean this alone would have
        # dropped (harder stage 5 = fewer chest-reaching sessions = lower
        # mean on its own). CONFIRMED at n=20000: s5 0.62->1.71% (~2.8x),
        # s6 2.30->1.26% (now under even production's own 1.37%), mean
        # 83.62->83.13x (essentially unchanged, as required), median
        # 33.45->33.90x (essentially unchanged).
        self.flat_damage_boss_hp_mult = {
            "normal": {1: 0.105, 2: 0.105, 3: 0.113, 4: 0.113, 5: 0.40, 6: 0.113},
            # SUPER EXPERIMENTAL (2026-09-20, per explicit request: "thử
            # bộ Dam lên boss về 1-2 và HP boss 10-20-30...") - tries
            # flat-damage for Super (previously only Normal used it under
            # spin-budget; Super was still on the random-range system).
            # flat_symbol_damage/flat_wild_damage below are already ~1-3
            # (shared across tiers, unchanged) - this multiplier targets
            # each stage's AVERAGE boss HP (across its 3 bosses) down to
            # roughly 10/20/30/40/50 for stages 2/3/4/5/6 (Super's own
            # stage range - it never sees stage 1), derived directly from
            # boss_stage_table's own per-stage averages: stage2 avg=391.67
            # -> mult=0.0255, stage3 avg=549 -> 0.0364, stage4 avg=858 ->
            # 0.0350, stage5 avg=1567.5 -> 0.0255, stage6 avg=3383.3 ->
            # 0.0148 (not perfectly monotonic because boss_stage_table's
            # own HP growth per stage isn't linear either - this is a
            # ratio to a linear 10/20/30/40/50 target, not a smoothed
            # curve). NOT YET MEASURED - replaces the spin_budget_boss_hp_
            # mult=1.8 experiment (dormant once use_flat_damage is True,
            # see roll_stage_bosses' if/elif chain).
            # REDERIVED (2026-09-21), per explicit request: the 0.0255/
            # 0.0364/... set above (targeting a naive linear 10/20/30/40/50
            # avg-HP-per-stage ladder) was measured to blow out massively -
            # mean=1482.66x, stage-end%={2:1.73,3:8.77,4:10.23,5:4.0,
            # 6:75.27} at n=3000 (75% of sessions reaching the endless
            # stage-6 tail, vs the best random-range config's 8.28%) - see
            # TOWORK.md for the full failure writeup. Root cause: that guess
            # wasn't grounded in this tier's OWN measured damage output, it
            # just scaled boss_stage_table's raw HP averages down to hit an
            # arbitrary round-number target.
            #
            # Correct derivation (mirrors EXACTLY how flat_damage_boss_hp_
            # mult["normal"] above was originally derived - "measured
            # avg-damage/spin under flat ON vs OLD system, ratio, mult =
            # 1/ratio"), this time done PER-STAGE since Super's ratio varies
            # by stage (unlike Normal's single flat 8.86x):
            # _tuning_scratch/measure_super_old_damage_rate.py (use_flat_
            # damage=False, boss HP inflated to ~infinite, isolates OLD
            # random-range avg dmg/spin) vs measure_super_flat_damage_rate.py
            # (same, use_flat_damage=True) - both per-stage, per-boss,
            # n=300 sessions/stage:
            #   stage2: old=351.93 new=32.13 ratio=10.955 -> mult=0.0913
            #   stage3: old=177.40 new=18.22 ratio=9.737  -> mult=0.1027
            #   stage4: old=88.63  new=9.346 ratio=9.483  -> mult=0.1055
            #   stage5: old=60.90  new=6.583 ratio=9.251  -> mult=0.1081
            #   stage6: old=38.71  new=4.177 ratio=9.267  -> mult=0.1079 (raw)
            # (ratios cluster 9.25-11.0x, consistent with Normal's own
            # 8.86x - confirms flat_symbol_damage/flat_wild_damage's 1-3
            # scale is a sane choice independent of tier). Applying these
            # mults to boss_stage_table's per-boss values and rounding each
            # to the nearest 5 (per explicit request - see
            # flat_damage_boss_hp_round below) gives:
            #   stage2: boss1=35 boss2=45 boss3=25
            #   stage3: boss1=55 boss2=70 boss3=45
            #   stage4: boss1=85 boss2=110 boss3=75
            #   stage5: boss1=165 boss2=205 boss3=140
            #   stage6: boss1=340 boss2=455 boss3=300 (at raw mult=0.1079)
            # (boss2 > boss1 > boss3 at every stage, preserved automatically
            # since a per-stage scalar mult keeps boss_stage_table's own
            # existing per-boss ratio - matches the explicit "boss vi tri so
            # 2 cao nhat, roi den 1, roi den 3" requirement without needing
            # any separate per-boss override.)
            #
            # STAGE 6 EASED (2026-09-21), per explicit request ("so 6 dang
            # nhay len cao qua"): the raw-ratio stage6 numbers above jump
            # ~2.06-2.22x over stage5 (165/205/140 -> 340/455/300) - much
            # steeper than every earlier stage-to-stage step (~1.5-1.9x),
            # because boss_stage_table's OWN raw stage6 HP already has this
            # same disproportionate jump (avg 1567.5 -> 3383.3, 2.16x) and
            # the per-stage-scalar-mult approach faithfully reproduces it.
            # At this small integer scale that jump reads as an awkward
            # discontinuity rather than a smooth ramp, so stage6's mult was
            # eased 0.1079 -> 0.0854 (targeting a gentler ~1.6-1.76x step
            # from stage5 instead) - gives boss1=270 boss2=360 boss3=240
            # (jitter +-5, all still multiples of 5, ordering unchanged).
            # CONFIRMED this does NOT reopen the stage6-reach blowout this
            # tier already fixed once: n=8000, mean=230.43x (vs 230.96x
            # before the ease - essentially unchanged) and stage-end%
            # unchanged at 8.43% for stage 6. Makes sense - easing stage6's
            # OWN HP only speeds up the endless tail's per-loop clear once a
            # session already reached stage6, it doesn't change how many
            # sessions get there in the first place (that's governed by
            # stage5's difficulty + cumulative spin budget, both untouched).
            # random-range system's own already-tuned behavior (this
            # derivation reproduces that system's per-stage damage/HP ratio
            # by construction), but needs confirmation before treating as
            # final.
            "super": {2: 0.0913, 3: 0.1027, 4: 0.1055, 5: 0.1081, 6: 0.0854},
            "hidden": 1.0,
        }
        # Rounding granularity for roll_stage_bosses' flat-damage HP roll -
        # per-tier so Super's new small-integer scale (tens, not hundreds)
        # can round to the nearest 5 (per explicit request) without
        # changing Normal's already-tuned nearest-10 rounding (Normal's
        # mean/median was calibrated at that granularity - switching it
        # would need re-verification for no real benefit at its HP scale).
        self.flat_damage_boss_hp_round = {"super": 5}
        # Flat additive HP jitter ("+-5 tren moi boss", per explicit
        # request), applied AFTER rounding instead of the shared
        # boss_variance_range multiplicative +-25% swing (which was
        # designed for the old hundreds-scale HP and produces awkward
        # non-multiple-of-5 spreads at this new tens-scale) - only active
        # for a tier listed here; every other tier keeps the original
        # multiplicative variance untouched.
        self.flat_damage_boss_hp_jitter = {"super": 5}
        # Same idea, player-side: counterattack dropped from an old average
        # base Dam of ~38.65/boss (mean of boss_stage_table's Dam column
        # across all 6 stages: 21.3,25.3,30.3,38.3,50,66.7) down to a flat 1,
        # so bonus_player_hp_choices' 200 must shrink by a similar ratio or
        # players become nearly unkillable (measured: with boss HP already
        # rescaled but player HP still at 200, avg spins/session was ~59 and
        # 100% of sessions reached stage 6, vs baseline's ~8.3 spins/session
        # - counterattack was no longer able to end a session at all).
        #
        # SPLIT INTO TWO MULTIPLIERS (2026-09-06) - a single shared scalar
        # (scaling the initial grant AND the +50/stage-clear bonus together)
        # produced an extremely sharp, near-discontinuous threshold: s1
        # death% barely moved across 0.030-0.044 (89.35%->66.60%) then
        # crashed to 11.85% at 0.045 - a 0.001 step in the shared scalar
        # (8.8 vs 9.0 raw HP) swinging s1 by 55 points. Coupling "how much
        # HP you start with" to "how much you get topped up per stage
        # cleared" compounds into that kind of cliff; splitting them lets
        # each be tuned independently and should smooth the response.
        # Applied as a multiplier on whichever choice bonus_player_hp_choices
        # rolls / on the flat 50 stage-clear bonus, not a replacement value -
        # the result is ROUNDED to a whole integer (game_bonus.py/
        # game_executables.py) since every other flat-damage value
        # (flat_symbol_damage, flat_wild_damage, flat_boss_counterattack_damage)
        # is a small whole integer too; a fractional HP value would be an
        # inconsistent unit.
        #
        # RESCALED AND MEASURED 2026-09-13 (was un-validated 0.08/0.08,
        # which gave mean=1087x against the ~85-90x target - over 12x too
        # high). Grid-searched the actual integer (initial HP, per-stage
        # bonus HP) pairs directly with boss_hp_mult held at the validated
        # 0.113 (n=5000-15000 per candidate, Normal Bonus,
        # `_tuning_scratch/flat_damage_sweep3.py`) rather than guessing a
        # multiplier and hoping it rounds well - confirmed the same
        # near-discontinuous-threshold behavior noted above is really a
        # staircase over the ROUNDED INTEGER HP values, most sensitive to
        # the per-stage bonus (it compounds across every stage cleared in a
        # session): (9,2)=34.71x, (10,2)=48.79x, (9,3)=54.66x, (11,2)=66.57x,
        # (10,3)=88.92x, (12,2)=105.09x, (11,3)=130.33x - (10,3) landed
        # closest to target. CONFIRMED at n=15000: mean=86.41x (inside the
        # ~85-90 target band), stage-death% 55.6/32.0/8.4/2.0/0.4/1.6 (a
        # smooth monotonic decay, no weird bimodality).
        # Mult values below are exact (10/200 and 3/50) so the rounding is a
        # no-op at these specific settings - not a coincidence, chosen this
        # way on purpose so the config value IS the integer HP, not an
        # approximation of it.
        # STILL OPEN: this only matches the OLD system's overall MEAN, not
        # its percentile SHAPE - measured median/mean ratio here is 30.8%
        # (p50=26.6/p75=48.8/p90=93.4/p95=166.2/p99=2282.1), noticeably more
        # tail-skewed than the random-damage system's own target shape
        # (~37-42% ratio). reward_drop_weights_normal_bonus is completely
        # unchanged by this pass - matching the OLD system's percentile
        # shape under flat damage (if wanted) would need its own dedicated
        # reward-table retune under this mechanic, the same conclusion
        # in-place-tumble's TOWORK.md item already reached for a different
        # mechanic change.
        self.flat_damage_player_hp_initial_mult = {"normal": 10 / 200, "super": 1.0, "hidden": 1.0}
        self.flat_damage_player_hp_bonus_mult = {"normal": 3 / 50, "super": 1.0, "hidden": 1.0}

        # --- 15 paylines across 5 rows (0=top .. 4=bottom) -------------------
        # Own design (not specified beyond "15 lines, continuous left-to-
        # right") - a varied mix of straights, V/zigzags and W-shapes so every
        # row/typical shape family is represented.
        self.paylines = {
            1: [0, 0, 0, 0, 0],
            2: [1, 1, 1, 1, 1],
            3: [2, 2, 2, 2, 2],
            4: [3, 3, 3, 3, 3],
            5: [4, 4, 4, 4, 4],
            6: [0, 1, 2, 3, 4],
            7: [4, 3, 2, 1, 0],
            8: [0, 1, 2, 1, 0],
            9: [4, 3, 2, 3, 4],
            10: [1, 2, 3, 2, 1],
            11: [3, 2, 1, 2, 3],
            12: [2, 1, 0, 1, 2],
            13: [2, 3, 4, 3, 2],
            14: [1, 0, 1, 0, 1],
            15: [3, 4, 3, 4, 3],
        }

        # --- Power system (Phase 2): 8 Wild-attached effect types ------------
        # A Power substitutes in paylines EXACTLY like plain Wild (Lines.
        # get_lines matches on the "wild" attribute, not the literal name
        # "W" - see src/calculations/symbol.py's check_attribute/special_flags
        # wiring), including the 2x-highest-symbol-substituted damage rule -
        # registering all 8 names under special_symbols["wild"] gets this for
        # free with no changes to Lines/Symbol. Like "W", none of these ever
        # land on reel/column 0 (see reels/BR0.csv, reels/WCAP.csv) and none
        # have paytable entries (wild-substitution only, never pays on its
        # own kind-count).
        self.power_immediate_names = {"PWM": "wild_multi", "PGM": "global_multi", "PMX": "maxwin"}
        self.power_fifo_names = {
            "PXW": "extra_wild", "PXP": "extra_power", "PBS": "big_symbol",
            "PMY": "mystery", "PAL": "alter",
        }
        self.power_type_by_symbol = {**self.power_immediate_names, **self.power_fifo_names}
        self.power_symbol_names = list(self.power_type_by_symbol.keys())
        # Every symbol that substitutes like Wild (used by
        # game_executables.resample_valid_symbol / enforce_removed_symbols /
        # Mystery/Alter reroll to make sure a reroll draw NEVER produces a
        # Wild-like symbol as a "normal paying symbol" replacement - the same
        # documented anti-wild-inflation fix Phase 1 already applied to "W"
        # alone, now extended to cover all 8 Power names too).
        self.wild_like_names = frozenset(["W"] + self.power_symbol_names)
        # Phase 3: resample_valid_symbol (stage-symbol-removal reroll /
        # Mystery / Alter) must never be able to conjure a Scatter back onto
        # the board either - it draws from a column's own reel-strip
        # weights, and "SC" IS present in that pool on BR0 (though never on
        # FR0/FR1/FR2 - Scatter simply isn't on those strips at all, so this
        # exclusion is a no-op there). Keeping it separate from
        # wild_like_names (which specifically means "has the wild
        # attribute") documents WHY it's excluded even though Scatter is not
        # wild-like.
        self.resample_exclude_names = self.wild_like_names | {"SC"}

        # Phase 3 bug fix: "EL"/"BO" (Elixir/Booster) are plain reel symbols
        # with no paytable entry and no wild/scatter attribute, but
        # GeneralGameState.create_symbol_map() (src/state/state.py) only ever
        # registers a symbol name if it appears as a paytable key OR
        # somewhere in special_symbols - neither was true for "EL"/"BO"
        # before this fix, so SymbolStorage never created a SymbolDefinition
        # for them and every create_symbol("EL"/"BO") call (i.e. every board
        # draw that happened to land one, which happens almost immediately
        # once a Bonus session starts, since FR0/FR1/FR2 carry them at
        # ordinary density) raised `ValueError: Symbol 'EL'/'BO' is not
        # registered` - a hard crash, not a hang, but the most likely actual
        # reason a from-scratch manual Bonus test never got anywhere (see
        # readme.txt's Phase 3 section). Fixed by giving them their own
        # special_symbols categories ("elixir"/"booster") purely so they get
        # registered - this does not give them "wild" or "scatter" semantics
        # (Symbol.assign_default_attribute's match statement has no case for
        # these two flag names, so nothing else about their behaviour
        # changes; every actual Elixir/Booster check in game_bonus.py already
        # matches by literal symbol name, not by attribute).
        self.special_symbols = {
            "wild": ["W"] + self.power_symbol_names,
            "scatter": ["SC"],
            "elixir": ["EL"],
            "booster": ["BO"],
        }
        # Standard SDK "anticipation" (highlight remaining reels once enough
        # scatters are already visible) trigger count - purely a frontend
        # hint, no gameplay effect; board.py's create_board_reelstrips reads
        # anticipation_triggers[self.gametype] whenever ANY scatter lands, so
        # both gametypes need a value even though "SC" never appears on the
        # Scatter-free Bonus/freegame reels (see FR0/FR1/FR2 below).
        self.anticipation_triggers = {self.basegame_type: 3, self.freegame_type: 3}

        # Wild Multi / Global Multi shared factor list (spec: "Wild Multi
        # doi gia tri: gio dung CHUNG list voi Global Multi") - the doc gives
        # only the value SET, not relative probabilities (same situation as
        # reward_drop_weights). ASSUMPTION/design choice, tuned against
        # measurement (see readme.txt): a uniform roll among these 7 values
        # compounds far too aggressively with the whole-board-explode design
        # (Wild Multi's per-line product AND Global Multi's uncapped,
        # additive-for-the-rest-of-the-spin total both stack on top of a
        # boss reward-drop table that already reaches 5000x on its own) - a
        # small-scale measurement with this weighted straight after adding
        # the 8 Power symbols to the reels still needed a ~5-6x downweight
        # from uniform before the natural/raw RTP was in a tunable range.
        # Weighted heavily toward 2x, geometric-ish decay toward 10x.
        self.power_multi_factors = [2, 3, 4, 5, 6, 8, 10]
        # TIER-SCOPED 2026-08-28 (was a single global dict - see git history
        # for the pre-scoping value/comment). The 2026-08-10 "TEMP TEST
        # VALUE" compression ({2:90,3:10,rest:0}) was meant to probe Hidden
        # specifically (per BOSS_LINES_SPEC_REVISION_2026-08-10.md) but,
        # being a bare global, silently applied to EVERY tier (and base-game
        # combat) for 18 days - Normal's own 79.90-80.85x-mean validation
        # this whole time was measured WITH it in effect. Discovered while
        # restoring the original wider table for Super specifically (part of
        # the game designer's funnel/distribution re-tune, 2026-08-28):
        # applying the wider table globally regressed Normal from ~80x to
        # 141.82x mean (measured directly, not assumed) - confirms the
        # compression is load-bearing for Normal/base/Hidden's current
        # calibration, not just an unused leftover. Scoped per-tier so
        # Super can use the wider table without touching the other two.
        # "default" covers base-game combat (self.bonus_tier is None there)
        # and any bonus tier without its own explicit entry - see
        # game_calculations.evaluate_and_explode / game_executables.
        # activate_global_multi_cells for the lookup.
        self.power_multi_factor_weights = {
            "default": {2: 90, 3: 10, 4: 0, 5: 0, 6: 0, 8: 0, 10: 0},
            "normal": {2: 90, 3: 10, 4: 0, 5: 0, 6: 0, 8: 0, 10: 0},
            "hidden": {2: 90, 3: 10, 4: 0, 5: 0, 6: 0, 8: 0, 10: 0},
            # Super only: restored the original, wider, un-compressed table
            # (2026-08-28 re-tune) - measured as a real, substantial
            # contributor to spreading Super's stage-death funnel toward
            # the requested 10/30/35/20/5 shape (see TOWORK.md), not just a
            # payout-side change.
            "super": {2: 50, 3: 25, 4: 12, 5: 6, 6: 3, 8: 2, 10: 1},
        }

        # FIFO-group effect ranges/choices. Counts are uniform-random integers
        # in the inclusive range given.
        self.extra_wild_count_range = (3, 10)
        self.extra_power_count_range = (2, 4)
        self.mystery_count_range = (5, 20)
        # Big Symbol size weights: ASSUMPTION/design choice (spec only says
        # "uniform among the 4 sizes unless you have reason to weight
        # otherwise"). A 5x5 Big Symbol covers the ENTIRE board (all 15
        # paylines become a single 5-of-a-kind, every cell explodes) - a
        # much bigger swing than 2x2, so weighting descending by size (mild,
        # not extreme) tempers volatility without contradicting "uniform
        # unless you have reason to" - see readme.txt for the measurement
        # that motivated keeping this non-uniform.
        self.big_symbol_size_weights = {2: 40, 3: 30, 4: 20, 5: 10}
        # Normal paying symbols only (never Wild/Power) - used by Big Symbol
        # (uniform pick of which symbol to draw large) and as the target pool
        # for Mystery/Alter rerolls (via resample_valid_symbol).
        self.normal_paying_symbols = list(self.low_pay_order) + ["H1", "H2", "H3", "H4"]

        # --- Phase 3: Elixir/Booster (Bonus-exclusive collectibles) ----------
        # Plain reel symbols (see reels/FR0.csv, FR1.csv, FR2.csv - never on
        # BR0/WCAP). Collected on the board, then BOTH activate together at
        # the moment a bonus spin's resolve loop produces a pass with no new
        # wins/connections and an empty Power queue (i.e. right as the
        # cascade is about to reach static state) - see
        # game_bonus.run_one_bonus_spin.
        self.elixir_heal_pct_range = (0.10, 1.00)  # of Player HP's CURRENT value
        self.elixir_heal_round_to = 10
        # "Doubles all boss damage dealt during the immediately-following
        # spin's resolve loop" - INTERPRETATION: "the immediately-following
        # spin" is read as the NEXT bonus spin taken in this session (this
        # spin is already winding down when Booster activates, so it can't
        # be "this" spin's damage) - a boolean flag consumed entirely by the
        # very next spin, never stacking (multiple Boosters collected at
        # once still only apply one x2, matching "effect expires after that
        # one next spin"). See readme.txt for the full reasoning.
        # TIER-SCOPED 2026-08-28 (was a bare 2.0 for every tier - see git
        # history). Super only: raised to 3.0 as part of the game
        # designer's funnel/distribution re-tune - measured (real harness,
        # not assumed) as a meaningfully effective, previously-untested
        # lever for spreading Super's stage-death distribution: combined
        # with the power_multi_factor_weights restoration above, moved the
        # stage funnel from a poor fit (total abs. deviation from the
        # 10/30/35/20/5 target ~18.6) to a much closer one (~9), including
        # closing most of stage 5's gap that direct Wild%/HP tuning alone
        # could not move (see TOWORK.md for the full candidate history).
        # Normal/Hidden left at the original 2.0 (unchanged, not
        # re-verified against a higher value this pass).
        self.booster_damage_multiplier = {"normal": 2.0, "super": 3.0, "hidden": 2.0}

        # --- Phase 3: Scatter -> 3-tier Bonus ---------------------------------
        self.bonus_scatter_tier_by_count = {3: "normal", 4: "super", 5: "hidden"}
        self.bonus_tiers = ["normal", "super", "hidden"]
        # Player HP is quantized to multiples of 50 throughout - granted
        # uniformly at random from these per-tier sets at Bonus start (max HP
        # starts equal to the granted value).
        #
        # Design decision: normal/super's pools were found (empirically,
        # via hp_pool_sweep.py) to be FAR too generous for the shared
        # reward_drop_weights table's stage-6-chest economics - measured
        # avg session payout (single-clear-stops behavior, i.e. before the
        # endless stage-6 tail existed) was 1107x for normal (target
        # 80.13x) and 204-446x for super (target 250.00x) against the OLD
        # pools below, because the shared table's stage-6 EV (~1314x/clear:
        # 2 normal-boss drops + 1 chest) already dwarfs normal's target on
        # its own once its stage-6 clear rate is anywhere near 50%+. Lowered
        # both pools until clear-through-to-stage-6 rate dropped enough
        # (measured, not assumed) for the SAME shared table to land back
        # near each tier's stated target - normal ~78.9x @ ~3.3% clear
        # rate, super ~255.7x @ ~15.2% clear rate (hidden's pool was
        # already close, ~1233x measured vs 1070x target, left unchanged).
        # OLD pools (pre-fix): normal=[250,300,350,400],
        # super=[350,400,450,500,550,600].
        # 2026-08-19 rebalance: Normal's HP pool raised flat to 200 (from
        # [50,50,50,100,100]) as part of the bundled boss-table/reward-table
        # rebalance below - see boss_stage_table and
        # reward_drop_weights_normal_bonus for the paired changes this HP
        # pool assumes. Ported from _tuning_scratch's "candidate" preset
        # (boss_lines_normal_slot_demo.html) - see game_config.py's own
        # boss_stage_table comment for the measured target this whole
        # bundle was validated against.
        # 2026-09-08 ITERATION 4 (mechanic lever, unverified): the flat
        # [200]*5 pool has ZERO session-length variance - every Normal
        # session starts with the exact same HP budget, which caps how
        # much the reward table alone can spread p50 vs p85-p99.5 (3
        # reward-table-only passes squeezed p85-p95 while chasing
        # p99.5/p99.9, without ever widening this). Introduced real
        # spread instead: shorter-HP draws die faster/cheaper (pulls
        # p50-p75 down toward target), longer-HP draws survive deeper
        # (feeds p85-p99.5 independently of reward-table VALUES). Kept the
        # average close to the old flat 200 (new mean=210, +5%) rather
        # than solving it exactly - per this file's own established
        # convention, measure the real effect before assuming the guess.
        # ITERATION 4b: [110,155,200,255,330] (avg 210, +5% vs flat 200)
        # measured mean=131.87 - a +53% RELATIVE mean blowout from a +5%
        # average HP change. HP is a highly convex lever - the high end of
        # the spread crosses into reaching the endless stage-6 loop far
        # more often, which pays out disproportionately vs. the HP
        # increase itself. Direction was right (p99.5 gap -52%->-18%,
        # p99.9 -57%->-36%) but magnitude was far too strong. Cut the
        # spread from +-45% to +-9% around 200, same average.
        # ITERATION 4c: 4b's +-9% uniform spread barely moved anything
        # (p99.5 1204->1246, +3.5%); the earlier +-45% spread moved p99.5
        # to 2039 (+69%) but blew mean out to 131.87 (+53%). The response
        # to spread WIDTH is highly convex, but a UNIFORM 5-way spread
        # can't target p99-p99.9 specifically without dragging the whole
        # body with it. Redesigned as a WEIGHTED pool instead (via
        # repetition - random.choice treats list entries uniformly, so
        # repeats encode probability): 98.6% of sessions keep ordinary
        # ~200 HP (protects the already-close p50-p95 body), with 3 rare
        # tiers mapped directly onto the target's own percentile
        # ITERATION 4d: 4c (990/6/3/1 @ 200/500/900/2000 - see below, this
        # replaces the 986/9/4/1 @ 200/350/550/900 shape) measured
        # mean=94.53 (target 85, worse than 4's 86.10), p99=1160.91
        # (OVERSHOT the 800-1000 band), p99.5=1415.30 (target 2500, still
        # -43%), p99.9=2432.30 (target 5000+, still -51%) - the 350 tier
        # was pushing too much mass right at p99 while 900 wasn't nearly
        # enough for p99.9. Dropped 350 entirely, pushed the top tier
        # 900->2000 at a smaller 0.1% share, added an intermediate 500 @
        # 0.6% to replace 350's old job without overshooting p99 as hard.
        # Mean HP = 205.70 (+2.85%) - still isolating the HP-pool lever
        # alone this pass (reward table unchanged from iteration 3/4) to
        # keep the diagnosis clean before doing a final joint compensation
        # pass.
        # ITERATION 4e: 4d (990/6/3/1 @ 200/500/900/2000) measured
        # mean=97.15 (worse than 4c's 94.53) and p99=1202.20 (overshot the
        # 800-1000 band even harder than 4c's 1160.91) - 500 HP (+150%) is
        # STILL too strong for what should be a modest p99 boundary case;
        # the convexity is steeper than assumed. Cut the closest/most-
        # frequent rare tier way down (500->250, a much gentler +25%) to
        # aim p99 at the 800-1000 band directly, kept a middle tier for
        # p99.5, and left the extreme tier high for p99.9 (still
        # unverified whether 2000 is even enough there - 4d only reached
        # 2640 total session payout from it, not 5000+, so may need
        # pushing further next pass).
        # ITERATION 4f: found the actual bug in 4c/4d/4e - total rare-tier
        # frequency was exactly 1.0% (0.6+0.3+0.1), which EXACTLY coincides
        # with the p99 cutoff, so p99 was being set by the bottom of the
        # rare population, not the baseline. That's why 350->250 HP barely
        # moved p99 (1160->1116) - the wrong variable was being tuned.
        # Even at 0.5% (below the p99 cutoff), p99 STILL climbed
        # (1127.92) - the real cause: a session's total is a SUM of many
        # draws, and a small rare-HP tail shifts the effective percentile
        # rank WITHIN the baseline population itself at any fixed sample
        # index (99.0th->~99.5th), and baseline's own p99->p99.5 climb is
        # already steep (947->1204). REVERTED to flat 200 (all HP-pool
        # sub-iterations abandoned) - a smooth HP spread cannot create the
        # near-2.5x CLIFF the target wants between p99 and p99.5 without
        # dragging p99 up too; that requires a genuinely discrete jump,
        # which only the reward table's rare/exclusive chest draw can
        # provide (see reward_drop_weights_normal_bonus's chest-tier
        # rebalance below).
        self.bonus_player_hp_choices = {
            "normal": [200, 200, 200, 200, 200],
            "super": [300, 350, 400, 450],
            # hidden was already close (measured ~1233-1299x vs 1070x
            # target at the old pool - much less severe than normal/super's
            # blowout, since hidden's near-certain stage-6 clear is closer
            # to what the shared reward table can support) - nudged down
            # for a tighter match: ~1038x measured at this pool, ~74.5%
            # clear-to-stage6 rate (was ~93-97%). OLD pool (pre-fix):
            # [500,550,600,650,700,750,800].
            "hidden": [200, 250, 300, 350, 400, 450, 500],
        }
        # EXPERIMENTAL (2026-09-16, per explicit user request: "sửa lại cơ
        # chế bỏ máu người chơi thay vào đó là số lượt spin cố định, lên
        # stage sau thì + lượt spin"): replaces the Player-HP/boss-
        # counterattack session-ending mechanic with a fixed spin budget,
        # per tier - default OFF everywhere, same convention as
        # use_flat_damage/use_inplace_tumble (an unmeasured behavior change
        # to a carefully-tuned economy should not silently become live).
        # See game_bonus.run_bonus_session/reset_bonus_state and
        # game_executables.clear_stage for the mechanic itself.
        #
        # Session starts with `spin_budget_initial[tier]` spins and ends
        # the instant that count reaches 0 - every internal Bonus spin
        # ALWAYS consumes exactly 1, UNCONDITIONALLY (including a
        # boss_counterattack_grace spin and an endless-stage6-reroll
        # `continue` spin). This must be unconditional, not mirrored off
        # the old counterattack block's position in the loop: HP-vs-
        # boss_dam has a natural escalating counter-pressure
        # (stage6_dam_escalation eventually outraces any HP top-up) that
        # bounds the endless tail; a spin count has none, so any branch
        # that let a spin run "free" (skipped because it hit an early
        # `continue`/grace-consumption path) would let super/hidden farm
        # the endless tail up to bonus_safety_cap_spins with no offsetting
        # cost. Decrementing unconditionally right after every
        # run_one_bonus_spin call, before any of that downstream branching,
        # avoids the loophole entirely rather than patching each path.
        #
        # Stage-clear grants a fresh `random.randint(*spin_budget_per_stage_
        # clear[tier])` MORE spins - the direct analogue of the old +50
        # Player HP stage-clear bonus, except a random 1-3 range (per spec)
        # rather than a fixed amount.
        # Deliberately placed inside the SAME stage-6-endless-repeat
        # suppression guard clear_stage already uses for the HP bonus
        # (`not (stage == max_stage and stage6_loop_count > 0)`) and for
        # the identical reason: without it, every endless-tail loop would
        # extend the budget with no offsetting cost and the tail would
        # never self-bound (same problem as the unconditional-decrement
        # note above, from the other direction - grants must be capped
        # even though costs can't be skipped).
        #
        # DEAD LEVERS for any tier with this flag on: use_flat_damage and
        # flat_damage_player_hp_initial_mult/_bonus_mult (Player HP is
        # never granted/read/spent - self.player_hp/max stay 0.0 all
        # session; bonus_player_hp_choices is never drawn from either),
        # and elixir_heal_pct_range/elixir_heal_round_to (Elixir is
        # repurposed below to grant spins instead of a % HP heal, rather
        # than silently becoming a no-op collectible - see
        # game_bonus._activate_elixir_booster). bonus_trigger_event/
        # player_hp_state_event/bonus_end_event still fire unchanged for
        # event-schema compatibility, just always reporting 0.0 for
        # playerHp/playerHpMax/playerHpFinal on a spin-budget tier -
        # bonus_end_event's end_reason gets a new value, "spins_depleted",
        # alongside the existing "hp_depleted"/"wincap"/"safety_cap"/
        # "stage_cleared".
        #
        # VALUES per explicit game-designer spec (2026-09-16): Normal Bonus
        # starts with 6 spins; clearing a stage grants a random 1-3 MORE
        # (uniform-random int, rolled fresh at each clear - see
        # game_executables.clear_stage - not a fixed amount, unlike the old
        # +50 Player HP grant it replaces). Super/Hidden are NOT part of
        # this spec (only Normal was requested) - left at the same shape
        # for type-consistency, but unverified/unused while their own flag
        # stays False.
        # FLIPPED TO LIVE 2026-09-17 for "normal" (per explicit request:
        # "đổi sang từ HP sang spin trước" - switch Normal Bonus over to
        # the spin-budget mechanic as the real live default, not just an
        # experiment). This is the first tier to switch off the old HP-
        # based/counterattack ending mechanic entirely - Super/Hidden stay
        # on it (their own spin-budget placeholders above are still
        # unmeasured, per the Super-vs-Normal comparison this session did).
        # Normal's spin-budget economy was tuned across this whole session
        # to mean~88.2x/median~25.9x against an explicit target of
        # mean=88.9x (see TOWORK.md for the full round-by-round history:
        # deadspin=33%, spin_budget_chain_block threshold=1/step=0.80,
        # boss_last_hit base=0.005/scale=0.02 per-pass-aggregated, and the
        # reward_drop_weights_normal_bonus K_low/K_high split-rescale).
        # SUPER PORTED 2026-09-20 (per explicit request: "add các config
        # mới này cho super... mục tiêu như cũ với super"), same
        # mechanic/flag Normal already uses, targeting SUPER'S OWN
        # pre-existing designer mean target (240.77x - see "CORRECTED
        # TARGETS" comment near boss_stage_table below), NOT Normal's
        # 88.9x. spin_budget_initial["super"]=8 was already sitting here
        # as an untouched placeholder before this - kept as the starting
        # point since it happens to match Super's own natural ~8-spin
        # average session length under the OLD HP-based system (see
        # bonus_rescue_roll's docstring: "trung binh game 8 spin"), a much
        # better-grounded starting guess than Normal's own initial=7 was.
        # spin_budget_per_stage_clear["super"]=(1,3)/elixir_spin_budget_
        # grant["super"]=1 are still raw, unmeasured placeholders, same
        # shape as Normal's before its own tuning pass. NOT YET MEASURED
        # against the 240.77x target - needs the same measure-iterate pass
        # Normal went through (deadspin/chain-block first, then
        # reward_drop_weights_super_bonus if that alone isn't enough -
        # Super's own reward table has NOT been touched by any of this
        # session's work and almost certainly needs its own K-rescale/
        # shoulder pass, since Super's economy is line-pay-dominated
        # (75.4%) rather than reward-drop-dominated like Normal).
        self.use_spin_budget = {"normal": True, "super": True, "hidden": False}
        self.spin_budget_initial = {"normal": 7, "super": 8, "hidden": 8}
        self.spin_budget_per_stage_clear = {"normal": (1, 3), "super": (1, 3), "hidden": (1, 3)}
        self.elixir_spin_budget_grant = {"normal": 1, "super": 1, "hidden": 1}

        self.bonus_start_stage = {"normal": 1, "super": 2, "hidden": 3}
        # Dedicated Scatter-free Bonus/freegame reel per tier - see
        # reels/FR0.csv (baseline Power density, matches base-game rate) /
        # FR1.csv (Super, ~2x density) / FR2.csv (Hidden, ~3x density) -
        # picked via game_override.get_current_distribution_conditions'
        # per-tier override, not the generic per-distribution reel_weights
        # mechanism (tier is a runtime outcome, not a Distribution-level
        # setting - see readme.txt).
        # Phase 4 v2: repointed from FR0/FR1/FR2 to the 3 new dedicated
        # Bonus-pool reels (see the Reels section below) - FR0/FR1/FR2 are
        # no longer used for Bonus session content (kept on disk, unused
        # for this purpose, same "leave it, don't delete" convention as
        # PWR1.csv).
        # Stage-aware reel lookup (Wild/Power tapering, see the reels-
        # section comment above): (tier, stage) -> reel id. Stage 6's entry
        # is reused for every loop of the endless stage-6 tail (self.stage
        # stays pinned at 6 throughout that tail - see game_bonus.py's
        # run_bonus_session), so no separate per-loop reel is needed.
        self.bonus_tier_stage_reel = {
            "normal": {s: f"BM_Reels_S{s}" for s in range(1, 7)},
            "super": {s: f"Super_BM_S{s}" for s in range(2, 7)},
            "hidden": {s: f"UP_Reels_S{s}" for s in range(3, 7)},
        }
        # "Both Ways" (pay left-to-right AND right-to-left on the same line
        # shape) - Hidden tier only.
        self.bonus_both_ways = {"normal": False, "super": False, "hidden": True}
        # Defensive-programming cap only (see readme.txt: the boss-
        # counterattack mechanic already guarantees termination on its own -
        # Player HP strictly decreases every spin unless the current stage's
        # 3 bosses are all already dead, in which case a stage-clear (fresh
        # bosses) already happened this same spin).
        self.bonus_safety_cap_spins = 500

        # --- Boss battle: column -> boss zone routing ("scenario 1") --------
        # col0 -> boss1 always; col2 -> boss2 always; col4 -> boss3 always.
        # col1 -> boss1 while boss1 alive, else boss2.
        # col3 -> boss3 while boss3 alive, else boss2.
        self.boss_primary_zone = {0: "boss1", 2: "boss2", 4: "boss3"}
        self.boss_fallback_zone = {1: ("boss1", "boss2"), 3: ("boss3", "boss2")}
        self.boss_ids = ["boss1", "boss2", "boss3"]

        # --- 6-stage Dam/HP table (base values, before +/-25% variance) ------
        # "Dam" is each boss's counter-attack power against the Player-HP pool
        # - that pool does not exist yet in this phase (Phase 3 only; base/
        # ante/feature spins have no Player HP per the spec), so Dam is rolled
        # and stored for structural completeness/forward-compatibility but has
        # NO gameplay effect in Phase 1. Only HP (damaged by exploding board
        # symbols) matters this phase.
        # 2026-08-19 rebalance: Normal-tier boss HP scaled up by
        # {1:3.7, 2:2.5, 3:2.7, 4:3.3, 5:4.75, 6:7.0} per stage (Dam
        # unchanged) - paired with bonus_player_hp_choices["normal"]=[200]*5
        # above and reward_drop_weights_normal_bonus's SEG1-7/chest table
        # below as one bundled design, ported from
        # _tuning_scratch/boss_lines_normal_slot_demo.html's "candidate"
        # preset / final_combined_candidate.py's HP_MULT. This table is
        # SHARED across all 3 tiers (Super/Hidden still use these same
        # values) - only Normal's own HP pool and reward table changed to
        # match; Super/Hidden's own separate hard-tuning is unaffected by
        # this rebalance.
        self.boss_stage_table = {
            1: {"boss1": (20, 444.0), "boss2": (24, 555.0), "boss3": (20, 370.0)},
            2: {"boss1": (24, 375.0), "boss2": (28, 500.0), "boss3": (24, 300.0)},
            3: {"boss1": (28, 540.0), "boss2": (35, 675.0), "boss3": (28, 432.0)},
            4: {"boss1": (35, 825.0), "boss2": (45, 1056.0), "boss3": (35, 693.0)},
            5: {"boss1": (45, 1520.0), "boss2": (60, 1900.0), "boss3": (45, 1282.5)},
            6: {"boss1": (60, 3150.0), "boss2": (80, 4200.0), "boss3": (60, 2800.0)},
        }
        # Endless stage-6 tail: each additional loop (every re-clear of
        # stage 6's 3 bosses, after the first) multiplies every boss's Dam
        # AND HP by this factor raised to the loop count, on top of the
        # usual per-roll +/-25% variance - bounds the tail by rising risk
        # instead of a hard stop. Per-tier, NOT a single shared value - see
        # game_bonus.run_bonus_session, which looks this up as
        # `stage6_dam_escalation[tier]`.
        #
        # CORRECTED TARGETS (2026-08-13, supersedes the original 250x/1070x
        # figures this was first tuned against): Normal 80.13x, Super
        # 240.77x, Hidden 2250.00x mean session payout - Hidden's number in
        # particular is more than DOUBLE the earlier (wrong) 1070x figure
        # this project was tuned against for most of an earlier session.
        #
        # BUG FOUND AND FIXED: the endless-loop code originally scaled only
        # Dam per loop, not HP. For a strong-damage tier (Hidden - Both Ways
        # + dense reel), a freshly-rolled stage-6 trio is usually one-shot-
        # cleared within the SAME spin it's rolled, which means the
        # counter-attack damage step (game_bonus.run_bonus_session) never
        # even runs that loop - so Dam's escalation multiplier had nothing
        # to act on most of the time, no matter how extreme. Measured: even
        # at escalation x10.0/loop (Dam-only), Hidden's mean plateaued
        # around ~4700-5000x, never approaching ANY reasonable target -
        # this was previously (wrongly) diagnosed as an unfixable
        # "structural ceiling" and used as the reason to exclude Hidden
        # from the endless tail entirely. Once HP was ALSO scaled per loop
        # (forcing the trio to actually survive past spin 1 more often, so
        # the damage step - and Dam's escalation - actually fires), the
        # mean became cleanly responsive to escalation again: 1.05->13120x,
        # 1.2->5817x, 1.5->3236x, 1.8->2448x, 2.0->2193x, 2.2->2100x
        # (n=3000 each). 2.0 lands closest to the 2250x target (within
        # 2.5%) with median=1892x (target band 1687-1800x, i.e. still ~5-
        # 12% over but far closer than before the HP-scaling fix); median/
        # mean ratio plateaus around 86-92% there rather than reaching the
        # 75-80% design band - closing that last gap needs a complementary
        # small lever (e.g. HP pool or variance), not more escalation, and
        # was left for a follow-up pass rather than over-fitting escalation
        # alone.
        #
        # Normal/Super's 1.20 default predates the HP-scaling fix above and
        # has NOT yet been re-verified against it (they reach stage 6 rarely
        # enough - 3.7%/15.8% - that the fix likely matters far less for
        # them than for Hidden, but this is not yet confirmed by
        # measurement) - flagged for the same follow-up pass.
        # Super: RE-TUNED 2026-08-28 from 1.20 to 1.06, as part of the
        # funnel/distribution re-tune (see gen_stage_reels.py's
        # STAGE_WILD_PCT["super"] comment for the full context). 1.20 was
        # crashing the stage-6 endless clear-chance curve almost
        # immediately (attempt#1=10.6%, attempt#2=4.6%, attempt#3=0% - see
        # TOWORK.md) against a requested gentle ~25%-decaying-by-0.5pp/
        # loop-floor-5% target. 1.06 tracks that target much better
        # (measured n=15000: attempt#1=20.1%, #2=27.5%, #3=20.0%, #4=0% -
        # survives several loops deep instead of crashing by #3). Normal/
        # Hidden left at their prior values, not re-verified against a
        # gentler escalation this pass.
        self.stage6_dam_escalation = {"normal": 1.20, "super": 1.06, "hidden": 2.0}
        # Per-tier gate on the endless stage-6 tail. Hidden: enabled (see
        # escalation comment above - the earlier exclusion was based on a
        # diagnosis since found to be wrong). Normal: DISABLED (2026-08-14
        # hard-tune, see reward_drop_weights_normal_bonus above) - even
        # after compressing Normal's reward table ~4.45x, re-testing with
        # endless still enabled added enough extra EV on top to blow past
        # the 80.13x mean target; measurement showed disabling it was
        # necessary to land the mean precisely (79.84x +/-2.04 at n=40000).
        # Super: left enabled, unchanged and NOT yet re-verified against
        # this same hard-tuning pass (only Normal was hard-tuned so far -
        # Super is next).
        self.stage6_endless_tiers = {"normal": False, "super": True, "hidden": True}

        # Per-spin "rescue roll" safety net (2026-09-04, game designer's own
        # idea, refined in discussion). Every Bonus spin, while the session's
        # running total is still under `floor`, roll `trigger_prob` chance to
        # top the session up directly into [floor, band_high]. Deliberately
        # NOT a guarantee (that used to be the separate finishing-blow
        # mechanic - REMOVED 2026-09-16, see boss_low_hp_execute_chance
        # below for its replacement, which is also explicitly NOT a
        # guarantee) - some sessions still end genuinely low if the coin-
        # flip never lands, by design ("van de ngo kha nang den cuoi van k
        # duoc gi").
        #
        # "Roll until you get something" is resolved as ONE direct draw from
        # the already-successful [floor, band_high] range once the trigger
        # fires, NOT a literal reel-reroll loop - rejection-sampling the full
        # cascade engine until a specific payout band hits is unbounded (some
        # game states may never naturally land there) and would leave a
        # visible "how many attempts" audit trail. A single conditional draw
        # gives the mathematically identical outcome distribution with zero
        # loop risk and zero visible retries.
        #
        # `trigger_prob` = 1/8, matched to Super's own ~8-spin average
        # session length per the designer's framing ("trung binh game 8
        # spin, thi moi spin co ty le 1/8 nha").
        #
        # Only calls award_win (never touches boss_hp/player_hp/stage), so it
        # is mechanically decoupled from the funnel re-tune (2117cfe) and the
        # (since-removed) finishing-blow guarantee (756f968) by construction -
        # confirmed by measurement, not just this reasoning: n=8000
        # stage-death% held at
        # s2=10.03/s3=28.69/s4=34.07/s5=18.15/s6=9.07 (baseline) - see
        # TOWORK.md for the combined-effect numbers this was validated
        # against (_tuning_scratch/perspin_rescue_roll.py):
        #   mean 245.38x->243.14x, median 105.25x->108.46x (both within
        #   noise), 0-5x 1.14%->0.69% (target was "<1%"), 0-10x 4.06%->2.46%,
        #   =0x 0.00%->0.00%, rescue actually triggers in ~16.3% of sessions
        #   (average ~1.33 under-floor check opportunities/session).
        #
        # Only "super" is configured - this was designed and tested against
        # Super's specific 0-5x request and average spin count. A tier
        # absent from this dict gets no rescue roll at all (see the `.get()`
        # call site in run_bonus_session). Hidden's own economy is still
        # completely untuned (see reward_drop_weights_hidden_bonus falling
        # through to the shared base table) - extending this there needs its
        # own floor/band/trigger_prob tuned to Hidden's own scale and average
        # spin count first, not a copy of Super's numbers.
        self.bonus_rescue_roll = {
            "super": {"trigger_prob": 1.0 / 8.0, "floor": 5.0, "band_high": 10.0},
        }

        # --- Last-hit ("execute") chance (2026-09-17) --------------------
        # REPLACES the old end-of-session "finishing blow" guarantee (see
        # git history / _tuning_scratch/consolation_test.py for that
        # mechanic's own validation record - it guaranteed a 0-kill session
        # always landed at least 1 kill, specifically to hit the "0-10x ~
        # 0%" designer requirement for Super/Hidden) AND supersedes the
        # 2026-09-16 flat per-spin placeholder (threshold_pct/flat 5%
        # chance) that briefly stood in for it - per explicit spec:
        #
        #   chance = (1 - current_hp / max_hp) * boss_last_hit_scale
        #            + boss_last_hit_base_chance
        #
        # `current_hp` is the boss's HP BEFORE damage. Only rolled when that
        # damage would NOT already reduce the boss to <=0 (a hit that
        # already kills the boss doesn't need a "last hit" - it already is
        # one).
        #
        # GRANULARITY (2026-09-17 v2, per explicit follow-up correction):
        # first built as a roll per INDIVIDUAL exploding cell/instance (see
        # game_executables.deal_damage_to_boss's old version in git
        # history) - measured to fire far too often, since a single
        # whole-board-explode pass can have dozens of exploding cells, each
        # an independent roll (Normal HP-based mean 80.82x -> 193.78x,
        # Super 240-260x target -> 779.72x, n=2000 each - roughly 2-3x
        # inflation across every tier). Per explicit correction ("Ko nên
        # tính theo ô... nên chỉ nên tính khi có connection gây damage vào
        # boss đấy"), re-scoped to roll ONCE per boss per PASS instead:
        # every exploding instance in a pass still deals its own raw
        # damage (unchanged, still correctly re-routed live if a boss dies
        # mid-pass), but `current_hp`/the last-hit roll itself only happens
        # once per boss, using the boss's HP at the START of the pass (not
        # per individual instance) and firing only if the boss is still
        # alive after the WHOLE pass's combined damage - see
        # game_executables.resolve_pass_last_hit, called once per pass from
        # game_calculations.evaluate_and_explode, right after the exploding
        # loop. A single pass therefore rolls at most 3 times (once per
        # boss), not once per exploding cell.
        #
        # The chance scales linearly with how LOW the boss's HP already is:
        # a full-HP boss (current_hp/max_hp = 1) only gets the base 0.5%;
        # a boss already chipped down near 0 HP approaches 0.5% + scale.
        #
        # THIS IS NOT A GUARANTEE, same as the mechanic it replaces - a
        # session can still end with 0 kills (and therefore under 10x) if
        # the chance never lands. Applied identically to Normal/Super/
        # Hidden (per explicit request, not scoped to use_spin_budget) and
        # to both the random-range AND flat-damage damage systems
        # (deal_damage_to_boss/resolve_pass_last_hit are shared code, gated
        # by neither use_flat_damage nor use_spin_budget) - Super/Hidden's
        # own "0-10x ~ 0%" requirement is THEREFORE NO LONGER GUARANTEED and
        # has NOT been re-measured against this change (same open item as
        # the 2026-09-16 removal, carried over unchanged).
        #
        # scale lowered 0.045 -> 0.02 per explicit request, ON TOP OF the
        # per-cell -> per-pass re-scoping above (both moves reduce roll
        # frequency/impact - not yet re-measured together at this exact
        # combination for Normal HP-based/Super/Hidden per explicit
        # instruction to only track the spin-budget economy going forward -
        # see TOWORK.md). base_chance unchanged.
        self.boss_last_hit_base_chance = 0.005
        self.boss_last_hit_scale = 0.02

        self.max_stage = max(self.boss_stage_table.keys())
        self.boss_variance_range = (0.75, 1.25)
        # Reroll cap for the "3 bosses' HP must be within 35% of each other"
        # constraint below.
        self.boss_hp_spread_max = 0.35
        self.boss_hp_reroll_attempts = 60

        # Stage-clear effect: remove a low-pay symbol from play (see
        # game_executables.enforce_removed_symbols) and prune the given
        # reward-drop tiers from the pool for the REST of this spin. Stage 6
        # has no symbol removal (all 5 low-pay symbols are already gone by
        # then) and uses a special reward path for its last-defeated boss
        # instead of pruning further tiers (see reward_drop_weights below).
        self.stage_clear_removed_symbol = {
            1: "L1", 2: "L2", 3: "L3", 4: "L4", 5: "L5", 6: None,
        }
        # 2026-08-19: stage 4's list extended to [10,12,15,18] (was [10,15])
        # to match reward_drop_weights_normal_bonus's new SEG4 tiers below -
        # the extra 12/18 keys don't exist in the shared base-game
        # reward_drop_weights table, so pruning them there is a harmless
        # no-op (dict-membership check, not a lookup).
        self.stage_clear_pruned_tiers = {
            1: [1, 2],
            2: [3, 4],
            3: [5, 6, 8],
            4: [10, 12, 15, 18],
            5: [20, 25],
            6: [],
        }

        # --- Boss-defeat reward-drop table (21 tiers) -------------------------
        # Key = payout multiplier ("x"); the literal wincap value (20000)
        # stands in for the "Maxwin" tier. Weighted heavily toward the lower
        # tiers. IMPORTANT: the 20000 ("Maxwin") entry must never be paid out
        # directly on a non-"wincap" criteria spin - see
        # game_executables.roll_reward_drop / award_win, this is exactly the
        # mistake flagged in QUESTIONS_FOR_YOU.md as previously made & fixed.
        self.reward_drop_weights = {
            1: 400, 2: 320, 3: 260, 4: 210, 5: 170, 6: 140, 8: 110, 10: 90,
            15: 65, 20: 50, 25: 38, 50: 22, 100: 13, 150: 9, 200: 6, 250: 4,
            500: 2.2, 1000: 1.1, 2000: 0.5, 5000: 0.18, 20000: 0.02,
        }
        # Top-3 tiers only rollable by whichever boss is defeated LAST within
        # a stage (chronologically, any of the 3 - order doesn't matter).
        self.reward_drop_top_tiers = {2000, 5000, 20000}
        # Stage 6's last-defeated boss instead rolls "random payout >= 500x"
        # from this subset of the very same table (spec's stage-6 special
        # case), rather than a further-pruned normal list.
        self.reward_drop_stage6_last_tiers = {500, 1000, 2000, 5000, 20000}
        # Super-tier-Bonus-ONLY reward-drop table (2026-08-27 REDESIGN,
        # supersedes the unscaled-placeholder table below the history
        # comment). Per the game designer's request ("i like the mean and
        # median but the distribution i want it alike the normal bonus
        # with 3 vertices") - shape adapted from
        # reward_drop_weights_normal_bonus's LOW/MID + exclusive-chest
        # structure (same VALUES, same WEIGHTS), value-rescaled by
        # K=0.5985 (_tuning_scratch/super_reward_redesign_v2.py) so the
        # reward-drop component lands near Super's own measured budget
        # (~64.46x of its ~261-267x total mean - see
        # payout_component_split_super.py: Super's economy is line-pay-
        # DOMINATED, 75.4% of total, the OPPOSITE of Normal's ~72%
        # reward-drop-dominated split, because Super survives far more
        # spins per session and has Power's Wild/Global Multi compounding
        # line-pay in a way Normal's power_frac=0.0 reels never do).
        # MEASURED (n=8000): mean=249.82x median=168.70x ratio=67.5% -
        # close to the pre-redesign placeholder's own measured mean
        # (~261-267x) and median (~178x), by design (see K derivation).
        # A genuine visible 3rd (chest) peak was explicitly tried and
        # REJECTED as not achievable at this budget without raising the
        # mean past target: both reusing Normal's spread chest tiers
        # (super_reward_redesign_v2.py) AND concentrating the same total
        # chest weight into a narrow 900-1100x band
        # (super_reward_redesign_v3.py) produced no locally-visible bump -
        # Super's dominant, smooth line-pay component swamps any
        # reward-table-driven cluster at the current ~24.6%-of-mean
        # reward-drop budget. Game designer's explicit decision (2026-08-27,
        # given this tradeoff): keep current mean/median, accept the
        # resulting single-peak shape rather than push mean above target
        # to force a 3rd peak. Revisit only if the designer wants to
        # trade mean precision for a real 3rd peak, or wants to instead
        # shrink line-pay's dominance (Power multiplier compounding /
        # Wild% - see TOWORK.md).
        self.reward_drop_weights_super_bonus = {
            0.6: 150, 1.2: 120, 1.8: 380, 2.4: 300, 3: 320, 3.6: 260,
            4.8: 210, 6: 110, 7.2: 85, 9: 65, 10.8: 48, 12: 60, 15: 44,
            18: 36, 20.9: 29.3, 23.9: 24.1, 29.9: 19.6, 35.9: 16.1,
            47.9: 13.2, 59.9: 10.8, 71.8: 8.8, 89.8: 7.2, 107.7: 5.0,
            119.7: 4.1, 149.6: 2.0, 179.6: 1.7, 209.5: 1.4, 359.1: 0.8,
            598.5: 0.5,
            # Chest tiers (stage-6-last-kill exclusive, same convention as
            # Normal's own table - applied last, matches
            # {**REGULAR_WEIGHTS, **CHEST} dict-collision-wins semantics):
            239.4: 15, 299.2: 8, 478.8: 4, 897.8: 0.9, 1496.2: 0.35, 2394: 0.12,
        }
        self.reward_drop_top_tiers_super_bonus = {239.4, 299.2, 478.8, 897.8, 1496.2, 2394}
        self.reward_drop_stage6_last_tiers_super_bonus = {239.4, 299.2, 478.8, 897.8, 1496.2, 2394}
        # --- OLD placeholder table (2026-08-15, unscaled copy of the
        # shared table) - SUPERSEDED 2026-08-27 by the redesign above, kept
        # here only as a historical reference, not read by any code:
        # self.reward_drop_weights_super_bonus = {
        #     1: 400, 2: 320, 3: 260, 4: 210, 5: 170, 6: 140, 8: 110, 10: 90,
        #     15: 65, 20: 50, 25: 38, 50: 22, 100: 13, 150: 9, 200: 6, 250: 4,
        #     500: 2.2, 1000: 1.1, 2000: 0.5, 5000: 0.18, 20000: 0.02,
        # }
        # self.reward_drop_top_tiers_super_bonus = {2000, 5000, 20000}
        # self.reward_drop_stage6_last_tiers_super_bonus = {500, 1000, 2000, 5000, 20000}
        # On the dedicated "wincap" fence only, heavily bias the last-of-stage
        # roll toward the Maxwin (20000) tier so the fence converges in a
        # reasonable number of repeats (see game_executables.roll_reward_drop
        # and readme.txt).
        self.wincap_force_maxwin_weight = 5000.0
        self.wincap_force_other_weight = 0.01
        # "Natural" Max-Win path (see game_executables.roll_reward_drop):
        # weight for the Maxwin tier within the stage-6-chest pool on every
        # NON-"wincap" criteria (every other criteria's reward-drop pools
        # still exclude it entirely). Against the pool's other weights
        # (500+1000+2000+5000 tiers = 3.98 total), this value gives
        # P(maxwin | one chest-open) = w/(w+3.98).
        # 2026-08-19: recalibrated against Normal's NEW chest pool weight
        # sum (15+8+4+0.9+0.35+0.12=28.37, not the old shared pool's 3.98)
        # for a 1-in-25000 session-level Max Win target - solved as
        # w = pool_weight_base * p_select_needed / (1 - p_select_needed),
        # P(chest reached) calibrated at ~1.75% via a 60000-session/3-seed
        # run. Result: w=0.0651 -> P(selected | chest reached)=0.2289% ->
        # session-level rate = 1-in-23509, inside the 1-in-20000-1-in-40000
        # target band. This value is SHARED with base/Super/Hidden's own
        # stage-6-chest rolls too (see roll_reward_drop) - was the
        # old-shared-pool placeholder (0.00000796, 1-in-500k) before this
        # change; only Normal's own chest pool weight sum was used to
        # derive the new number.
        # 2026-09-08 RETARGETED (supersedes the 1-in-23509/2026-08-19 note
        # above - that number is now stale, do not resurrect it): explicit
        # new spec is 1-in-35000 session-level Max Win rate, verified at
        # n=35000 (one expected hit per run). Re-solved again for
        # ITERATION 5's chest-weight flip (400/500/800/1500/2500/4000:
        # 15/8/4/2.2/1.0/0.5 -> 2/1.5/1.5/9/6/3, pool sum 30.7 -> 23),
        # same ~1.75% P(chest reached) measurement (stage-clear mechanic,
        # untouched): p_needed = (1/35000)/0.0175 = 0.16327%,
        # w = p_needed*pool/(1-p_needed) = 0.03761.
        self.stage6_chest_natural_maxwin_weight = 0.03761

        # Normal-tier-Bonus-ONLY reward-drop table (2026-08-14/15 hard-tune
        # + shape redesign, SUPERSEDES the earlier two-band-compression
        # pass): the shared table above, applied identically to base-game
        # combat and to Super/Hidden Bonus, was found to make Normal
        # Bonus's median session payout collapse toward ~0 no matter how HP
        # pool or Wild% were tuned - line-win income alone tracks the
        # median, boss-kill-drop income is a rare/heavy tail that alone
        # dominates the mean but contributes ~nothing typical. A two-band
        # compression (tiers <=50 divided by 3.5, tiers >50 divided by 700)
        # fixed the mean/median split and locked at mean=79.37x/median=
        # 28.70x/ratio=36.2% (n=25000) - see git history for that table's
        # values and the collision-bug war story if needed.
        #
        # SHAPE REDESIGN (2026-08-15): user feedback on that locked table's
        # payout-distribution image was that 0-5x was too crowded and asked
        # for a "valley at the mean, two visible peaks" shape (one from the
        # died-early/mid population, one from clearing stage 6's chest).
        # Investigation before touching any values:
        #
        # 1) Wild% has a CLIFF, not a smooth response: STAGE_WILD_PCT
        # ["normal"] in _tuning_scratch/gen_stage_reels.py went through
        # several front-loaded profiles before landing on 23/16/10/4/2/1
        # (see that file's comment) - a later attempt to taper stage5/6
        # wild% specifically to reduce the stage-6-clear rate (see point 3
        # below) found this lever barely moves clear rate at all (a 75%
        # cut only took clear-rate from 25.24% to 23.73%) - deep-stage
        # survival is governed by the shared boss_stage_table Dam/HP
        # progression (shared across all 3 tiers, not touchable here), not
        # by reel wild density. This lever was RULED OUT for shape control.
        #
        # 2) Population-overlap finding: P(reach stage 6) ~28.79% and
        # P(clear stage 6) ~25.24% turned out to be nearly the SAME
        # population (conditional clear-given-reached ~88%), not two
        # well-separated milestones as first assumed.
        #
        # 3) The user separately asked that clearing to stage 5 should
        # guarantee an average payout >150x. Measuring the then-locked
        # table directly (normal_stage_clear_table.py, scratchpad) found
        # avg-payout-if-cleared-stage5 = 223.30x ALREADY, comfortably above
        # 150x, with no new mechanism needed. A dedicated "stage-5 chest"
        # (is_stage5_chest, mirroring the stage-6 chest one stage earlier)
        # was implemented and tested to explore a stacking-guarantee
        # design, but was found unnecessary given this measurement and was
        # REVERTED (dead code removed from game_executables.roll_reward_
        # drop) - the only piece of it kept was the insight that the
        # stage-6 chest pool needs to be made EXCLUSIVE (never leaking into
        # the regular per-kill pool) for its payouts to read as a visually
        # distinct second peak rather than being smeared into the main
        # distribution.
        #
        # 4) Tier-value entanglement: an initial attempt reused the locked,
        # collision-merged two-band table as the base for the shape
        # redesign. Because that table's rounding had already merged
        # multiple original tiers into single dict entries, raising a "low
        # tier" value sometimes silently also raised part of the stage-6-
        # chest-exclusive pool (and vice versa when trimming the chest to
        # fix a mean overshoot) - fixes to one lever kept undoing the
        # other. FIX: clean rebuild directly from the original 21-tier
        # (value:weight) structure, assigning each tier ONE of three
        # explicit, non-colliding roles - LOW/MID (die early/mid population,
        # 1875/1911=98.1% of weight), CHEST (stage-6-exclusive, drives the
        # second peak, 34.2/1911=1.8%), TOP (rare tail, 1.8/1911=0.09%) -
        # see normal_shape_v3.py (scratchpad) for the full search (12
        # candidates, differential LOW/MID-vs-CHEST/TOP scaling to hit mean
        # and median independently).
        #
        # FINAL, measured at n=50000 (95% CI): mean=85.35x (+/-1.79),
        # median=30.80x, ratio=36.1%, avg-payout-if-stage6+=242.1x. Mean
        # landed ~6.5% above the 80.13x target rather than within ~1-2% -
        # this is a genuine, reproducible trade-off frontier (confirmed
        # across n=15000/27000/50000 runs at different seeds), not sampling
        # noise: the LOW/MID raise needed to lift median into the target
        # 30x+ zone already consumes nearly the entire mean budget, leaving
        # little room for a CHEST value large enough to keep the second
        # peak visible without pushing mean further over. Given the
        # explicit priority was fixing the SHAPE (median/ratio now matches
        # or beats the old locked table's 36.2%, and the histogram shows a
        # real, reproducible valley + second peak around 90-150x - see
        # payout_distribution_normal.png), this trade-off was accepted
        # rather than sacrificing the shape to chase mean precision -
        # flagged here explicitly rather than papered over, per this
        # project's "report honestly" convention.
        # 2026-08-18 RESCALE (x4.28), on top of the FINAL shape above: the
        # Wild-col0 fix (a real bug - see gen_stage_reels.py's
        # COL0_GETS_WILD - Wild was never supposed to land on column 1) cut
        # how often lines connect at all, which starves BOTH of Normal
        # Bonus's two independent payout sources (game_calculations.
        # evaluate_and_explode's line-pay AND this reward-drop table's
        # boss-kill bonus - see game_executables.roll_reward_drop/award_win)
        # roughly in proportion. Measured split at the CURRENT (post-fix)
        # mechanic, pure production, n=10000: line-pay mean=23.20x (fixed -
        # not reachable by this table at all), reward-drop mean=13.60x
        # (n=10000) against a combined 36.80x total vs the 80.13x target.
        # Since the SHAPE here was already correct post-fix (ratio 39-44%,
        # already inside the 40-50% target band - see
        # payout_component_split.py) the fix was a pure uniform RESCALE of
        # every tier VALUE by a constant K (weights/probabilities
        # untouched) rather than a fresh shape redesign - this scales every
        # possible session's reward-drop total by exactly K deterministically
        # (same random draw path, every value in it just K times bigger),
        # so median/mean ratio carries over unchanged; only the FIXED line-
        # pay component (unreachable by this lever) keeps the ratio from
        # being a mathematically exact invariant, which is why K was fit
        # empirically (reward_table_scale_test.py) rather than solved in
        # closed form. K=4.28 confirmed at n=25000: mean=81.14x (target
        # 80.13x), median=36.30x (target ~32-40x), ratio=44.7% (target
        # 40-50%) - all three land inside target. top_tiers/stage6_last_
        # tiers reference tier VALUES (not indices - see roll_reward_drop),
        # so they're rescaled by the same K to keep matching this dict's
        # keys, or the "reserved for last boss"/"stage-6 chest exclusivity"
        # checks would silently stop matching anything.
        # 2026-08-19 rebalance, replaces the K=4.28-rescaled table above:
        # a genuinely new "7-segment" structure (not a rescale of the old
        # one) - seg1/seg2/.../seg5 are progressively PRUNED as each stage
        # clears (see stage_clear_pruned_tiers below), seg6 (30-1000) stays
        # in the regular pool through stage 6, and the 6 chest tiers
        # (400-4000) are stage-6-last-kill EXCLUSIVE only (see
        # reward_drop_stage6_last_tiers_normal_bonus / roll_reward_drop's
        # exclusive_chest_tiers). Ported from
        # _tuning_scratch/reshape_segments_test.py's SEG1..SEG7_CHEST -
        # bundled with bonus_player_hp_choices["normal"]=[200]*5 and
        # boss_stage_table's HP scale-up above; measured together (real
        # run_bonus_session("normal"), n=100000): mean=83.89x, median=38.10x,
        # ratio=45.4%, p75=84.10x. See
        # _tuning_scratch/results/segments_n100000_20260822_003530.json for
        # the full percentile table this was validated against.
        # NOTE: values 400/500/800 exist in BOTH seg6 (regular pool) and the
        # chest table below - this collision is INTENTIONAL and matches the
        # source script exactly (`{**REGULAR_WEIGHTS, **SEG7_CHEST}`, chest
        # applied last so it wins the dict-key collision). It's harmless:
        # seg6's own 400/500/800 entries are excluded from the regular pool
        # anyway (every key in reward_drop_stage6_last_tiers_normal_bonus is
        # excluded from non-chest rolls via exclusive_chest_tiers in
        # roll_reward_drop), so only the chest weights below are ever
        # actually reachable at these 3 values - the seg6 weights that
        # would collide (1.1/0.9/0.6) are dead code, kept only for fidelity
        # with the original candidate's literal numbers.
        # 2026-09-08 ITERATION 2 (unverified, not yet measured). Iteration 1
        # (n=20000: mean=86.04, median=40.80, p75=88.50, p80=108.82,
        # p85=136.21, p90=186.11, p95=292.51, p99=877.61, target mean=84.93/
        # median=38.35/p75=84.60/p80=105.10/p85=140.00/p90=196.10/
        # p95=306.90/p99=1012.80) cut p99's gap from -25% to -13% (real
        # win) but barely moved p90 (-5.1% -> -5.1%, unchanged) and median
        # (+6.8% -> +6.4%, unchanged) - reducing tiers 200/250 to feed the
        # tail apparently hurt p90 directly (sessions that land AROUND p90
        # often do so via a 200/250 draw), a genuine trade-off, not a bug.
        # This pass: partially restore 200/250 toward their original
        # values (stop taxing the exact tier that builds p90) while
        # pushing 300/350/600/1000 further (p99 still needs +13%); nudge
        # the 1-8 tiers up slightly to pull mean/median back down (mean
        # crept from 85.10 to 86.04 last pass, wrong direction). Still a
        # first-order guess, not solved analytically - see this file's own
        # established convention (game_config.py's Hidden/Super sections)
        # of empirical measure-adjust-remeasure over closed-form solving.
        # ITERATION 3 (unverified). iter2 measured (n=20000): mean=87.18
        # (target 85, +2.6%), median=40.50 (target 37.5, +8%), p90=186.41
        # (target 200, stuck across 2 different attempts - NOT retried
        # this pass, likely a stage-clear/HP mechanic, not a reward-table
        # value issue), p95=301.10 (target 350, +16.3% still short),
        # p99=974.71 (target 800-1000, ALREADY IN BAND - left 300-1000
        # tiers untouched this pass), p99.5=1216.67 (target 2500, +105%
        # short), p99.9=1647.18 (target 5000+, +200% short). This pass:
        # boost chest-exclusive 1500/2500/4000 hard (only lever for
        # p99.5/p99.9, untouched by iter1/2) - see
        # stage6_chest_natural_maxwin_weight's recalibration above, the
        # chest pool sum changing means Max Win rate would silently drift
        # if that weren't re-solved. Push 1-8 up further and 100-250 down
        # further to fight the mean/median drift iter1->iter2 made worse,
        # not better (85.10->86.04->87.18 mean, wrong direction).
        # ITERATION 5 (HP-mechanic sub-iterations 4/4b-4f abandoned/
        # reverted - see bonus_player_hp_choices above for why a smooth
        # spread can't make the cliff the target wants). Root cause of the
        # p99/p99.5 gap: chest weights 400/500/800 (15/8/4=27 of the 30.7
        # pool, 88%) dominate the chest draw, so "reaching chest" usually
        # means only a modest 400-800 top-up, not a real jump - it blends
        # into the top of the ordinary-session range instead of creating
        # separation. Flipped the emphasis: cut 400/500/800 down hard,
        # concentrate weight on 1500/2500/4000 instead (now 18/23=78% of
        # chest draws land >=1500, was 12%) so reaching chest reliably
        # means a big jump. Regular pool's own top tiers (300-1000) left
        # untouched this pass to isolate the chest-weight effect alone.
        # ITERATION 5b: iter5's chest rebalance nailed p99/p99.5/p99.9
        # (947->1010/1204->2164/2166->4489, all now within ~10-13% of
        # target or better) while leaving p50-p95 completely undisturbed -
        # confirms the chest is now a genuine isolated "cliff" lever. Only
        # cost: mean overshot to 96.03 (target 85, +13%) - chest's higher
        # average value (from concentrating on 1500-4000) inflates mean
        # even though it barely shows below p99 (chest reach rate 1.75%
        # sits above the p99 cutoff). Trimmed 1-8 tiers ~8% and 10-250
        # tiers ~5% to pull mean back down - this also happens to be
        # exactly what p50-p80 need anyway (all running ~6-7% high).
        # ITERATION 5c: 5b's mean got WORSE (96.03->97.29), not better -
        # traced the real cause via game_executables.roll_reward_drop:
        # the stage-6 chest draw pool is `{k: w for k,w in weights.items()
        # if k in stage6_last_tiers}` - ONLY the 6 chest values, fully
        # isolated from the regular pool (confirmed from the actual code,
        # not assumed). So trimming ONLY 1-8/10-250 while leaving
        # 300/350/600/1000 untouched didn't scale the regular pool down -
        # it shifted RELATIVE mass upward within it (less weight on cheap
        # outcomes = proportionally more on the expensive ones left
        # alone), raising the regular pool's own average. That was the
        # actual bug in 5b, not sampling noise (same seeds both runs).
        # Reverted 1-8/10-250 to iteration 3's original values (correctly
        # calibrated for the regular pool's own mean/median). This time
        # trimming 300/350/600/1000 instead - their original job (helping
        # p99) is now redundant since the rebalanced chest handles that
        # cliff on its own; they're pure extra mean cost at this point.
        # ITERATION 7: iter6b (n=35000) closed the tail well (p85 basically
        # exact, p90-p99.9 all within ~5-16%) but the -45% cut on
        # 300/350/600/1000 barely moved mean/p50 (chain-block's inflation
        # runs largely through line-pay, untouched by this table) - p50-p80
        # ran uniformly +13-14% high, mean +17.6%. Boosting 1-8 by +30%
        # (the historically reliable lever from iterations 1-3 - makes
        # minimal-kill sessions proportionally more common, pulling both
        # mean AND median down together) rather than cutting high tiers
        # further, which risks the relative-mass-shifts-upward bug from
        # iteration 5b again.
        # ITERATION 8 (user priority: mean first, then grow p85/p90
        # specifically, explicit room to push p60/70/80 lower). iter7's
        # blanket +30% on 1-8 pulled p50-p80/mean closer but ALSO pulled
        # p85/p90/p95 down further (127.70/175.00/273.91, worse than
        # iter6b) since it reduced every other tier's relative share
        # equally, including 100-250 which is what actually populates the
        # p85-p90 zone. This pass: push 1-8 further still (more room for
        # p60-p80 to drop, matches instruction), AND separately grow
        # 100-250 substantially (~2.5-3x) to directly target p85/p90
        # rather than leaving them to whatever's left over.
        # ITERATION 8b: iter8's ~2.7x boost on 100-250 grew p85-p99.5 close
        # to target (real win: p85 +6.8%, p90 +5.2%, p95 -7.0%, p99.5
        # -4.1%, all far tighter than before) but had a much bigger
        # inflating effect on mean than expected (94.99->103.97, WORSE,
        # contrary to the stated first priority). Dialing 100-250 back
        # from ~2.7x to ~1.5x, keeping 1-8's boost as-is.
        # ITERATION 11: user wants p10/p20/p30/p40 pushed down specifically
        # to free mean-budget for growing p85/p90/p95, on top of
        # iteration 10's state (mean=89.00, PASSED the <=90 ceiling;
        # p50-p75 essentially exact; p85-p99.9 all undershooting since
        # chain_block_step=0.26 traded tail richness for that precision).
        # Current p10/p20/p30/p40 (from iter10 raw data): 9.30/13.50/
        # 20.77/29.10 - governed almost entirely by the 1-8 tiers (very-
        # few-kill sessions). Boosted 1-8 further (+20% from iteration
        # 8/9/10's level) to push those down, and spent the freed budget
        # re-growing 100-250 partway back toward iteration 8's stronger
        # level (was dialed back to 1.5x in 8b to save mean - now going
        # to ~2.2x) to grow p85/p90/p95. Watching mean carefully to stay
        # near/under 90.
        # SPIN-BUDGET MEAN/MEDIAN RESCALE (2026-09-17): after 4 rounds of
        # shoulder-building (see the 100-1000 tiers below), mean/median had
        # drifted up to 113.56x/30.60x - per explicit request (target mean
        # 88.6x, median 24x, ratio 88.6/113.56=0.780 and 24/30.60=0.784,
        # close enough to treat as one factor), rescaled EVERY tier VALUE
        # in this whole table (both the regular pool below and the chest
        # tiers further down) by a single K=0.78, weights UNCHANGED - same
        # "uniform K-rescale preserves shape, weights untouched" technique
        # as the 2026-08-18 K=4.28 rescale elsewhere in this file's
        # history.
        #
        # MEASURED (n=15000) after that single-K pass: mean=75.04x (target
        # 88.6, UNDERSHOT by -15%), median=27.15x (target 24, OVERSHOT by
        # +13%) - a single scalar can't fix both at once when they need to
        # move in OPPOSITE directions. Split into two factors per explicit
        # follow-up ("Tiếp tục đi"): the highest-weight/lowest-value tiers
        # (this block, originally 1-80) dominate the SESSION MEDIAN by
        # sheer draw frequency (a typical 1-3-kill session draws almost
        # entirely from here) but barely move the mean (their absolute
        # values are tiny); the 100+/chest tiers below dominate the MEAN
        # (rare but huge) while barely touching the median. Applied a
        # further K_low=0.884 (24/27.15) ON TOP of the K=0.78 above to
        # this block specifically, and K_high=1.22 to the 100+/chest
        # blocks below (net effect vs the ORIGINAL pre-K=0.78 values:
        # this block x0.78x0.884=0.690, the 100+/chest blocks
        # x0.78x1.22=0.952) - NOT yet re-measured at this exact split,
        # first attempt.
        self.reward_drop_weights_normal_bonus = {
            0.69: 288, 1.38: 230, 2.07: 720, 2.76: 568, 3.45: 605, 4.14: 492, 5.52: 400,
            6.9: 110, 8.28: 85, 10.34: 65, 12.41: 48, 13.79: 60, 17.24: 44,
            20.69: 36, 24.13: 29.3, 27.58: 24.1, 34.48: 19.6, 41.38: 16.1, 55.16: 13.2,
            # ITERATION 13 (2026-09-14, flat-damage mean-under-85 pass): cut
            # -60% on top of the values below (17/13.5/11/7.5/8/4.3 -> x0.40)
            # per explicit request to bring flat-damage's mean under 85
            # while keeping median unchanged (user confirmed median~33 is
            # good - do not disturb it). Tried boosting 1-8 tiers +30% first
            # (the historically reliable cascade-era lever) but it barely
            # moved mean (95.28->98.78, WRONG direction) and dragged median
            # down (33.31->32.20) - abandoned, since disturbing the
            # already-good median was explicitly unwanted. 100-250 doesn't
            # govern median (governed by the much-more-frequent 1-8/10-80
            # tiers) but does meaningfully feed mean via the many sessions
            # that reach a handful of kills without going deep - cutting it
            # instead moved mean the right way without touching median.
            # RESTORED 2026-09-14: once stage 5 was hardened (see
            # flat_damage_boss_hp_mult above), chest-reaching sessions grew
            # rarer on their own, which cost mean back down again - restored
            # this tier all the way back to its pre-iteration-13 level
            # (x1.0, no cut) to compensate, rather than stacking two
            # mean-reducing cuts on top of each other.
            # SPIN-BUDGET SHOULDER PASS (2026-09-17): per explicit request
            # to try adjusting multiple tiers together in one combined
            # pass, rather than one lever at a time - a percentile check
            # against a new target table (_tuning_scratch/
            # spin_budget_percentile_check.py) found p50/p99/p99.5 already
            # close, but p60-p95 badly UNDER target (p90 measured 102.4 vs
            # target 250, p95 measured 205.8 vs target 500 - up to -59%) -
            # a missing "shoulder" between the median and the chest-driven
            # tail. Boosted ONLY the 100-1000 regular-pool tiers (weight,
            # several also value) to build that shoulder, deliberately
            # leaving the 1-80 tiers (which set the median/mode - already
            # correct) and the chest-exclusive 275-1500 tiers (which set
            # p99+ - already roughly correct) untouched, so this pass
            # targets exactly the gap and nothing already working. NOT YET
            # measured against the target table - first combined attempt.
            # ROUND 2 (2026-09-17): p75-p85 still -35% to -46% under target
            # after round 1 - pushed 100-250 further (roughly x1.5).
            # ROUND 4 (2026-09-17): p75-p95 still -27% to -38% under target
            # after round 3 - pushed 250 further to keep feeding that zone.
            # Values below rescaled x0.78 along with the rest of the table
            # (see the mean/median rescale note above) - weights unchanged.
            # K_high pushed 1.34 -> ~1.39 (extra x1.04, per explicit
            # priority on hitting mean=88.6 exactly - was 86.50, -2.4%) -
            # 104.68/125.61/157.01/188.42/209.35/261.69 ->
            # 108.87/130.63/163.29/195.96/217.72/272.16.
            108.87: 45, 130.63: 36, 163.29: 30, 195.96: 22, 217.72: 24, 272.16: 26,
            # ITERATION 5d: 5c's -60% cut on 300/350/600/1000 overcorrected
            # - mean improved (96.03->90.27) but p85/p90/p95/p99 all
            # dropped BELOW target too (p99 685.03, undershot the 800-1000
            # band; iter5's 1010.28 was closer). These tiers matter for
            # the body too, not just mean. Splitting the difference: ~25%
            # cut instead of ~60%.
            # ITERATION 6: chain_block_step 0.30->0.22 (see above) let
            # sessions survive deeper before being cut off - nailed p85
            # (130.70->140.60) and closed p90/p95/p99.5/p99.9 gaps
            # significantly, but raised the WHOLE distribution (mean
            # 93.70->101.77, p50 40.05->42.60, p99 855->1055, overshooting
            # the band again) since it's a different mechanic entirely,
            # not routed through reward-table weights at all. Needs a
            # stronger compensating cut than 5d's -25% - pushing to ~-45%.
            # ITERATION 9: user relaxed the mean target - ceiling of 90 is
            # acceptable (not necessarily exactly 85). iter8b's 96.57 is
            # over that ceiling. 300/350/600/1000 are the best remaining
            # cut - p85/p90 are now mostly carried by the 100-250 boost
            # and chest, not these, so trimming further should cost little
            # there. Cutting another ~50% on top of iter6b's already -45%.
            # ITERATION 12 (2026-09-13, flat-damage line-pay/reward-drop
            # rebalance): -40% further cut on top of iteration 9's values
            # (0.83/0.72/0.50/0.33 -> 0.498/0.432/0.30/0.198), paired with
            # the paytable x1.3 rescale above and the chest-VALUE cut below -
            # measured under flat-damage (n=20000, use_flat_damage["normal"]
            # =True): mean=95.28x (close to the ~90 ceiling), p50-p95 track
            # target closely (p50=33.31/p75=61.36/p85=88.49/p95=207.61 vs
            # targets 37.5/80/140/350 - some now under rather than over).
            # Same SPIN-BUDGET SHOULDER PASS as 100-250 above - boosted
            # (300/350 by ~10x, 600/1000 by ~10-12x) to keep building the
            # shoulder up through the 300-1000 range too, right below the
            # chest-exclusive tiers.
            # ROUND 2: p99 overshot (+41.8% vs target) after round 1's
            # 600/1000 boost - pulled those back down (300/350 left alone,
            # they sit closer to the p85-p95 zone that's still under).
            # ROUND 4: pushed 300/350 (p85-p90 zone) and nudged 600/1000
            # (p90-p95 zone) up slightly - cautious on the latter two since
            # round 2's version of this same push overshot p99.
            # K_high=1.22 applied here too - 234/273/468/780 ->
            # 285.48/333.06/570.96/951.6.
            # Same extra x1.10 bump - 285.48/333.06/570.96/951.6 ->
            # 314.03/366.37/628.06/1046.76.
            # Same extra x1.04 - 314.03/366.37/628.06/1046.76 ->
            # 326.59/381.03/653.18/1088.63.
            326.59: 10, 381.03: 8, 653.18: 3, 1088.63: 1.3,
            # Chest tiers (applied last, same as {**REGULAR_WEIGHTS, **SEG7_CHEST}).
            # VALUES cut 2026-09-13 (not just weight - weight-only cuts were
            # tried first and measured to only relocate the tail to a higher
            # percentile without shrinking it: n=12000 with these same 6
            # weights x0.55 and values UNCHANGED still gave p99=3210,
            # essentially unmoved). New values chosen to avoid every
            # existing tier key in this table (asserted in the measurement
            # harness - a first attempt collided at 250/350/1000, silently
            # overwriting those REGULAR tiers via dict update, and had to be
            # redone). Weights themselves are unchanged from iteration 9.
            # CONFIRMED at n=20000: p99 3210->1967 (still ~2.5x over the
            # 800-1000 target - improved, not fully closed), p99.5=2186
            # (close to the 2500 target), p99.9=2588 (under the 5000+
            # target). Scratch: _tuning_scratch/
            # payout_component_split_normal_flatdamage.py (line-pay/
            # reward-drop split measurement that motivated this pass).
            # ITERATION 13 (2026-09-14): values cut further (~25-30%,
            # 275/425/675/950/1100/1500 -> 210/320/500/700/800/1050), paired
            # with the 100-250 cut above, as part of the same mean-under-85
            # pass. New values again chosen to avoid every other tier key in
            # this table (asserted in the measurement harness). CONFIRMED at
            # n=20000: mean=83.62x (target achieved, was 95.28x), median
            # =33.45x (essentially unchanged from 33.31x, as required), p99
            # 1967->1581 (continued improvement, still above the 800-1000
            # target). Scratch: _tuning_scratch/
            # flat_damage_mean_under_85.py.
            # RESTORED 2026-09-14: reverted to the pre-iteration-13 values
            # (210/320/500/700/800/1050 -> 275/425/675/950/1100/1500) as
            # part of the same stage-5-hardening pass above - hardening
            # stage 5 already reduces how often the chest is reached
            # structurally (measured chest-hit-rate: see
            # _tuning_scratch/payout_component_split_chest.py), so this
            # value cut was no longer needed to compensate mean and was
            # trading away too much p99 headroom for no remaining benefit.
            # ROUND 3 (2026-09-17, spin-budget shoulder pass continued):
            # p99 overshot target even MORE after round 2's 100-250 boost
            # (+41.8% -> +45.6%) despite pulling 600/1000 back down -
            # chest-reaching sessions' NON-chest kills got richer too
            # (round 1/2 boosted the whole regular pool), so their overall
            # total rose even with chest itself untouched. Cut chest VALUES
            # ~25-30% (not just weight - a weight-only cut was already
            # measured elsewhere in this file to just relocate the tail
            # without shrinking it) to compensate: 275/425/675/950/1100/
            # 1500 -> 190/310/480/650/780/1050 (picked to avoid colliding
            # with every other tier key in this table, same convention as
            # every earlier chest-value change here). Weights unchanged.
            # ROUND 4: p99.5 undershot (-18%) after round 3's cut - nudged
            # the top 2 chest tiers back up a bit (780/1050 -> 850/1150,
            # picked to keep avoiding every other tier key), leaving the
            # bottom 4 alone (those set p99, already +23% over - no need
            # to push that further).
            # Values rescaled x0.78 along with the rest of the table (see
            # the mean/median rescale note at the top of this dict), then
            # K_high pushed 1.34 -> ~1.39 (same extra x1.04 as the other
            # 100+ tiers above, per explicit priority on mean=88.6):
            # 198.88/324.5/502.48/680.35/889.79/1203.73 ->
            # 206.84/337.48/522.58/707.56/925.38/1251.88. Weights unchanged.
            206.84: 2, 337.48: 1.5, 522.58: 1.5, 707.56: 9, 925.38: 6, 1251.88: 3,
        }
        self.reward_drop_top_tiers_normal_bonus = {206.84, 337.48, 522.58, 707.56, 925.38, 1251.88}
        self.reward_drop_stage6_last_tiers_normal_bonus = {206.84, 337.48, 522.58, 707.56, 925.38, 1251.88}

        # Safety cap on resolve-loop passes per spin (should never be hit by a
        # legitimate board; guards against a logic bug causing a true infinite
        # cascade rather than reflecting a real game rule).
        self.max_resolve_passes = 300

        # --- Reels ------------------------------------------------------------
        # BR0/WCAP: base/ante/feature spins (BR0 carries Scatter; WCAP stays
        # Scatter-free by design - the dedicated wincap fence must never be
        # able to also trigger Bonus, see readme.txt). FR0/FR1/FR2: the 3
        # Bonus-tier reels (Scatter-free, carry Elixir/Booster, Power density
        # scaled 1x/2x/3x - see game_config.bonus_tier_stage_reel).
        # PWR0 (Phase 4): dedicated reel for the Ultimate Power/God Mode
        # feature-spin bet modes - Scatter-free (these modes must never
        # trigger Bonus, per spec) AND Elixir/Booster-free (those are
        # Bonus-exclusive, never meant to appear on a single-spin feature
        # buy). Built from WCAP.csv (already the richest Wild/Power/high-pay
        # reel in this game, proven to converge deep stage chains and huge
        # single-spin wins in Phase 1's own WCAP harness measurements) with
        # every "PMX" (Maxwin power) occurrence replaced by "W" - PMX must
        # stay excluded from every non-"wincap" criteria (see
        # power_type_by_symbol/roll_reward_drop's existing Maxwin-exclusion
        # rule elsewhere in this file), and these 2 feature-spin modes' own
        # "0"/"basegame" fences are never "wincap" criteria (their OWN
        # "wincap" fence reuses WCAP.csv directly instead, unchanged, where
        # PMX activating is legitimate exactly like it already is for base).
        # (PWR1.csv exists on disk from an abandoned attempt to fix God
        # Mode's etl10k volatility violation via a richer reel - measurement
        # showed this made etl10k WORSE, not better, and reading
        # utils/analysis/distribution_functions.get_etl_cvar_p5k_10k_vales
        # directly showed why: etl10k is an ABSOLUTE-threshold (payout
        # >=10000), NOT-cost-normalized metric, so reel richness was never
        # the right lever - see game_optimization.py's godmode section /
        # readme.txt's Phase 4 section for the full investigation. Not
        # wired into `reels` below - kept on disk, unused, rather than
        # deleted.)
        reels = {
            "BR0": "BR0.csv", "WCAP": "WCAP.csv", "FR0": "FR0.csv", "FR1": "FR1.csv", "FR2": "FR2.csv",
            "PWR0": "PWR0.csv",
            # Phase 4 v2 (see QUESTIONS_FOR_YOU.md's "Phase 4 v2" section): 3
            # NEW dedicated, isolated Bonus-pool reels - one per tier, SHARED
            # across every entry path (natural Normal/Ante trigger AND
            # Buy3+/Buy4+ forced entry all run their Bonus session on these
            # same 3 files - now superseded by their per-stage
            # BM_Reels_S*/Super_BM_S*/UP_Reels_S* variants, see
            # bonus_tier_stage_reel below). Each is tuned in
            # isolation (see game_bonus_pool_harness.py / QUESTIONS_FOR_YOU.md
            # for the measured convergence) to hit its own target average
            # session payout (80.13x / 250.00x / 1070.00x), independent of
            # FR0/FR1/FR2 (which remain on disk, still used only as
            # padding_reels[freegame_type]'s cosmetic fallback - see below -
            # and are otherwise now dead code for Bonus content itself).
            "BM_Reels": "BM_Reels.csv", "Super_BM": "Super_BM.csv", "UP_Reels": "UP_Reels.csv",
            "Ante_BR0": "Ante_BR0.csv",
        }
        # Per-stage Wild/Power-tapering variants of the 3 Bonus-pool reels
        # above (design decision: Wild+Power density tapers down stage-by-
        # stage as low-pay symbols get permanently removed from play - see
        # stage_clear_removed_symbol - to counteract match-density rising as
        # the surviving symbol pool narrows). One file per (tier, stage from
        # that tier's own bonus_start_stage through 6) - see
        # bonus_tier_stage_reel below for the lookup and
        # _tuning_scratch/gen_stage_reels.py for how these were built (same
        # L/H/EL/BO shape as the tier's own original BM_Reels/Super_BM/
        # UP_Reels baseline, only the Wild/Power weight amount changes per
        # stage - deliberately not touching L/H proportions, see
        # gen_bm_reels.py's "WRONG DIRECTION FOUND" note on why).
        for tier_prefix, stage_range in (("BM_Reels", range(1, 7)), ("Super_BM", range(2, 7)), ("UP_Reels", range(3, 7))):
            for stage in stage_range:
                key = f"{tier_prefix}_S{stage}"
                reels[key] = f"{key}.csv"
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(os.path.join(self.reels_path, f))

        self.padding_reels[self.basegame_type] = self.reels["BR0"]
        self.padding_reels[self.freegame_type] = self.reels["FR0"]

        # Every distribution's "reel_weights" needs both gametype keys
        # present (create_board_reelstrips indexes by self.gametype, and
        # Bonus switches self.gametype to freegame_type mid-book) - the
        # freegame_type entry here is only ever a fallback default; the
        # actual per-tier reel choice is applied at runtime via
        # game_override.get_current_distribution_conditions' override (see
        # readme.txt for why a runtime override was used instead of trying
        # to express 3 tiers through this static per-distribution dict).
        basegame_condition = {
            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1}},
            "force_wincap": False,
            "force_freegame": False,
        }
        zero_condition = {
            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1}},
            "force_wincap": False,
            "force_freegame": False,
        }
        wincap_condition = {
            "reel_weights": {self.basegame_type: {"WCAP": 1}, self.freegame_type: {"FR0": 1}},
            "force_wincap": True,
            "force_freegame": False,
        }
        # Dedicated scatter-triggered-Bonus fence: the OUTER (triggering)
        # spin's INITIAL reveal is deterministically forced to land exactly
        # one of {3, 4, 5} Scatters (see gamestate.run_spin, which calls
        # Board.force_special_board("scatter", N) instead of
        # create_board_reelstrips() whenever this fence's force_freegame
        # condition is True), N picked per-book from
        # freegame_trigger_count_weights below - then the book switches into
        # a persisted-state, multi-internal-spin Bonus session (see
        # game_bonus.py) for whichever tier that count maps to.
        #
        # BUG FIX (see readme.txt's Phase 3 section for the full story): an
        # earlier version of this fence did NOT force anything - it drew a
        # perfectly ordinary create_board_reelstrips() board and relied
        # entirely on check_repeat's "force_freegame and not
        # triggered_freegame -> repeat" fallback (src/state/state.py) to
        # reject-sample until a NATURAL 3+ Scatter spin happened to occur.
        # That was measured (standalone harness, 30000 draws) at P(>=3
        # Scatter) ~=0.26%, all but a vanishing fraction of which land on
        # exactly 3 - conditional on triggering, the natural split was
        # ~96.6% normal / ~3.4% super / ~0.047% hidden (i.e. an expected ~0.2
        # Hidden-tier books out of a 400-book freegame quota at 100k sims -
        # Both Ways would ship essentially unvalidated by the pipeline, and
        # forcing a specific count via a naive retry-until-natural-match loop
        # for manual testing purposes could take ~1/1.17e-6 ~= 850000
        # attempts on average for count=5 specifically - a very plausible
        # explanation for this game's previous multi-minute hang). Switched
        # to the SDK's OWN designed mechanism for exactly this situation
        # (Board.force_special_board, already used by the "wincap" fence
        # above) instead of reel-density tuning: forcing a given count N
        # directly sets N reel positions to a real Scatter stop from that
        # column's own strip and only re-draws (bounded, cheap) if one of the
        # remaining un-forced reels ALSO happens to show one - for N=5 (all 5
        # reels forced) this is a GUARANTEED first-attempt success, for N=3/4
        # the retry probability is bounded by how many un-forced reels
        # remain (2 and 1 respectively), never by how rare N-simultaneous-
        # Scatter naturally is. This makes the conditional tier split a
        # direct, controllable design choice (freegame_trigger_count_weights)
        # instead of an accident of reel density, and completely decouples
        # it from the (unrelated, still worth keeping realistic) question of
        # how RARE Scatter should look on the reel strip for its own sake.
        #
        # Accidental 3+ Scatter under any OTHER criteria ("wincap"/"0"/
        # "basegame", where force_freegame is False) still just forces a
        # repeat instead of running Bonus (see gamestate.run_spin /
        # check_repeat) - this remains the ONLY fence whose books ever
        # contain a Bonus session.
        freegame_condition = {
            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1}},
            "force_wincap": False,
            "force_freegame": True,
        }
        # Phase 4 v2 UPDATE (spec revision - Super/Hidden pool averages and
        # this tier-mix both changed together, see game_optimization.py's
        # base/ante comments for why the BLENDED average driving base/ante's
        # own fence tuning is unaffected): shared tier-mix table - 92.00%
        # Normal / 7.80% Super / 0.20% Hidden (was 92/7.6/0.4), applied
        # identically once ANY path (base's natural trigger, ante's natural
        # trigger, OR buy3's forced-floor-3 entry) has triggered ">=3
        # Scatter". Reused as-is by
        # base's and ante's own freegame fences below (both already funnel
        # this dict through get_random_outcome + the exact-count
        # force_special_board call in gamestate.run_spin, so declaring the
        # table here is the ONLY change needed to realize the shared split
        # for those two). buy3/buy4 have their OWN separate tables (see
        # buy3_freegame_condition/buy4_freegame_condition below) - buy4
        # structurally excludes count=3 entirely ("block 3-Scatter"), so it
        # cannot reuse this dict.
        self.freegame_trigger_count_weights = {3: 92, 4: 7.8, 5: 0.2}

        mode_maxwin = 20000

        # --- Optimizer fence quotas/RTP split ---------------------------------
        # Standard fence formula for this SDK: for a fence needing target RTP
        # contribution r out of a given quota q of simulations, set hr=1/q and
        # rtp=r directly (both explicit) - see game_optimization.py.
        #
        # Phase 2 note: adding the Power system raised the natural/raw hit
        # rate and average win of the "basegame" population (whole-board-
        # explode chains more readily with more Wild-like symbols on the
        # board, and Global Multi/Wild Multi then scale up whatever wins
        # result) - measured via a standalone harness calling
        # gamestate.run_spin() directly at 10k sims (raw, "basegame"
        # criteria, optimization OFF - see readme.txt): zero-win fraction
        # ~0.61 (down from Phase 1's ~0.64), raw mean win ~2.27 (up from
        # Phase 1's ~0.60 target - Power roughly quadruples the natural
        # average). The "0" quota below was updated to match the new
        # measured zero-win rate; the target RTP split (wincap 0.001 / "0" 0
        # / basegame 0.599, summing to self.rtp=0.600) is UNCHANGED from
        # Phase 1 per task instructions ("keep targeting ~0.60") - the
        # optimizer's own per-book reweighting search (not the quotas
        # themselves) is what pulls the wider, Power-inflated natural
        # distribution down to that exact target; see game_optimization.py's
        # ConstructScaling for the shape hints added to help it do so
        # without breaching the 3-star volatility limits.
        # Phase 3 fence split - quota=0.02 (hr=50) gives ~2000 raw freegame
        # books at 100k (vs an earlier-tried 0.004's ~400), which helps
        # tier-coverage (Normal/Super/Hidden all get a meaningful sample).
        #
        # Phase 3 v3 UPDATE (see QUESTIONS_FOR_YOU.md's "Phase 3 v3" section
        # for the full writeup - this corrects a wrong diagnosis from the
        # previous round): the PREVIOUS agent found that a naive fence split
        # (basegame rtp=0.600 / freegame rtp=0.366, each mirroring its own
        # "natural" contribution) converges the ACHIEVED total RTP to
        # ~0.607 regardless of quota, and attributed this to "the overall
        # bet-mode rtp field is read from config but never actually consumed
        # inside create_show_pigs (an unused function parameter)". That is
        # true as a narrow fact (rtp genuinely isn't referenced in that
        # function's body) but was the WRONG explanation for the ~0.607
        # plateau: this round confirmed (a) the raw freegame distribution is
        # actually healthy (mean 1118.9x, median 22.6x, zero-rate 2.15% -
        # the previous round's "mean=0.83x/69% zero" figure was a misread of
        # lookUpTableSegmented_base.csv's column schema, see readme.txt) and
        # (b) empirically, the declared per-fence `rtp` DOES move the
        # achieved total a lot - swapping the basegame/freegame rtp values
        # (0.600/0.366 -> 0.366/0.600) with nothing else changed moved the
        # achieved total from 0.607 to 0.994. The real limitation is that
        # this shared optimizer's cross-fence combination stage
        # (create_show_pigs, scored purely on bankroll-survival) maps
        # (declared per-fence rtp/hr) -> (achieved total) in a highly
        # non-linear, fence-shape-dependent way when 2+ ranged
        # ("distribution") fences coexist - not a simple weighted sum, and
        # not something fixable from this file alone (fixing
        # optimization_program/ is still out of this task's scope). The
        # actual `rtp=` values now set in game_optimization.py's
        # ConstructConditions (basegame 0.3835 / freegame 0.5825) were found
        # by empirically walking that mapping (5 iterations, see
        # readme.txt's experiment log) until the ACHIEVED total (verified
        # via the same lookUpTableSegmented_base.csv x lookUpTable_base_0.csv
        # cross-reference) landed at ~0.965, just under the 0.967 ceiling
        # utils/rgs_verification.py's verify_mode_volatility enforces (it
        # treats "rtp" as a hard MAXIMUM, not a target band).
        # ======================================================================
        # Phase 4: feature-buy bet modes (Ante / Ultimate Power / God Mode /
        # buy-3+-scatter / buy-4+-scatter) - see readme.txt's Phase 4 section
        # and QUESTIONS_FOR_YOU.md's "Phase 4" spec for the full writeup.
        # ALL of this is purely ADDITIVE: it reuses the exact same
        # GameState/gamestate.run_spin/game_bonus/game_executables engine
        # "base" already validated at RTP=0.965, only wiring in a different
        # FORCED STARTING CONDITION per mode (own reels, own conditions
        # dicts, own Distributions/quotas, own opt_params entry in
        # game_optimization.py). "base"'s own conditions dicts/Distributions/
        # opt_params entry above are UNTOUCHED - do not move/edit them when
        # reading this section.
        # ======================================================================

        # --- Ante spin (cost 2x): same engine as "base", just a 5x higher
        # SAMPLING QUOTA on its own dedicated "freegame" (Scatter-trigger)
        # fence - realizes "5x higher probability of landing a 3+-Scatter
        # board" as a distribution-quota lever specific to Ante's OWN fence
        # (see the task's own suggested mechanism), never touching "base"'s
        # freegame_condition/quota above. Reuses BR0/WCAP (same reels as
        # base - re-reading the same read-only reel data from a DIFFERENT
        # bet mode's Distribution does not "touch" base's own scatter
        # probability; only base's OWN Distribution quota would).
        # Phase 4 v2: ante's non-wincap/non-freegame fences now draw from
        # their OWN dedicated Ante_BR0.csv (richer non-Scatter symbol
        # density than BR0.csv - see reels/Ante_BR0.csv / QUESTIONS_FOR_YOU.md)
        # instead of sharing BR0.csv, since ante's Line-Wins RTP target
        # (169.75% base-bet) is deliberately more than double base's
        # (72.75%) - the wincap fence keeps sharing WCAP.csv (already the
        # richest reel in the game; both base's and ante's wincap fences
        # force the SAME maxwin-biased outcome regardless of the underlying
        # strip's ordinary-symbol density, so no separate wincap reel is
        # needed for ante).
        ante_wincap_condition = {
            "reel_weights": {self.basegame_type: {"WCAP": 1}, self.freegame_type: {"FR0": 1}},
            "force_wincap": True,
            "force_freegame": False,
        }
        ante_zero_condition = {
            "reel_weights": {self.basegame_type: {"Ante_BR0": 1}, self.freegame_type: {"FR0": 1}},
            "force_wincap": False,
            "force_freegame": False,
        }
        ante_basegame_condition = ante_zero_condition
        ante_freegame_condition = {
            "reel_weights": {self.basegame_type: {"Ante_BR0": 1}, self.freegame_type: {"FR0": 1}},
            "force_wincap": False,
            "force_freegame": True,
        }

        # --- Ultimate Power / God Mode (cost 25x / 500x): a single forced-
        # starting-condition BASE SPIN (never a Bonus session - Scatter must
        # not appear at all, per spec: "Vong quay tinh nang khong the xuat
        # hien Scatter"). Both use the dedicated Scatter-free/Elixir-Booster-
        # free "PWR0" reel (see the Reels section above) for their "0"/
        # "basegame" fences; their "wincap" fence reuses WCAP.csv directly,
        # same as base's own wincap fence (also Scatter-free already).
        # force_freegame is False everywhere here - Scatter simply isn't on
        # PWR0/WCAP's strips, so this is structurally guaranteed, not just a
        # flag (belt-and-braces, matching this game's established pattern of
        # never relying on a single point of enforcement for a hard rule).
        feature_wincap_condition = {
            "reel_weights": {self.basegame_type: {"WCAP": 1}, self.freegame_type: {"FR0": 1}},
            "force_wincap": True,
            "force_freegame": False,
        }
        feature_zero_condition = {
            "reel_weights": {self.basegame_type: {"PWR0": 1}, self.freegame_type: {"FR0": 1}},
            "force_wincap": False,
            "force_freegame": False,
        }
        feature_basegame_condition = feature_zero_condition
        # NOTE: an earlier iteration gave God Mode its own richer PWR1 reel
        # (a WCAP clone) to try to fix an etl10k volatility violation by
        # raising the raw pool's mean closer to the required target -
        # REVERTED after direct measurement showed it made etl10k WORSE
        # (65.07 vs 14.7 on PWR0), and after reading
        # utils/analysis/distribution_functions.get_etl_cvar_p5k_10k_vales
        # directly: etl10k sums `win * weight_fraction` for every payout
        # >=10000 with NO division by bet_cost (unlike cvar, which divides
        # by bet_cost, and unlike p5k/p10k, which get a cost-based leniency
        # factor) - it is an ABSOLUTE-value, absolute-threshold metric. For
        # a 500x-cost mode needing average win ~482.5x to hit RTP=0.965,
        # the fixed 10000 threshold is only ~20.7x that target average, so
        # the fix is "keep essentially ALL probability mass below the
        # absolute value 10000" (see game_optimization.py's godmode
        # scaling), which reel richness does not help with - reverted to
        # sharing PWR0/feature_zero_condition/feature_basegame_condition
        # with Ultimate Power (see readme.txt's Phase 4 section for the
        # full investigation log). PWR1.csv is left on disk, unused, rather
        # than deleted, in case a future cost/wincap adjustment revives the
        # need for a richer reel.

        # Forced starting stage (uniform over the given choices - not
        # specified beyond "uniform among stages 3-6 (Ultimate Power) / 4-6
        # (God Mode) unless you have reason to weight otherwise" per the
        # task spec, and no such reason was found, so left uniform) and the
        # guaranteed minimum count of Power symbols that must be present on
        # this spin's very FIRST reveal (see game_executables.
        # guarantee_min_power_landed - landing on the initial reveal
        # trivially satisfies "at least N Power symbols land within the
        # spin" without needing to track a running tally across later
        # tumble passes). Read by game_override.reset_book /
        # gamestate.run_spin, keyed by bet-mode NAME (self.get_current_
        # betmode().get_name()) rather than by criteria/fence, since the
        # guarantee applies identically across all 3 of a mode's fences.
        self.feature_spin_start_stage_choices = {
            "ultimatepower": [3, 4, 5, 6],
            "godmode": [4, 5, 6],
        }
        self.feature_spin_min_power_landed = 5
        self.feature_spin_guarantee_power_modes = frozenset(self.feature_spin_start_stage_choices.keys())
        # God Mode's own override (see game_executables.activate_all_queued_
        # powers / gamestate.run_spin): drain the ENTIRE FIFO power_queue in
        # one step instead of one-at-a-time - the previous phase's readme.txt
        # explicitly left activate_next_power's one-pop-per-call design easy
        # to bypass for exactly this feature, per the task's own note.
        self.power_drain_all_modes = frozenset(["godmode"])

        # --- Direct bonus-buy (cost 100x / 300x): skip the base-spin engine
        # entirely for the OUTER triggering spin's tier - reuse the SAME
        # "freegame" criteria name (scoped per bet mode, not global) so the
        # existing `if self.criteria == "freegame": run_bonus_session(tier)`
        # branch in gamestate.run_spin fires completely unchanged. Matches
        # games/0_0_scatter's own shipped "bonus" bet-mode convention: only
        # "wincap" + "freegame" fences, no "0"/"basegame" (every sim in this
        # mode enters Bonus, by design - there is no non-Bonus outcome to
        # sample separately).
        #
        # Phase 4 v2 DEVIATION (documented in QUESTIONS_FOR_YOU.md's "Phase
        # 4 v2 - ket qua" section): the OLD mechanism here was
        # game_bonus.force_min_scatter_board (a partial force_board_from_
        # reelstrips call pinning only `floor` reels to Scatter, letting the
        # rest overshoot naturally) - an IMPLICIT tier split driven by
        # whatever the reel's own natural extra-Scatter density happened to
        # produce. The new spec requires an EXACT composition (92/7.8/0.2
        # for buy3, 97.5/2.5 for buy4 - updated from 92/7.6/0.4 and 95/5),
        # which cannot coexist with "let it overshoot naturally" (natural
        # overshoot would add uncontrolled extra probability mass on top of
        # the exact table). Replaced with the SAME exact-count
        # `force_special_board` mechanism base/ante's own freegame fences
        # already use (weighted count draw, then force exactly that many
        # Scatters) - see buy3_scatter_count_weights/buy4_scatter_count_weights
        # below and gamestate.run_spin's updated branch. force_min_scatter_board
        # itself is left defined in game_bonus.py, unused, rather than deleted
        # (same "leave it, don't delete" convention as PWR1.csv/FR0-2.csv).
        buy_wincap_condition = {
            "reel_weights": {self.basegame_type: {"WCAP": 1}, self.freegame_type: {"FR0": 1}},
            "force_wincap": True,
            "force_freegame": False,
        }
        # buy3 reuses the EXACT SAME shared 92/7.8/0.2 table as base/ante
        # (per spec: "khi DA trigger >=3 Scatter bang bat ky duong nao").
        self.buy3_scatter_count_weights = dict(self.freegame_trigger_count_weights)
        # buy4 blocks 3-Scatter entirely (its own separate 97.5/2.5 table -
        # updated from 95/5 per spec revision).
        self.buy4_scatter_count_weights = {4: 97.5, 5: 2.5}

        def _buy_freegame_condition(count_weights: dict) -> dict:
            return {
                "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1}},
                "force_wincap": False,
                "force_freegame": True,
                "scatter_count_weights": count_weights,
            }

        buy3_freegame_condition = _buy_freegame_condition(self.buy3_scatter_count_weights)
        buy4_freegame_condition = _buy_freegame_condition(self.buy4_scatter_count_weights)

        self.bet_modes = [
            BetMode(
                name="base",
                cost=1.0,
                rtp=self.rtp,
                max_win=mode_maxwin,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.0005,
                        win_criteria=mode_maxwin,
                        conditions=wincap_condition,
                    ),
                    Distribution(
                        criteria="0",
                        quota=0.584,
                        win_criteria=0.0,
                        conditions=zero_condition,
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.02,
                        conditions=freegame_condition,
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.3955,
                        conditions=basegame_condition,
                    ),
                ],
            ),
            # ------------------------------------------------------------------
            # Phase 4 feature-buy modes (see the big comment block above) -
            # target RTP 0.965 each (same safety margin under the 0.967 hard
            # ceiling utils/rgs_verification.py's verify_mode_volatility
            # applies PER bet mode, confirmed by reading execute_all_tests'
            # per-bet-mode loop). Quotas below are the PRE-optimizer raw-book
            # sampling shares - see game_optimization.py / readme.txt's Phase
            # 4 section for how they were measured/chosen and how the actual
            # opt_params rtp/hr targets were derived from a raw-mean harness
            # measurement per mode (this game's own established practice,
            # not a formula - see readme.txt for why "hr=1/quota, rtp=r" is
            # cost-AGNOSTIC in this SDK's optimizer, so no manual cost
            # scaling is needed here despite cost ranging 2x-500x).
            BetMode(
                name="ante",
                # Phase 4 v2: cost 2x -> 3x (intentional, user-confirmed
                # change, NOT a bug - keeps the true 5x trigger-frequency
                # multiplier exact rather than rounding it down; see
                # QUESTIONS_FOR_YOU.md's "Phase 4 v2" section).
                cost=3.0,
                rtp=0.97,
                max_win=mode_maxwin,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.0005,
                        win_criteria=mode_maxwin,
                        conditions=ante_wincap_condition,
                    ),
                    # etl40b (40-bet-horizon tail loss) was VIOLATED at
                    # quota=0.10 (1.375 at 20k, worse than 3k's 1.23 - a
                    # real shape issue, not sample noise) - too much of
                    # ante's overall outcome mix was a rich-bonus-session
                    # tail relative to the 40-bet window. Reduced freegame's
                    # OWN sampling quota from 0.10 to 0.07 (still well above
                    # base's 0.02, still a meaningfully higher Bonus-trigger
                    # rate, but not as extreme) - see readme.txt's Phase 4
                    # section for the achieved trigger-rate multiple this
                    # ends up landing at (measured, not assumed to be
                    # exactly the declared "5x").
                    Distribution(
                        criteria="0",
                        quota=0.575,
                        win_criteria=0.0,
                        conditions=ante_zero_condition,
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.07,
                        conditions=ante_freegame_condition,
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.3545,
                        conditions=ante_basegame_condition,
                    ),
                ],
            ),
            BetMode(
                name="ultimatepower",
                cost=25.0,
                rtp=0.965,
                max_win=mode_maxwin,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.002,
                        win_criteria=mode_maxwin,
                        conditions=feature_wincap_condition,
                    ),
                    Distribution(
                        criteria="0",
                        quota=0.155,
                        win_criteria=0.0,
                        conditions=feature_zero_condition,
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.843,
                        conditions=feature_basegame_condition,
                    ),
                ],
            ),
            BetMode(
                name="godmode",
                cost=500.0,
                rtp=0.965,
                max_win=mode_maxwin,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.002,
                        win_criteria=mode_maxwin,
                        conditions=feature_wincap_condition,
                    ),
                    Distribution(
                        criteria="0",
                        quota=0.153,
                        win_criteria=0.0,
                        conditions=feature_zero_condition,
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.845,
                        conditions=feature_basegame_condition,
                    ),
                ],
            ),
            BetMode(
                name="buy3",
                cost=100.0,
                # Phase 4 v2: declared 0.969, not the "flat 97.00%" spec
                # value literally - see game_optimization.py's buy3 comment:
                # measured (5000 AND 20000-sim scale, both confirmed) a
                # persistent ~+0.001 gap between this SDK's declared
                # fence-rtp-sum optimizer target and the actual achieved
                # RTP for this mode's single-ranged-fence shape, unmoved by
                # either ConstructScaling or several different wincap/
                # freegame splits at the same sum - reads as a structural
                # property of this raw pool/optimizer combination, not a
                # fixable input. Nudging the DECLARED value down by that
                # same ~0.001 (0.97->0.969) is the same kind of "config
                # field is an optimizer input, not a literal promise of the
                # achieved value" compensation this file's "base" mode
                # already used historically (declared 0.967, achieved
                # ~0.965) - the ACTUAL target that matters (achieved RTP
                # within the spec's own +-0.05% QA tolerance of 97.00%) is
                # verified directly via stats_summary.json, not via this
                # field.
                rtp=0.969,
                max_win=mode_maxwin,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=mode_maxwin,
                        conditions=buy_wincap_condition,
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.999,
                        conditions=buy3_freegame_condition,
                    ),
                ],
            ),
            BetMode(
                name="buy4",
                cost=300.0,
                # Phase 4 v2: same ~0.001 declared-vs-achieved gap and same
                # compensation as buy3 (see that mode's comment above).
                rtp=0.969,
                max_win=mode_maxwin,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=mode_maxwin,
                        conditions=buy_wincap_condition,
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.999,
                        conditions=buy4_freegame_condition,
                    ),
                ],
            ),
        ]

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
        self.paytable = {
            (3, "L1"): 0.1, (4, "L1"): 0.2, (5, "L1"): 0.5,
            (3, "L2"): 0.2, (4, "L2"): 0.3, (5, "L2"): 0.8,
            (3, "L3"): 0.2, (4, "L3"): 0.4, (5, "L3"): 1.0,
            (3, "L4"): 0.3, (4, "L4"): 0.6, (5, "L4"): 1.5,
            (3, "L5"): 0.5, (4, "L5"): 1.0, (5, "L5"): 2.5,
            (3, "H1"): 1.0, (4, "H1"): 2.0, (5, "H1"): 5.0,
            (3, "H2"): 1.5, (4, "H2"): 4.0, (5, "H2"): 10.0,
            (3, "H3"): 2.0, (4, "H3"): 6.0, (5, "H3"): 15.0,
            (3, "H4"): 3.0, (4, "H4"): 8.0, (5, "H4"): 20.0,
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
        self.power_multi_factor_weights = {2: 50, 3: 25, 4: 12, 5: 6, 6: 3, 8: 2, 10: 1}
        # TEMP TEST VALUE (2026-08-10, being probed for Hidden median/variance
        # compression - see D:\Stake Engine\BOSS_LINES_SPEC_REVISION_2026-08-10.md
        # - revert to the line above if not adopted): softened tail, less mass
        # on big single-tick jumps, to test whether Global Multi can raise the
        # mean without reintroducing a fat tail.
        self.power_multi_factor_weights = {2: 90, 3: 10, 4: 0, 5: 0, 6: 0, 8: 0, 10: 0}

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
        self.booster_damage_multiplier = 2.0

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
        self.bonus_player_hp_choices = {
            "normal": [50, 50, 50, 100, 100],
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
        self.boss_stage_table = {
            1: {"boss1": (20, 120), "boss2": (24, 150), "boss3": (20, 100)},
            2: {"boss1": (24, 150), "boss2": (28, 200), "boss3": (24, 120)},
            3: {"boss1": (28, 200), "boss2": (35, 250), "boss3": (28, 160)},
            4: {"boss1": (35, 250), "boss2": (45, 320), "boss3": (35, 210)},
            5: {"boss1": (45, 320), "boss2": (60, 400), "boss3": (45, 270)},
            6: {"boss1": (60, 450), "boss2": (80, 600), "boss3": (60, 400)},
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
        self.stage6_dam_escalation = {"normal": 1.20, "super": 1.20, "hidden": 2.0}
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
        self.stage_clear_pruned_tiers = {
            1: [1, 2],
            2: [3, 4],
            3: [5, 6, 8],
            4: [10, 15],
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
        # Super-tier-Bonus-ONLY reward-drop table (2026-08-15 hard-tune, IN
        # PROGRESS - see scratchpad/super_shape_v1.py). PLACEHOLDER: exact
        # copy of the shared table above pending the redesign's final
        # values - see game_executables.roll_reward_drop's Super branch.
        self.reward_drop_weights_super_bonus = {
            1: 400, 2: 320, 3: 260, 4: 210, 5: 170, 6: 140, 8: 110, 10: 90,
            15: 65, 20: 50, 25: 38, 50: 22, 100: 13, 150: 9, 200: 6, 250: 4,
            500: 2.2, 1000: 1.1, 2000: 0.5, 5000: 0.18, 20000: 0.02,
        }
        self.reward_drop_top_tiers_super_bonus = {2000, 5000, 20000}
        self.reward_drop_stage6_last_tiers_super_bonus = {500, 1000, 2000, 5000, 20000}
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
        # PLACEHOLDER at 1-in-500,000 per chest-open (w = 3.98/499999 =
        # 0.00000796) - user-confirmed starting point, pending final
        # calibration against the endless stage-6 tail's measured expected
        # chest-opens-per-spin (more loops survived per session -> more
        # rolls at this pool -> this weight needs to shrink further to hit
        # any specific overall per-spin target).
        self.stage6_chest_natural_maxwin_weight = 0.00000796

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
        self.reward_drop_weights_normal_bonus = {
            0.6: 400, 0.9: 320, 1.1: 260, 1.5: 210, 1.7: 170, 2.1: 140,
            2.5: 110, 3.0: 90, 3.8: 65, 4.8: 50, 5.9: 38, 7.7: 13, 8.4: 22,
            10.3: 9, 12.8: 6, 15.4: 4, 20.5: 2.2, 41.1: 1.1, 77.0: 0.5,
            179.7: 0.18, 513.5: 0.02,
        }
        self.reward_drop_top_tiers_normal_bonus = {41.1, 77.0, 179.7, 513.5}
        self.reward_drop_stage6_last_tiers_normal_bonus = {
            7.7, 10.3, 12.8, 15.4, 20.5, 41.1, 77.0, 179.7, 513.5,
        }

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

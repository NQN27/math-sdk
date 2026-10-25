"""Boss Lines v3 configuration (Proposal_KichBan1_2026-10-06.md; paylines from Proposal_2026-10-06.docx).

Rule data that the proposal fixes (paytable, damage, HP, paylines, coin
values, chest rules, mode costs) is copied exactly. Every DISTRIBUTION weight
(chance of an event, how often a value is picked) is a placeholder for the
tuning phase. Every place where the proposal is ambiguous is a named flag
that points to its question number in QUESTIONS.md ("Q<n>").
"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode

ENDLESS = 6  # internal stage number of the Endless stage

# Cell priority ("thu tu o") from the proposal's section-1 diagram:
# rows top->bottom, columns left->right.
CELL_PRIORITY_ROWS = [
    [1, 2, 4, 7, 11, 16],
    [3, 5, 8, 12, 17, 21],
    [6, 9, 13, 18, 22, 25],
    [10, 14, 19, 23, 26, 28],
    [15, 20, 24, 27, 29, 30],
]

# 35 paylines decoded from the proposal's green-cell diagrams: row index per
# column, row 0 = top.
PAYLINES = {
    1: [0, 0, 0, 0, 0, 0],
    2: [1, 1, 1, 1, 1, 1],
    3: [2, 2, 2, 2, 2, 2],
    4: [3, 3, 3, 3, 3, 3],
    5: [4, 4, 4, 4, 4, 4],
    6: [0, 1, 0, 1, 0, 1],
    7: [1, 0, 1, 0, 1, 0],
    8: [1, 2, 1, 2, 1, 2],
    9: [2, 1, 2, 1, 2, 1],
    10: [2, 3, 2, 3, 2, 3],
    11: [3, 2, 3, 2, 3, 2],
    12: [3, 4, 3, 4, 3, 4],
    13: [4, 3, 4, 3, 4, 3],
    14: [0, 1, 2, 2, 1, 0],
    15: [2, 1, 0, 0, 1, 2],
    16: [1, 2, 3, 3, 2, 1],
    17: [3, 2, 1, 1, 2, 3],
    18: [2, 3, 4, 4, 3, 2],
    19: [4, 3, 2, 2, 3, 4],
    20: [0, 0, 1, 1, 0, 0],
    21: [1, 1, 0, 0, 1, 1],
    22: [1, 1, 2, 2, 1, 1],
    23: [2, 2, 1, 1, 2, 2],
    24: [2, 2, 3, 3, 2, 2],
    25: [3, 3, 2, 2, 3, 3],
    26: [3, 3, 4, 4, 3, 3],
    27: [4, 4, 3, 3, 4, 4],
    28: [0, 1, 1, 1, 1, 0],
    29: [1, 0, 0, 0, 0, 1],
    30: [1, 2, 2, 2, 2, 1],
    31: [2, 1, 1, 1, 1, 2],
    32: [2, 3, 3, 3, 3, 2],
    33: [3, 2, 2, 2, 2, 3],
    34: [3, 4, 4, 4, 4, 3],
    35: [4, 3, 3, 3, 3, 4],
}


class GameConfig(Config):
    """Singleton game configuration."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "0_0_boss_lines_v3"
        self.provider_number = 0
        self.game_name = "Boss Lines"
        self.working_name = "Boss Lines v3 (Proposal 2026-10-06)"
        self.wincap = 25000.0
        self.win_type = "lines"
        self.rtp = 0.967  # designer target 2026-10-07: 96.7% for every bet mode
        self.construct_paths()

        # ---- Board ------------------------------------------------------------
        self.num_reels = 6
        self.num_rows = [5] * self.num_reels
        self.include_padding = True
        self.cell_priority = {
            (c, r): CELL_PRIORITY_ROWS[r][c] for r in range(5) for c in range(6)
        }
        self.cells_by_priority = sorted(self.cell_priority, key=self.cell_priority.get)
        self.paylines = dict(PAYLINES)

        # ---- Symbols ----------------------------------------------------------
        self.low_symbols = ["L1", "L2", "L3", "L4"]
        self.high_symbols = ["H1", "H2", "H3", "H4", "H5"]
        self.basic_symbols = self.low_symbols + self.high_symbols
        self.weapon_symbols = ["AR", "BM", "SW", "LT"]  # Arrow, Bomb, Sword, Lightning
        self.treasure_symbols = ["TC", "TM", "TV", "TS", "TG"]  # Coin, Magnet, Clover/Golden, Star, Global
        self.special_symbols = {
            "wild": ["W"],
            "scatter": ["SC"],
            "weapon": list(self.weapon_symbols),
            "treasure": list(self.treasure_symbols),
        }
        self.max_scatters_on_board = 5  # max 1 per column, column 6 blocked if 1-5 all have one

        # ---- Paytable (fixed by the proposal - section 7: do not edit) --------
        pays = {
            "L1": (0.1, 0.3, 1, 2), "L2": (0.15, 0.45, 1.5, 3), "L3": (0.2, 0.6, 2, 4),
            "L4": (0.25, 0.75, 2.5, 5), "H1": (0.5, 1.25, 3.75, 7.5), "H2": (0.75, 1.75, 5, 10),
            "H3": (1, 2.25, 6.25, 12.5), "H4": (1.5, 3, 7.5, 15), "H5": (2, 4, 10, 20),
        }
        self.paytable = {(k, s): v for s, vals in pays.items() for k, v in zip((3, 4, 5, 6), vals)}
        self.paytable[(6, "W")] = 25
        # Damage per destroyed symbol (merged cells: L=1, H1-H4=2, H5+Wild=3).
        self.symbol_damage = {"L1": 1, "L2": 1, "L3": 1, "L4": 1,
                              "H1": 2, "H2": 2, "H3": 2, "H4": 2, "H5": 3, "W": 3}

        # ---- Stages (HP fixed by the proposal) --------------------------------
        self.stage_hp_range = {0: (25, 25), 1: (30, 40), 2: (35, 50), 3: (45, 65),
                               4: (65, 90), 5: (85, 120), ENDLESS: (350, 400)}
        self.hp_round = 5
        # Per-boss HP change added to the stage draw, {boss id: {stage: delta}} (designer 2026-10-22 trial:
        # boss3 over columns 5-6 takes the least line damage, e.g. {"boss3": {1: -5, 2: -5, 3: -5, 4: -10, 5: -10}}).
        self.boss_hp_offset = {}
        # Q9: later Endless bosses: previous HP + one of these.
        self.endless_hp_step_choices = list(range(0, 55, 5))
        # Q7: number of low symbols removed AT each stage (cumulative, by stage).
        self.stage_removed_lows = {0: 0, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, ENDLESS: 4}
        self.stage_min_chest = {0: "dong", 1: "dong", 2: "dong", 3: "bac", 4: "vang",
                                5: "kimcuong", ENDLESS: "kimcuong"}
        self.stage_min_coin = {0: 0.2, 1: 0.2, 2: 1, 3: 1, 4: 5, 5: 20, ENDLESS: 20}
        # Per-Bonus-tier replacements of stage_min_coin, e.g. {"super": {2: 0.2}} (designer 2026-10-17:
        # trial for Super, whose first clear lights ~all cells, so a 1x minimum puts every clear >= ~40x).
        # Empty = the proposal minimums above for every tier.
        self.tier_stage_min_coin = {}
        self.boss_zones = {"boss1": (0, 1), "boss2": (2, 3), "boss3": (4, 5)}
        self.endless_zone = {"endless": tuple(range(6))}

        # ---- Coins (values fixed; weights placeholder) -------------------------
        self.chest_order = ["dong", "bac", "vang", "kimcuong"]
        self.coin_tiers = {
            "dong": [0.2, 0.5, 1, 2, 3, 4],
            "bac": [5, 6, 8, 10, 12, 15],
            "vang": [20, 25, 30, 40, 50],
            "kimcuong": [100, 150, 200, 250, 500, 1000],
            "maxwin": [25000],
        }
        # Coin label by CURRENT value (after Global/Clover/Star changes it).
        self.coin_label_bounds = [(5, "dong"), (20, "bac"), (100, "vang"), (25000, "kimcuong")]
        self.coin_value_weights = {
            0.2: 30, 0.5: 26, 1: 22, 2: 16, 3: 12, 4: 10,
            5: 8, 6: 7, 8: 6, 10: 5, 12: 4, 15: 3,
            20: 2.5, 25: 2, 30: 1.6, 40: 1.2, 50: 1,
            100: 0.5, 150: 0.35, 200: 0.25, 250: 0.2, 500: 0.08, 1000: 0.03, 25000: 0.0004,
        }

        # ---- Chests ------------------------------------------------------------
        # Q16: chest tier at boss spawn = stage minimum + k steps, k drawn from:
        self.chest_tier_step_weights = [85, 12, 3]
        self.chest_upgrade_chance = 0.05  # once, may skip tiers
        self.chest_gift_count_weights = {
            "dong": {1: 60, 2: 30, 3: 10}, "bac": {2: 70, 3: 30},
            "vang": {3: 1}, "kimcuong": {3: 1},
        }
        # Bonus only (outside Bonus chests hold coins only). Section 7: the higher
        # the chest, the LOWER the chance a gift is a coin.
        self.chest_gift_power_chance = {"dong": 0.15, "bac": 0.25, "vang": 0.35, "kimcuong": 0.45}
        self.chest_power_overflow_to_coin = True  # Q18

        # ---- Wild events ---------------------------------------------------------
        self.wild_event_chance = 0.15
        self.wild_event_weights = {"multiplier": 50, "coin": 35, "power": 15}
        self.wild_mult_weights = {2: 40, 3: 25, 4: 15, 5: 12, 10: 8}
        self.wild_mult_combine = "mul"  # Q2 (answered 2026-10-07): 2x and 5x on one line -> 10x
        self.wild_coin_uses_global = True  # Q1
        # Wild coin event (designer 2026-10-14, Normal Bonus trial; OK for it to differ from Treasure coins):
        # minimum coin value, and an optional own value table (None = the Treasure coin table).
        # Both can be set per Bonus tier through tier_weights. Defaults keep the old behaviour.
        self.wild_coin_min_value = 0.0
        self.wild_coin_value_weights = None
        # Treasure Star value: optional own weights over the (fixed) coin values; None = the coin table.
        # Per Bonus tier through tier_weights (tuning only, 2026-10-17: Super spread). Values below the
        # stage minimum are dropped; if none is left the coin table is used.
        self.star_value_weights = None

        # ---- Powers --------------------------------------------------------------
        self.power_names = ["enhance", "upgrade", "transform", "replace", "destroy"]
        self.power_pick_weights = {"enhance": 30, "upgrade": 20, "transform": 25, "replace": 15, "destroy": 10}
        self.power_reserve_cap = 3
        self.enhance_factor_weights = {2: 30, 3: 22, 4: 16, 5: 12, 10: 8, 15: 5, 20: 3, 25: 2, 50: 1, 100: 0.5}
        self.upgrade_target_weights = {"H5": 1, "W": 1}
        self.transform_count_range = (2, 5)
        # Transform/Destroy/Bomb/Sword never touch Scatter outside Bonus (Q15, N1).
        self.destroy_deals_damage = True  # Q13 (answered: Destroy counts as destruction)

        # ---- Weapons -------------------------------------------------------------
        # Designer 2026-10-20: weapons have no damage factor any more (always 1); every tuning candidate since
        # b6 already used {1: 1}. Was {1: 30, 2: 20, 3: 14, 4: 10, 5: 8, 6: 6, 7: 4, 8: 3, 9: 3, 10: 2}.
        self.weapon_factor_weights = {1: 1}
        self.arrow_base = 3
        self.arrow_k_choices = [round(0.05 * i, 2) for i in range(1, 11)]
        # Designer 2026-10-21 (trial flags, set in the candidate overrides, defaults keep the old rules):
        # Bomb/Sword/Lightning also deal this damage from their own cell to the boss of its column.
        self.weapon_self_damage = 0
        # Last-hit chance multiplier when the damage step is an Arrow ("arrow" step).
        self.arrow_last_hit_mult = 1.0
        # Damage of a display-only Wild (wild_skin_chance) when its cell is destroyed: None = the real symbol's
        # damage (pure display), a number = that damage (designer: every Wild deals 3, shown or real).
        self.wild_skin_damage = None
        # A weapon's area (Bomb/Sword) never destroys another weapon: that weapon stays and fires in its turn
        # (designer 2026-10-21: one weapon firing must not remove another).
        self.weapons_spare_weapons = True
        # Feature (Heroic / Treasure hunt): event "featureBigWin" when the spin pays more than this x the Feature
        # cost (designer 2026-10-21: effect only above buy price + 10%). Display only.
        self.feature_big_win_ratio = 1.1
        self.arrow_endless_divisor = 3

        # ---- Last hit / boss drops ----------------------------------------------
        self.last_hit_base = 0.005
        self.last_hit_scale = 0.03
        self.last_hit_final_spin_mult = 2.0
        self.boss_drop_chance = 0.03  # Q11: per boss per damage step
        self.boss_drop_weights = {"wild": 60, "power": 40}

        # Hold and Spin: removed from every mode (designer 2026-10-07).

        # ---- Treasure --------------------------------------------------------------
        self.treasure_kind_weights = {"coin": 60, "magnet": 7, "clover": 8, "golden": 2, "star": 4,
                                      "global": 6, "scatter": 1}
        self.clover_factor_weights = {2: 40, 3: 25, 4: 15, 5: 10, 10: 7, 20: 3}
        self.golden_factor_weights = {2: 40, 3: 25, 4: 15, 5: 10, 10: 7, 20: 3}
        self.magnet_min_coins = 2  # a magnet only appears with >= 2 coins on the Treasure board (N4)
        self.global_factor_weights = {2: 30, 3: 22, 4: 15, 5: 11, 6: 8, 7: 6, 8: 4, 9: 2, 10: 2}
        self.clover_hits = ("coin", "magnet")  # Q20
        self.treasure_scatter_capped = True
        self.treasure_max_rounds = 60
        # Treasure symbol weight factors by round, {kind: [round 1, round 2, ...]} (last repeats); per tier via
        # tier_weights (designer 2026-10-22 trial for Treasure hunt: no early Clover, more Magnets). {} = off.
        self.treasure_round_kind_mult = {}
        # Activated Clover / Golden clover leave their cell empty for the next round (Proposal Treasure step 2),
        # instead of staying inactive (N10, 2026-10-07). Per tier via tier_weights (designer 2026-10-22: Treasure hunt).
        self.treasure_clover_vanishes = False
        self.treasure_hunt_min_coin = 1
        self.treasure_skips_scatter_cells = True  # Q28 (answered) / N7
        # Q23 trial (designer idea 2026-10-11, NOT approved yet): Bonus tiers listed here clear
        # the lit cells at the start of every free spin after the first, so a Treasure only uses
        # cells lit during the spin that cleared the stage. The Scatter cells that triggered the
        # Bonus are lit for the first spin only. Empty = Q23 as answered (lit for the whole Bonus).
        self.lit_reset_each_spin_tiers = ()
        # Bonus tiers whose lit cells all go dark after each Treasure (stage clear), event "litReset"
        # (designer 2026-10-23: Normal). () = lit cells accumulate over the whole Bonus.
        self.lit_reset_after_treasure_tiers = ()
        # Which cells light (designer 2026-10-20, NOT approved into config yet):
        #  "symbols": every destroyed copy of a connected symbol (basic symbols, not Wild) - as built so far;
        #  "lines":   only the cells of the winning lines' positions (Wilds included; not the other copies of the
        #             symbol, not the non-matching rest of a payline), plus activated special symbols: a weapon's
        #             own cell when it fires, a Scatter collected in a Bonus, and the triggering Scatters at Bonus
        #             entry. Cells destroyed by weapons, Destroy or any other mechanic never light.
        self.lit_rule = "symbols"
        # Trial (designer 2026-10-18, NOT approved yet; replaces a hard lit-cell cap): per Bonus tier (or "heroic")
        # {"free": n, "decay": d}. A connected cell that is not lit yet lights with chance
        # d ** max(0, lit + 1 - n), lit = cells already lit (the first n always light), so lighting gets gradually harder as the board fills.
        # Empty = every connected cell lights (Q23).
        self.lit_decay = {}
        # Steer connections onto already-lit cells instead of dropping lit cells (designer 2026-10-22, replaces
        # lit_decay): {tier or "heroic": {"free": n, "decay": d, "tries": k}}. A board / refill whose connections would
        # light new cells past `free` is kept with chance d ** (lit + new - free), else redrawn (up to k draws). {} = off.
        self.lit_steer = {}
        # Event chance of a Wild made by the Transform power, in a Bonus only (Heroic keeps 1.0); per tier via
        # tier_weights. Designer 2026-10-22: 0.05. None = same as any Wild (wild_event_chance).
        self.power_wild_event_chance = None
        self.epic_min_coin = 5  # N6: no Dong coins during Epic free spins
        self.epic_opening_treasure_stage = 2  # N5: Epic starts with a Treasure "as if stage 2 was cleared"
        # Per-Bonus-tier replacements for the weight tables above (coin_value_weights,
        # treasure_kind_weights, clover/golden/global_factor_weights), e.g.
        # {"epic": {"treasure_kind_weights": {...}}}; key "treasure_hunt" = Treasure hunt, key "heroic" = Heroic
        # feature spin (until it enters a Bonus). Tuning only; no rule change.
        self.tier_weights = {}
        self.win_levels = [(20, "nice"), (50, "big"), (100, "super"), (500, "mega"), (25000, "maxwin")]

        # ---- Bonus ------------------------------------------------------------------
        self.bonus_tiers = {
            "bonus": {"spins": 6, "start_stage": 1},
            "super": {"spins": 7, "start_stage": 2},
            "epic": {"spins": 8, "start_stage": 3},
        }
        self.scatter_to_tier = {3: "bonus", 4: "super", 5: "epic"}
        # Scatter-count mix (%) of a forced Bonus (designer table 2026-10-12, tuning/targets/mode_targets_2026-10-12.csv).
        self.tier_mix = {"buy3": {3: 97.5, 4: 2.4, 5: 0.1}, "buy4": {4: 97.5, 5: 2.5},
                         # Random Bonus (cost 400): one spin with guaranteed 3/4/5 Scatters (designer 2026-10-12)
                         "random_bonus": {3: 60, 4: 27, 5: 13}}
        # Natural trigger rate per spin of each tier in base / ante (same table).
        self.tier_trigger_rate = {"base": {"bonus": 1 / 350, "super": 1 / 2815, "epic": 1 / 14990},
                                  "ante": {"bonus": 1 / 70, "super": 1 / 563, "epic": 1 / 2998}}
        # Max Win (25,000x) rate per tier session, implied by the designer's Google Sheet curves (2026-10-14):
        # Total = sum(value * bucket width), the last bucket (to p100 = 25,000x) is the Max Win share.
        self.tier_maxwin_rate = {"bonus": 0.000108, "super": 0.000855, "epic": 0.01}
        # Feature (designer 2026-10-12): 50/50, Heroic 403x, Treasure hunt 564x (its own Bonus entries included).
        # Heroic pays 0 on 30% of spins (designer curve p1-p30 = 0). Max Win rates implied by the sheet (2026-10-14).
        self.feature_mean_targets = {"heroic": 403.0, "treasure_hunt": 564.0}
        self.feature_zero_share = {"heroic": 0.30, "treasure_hunt": 0.0}
        self.feature_maxwin_rates = {"heroic": 0.001945, "treasure_hunt": 0.00185}
        self.feature_maxwin_rate = 0.5 * 0.001945 + 0.5 * 0.00185
        # Treasure hunt spins that enter a Bonus (designer: Bonus 1.4% / Super 0.4% / Epic 0.1% of Treasure hunt
        # spins): {tier: (share of Treasure hunt spins, average book pay x bet incl. the Treasure hunt spin)}.
        # The average sits near the books' median so the optimizer can reach it. Epic is left free: a 10k
        # Feature run has only ~1 Epic book.
        self.feature_bonus_entry = {"bonus": (0.014, 260.0), "super": (0.004, 720.0)}
        # base/ante: tiers whose Max Win books get their own exact-rate fence (the others keep their Max Win books
        # inside the tier fence, so the tier mean incl. Max Win is exact and its Max Win rate is free).
        self.base_maxwin_fence_tiers = ("epic",)
        # Designer 2026-10-08: minimum total Bonus win per tier, topped up at Bonus end.
        self.bonus_min_total_win = {"epic": 600.0}
        # Weapons guaranteed on each free spin's opening board (designer 2026-10-07;
        # was 3 Wild-or-weapon for both, which drove Super to ~1068x vs 240x).
        self.bonus_min_weapons = {"super": 1, "epic": 2}
        # Weapons favour bosses with HP left (designer 2026-10-22), per Bonus tier: {tier: floor}. A weapon drawn in
        # column c is kept with chance floor + (1 - floor) x HP share left of that column's boss (dead: floor),
        # else redrawn; guaranteed weapons pick their cells with the same weights. {} = off.
        self.weapon_hp_bias = {}
        # Trial (designer 2026-10-21: fewer but stronger weapons): {tier: chance} that a free spin gets the full
        # guarantee above; otherwise it guarantees one weapon fewer. Empty = always the full guarantee.
        self.bonus_min_weapons_chance = {}
        # Which symbol fills a guaranteed slot (Heroic: any; Super/Epic: weapons only); placeholder.
        self.guarantee_symbol_weights = {"W": 70, "AR": 10, "BM": 8, "SW": 8, "LT": 4}
        self.heroic_min_wild_or_weapon = 5
        # Trial (designer 2026-10-20, NOT approved yet): a Heroic spin starts with a random line multiplier
        # {factor: weight} (2x-10x) that multiplies its line wins only, to raise the lines' share of Heroic pay
        # (~5% -> ~20%). Empty = off.
        self.heroic_line_mult_weights = {}
        # Trial (designer 2026-10-20, NOT approved yet): display-only Wilds. On a fresh board (opening board or
        # refill), each winning line shows one of its symbols as a Wild with this chance, only where a real
        # Wild there would give exactly the same line wins (no new or longer line). The cell keeps its real
        # symbol for every rule (damage, lighting, no Wild event), and the choice uses its own RNG, so the
        # math is unchanged. Event "wildSkin". 0 = off.
        self.wild_skin_chance = 0.0
        # Trial (designer 2026-10-20, NOT approved yet): share of Heroic spins that are BUILT as dead spins
        # (natural board without weapons + the guaranteed Wilds on random cells, redrawn until nothing connects),
        # so the designer's 30% 0x Heroic share comes from real dead boards, not from re-weighted natural ones.
        # 0 = off.
        self.heroic_dead_spin_chance = 0.0
        # tries of basic symbols per Wild placement when building a dead Heroic board. 1 = redraw the
        # Wild cells too every try (dead-board Wilds pile up in columns 4-6, since a left-side Wild almost
        # always connects); larger keeps the placement and redraws the symbols, so Wild columns look natural
        self.heroic_dead_symbol_tries = 1
        self.heroic_dead_wild_col_weights = []  # per column, e.g. [3, 3, 3, 1, 1, 1]; [] = uniform
        self.base_global_into_bonus = False  # Q25
        # Q27 (answered): placeholder 50/50; tune only inside [0.2, 0.8].
        # Heroic and Treasure hunt may have DIFFERENT means (designer 2026-10-07);
        # only p*mean_heroic + (1-p)*mean_treasure_hunt = 0.967*500 = 483.5x is fixed,
        # balanced through this chance p.
        self.feature_heroic_chance = 0.5
        self.feature_heroic_chance_range = (0.2, 0.8)
        self.max_actions_per_spin = 400  # safety cap on cycles of steps (1)-(8)
        # A 25,000x win should only come from the "wincap" fence. OFF until the
        # first tuning pass: with placeholder weights most Bonus rounds hit the
        # cap, so the other fences would repeat almost forever.
        self.reject_wincap_outside_wincap_fence = False

        # ---- Accepted tuning: candidate f17 (designer accepted 2026-10-25) --------------------------------
        # Source: tuning/overrides/f17.json (readable sheet: tuning/results/f17_config.md). These values replace the
        # defaults set above; reels come from gen_reels.REEL_SPECS (f17 specs written there).
        self.treasure_kind_weights = {'coin': 95, 'magnet': 0.4, 'clover': 2.483, 'golden': 0.04, 'star': 0.25, 'global': 0.15, 'scatter': 1}
        self.clover_factor_weights = {2: 70, 3: 15, 4: 8, 5: 4, 10: 2, 20: 1}
        self.golden_factor_weights = {2: 80, 3: 15, 4: 4, 5: 1}
        self.global_factor_weights = {2: 60, 3: 25, 4: 10, 5: 5}
        self.coin_value_weights = {0.2: 40,
                                   0.5: 30,
                                   1.0: 25,
                                   2.0: 8,
                                   3.0: 4,
                                   4.0: 2.5,
                                   5.0: 1.5,
                                   6.0: 1,
                                   8.0: 0.6,
                                   10.0: 0.4,
                                   12.0: 0.25,
                                   15.0: 0.15,
                                   20.0: 0.1,
                                   25.0: 0.03,
                                   30.0: 0.015,
                                   40.0: 0.007,
                                   50.0: 0.003,
                                   100.0: 0.0008,
                                   150.0: 0.0003,
                                   200.0: 0.00015,
                                   250.0: 0.0001,
                                   500.0: 3e-05,
                                   1000.0: 1e-05,
                                   25000.0: 2e-07}
        self.enhance_factor_weights = {2: 60, 3: 25, 4: 10, 5: 4, 10: 1}
        self.wild_mult_weights = {2: 70, 3: 20, 4: 7, 5: 3}
        self.weapon_factor_weights = {1: 1}
        self.last_hit_scale = 0.002
        self.boss_drop_chance = 0.002
        self.tier_weights = {'bonus': {'treasure_kind_weights': {'coin': 92,
                                                                 'magnet': 0.4,
                                                                 'clover': 2.413,
                                                                 'golden': 0.15,
                                                                 'star': 0.25,
                                                                 'global': 0.27,
                                                                 'scatter': 1},
                                       'wild_event_chance': 0.65,
                                       'wild_event_weights': {'multiplier': 30, 'coin': 30, 'power': 40},
                                       'coin_value_weights': {0.2: 160,
                                                              0.5: 4,
                                                              1.0: 1.5,
                                                              2.0: 0.3,
                                                              3.0: 0.18,
                                                              4.0: 0.12,
                                                              5.0: 0.2808,
                                                              6.0: 0.1872,
                                                              8.0: 0.1404,
                                                              10.0: 0.11232,
                                                              12.0: 0.08424,
                                                              15.0: 0.06552,
                                                              20.0: 0.184548,
                                                              25.0: 0.105456,
                                                              30.0: 0.06591,
                                                              40.0: 0.042182,
                                                              50.0: 0.026364,
                                                              100.0: 0.01268768,
                                                              150.0: 0.02114612,
                                                              200.0: 0.01268768,
                                                              250.0: 0.0065065,
                                                              500.0: 0.00225224,
                                                              1000.0: 0.00075074,
                                                              25000.0: 8e-06},
                                       'clover_factor_weights': {2: 70, 3: 15, 4: 8, 5: 4, 10: 2, 20: 1},
                                       'golden_factor_weights': {2: 50, 3: 30, 4: 15, 5: 5},
                                       'chest_gift_count_weights': {'dong': {1: 92, 2: 6, 3: 2},
                                                                    'bac': {2: 95, 3: 5},
                                                                    'vang': {3: 1},
                                                                    'kimcuong': {3: 1}},
                                       'enhance_factor_weights': {2: 60, 3: 25, 4: 10, 5: 4, 10: 1},
                                       'wild_mult_weights': {2: 40, 3: 40, 4: 20},
                                       'chest_tier_step_weights': [81, 11, 7.7, 0.3],
                                       'chest_upgrade_chance': 0.02,
                                       'global_factor_weights': {2: 60, 3: 30, 4: 10},
                                       'wild_coin_min_value': 1.0,
                                       'power_pick_weights': {'enhance': 33,
                                                              'upgrade': 27,
                                                              'transform': 22,
                                                              'replace': 11,
                                                              'destroy': 7}},
                             'epic': {'wild_event_chance': 1.0,
                                      'wild_event_weights': {'multiplier': 40, 'coin': 40, 'power': 20},
                                      'enhance_factor_weights': {5: 20, 10: 30, 15: 25, 20: 15, 25: 10},
                                      'wild_mult_weights': {2: 30, 3: 25, 4: 20, 5: 15, 10: 10},
                                      'chest_upgrade_chance': 0.005,
                                      'chest_tier_step_weights': [99, 0.8, 0.2],
                                      'clover_factor_weights': {2: 70, 3: 18, 4: 8, 5: 4},
                                      'golden_factor_weights': {2: 30, 3: 30, 4: 20, 5: 15, 10: 5},
                                      'global_factor_weights': {2: 30, 3: 30, 4: 20, 5: 15, 10: 5},
                                      'chest_gift_count_weights': {'dong': {1: 90, 2: 10},
                                                                   'bac': {2: 95, 3: 5},
                                                                   'vang': {2: 50, 3: 50},
                                                                   'kimcuong': {2: 1}},
                                      'chest_gift_power_chance': {'dong': 0.1, 'bac': 0.2, 'vang': 0.45, 'kimcuong': 0.6},
                                      'coin_value_weights': {0.2: 0,
                                                             0.5: 0,
                                                             1.0: 30,
                                                             2.0: 3,
                                                             3.0: 1.5,
                                                             4.0: 1,
                                                             5.0: 60,
                                                             6.0: 1.5,
                                                             8.0: 0.75,
                                                             10.0: 40,
                                                             12.0: 10,
                                                             15.0: 25,
                                                             20.0: 15,
                                                             25.0: 5,
                                                             30.0: 3,
                                                             40.0: 2,
                                                             50.0: 1.5,
                                                             100.0: 0.6,
                                                             150.0: 0.02,
                                                             200.0: 0.01,
                                                             250.0: 0.006,
                                                             500.0: 0.002,
                                                             1000.0: 0.0006,
                                                             25000.0: 0.013500000000000002},
                                      'treasure_kind_weights': {'coin': 98,
                                                                'magnet': 0.1,
                                                                'clover': 2.553,
                                                                'golden': 0.36,
                                                                'star': 0.7,
                                                                'global': 0.25,
                                                                'scatter': 1},
                                      'power_pick_weights': {'enhance': 1, 'upgrade': 0, 'transform': 0, 'replace': 0, 'destroy': 0},
                                      'star_value_weights': {10.0: 45, 20.0: 45, 50.0: 10}},
                             'super': {'treasure_kind_weights': {'coin': 92,
                                                                 'magnet': 0.65,
                                                                 'clover': 2.0,
                                                                 'golden': 0.4,
                                                                 'star': 2.5,
                                                                 'global': 0.3,
                                                                 'scatter': 1},
                                       'clover_factor_weights': {2: 60, 3: 25, 4: 15},
                                       'coin_value_weights': {0.2: 130,
                                                              0.5: 30,
                                                              1.0: 50,
                                                              2.0: 17.5,
                                                              3.0: 7.0,
                                                              5.0: 14.0,
                                                              6.0: 3.5,
                                                              8.0: 2.8,
                                                              10.0: 5.6,
                                                              12.0: 2.8,
                                                              15.0: 2.8,
                                                              20.0: 2.8,
                                                              25.0: 0.015,
                                                              30.0: 0.01,
                                                              40.0: 0.006,
                                                              50.0: 0.002,
                                                              100.0: 0.0011,
                                                              150.0: 0.00044000000000000007,
                                                              200.0: 0.00022000000000000003,
                                                              250.0: 0.00015400000000000003,
                                                              500.0: 4.4000000000000006e-05,
                                                              1000.0: 1.54e-05,
                                                              25000.0: 8e-06},
                                       'chest_gift_count_weights': {'dong': {1: 80, 2: 15, 3: 5},
                                                                    'bac': {2: 40, 3: 60},
                                                                    'vang': {2: 50, 3: 50},
                                                                    'kimcuong': {2: 1}},
                                       'chest_tier_step_weights': [95.75, 4, 0.25],
                                       'chest_upgrade_chance': 0.02,
                                       'global_factor_weights': {2: 45, 3: 30, 4: 15, 5: 10},
                                       'star_value_weights': {1.0: 50, 2.0: 45, 3.0: 5},
                                       'golden_factor_weights': {2: 45, 3: 30, 4: 15, 5: 10},
                                       'wild_event_weights': {'multiplier': 45, 'coin': 30, 'power': 25},
                                       'wild_event_chance': 0.6,
                                       'wild_coin_min_value': 5.0,
                                       'wild_mult_weights': {2: 35, 3: 35, 4: 20, 5: 10}},
                             'treasure_hunt': {'treasure_kind_weights': {'coin': 83,
                                                                         'magnet': 1.5,
                                                                         'clover': 2.218,
                                                                         'golden': 0.4,
                                                                         'star': 0.7,
                                                                         'global': 1.2,
                                                                         'scatter': 1.6},
                                               'coin_value_weights': {0.2: 40,
                                                                      0.5: 30,
                                                                      1.0: 150,
                                                                      2.0: 14,
                                                                      3.0: 9,
                                                                      4.0: 6,
                                                                      5.0: 4,
                                                                      6.0: 3,
                                                                      8.0: 2,
                                                                      10.0: 1.4,
                                                                      12.0: 1,
                                                                      15.0: 0.6,
                                                                      20.0: 0.4,
                                                                      25.0: 0.2,
                                                                      30.0: 0.12,
                                                                      40.0: 0.06,
                                                                      50.0: 0.03,
                                                                      100.0: 0.008,
                                                                      150.0: 0.003,
                                                                      200.0: 0.0015,
                                                                      250.0: 0.001,
                                                                      500.0: 0.0003,
                                                                      1000.0: 0.0001,
                                                                      25000.0: 0.004},
                                               'global_factor_weights': {2: 50, 3: 30, 5: 20},
                                               'golden_factor_weights': {2: 50, 3: 40, 5: 10},
                                               'star_value_weights': {5.0: 40, 10.0: 40, 20.0: 20},
                                               'treasure_round_kind_mult': {'clover': [0, 1.0],
                                                                            'golden': [0, 1.0],
                                                                            'scatter': [1, 0.4],
                                                                            'global': [1, 0.15]},
                                               'clover_factor_weights': {2: 75, 3: 20, 4: 5},
                                               'treasure_clover_vanishes': True},
                             'heroic': {'wild_mult_weights': {2: 45, 3: 30, 4: 15, 5: 8, 10: 2},
                                        'wild_event_weights': {'multiplier': 45, 'coin': 35, 'power': 20},
                                        'chest_gift_count_weights': {'dong': {1: 80, 2: 15, 3: 5},
                                                                     'bac': {2: 85, 3: 15},
                                                                     'vang': {3: 1},
                                                                     'kimcuong': {1: 75, 2: 17, 3: 8}},
                                        'treasure_kind_weights': {'coin': 98,
                                                                  'magnet': 0.2,
                                                                  'clover': 0.5,
                                                                  'golden': 0,
                                                                  'star': 0,
                                                                  'global': 1.5,
                                                                  'scatter': 0},
                                        'coin_value_weights': {0.2: 40,
                                                               0.5: 30,
                                                               1.0: 25,
                                                               2.0: 8,
                                                               3.0: 4,
                                                               4.0: 2.5,
                                                               5.0: 1.5,
                                                               6.0: 1,
                                                               8.0: 0.6,
                                                               10.0: 0.4,
                                                               12.0: 0.25,
                                                               15.0: 0.15,
                                                               20.0: 0.1,
                                                               25.0: 0.009,
                                                               30.0: 0.0045,
                                                               40.0: 0.0021,
                                                               50.0: 0.0009,
                                                               100.0: 0.00024,
                                                               150.0: 8.999999999999999e-05,
                                                               200.0: 4.4999999999999996e-05,
                                                               250.0: 3e-05,
                                                               500.0: 9e-06,
                                                               1000.0: 3e-06,
                                                               25000.0: 2e-07},
                                        'wild_coin_value_weights': {20.0: 45,
                                                                    25.0: 12,
                                                                    30.0: 12,
                                                                    40.0: 9,
                                                                    50.0: 9,
                                                                    75.0: 5,
                                                                    100.0: 4,
                                                                    150.0: 2,
                                                                    200.0: 1.2,
                                                                    250.0: 0.6,
                                                                    500.0: 0.5,
                                                                    1000.0: 0.15},
                                        'guarantee_symbol_weights': {'W': 1},
                                        'global_factor_weights': {2: 40, 3: 40, 5: 20}}}
        self.last_hit_base = 0.0
        self.feature_heroic_chance = 0.512
        self.lit_reset_each_spin_tiers = []
        self.tier_stage_min_coin = {'super': {2: 0.2}}
        self.lit_decay = {}
        self.heroic_line_mult_weights = {1: 45, 2: 20, 3: 15, 5: 12, 10: 8}
        self.heroic_dead_spin_chance = 0.3
        self.wild_skin_chance = 0.4
        self.lit_rule = 'lines'
        self.weapon_self_damage = 3
        self.arrow_last_hit_mult = 1.5
        self.wild_skin_damage = 3
        self.arrow_k_choices = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6]
        self.bonus_min_weapons = {'super': 1, 'epic': 1}
        self.bonus_min_weapons_chance = {'super': 0.62}
        self.heroic_dead_symbol_tries = 20
        self.heroic_dead_wild_col_weights = [3, 3, 3, 1, 1, 1]
        self.boss_hp_offset = {'boss3': {1: -5, 2: -5, 3: -5, 4: -10, 5: -10}}
        self.lit_steer = {}
        self.power_wild_event_chance = 0.05
        self.lit_reset_after_treasure_tiers = ['bonus']

        # ---- Reels ------------------------------------------------------------------
        reel_files = ["BR0", "ANTE", "HERO", "BON_S1", "BON_S2", "BON_S3", "BON_S4", "BON_S5", "BON_E",
                      "SUP_S2", "SUP_S3", "SUP_S4", "SUP_S5", "SUP_E", "EPI_S3", "EPI_S4", "EPI_S5", "EPI_E"]
        self.reels = {name: self.read_reels_csv(os.path.join(self.reels_path, f"{name}.csv")) for name in reel_files}
        self.bonus_stage_reel = {1: "BON_S1", 2: "BON_S2", 3: "BON_S3", 4: "BON_S4", 5: "BON_S5", ENDLESS: "BON_E"}
        # Super / Epic use their own stage reels (tuning only, 2026-10-08); Bonus uses bonus_stage_reel.
        self.tier_stage_reel = {
            "super": {2: "SUP_S2", 3: "SUP_S3", 4: "SUP_S4", 5: "SUP_S5", ENDLESS: "SUP_E"},
            "epic": {3: "EPI_S3", 4: "EPI_S4", 5: "EPI_S5", ENDLESS: "EPI_E"},
        }
        self.padding_reels[self.basegame_type] = self.reels["BR0"]
        self.padding_reels[self.freegame_type] = self.reels["BON_S1"]
        self.anticipation_triggers = {self.basegame_type: 2, self.freegame_type: 2}

        # ---- Bet modes ----------------------------------------------------------------
        def cond(base_reel, **extra):
            c = {"reel_weights": {self.basegame_type: {base_reel: 1}, self.freegame_type: {"BON_S1": 1}},
                 "force_wincap": False, "force_freegame": False}
            c.update(extra)
            return c

        maxwin = self.wincap
        # Scatter mix of the base/ante "freegame" BOOKS only: enough Super/Epic books for the optimizer's
        # tier fences, which then set the real trigger rates (tier_trigger_rate). Not a game rule.
        self.base_book_scatter_mix = {3: 60, 4: 25, 5: 15}
        self.bet_modes = []
        for name, cost, reel in (("base", 1.0, "BR0"), ("ante", 3.0, "ANTE")):
            self.bet_modes.append(BetMode(
                name=name, cost=cost, rtp=self.rtp, max_win=maxwin,
                auto_close_disabled=False, is_feature=True, is_buybonus=False,
                distributions=[
                    Distribution(criteria="wincap", quota=0.001, win_criteria=maxwin,
                                 conditions=cond(reel, force_wincap=True)),
                    Distribution(criteria="freegame", quota=0.1,
                                 conditions=cond(reel, force_freegame=True,
                                                 scatter_triggers=dict(self.base_book_scatter_mix))),
                    Distribution(criteria="0", quota=0.4, win_criteria=0.0, conditions=cond(reel)),
                    Distribution(criteria="basegame", quota=0.5, conditions=cond(reel)),
                ],
            ))
        self.bet_modes.append(BetMode(
            name="feature", cost=500.0, rtp=self.rtp, max_win=maxwin,
            auto_close_disabled=False, is_feature=False, is_buybonus=True,
            distributions=[
                Distribution(criteria="wincap", quota=0.001, win_criteria=maxwin,
                             conditions=cond("HERO", force_wincap=True)),
                Distribution(criteria="0", quota=0.1, win_criteria=0.0, conditions=cond("HERO")),
                Distribution(criteria="basegame", quota=0.899, conditions=cond("HERO")),
            ],
        ))
        # Tier means (designer table 2026-10-12): Bonus 91x, Super 245x, Epic 2045x. buy3 97.5/2.4/0.1 pays
        # 96.65x of 96.7x, buy4 97.5/2.5 290.0x of 290.1x, Random Bonus 60/27/13 386.6x of 386.8x.
        # Designer 2026-10-19: close that gap through the tier mix, not by adding it to every tier mean, so each
        # tier mean is exact: the Epic share grows by the gap / (2045 - lowest tier mean), taken from the lowest
        # tier (buy3 Epic 0.10256%, buy4 Epic 2.50556%, Random Bonus Epic 13.01%).
        self.tier_mean_targets = {"bonus": 91.0, "super": 245.0, "epic": 2045.0}
        for mode, cost in (("buy3", 100.0), ("buy4", 300.0), ("random_bonus", 400.0)):
            mix = self.tier_mix[mode]
            tot = sum(mix.values())
            mean = {n: self.tier_mean_targets[self.scatter_to_tier[n]] for n in mix}
            gap = self.rtp * cost - sum(w / tot * mean[n] for n, w in mix.items())
            low = min(mix)
            d = gap / (mean[5] - mean[low]) * tot
            mix[5] += d
            mix[low] -= d
        for name, cost, triggers in (("buy3", 100.0, self.tier_mix["buy3"]), ("buy4", 300.0, self.tier_mix["buy4"]),
                                      ("random_bonus", 400.0, self.tier_mix["random_bonus"])):
            self.bet_modes.append(BetMode(
                name=name, cost=cost, rtp=self.rtp, max_win=maxwin,
                auto_close_disabled=False, is_feature=False, is_buybonus=True,
                distributions=[
                    Distribution(criteria="wincap", quota=0.001, win_criteria=maxwin,
                                 conditions=cond("BR0", force_wincap=True, force_freegame=True,
                                                 scatter_triggers=triggers)),
                    Distribution(criteria="freegame", quota=0.999,
                                 conditions=cond("BR0", force_freegame=True, scatter_triggers=triggers)),
                ],
            ))

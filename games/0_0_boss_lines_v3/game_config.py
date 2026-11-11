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
        # How the stage HP draw leans inside its range, per Bonus tier (or "heroic"): {tier: t}, t in [-1, 1]; +1 = high HP
        # comes up most often, -1 = low HP (designer 2026-10-26: same HP rule for every tier, different odds). {} = uniform.
        self.tier_hp_tilt = {}
        # HP cut drawn per boss at stages 1-5, {cut: weight} (designer 2026-10-26: the cut is part of the odds, "no cut"
        # stays possible; same cut values for every tier, weights may differ per tier via tier_weights). {0: 1} = no cut.
        self.hp_cut_weights = {0: 1}
        # Odds of each allowed HP value per stage, {stage: {hp: weight}} (per tier via tier_weights; designer
        # 2026-11-02: no HP cut / boss offset, only how often each HP of the rule comes up). Values outside the stage's
        # stage_hp_range are dropped. Missing stage = uniform (or tier_hp_tilt).
        self.stage_hp_weights = {}
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
        # Treasure coin weights per Bonus tier and cleared stage, {tier: {stage: {coin: weight}}} (designer 2026-10-25:
        # pay each stage's Treasure its own amount, so more stages can be cleared at the same mean). Same coin values
        # as the proposal, only the weights differ. A missing tier / stage uses the tier's coin_value_weights.
        self.stage_coin_value_weights = {}
        # Chest tier odds per Bonus tier and stage, {tier: {stage: {chest: weight}}}; chests below stage_min_chest are
        # dropped. Missing = stage minimum + chest_tier_step_weights (designer 2026-10-27).
        self.stage_chest_weights = {}
        # How many of a stage's bosses get the stage minimum chest (3 = all, the proposal rule; 1 = one random boss,
        # designer 2026-10-27 option 2; 0 = none). The others draw from the lowest chest up.
        self.stage_min_chest_count = 3  # or {stage: n} (designer 2026-10-29: stage 5 / Endless all 3)
        # Chance that a weapon of the opening board on an unlit cell moves to a lit cell of its column (Bonus only,
        # per tier via tier_weights; designer 2026-10-28: fewer new lit cells). 0 = off.
        self.weapon_lit_bias = 0
        # Same for Wilds of the opening board (designer 2026-10-29). 0 = off.
        self.wild_lit_bias = 0
        # Multi Wild (designer 2026-10-29): {multiplier: weight} drawn when a Wild appears; replaces Wild events (no Wild
        # coin, no event roll). Per tier via tier_weights; {} = the old Wild event system.
        self.wild_multi_weights = {}
        # Multi Wild mode: chance that a connecting Wild drops a power (only if one has room).
        self.wild_power_drop_chance = 0.0
        # Tumble multi (designer 2026-10-30), replaces the old Global: no Global cells, nothing multiplied by the old
        # Global (Treasure, chests, Wild coins). Each connecting Wild multi (>= 2x) adds its value to the tumble multi;
        # boss multis (a chest gift) multiply it left to right; the spin's line pay x that multi is paid at spin end.
        self.tumble_multi = False
        # When the tumble multi resets in a Bonus (per tier via tier_weights): "spin" / "stage" / "bonus".
        self.tumble_reset_scope = "spin"
        # Chance a chest gift is a boss multi, by chest; boss multi values; the highest value each chest can give.
        self.chest_gift_multi_chance = {}
        self.chest_multi_weights = {2: 50, 3: 25, 4: 12, 5: 9, 10: 4}
        self.chest_multi_cap = {"dong": 3, "bac": 5, "vang": 10, "kimcuong": 10, "do": 10}
        # Chest powers act in the spin that opened the chest (designer 2026-10-30); the extra last-spin rule for a chest
        # power is then off. False = powers wait in reserve for the next spin.
        self.chest_power_immediate = False
        # Designer 2026-10-31. Chest names in events (internal ids stay dong/bac/vang): {} = the ids.
        self.chest_display_names = {}
        # Chest coins become money bags: value >= 1x from chest_bag_value_weights (per tier; {} = the tier's coin
        # table without 0.2x / 0.5x), not tied to the stage or the chest; named by value (bag_kinds).
        self.chest_bags = False
        self.chest_bag_value_weights = {}
        self.bag_kinds = [(4, "pinch"), (15, "small"), (50, "large"), (float("inf"), "chest")]
        # ---- Unified rules ("LUAT HOP NHAT" 1-7, designer 2026-11-02); every flag below is off by default ----------
        # chest_rule "v4": each boss's chest comes from stage_chest_sets (the stage's set shuffled over the bosses;
        # key "heroic" = the Heroic spin). Opening a chest first goes up one tier with chest_open_upgrade_chance[chest]
        # (at most once, never from the top chest), then gives ONE money bag from chest_tier_bags[chest], plus,
        # independently, a power (chest_gift_power_chance) and a chest multi (chest_gift_multi_chance, chest_multi_cap).
        self.chest_rule = "legacy"
        self.chest_order_v4 = ["dong", "bac", "vang", "do"]
        self.stage_chest_sets = {0: ["dong"] * 3, 1: ["dong"] * 3, 2: ["dong", "dong", "bac"], 3: ["bac"] * 3,
                                 4: ["bac", "bac", "vang"], 5: ["do", "vang", "vang"], ENDLESS: ["do", "vang", "vang"],
                                 "heroic": ["do"] * 3}
        self.chest_open_upgrade_chance = {"dong": 0.05, "bac": 0.05, "vang": 0.05}
        # Most tier-ups per chest open (None = no limit, up to red; designer 2026-11-02: several upgrades allowed).
        self.chest_open_upgrade_max = None
        # Bag values by chest: green pinch 1-4x, blue stack 5-15x, purple sack 20-50x, red money chest 100-1000x
        # (+ the 25,000x Max Win). Weights are placeholders for tuning.
        self.chest_tier_bags = {"dong": {1: 40, 2: 30, 3: 18, 4: 12}, "bac": {5: 35, 8: 25, 10: 18, 12: 12, 15: 10},
                                "vang": {20: 35, 25: 25, 30: 18, 40: 12, 50: 10},
                                "do": {100: 40, 150: 25, 200: 15, 250: 10, 500: 7, 1000: 3, 25000: 0.01}}
        self.chest_tier_bag_names = {"dong": "pinch", "bac": "stack", "vang": "sack", "do": "chest"}
        # tumble_combine "add" (rule 5): Global = sum(Wild multis) x product(chest multis) of this spin + the Global
        # accumulated by earlier spins inside the reset scope (tumble_reset_scope). "mul" = the 2026-10-30 rule
        # (Wild multis and chest multis collected over the scope, multiplied).
        self.tumble_combine = "mul"
        # Shuffle power (replaces Enhance, rule 3): fires after the weapons, shuffles the basic symbols (Wild, weapons,
        # Scatter stay), then puts a multi on 1-3 basic cells; a cell's multi lasts until the cell is destroyed and the
        # multis of one line add up.
        self.shuffle_cell_count_weights = {1: 50, 2: 35, 3: 15}
        self.shuffle_mult_weights = {2: 40, 3: 25, 4: 15, 5: 12, 10: 8}
        # Coin values never drawn (rule 4: the silver coins are 5/8/10/12/15, no 6x).
        self.coin_excluded_values = []
        # Trial (designer 2026-11-02): Wild multi / chest multi odds depend on the spin's tumble win so far (line pay +
        # money bags, before the Global). tumble_band_bounds = [b1, b2] splits small (< b1) / mid / big (>= b2);
        # tumble_band_tables = {"wild_multi_weights": [small, mid, big], "chest_multi_weights": [...]}, None = the
        # normal table. Per tier via tier_weights. {} = off.
        # Trial (designer 2026-11-03): the Destroy power's pick weight x this factor by the number of bosses still
        # alive, {alive: factor} (more bosses alive -> Destroy likelier). Per tier via tier_weights. {} = off.
        self.destroy_weight_by_alive = {}
        # Trial (2026-11-03 night): dead-spin guard. After this many Bonus free spins in a row that paid nothing and
        # dealt no boss damage, the next free spin's opening board gets dead_spin_guard_weapons guaranteed weapons
        # (per tier via tier_weights). 0 = off.
        self.dead_spin_guard_after = 0
        # Trial (2026-11-03 night): highest Global (tumble multi) a spin may pay with, per tier via tier_weights; or per
        # stage {stage: cap}. 0 = none.
        self.tumble_factor_cap = 0
        # Trial (2026-11-03 night, ported from Boss Lines v1 chain-block): {stage: [threshold, step]}. Once a spin has had
        # more than `threshold` connecting passes, each later refill is, with chance min(1, step x (passes - threshold)),
        # redrawn (up to 50 tries) so that nothing connects - capping long cascades. Per tier via tier_weights. {} = off.
        self.chain_block = {}
        # ---- Unified rules, complete document (designer 2026-11-03), all off by default ----------------------------
        # action_order "doc" (section 8): lines -> weapons -> open chests (inside the loop) -> powers in the order
        # Upgrade, Transform, Replace, Shuffle (screen held between them) -> back to lines; Destroy last.
        # "legacy" = powers fire at the start of each cycle and chests open at spin end.
        self.action_order = "legacy"
        # arrow_rule "table" (designer 2026-11-04): Arrow damage is one of arrow_damage_values (multiples of 5, 10-35).
        # Odds tilt toward the high values the more HP the boss has: t = w_max x (2 x hp_max-level - 1) +
        # w_ratio x (2 x hp/hp_max - 1), hp_max-level = (hp_max - lo) / (hi - lo) clipped to 0..1; weight of the i-th of
        # n values = max(0, 1 + t x (2i/(n-1) - 1)). "formula" = arrow_base + hp_max x k.
        self.arrow_rule = "formula"
        self.arrow_damage_values = [10, 15, 20, 25, 30, 35]
        self.arrow_hp_range = (20, 120)
        self.arrow_tilt_max = 0.6
        self.arrow_tilt_ratio = 0.4
        # shuffle_rule "doc": every cell not in a winning line (Scatter excepted) is shuffled; the shuffle must make a
        # new or longer line if it can (shuffle_tries attempts); EVERY shuffled cell gets a Shuffle Multiplier.
        # "basic" = only basic symbols move and 1-3 cells get a multiplier.
        self.shuffle_rule = "basic"
        self.shuffle_tries = 30
        # Transform may also turn weapon cells into Wild (document: only Wild and base-game Scatter are excluded).
        self.transform_skips_weapons = True
        # Accumulated Global use per tier (tumble_combine "add"): "always" (Epic / Legendary: added every spin that has
        # base pay) or "if2x" (Super: added only when the spin's own Wild x chest multi is >= 2x; otherwise the spin
        # pays x1 and the accumulated Global stays as it is).
        self.tumble_acc_rule = "always"
        # Epic starts with a Treasure on every cell (N5). The document has no such opening Treasure.
        self.epic_opening_treasure_on = True
        self.dead_spin_guard_weapons = 1
        # What the guard gives (designer 2026-11-03): "weapon" (dead_spin_guard_weapons weapons), "line" (the opening
        # board is sure to connect at least one 3-symbol line) or "either" (line or 1 weapon, 50/50).
        self.dead_spin_guard_mode = "weapon"
        self.tumble_band_bounds = [2, 10]
        self.tumble_band_tables = {}
        # Share of Wilds that flash (per tier): a flashing Wild always gives a power when it connects; other Wilds
        # give none (set wild_power_drop_chance to 0).
        self.wild_flash_chance = 0.0
        # A Wild only flashes while some power can still be stored (designer 2026-11-01: no flashing Wild that would
        # give nothing).
        self.wild_flash_needs_room = False
        # Display Wilds lean to winning lines already lit: line chance = wild_skin_chance x ((1-b) + b x 2 x lit share
        # of the line), b in [0, 1] (designer 2026-10-29). 0 = every winning line alike.
        self.wild_skin_lit_bias = 0
        # lit_rule "lines": only winning lines that hold a Wild (display Wilds included, the player sees a Wild)
        # light their cells; per tier via tier_weights (designer 2026-10-28 trial). False = every winning line;
        # "real" = only real Wilds count, a line with just a display Wild does not light; "cells" (rule 4,
        # 2026-11-02) = only the connected Wild cells themselves light (display Wilds included).
        self.lit_wild_lines_only = False
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
        # Coin floor inside a chest: "tier" = the chest tier's lowest coin (bac >= 5, vang >= 20, ...); "stage" = only the
        # stage minimum coin (designer 2026-10-27 trial: no tier coin guarantee for silver/gold/diamond chests).
        self.chest_coin_min = "tier"  # or "sure_only": only the guaranteed coin (chest_sure_coin_tiers) keeps the tier floor
        # Chest tiers that always hold at least one coin (proposal: gold and diamond; designer 2026-10-29: diamond only).
        self.chest_sure_coin_tiers = ["vang", "kimcuong"]
        # Chest power gifts only pick powers with nothing in reserve; none left -> the gift is a coin (designer 2026-10-29).
        self.chest_power_new_only = False
        # Upgrade target odds among the higher chests, {chest: weight}; per tier via tier_weights. {} = uniform (Q16).
        self.chest_upgrade_tier_weights = {}

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
        self.power_names = ["enhance", "upgrade", "transform", "replace", "destroy", "shuffle"]
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
            # Legendary Bonus (document section 9, hidden mode): 6 Scatters; only reachable when scatter_to_tier has 6
            # and max_scatters_on_board is 6.
            "legendary": {"spins": 10, "start_stage": 5},
        }
        # Wilds carrying a multiplier (>= 2x) guaranteed on each free spin's opening board, {tier: n}
        # (document section 9: Legendary >= 5).
        self.bonus_min_multi_wilds = {}
        # Tiers whose whole screen is lit from the start (Q25: Epic; document section 9: Legendary too).
        self.full_lit_tiers = ["epic"]
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
        # "topup": the shortfall is paid at Bonus end (bonusMinWin event). "reject" (designer 2026-11-09): a Bonus
        # under the floor is thrown away and simulated again (check_repeat), so no book of that tier pays under it.
        self.bonus_min_total_win_mode = "topup"
        # "reject" only: at most this many re-runs per Bonus, then the floor is topped up (None = no limit).
        # With R re-runs and p = share of Bonuses reaching the floor: mean = mean(>= floor) x (1 - f) + floor x f,
        # f = (1 - p) ** (R + 1), so the mean follows directly from one "topup" run.
        self.bonus_min_total_win_rerolls = None
        # "reject" only: chance that a Bonus under the floor is re-run (else topped up). Designer 2026-11-10: keep the
        # re-run share of all Bonuses at 0-10%: share = (1 - p) x chance. With R = 1:
        # f = (1 - p) x (1 - chance x p), mean = mean(>= floor) x (1 - f) + floor x f.
        self.bonus_min_total_win_reroll_chance = 1.0
        # Designer idea 2026-11-10 (trial, off by default). Big spins, only when needed: at the start of a free spin
        # (no burst running) the Bonus is "behind" when its win is under pace x (spins played + 1) / tier spins; then
        # (from free spin `from_spin` on) with `chance` a burst of 1-2 consecutive big spins starts (burst_weights), at most `max_bursts` per Bonus.
        # Each big spin gets one boost drawn from type_weights: "wilds" (min_multi_wilds Wilds carrying a multi),
        # "weapons" (min_weapons weapons), "line" (a sure line + 1 multi Wild). Aim: ~200x+ per big spin.
        # {tier: {"pace": 600, "chance": 0.5, "burst_weights": {1: 60, 2: 40}, "max_bursts": 2,
        #         "type_weights": {"wilds": 50, "weapons": 30, "line": 20}, "min_multi_wilds": 3, "min_weapons": 2}}
        self.bonus_big_spins = {}
        # Rescue Scatter: when at most `spins_left` free spins remain and the Bonus has won under `below`, the spin's
        # opening board gets 1 Scatter (+1 free spin), at most `max` times per Bonus.
        # {tier: {"spins_left": 0, "below": 600.0, "max": 2}}
        self.bonus_rescue_scatter = {}
        # Weapons guaranteed on each free spin's opening board (designer 2026-10-07;
        # was 3 Wild-or-weapon for both, which drove Super to ~1068x vs 240x).
        self.bonus_min_weapons = {"super": 1, "epic": 2}
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
        self.tier_stage_min_coin = {'super': {2: 0.2}}
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
        self.power_wild_event_chance = 0.05
        self.lit_reset_after_treasure_tiers = ['bonus']

        # ---- Reels ------------------------------------------------------------------
        reel_files = ["BR0", "ANTE", "HERO", "BON_S1", "BON_S2", "BON_S3", "BON_S4", "BON_S5", "BON_E",
                      "SUP_S2", "SUP_S3", "SUP_S4", "SUP_S5", "SUP_E", "EPI_S3", "EPI_S4", "EPI_S5", "EPI_E",
                      "SUPX_S1", "SUPX_S2", "SUPX_S3", "SUPX_S4", "SUPX_S5", "SUPX_E", "EPX_S1", "EPX_S2", "EPX_S3", "EPX_S4", "EPX_S5", "EPX_E"]
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
        # Accepted tuning 2026-11-11 (after the reel maps above, which it replaces). The rule tests run on the rule
        # defaults instead (tests/conftest.py sets BL3_RULE_DEFAULTS=1): they check mechanics on hand-built boards.
        if os.environ.get("BL3_RULE_DEFAULTS") != "1":
            self.accepted_tuning_2026_11_11()

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

    def accepted_tuning_2026_11_11(self) -> None:
        """Normal LH8, Super SP17, Epic EP34 (user 'chot' 2026-11-11). Source: tuning/overrides/final_2026_11_11.json."""
        # ---- Accepted tuning 2026-11-11: Normal LH8, Super SP17, Epic EP34 (user 'chot', 2026-11-11) --------------
        # Source: tuning/overrides/final_2026_11_11.json (readable sheets: tuning/results/normal_LH8_config.md,
        # super_SP17_config.md, epic_EP34_config.md). Replaces the f17 values above; reels are
        # gen_reels.REEL_SPECS (BON_S*, SUPX_*, EPX_*). Epic curve target = tuning/targets/epic_curve_2026-11-11_proposal.csv
        # (proposal, designer to confirm).
        self.stage_coin_value_weights = {'bonus': {1: {0.2: 0.3749999842, 0.5: 0.2730849464, 1: 0.1280804812, 2: 0.06761095014375533, 3: 0.04341828909098588, 4: 0.031710437159544885, 5: 0.022000595729274573, 6: 0.018027887216871628, 8: 0.013166621620259805, 10: 0.010318572806773795, 12: 0.008455319538101571, 15: 0.006626364118857974, 20: 0.004839548255268259, 25: 0.003792714053040235, 30: 0.0031078531098105242, 40: 0.002269812655810503, 50: 0.001778833464998639, 100: 0.0008342965623900105, 150: 0.0005357671905758766, 200: 0.00039129625825648674, 250: 0.0003066556512665735, 500: 0.00014382556089345612, 1000: 6.745611062220265e-05, 25000: 4.2e-08}, 2: {0.5: 0.4249999715, 1: 0.1555632073, 2: 0.09851137391966304, 3: 0.07036887971149453, 4: 0.055426437465268555, 5: 0.040775201101465666, 6: 0.035050818330534604, 8: 0.02760797107640013, 10: 0.022941758306834686, 12: 0.019720991701854956, 15: 0.016387811498022826, 20: 0.009035565304877138, 25: 0.0075084023837141455, 30: 0.006454306532348416, 40: 0.0050837702742352504, 50: 0.00422452736113752, 100: 0.002376887975784883, 150: 0.0016978643109856252, 200: 0.0013373322121164048, 250: 0.0011113005104001073, 500: 0.0006252620628204376, 1000: 0.000351797444503191, 25000: 6.7e-08}, 3: {1: 0.43029655568801195, 2: 0.0994502973, 3: 0.0735679338, 4: 0.0594020038, 5: 0.04454909835924514, 6: 0.038901872448582835, 8: 0.03141109251717116, 10: 0.02660932929622342, 12: 0.023236221866215257, 15: 0.01968413797586351, 20: 0.005785359091174636, 25: 0.00490096056289371, 30: 0.004279694769781526, 40: 0.0034556148402464675, 50: 0.0029273605606736745, 100: 0.0010491134963291474, 150: 0.0007760772471590286, 200: 0.0006266391002026815, 250: 0.0005308457865919933, 500: 0.00031707600107476735, 1000: 0.00018939058120863832, 25000: 2.8e-08}, 4: {5: 0.1402850865, 6: 0.1280621773, 8: 0.1109050988, 10: 0.099196536, 12: 0.090553634, 15: 0.0809936325, 20: 0.032722930283004, 25: 0.0288297542545584, 30: 0.025995218895510805, 40: 0.0220786059024024, 50: 0.017220562666947666, 100: 0.0032533053665365335, 150: 0.0025844380142017944, 200: 0.0021950493556592977, 250: 0.0019338956820000469, 500: 0.0003234133515876859, 1000: 0.00016170668185787917, 25000: 5.9e-06}, 5: {20: 0.12597039344500002, 25: 0.11267134515, 30: 0.10285439554, 40: 0.08907451943, 50: 0.0599697083670932, 100: 0.014032481685635728, 150: 0.005717880501251695, 200: 0.003024106216507994, 250: 0.0018451000121118026, 500: 0.0009702292971628465, 1000: 0.00048511464858142325, 25000: 1.7e-05}}, 'super': {1: {0.2: 0.3749999842, 0.5: 0.2730849464, 1: 0.1280804812, 2: 0.06761095014375533, 3: 0.04341828909098588, 4: 0.031710437159544885, 5: 0.022000595729274573, 6: 0.018027887216871628, 8: 0.013166621620259805, 10: 0.010318572806773795, 12: 0.008455319538101571, 15: 0.006626364118857974, 20: 0.004839548255268259, 25: 0.003792714053040235, 30: 0.0031078531098105242, 40: 0.002269812655810503, 50: 0.001778833464998639, 100: 0.0008342965623900105, 150: 0.0005357671905758766, 200: 0.00039129625825648674, 250: 0.0003066556512665735, 500: 0.00014382556089345612, 1000: 6.745611062220265e-05, 25000: 4.2e-08}, 2: {0.5: 0.4249999715, 1: 0.1555632073, 2: 0.09851137391966304, 3: 0.07036887971149453, 4: 0.055426437465268555, 5: 0.040775201101465666, 6: 0.035050818330534604, 8: 0.02760797107640013, 10: 0.022941758306834686, 12: 0.019720991701854956, 15: 0.016387811498022826, 20: 0.009035565304877138, 25: 0.0075084023837141455, 30: 0.006454306532348416, 40: 0.0050837702742352504, 50: 0.00422452736113752, 100: 0.002376887975784883, 150: 0.0016978643109856252, 200: 0.0013373322121164048, 250: 0.0011113005104001073, 500: 0.0006252620628204376, 1000: 0.000351797444503191, 25000: 6.7e-08}, 3: {0.5: 0.4249999715, 1: 0.1555632073, 2: 0.09851137391966304, 3: 0.07036887971149453, 4: 0.055426437465268555, 5: 0.040775201101465666, 6: 0.035050818330534604, 8: 0.02760797107640013, 10: 0.022941758306834686, 12: 0.019720991701854956, 15: 0.016387811498022826, 20: 0.0054213391829262825, 25: 0.004505041430228487, 30: 0.0038725839194090495, 40: 0.00305026216454115, 50: 0.0025347164166825116, 100: 0.0014261327854709297, 150: 0.0010187185865913751, 200: 0.0008023993272698429, 250: 0.0006667803062400644, 500: 0.0003751572376922625, 1000: 0.00021107846670191457, 25000: 6.7e-08}, 4: {5: 0.1402850865, 6: 0.1280621773, 8: 0.1109050988, 10: 0.099196536, 12: 0.090553634, 15: 0.0809936325, 20: 0.016361465141502, 25: 0.0144148771272792, 30: 0.012997609447755402, 40: 0.0110393029512012, 50: 0.008610281333473833, 100: 0.0016266526832682668, 150: 0.0012922190071008972, 200: 0.0010975246778296489, 250: 0.0009669478410000234, 500: 0.00016170667579384294, 1000: 8.085334092893959e-05, 25000: 5.9e-06}, 5: {20: 0.12597039344500002, 25: 0.11267134515, 30: 0.10285439554, 40: 0.08907451943, 50: 0.0299848541835466, 100: 0.007016240842817864, 150: 0.0028589402506258477, 200: 0.001512053108253997, 250: 0.0009225500060559013, 500: 0.00048511464858142325, 1000: 0.00024255732429071162, 25000: 1.7e-05}, 6: {20: 0.12597039344500002, 25: 0.11267134515, 30: 0.10285439554, 40: 0.08907451943, 50: 0.0299848541835466, 100: 0.007016240842817864, 150: 0.0028589402506258477, 200: 0.001512053108253997, 250: 0.0009225500060559013, 500: 0.00048511464858142325, 1000: 0.00024255732429071162, 25000: 1.7e-05}}, 'epic': {4: {5: 0.1402850865, 6: 0.1280621773, 8: 0.1109050988, 10: 0.099196536, 12: 0.090553634, 15: 0.0809936325, 20: 0.011453025599051399, 25: 0.01009041398909544, 30: 0.00909832661342878, 40: 0.0077275120658408395, 50: 0.006027196933431683, 100: 0.0011386568782877867, 150: 0.000904553304970628, 200: 0.0007682672744807542, 250: 0.0006768634887000163, 500: 0.00011319467305569005, 1000: 5.6597338650257705e-05, 25000: 5.9e-06}, 5: {20: 0.12597039344500002, 25: 0.11267134515, 30: 0.10285439554, 40: 0.0320668269948, 50: 0.010794547506076774, 100: 0.002525846703414431, 150: 0.0010292184902253052, 200: 0.000544339118971439, 250: 0.0003321180021801244, 500: 0.00017464127348931234, 1000: 8.732063674465617e-05, 25000: 1.7e-05}, 6: {20: 0.12597039344500002, 25: 0.11267134515, 30: 0.10285439554, 40: 0.0320668269948, 50: 0.010794547506076774, 100: 0.002525846703414431, 150: 0.0010292184902253052, 200: 0.000544339118971439, 250: 0.0003321180021801244, 500: 0.00017464127348931234, 1000: 8.732063674465617e-05, 25000: 1.7e-05}, 1: {0.2: 0.3749999842, 0.5: 0.2730849464, 1: 0.1280804812, 2: 0.06761095014375533, 3: 0.04341828909098588, 4: 0.031710437159544885, 5: 0.022000595729274573, 6: 0.018027887216871628, 8: 0.013166621620259805, 10: 0.010318572806773795, 12: 0.008455319538101571, 15: 0.006626364118857974, 20: 0.004839548255268259, 25: 0.003792714053040235, 30: 0.0031078531098105242, 40: 0.002269812655810503, 50: 0.001778833464998639, 100: 0.0008342965623900105, 150: 0.0005357671905758766, 200: 0.00039129625825648674, 250: 0.0003066556512665735, 500: 0.00014382556089345612, 1000: 6.745611062220265e-05, 25000: 4.2e-08}, 2: {0.5: 0.4249999715, 1: 0.1555632073, 2: 0.09851137391966304, 3: 0.07036887971149453, 4: 0.055426437465268555, 5: 0.08256978223046799, 6: 0.07097790711933258, 8: 0.05590614142971027, 10: 0.04645706057134024, 12: 0.03993500819625629, 15: 0.033185318283496225, 20: 0.018297019742376203, 25: 0.015204514827021147, 30: 0.013069970728005545, 40: 0.010294634805326382, 50: 0.008554667906303479, 100: 0.004813198150964388, 150: 0.0034381752297458915, 200: 0.0027080977295357205, 250: 0.002250383533560217, 500: 0.001266155677211386, 1000: 0.0007123898251189618, 25000: 6.7e-08}, 3: {0.5: 0.4249999715, 1: 0.1555632073, 2: 0.09851137391966304, 3: 0.07036887971149453, 4: 0.055426437465268555, 5: 0.08256978223046799, 6: 0.07097790711933258, 8: 0.05590614142971027, 10: 0.04645706057134024, 12: 0.03993500819625629, 15: 0.033185318283496225, 20: 0.010978211845425722, 25: 0.009122708896212688, 30: 0.007841982436803325, 40: 0.00617678088319583, 50: 0.005132800743782086, 100: 0.0028879188905786327, 150: 0.0020629051378475345, 200: 0.0016248586377214322, 250: 0.0013502301201361307, 500: 0.0007596934063268316, 1000: 0.000427433895071377, 25000: 6.7e-08}}}
        self.boss_hp_offset = {}
        self.stage_min_coin = {0: 0.2, 1: 0.2, 2: 0.5, 3: 1, 4: 5, 5: 20, 6: 20}
        self.tier_weights = {'bonus': {'treasure_kind_weights': {'coin': 92, 'magnet': 0.7, 'clover': 2.1, 'golden': 0.15, 'star': 0, 'global': 0, 'scatter': 1}, 'wild_event_chance': 0.65, 'wild_event_weights': {'multiplier': 30, 'coin': 30, 'power': 40}, 'coin_value_weights': {0.2: 160, 0.5: 4, 1.0: 1.5, 2.0: 0.3, 3.0: 0.18, 4.0: 0.12, 5.0: 0.2808, 6.0: 0.1872, 8.0: 0.1404, 10.0: 0.11232, 12.0: 0.08424, 15.0: 0.06552, 20.0: 0.184548, 25.0: 0.105456, 30.0: 0.06591, 40.0: 0.042182, 50.0: 0.026364, 100.0: 0.01268768, 150.0: 0.02114612, 200.0: 0.01268768, 250.0: 0.0065065, 500.0: 0.00225224, 1000.0: 0.00075074, 25000.0: 8e-06}, 'clover_factor_weights': {2: 70, 3: 15, 4: 8, 5: 4, 10: 1.7705856199999999, 20: 0.8852928099999999}, 'golden_factor_weights': {2: 50, 3: 30, 4: 15, 5: 5}, 'chest_gift_count_weights': {'dong': {1: 1}, 'bac': {2: 1}, 'vang': {3: 1}, 'kimcuong': {3: 1}}, 'enhance_factor_weights': {2: 60, 3: 25, 4: 10, 5: 4, 10: 1}, 'wild_mult_weights': {2: 40, 3: 40, 4: 20}, 'chest_tier_step_weights': [88, 8, 3.8, 0.2], 'chest_upgrade_chance': 0.02, 'global_factor_weights': {2: 60, 3: 30, 4: 10}, 'wild_coin_min_value': 1.0, 'power_pick_weights': {'shuffle': 10, 'upgrade': 25.4, 'transform': 25.4, 'replace': 19.6, 'destroy': 19.6}, 'hp_cut_weights': {0: 1}, 'lit_wild_lines_only': 'cells', 'wild_skin_chance': 0.2, 'chest_upgrade_tier_weights': {'bac': 60, 'vang': 30}, 'wild_lit_bias': 1.0, 'wild_skin_lit_bias': 1.0, 'weapon_lit_bias': 0.6, 'wild_multi_weights': {1: 68.83443055638499, 2: 18.0353, 3: 10.609, 4: 4.426464049999999, 5: 2.65587843, 10: 0.5}, 'wild_power_drop_chance': 0.0, 'tumble_reset_scope': 'spin', 'chest_gift_multi_chance': {'dong': 0.05635242852773999, 'bac': 0.07513657137032, 'vang': 0.06996964841403598, 'do': 0.093292864552048}, 'wild_flash_chance': 0.04, 'chest_gift_power_chance': {'dong': 0.18, 'bac': 0.3, 'vang': 0.4, 'kimcuong': 0.45, 'do': 0.4}, 'chest_bag_value_weights': {1: 0.4999995, 2: 0.1870084812, 3: 0.0993645876, 4: 0.0634422802, 5: 0.0447959932, 6: 0.0337092519, 8: 0.0215226758, 10: 0.0151969576, 12: 0.0114358011, 15: 0.0080747109, 20: 0.0051555396, 25: 0.0036402777, 30: 0.0027393307, 40: 0.0017490073, 50: 0.0012349575, 100: 0.000418957, 150: 0.0002226075, 200: 0.0001421304, 250: 0.0001003569, 500: 3.40459e-05, 1000: 1.155e-05, 25000: 1e-06}, 'chest_tier_bags': {'dong': {1: 30.816645064473896, 2: 34.75765853401745, 3: 30.357068521893286, 4: 23.373816567181354}, 'bac': {5: 30.816645064473896, 8: 29.840474989267456, 10: 27.54632682057528, 12: 21.272392797832865, 15: 15.170049869518284}, 'vang': {20: 35.82156889587, 25: 14.915910488357797, 30: 8.224279206378064, 40: 3.199955033559681, 50: 1.411437829844994}, 'do': {100: 47.76209186116001, 150: 20.022412482280824, 200: 10.715815462475579, 250: 6.537749978706237, 500: 3.474696256643199, 1000: 1.0009617835819866, 25000: 0.01}}, 'chest_multi_weights': {2: 61.902984550000006, 3: 30, 4: 9, 5: 3.5411712399999997, 10: 1.7705856199999999}, 'destroy_weight_by_alive': {3: 1.6, 2: 1.2, 1: 0.7, 0: 0.3}, 'chain_block': {4: [2, 0.6], 5: [2, 0.6], 6: [2, 0.6], 3: [2, 0.5], 1: [2, 0.3]}, 'shuffle_mult_weights': {2: 60, 3: 25, 4: 8, 5: 5, 10: 2}, 'last_hit_base': 0.005, 'last_hit_scale': 0.03}, 'epic': {'wild_event_chance': 1.0, 'wild_event_weights': {'multiplier': 40, 'coin': 40, 'power': 20}, 'enhance_factor_weights': {5: 20, 10: 30, 15: 25, 20: 15, 25: 10}, 'wild_mult_weights': {2: 30, 3: 25, 4: 20, 5: 15, 10: 10}, 'chest_upgrade_chance': 0.005, 'chest_tier_step_weights': [99, 0.8, 0.2], 'clover_factor_weights': {2: 74, 3: 18, 4: 6, 5: 2}, 'golden_factor_weights': {2: 30, 3: 30, 4: 20, 5: 15, 10: 5}, 'global_factor_weights': {2: 30, 3: 30, 4: 20, 5: 15, 10: 5}, 'chest_gift_count_weights': {'dong': {1: 1}, 'bac': {2: 1}, 'vang': {3: 1}, 'kimcuong': {3: 1}}, 'chest_gift_power_chance': {'dong': 0.18, 'bac': 0.3, 'vang': 0.45, 'kimcuong': 0.6, 'do': 0.45}, 'coin_value_weights': {0.2: 0, 0.5: 0, 1.0: 30, 2.0: 3, 3.0: 1.5, 4.0: 1, 5.0: 60, 6.0: 1.5, 8.0: 0.75, 10.0: 30.0, 12.0: 7.5, 15.0: 18.75, 20.0: 11.25, 25.0: 3.75, 30.0: 2.25, 40.0: 1.5, 50.0: 1.125, 100.0: 0.44999999999999996, 150.0: 0.015, 200.0: 0.0075, 250.0: 0.0045000000000000005, 500.0: 0.0015, 1000.0: 0.00045, 25000.0: 0.013500000000000002}, 'treasure_kind_weights': {'coin': 97.922468587285, 'magnet': 0.7442324127149555, 'clover': 2.244285999999999, 'golden': 0.10201299999999996, 'star': 0, 'global': 0, 'scatter': 1}, 'power_pick_weights': {'shuffle': 10, 'upgrade': 25.4, 'transform': 25.4, 'replace': 19.6, 'destroy': 19.6}, 'star_value_weights': {10.0: 45, 20.0: 45, 50.0: 10}, 'guarantee_symbol_weights': {'W': 0, 'AR': 40, 'BM': 20, 'SW': 20, 'LT': 20}, 'hp_cut_weights': {0: 1}, 'wild_multi_weights': {1: 63, 2: 22, 3: 11, 4: 3, 5: 0.9, 10: 0.15}, 'wild_power_drop_chance': 0.0, 'tumble_reset_scope': 'bonus', 'chest_gift_multi_chance': {'dong': 0.041999999999999996, 'bac': 0.055, 'vang': 0.05, 'do': 0.065}, 'wild_flash_chance': 0.1, 'last_hit_base': 0.005, 'last_hit_scale': 0.03, 'destroy_weight_by_alive': {3: 1.6, 2: 1.2, 1: 0.7, 0: 0.3}, 'chain_block': {1: [2, 0.3], 3: [1, 0.5], 4: [1, 0.5], 5: [1, 0.5], 6: [1, 0.5]}, 'chest_tier_bags': {'dong': {1: 30.816645064473896, 2: 87.91885399707829, 3: 132.1446712577341, 4: 149.55214412602604}, 'bac': {5: 30.816645064473896, 8: 29.840474989267456, 10: 27.54632682057528, 12: 21.272392797832865, 15: 15.170049869518284}, 'vang': {20: 35.82156889587, 25: 14.915910488357797, 30: 8.224279206378064, 40: 3.199955033559681, 50: 1.411437829844994}, 'do': {100: 47.76209186116001, 150: 20.022412482280824, 200: 10.715815462475579, 250: 6.537749978706237, 500: 3.474696256643199, 1000: 1.0009617835819866, 25000: 0.01}}, 'shuffle_mult_weights': {2: 60, 3: 25, 4: 8, 5: 5, 10: 2}, 'chest_multi_weights': {2: 60, 3: 27, 4: 9, 5: 3, 10: 1}}, 'super': {'treasure_kind_weights': {'coin': 92, 'magnet': 0.7, 'clover': 2.1, 'golden': 0.15, 'star': 0, 'global': 0, 'scatter': 1}, 'wild_event_chance': 0.65, 'wild_event_weights': {'multiplier': 30, 'coin': 30, 'power': 40}, 'coin_value_weights': {0.2: 160, 0.5: 4, 1.0: 1.5, 2.0: 0.3, 3.0: 0.18, 4.0: 0.12, 5.0: 0.2808, 6.0: 0.1872, 8.0: 0.1404, 10.0: 0.11232, 12.0: 0.08424, 15.0: 0.06552, 20.0: 0.184548, 25.0: 0.105456, 30.0: 0.06591, 40.0: 0.042182, 50.0: 0.026364, 100.0: 0.01268768, 150.0: 0.02114612, 200.0: 0.01268768, 250.0: 0.0065065, 500.0: 0.00225224, 1000.0: 0.00075074, 25000.0: 8e-06}, 'clover_factor_weights': {2: 70, 3: 15, 4: 8, 5: 4, 10: 1.7705856199999999, 20: 0.8852928099999999}, 'golden_factor_weights': {2: 50, 3: 30, 4: 15, 5: 5}, 'chest_gift_count_weights': {'dong': {1: 1}, 'bac': {2: 1}, 'vang': {3: 1}, 'kimcuong': {3: 1}}, 'enhance_factor_weights': {2: 60, 3: 25, 4: 10, 5: 4, 10: 1}, 'wild_mult_weights': {2: 40, 3: 40, 4: 20}, 'chest_tier_step_weights': [88, 8, 3.8, 0.2], 'chest_upgrade_chance': 0.02, 'global_factor_weights': {2: 60, 3: 30, 4: 10}, 'wild_coin_min_value': 1.0, 'power_pick_weights': {'shuffle': 10, 'upgrade': 25.4, 'transform': 25.4, 'replace': 19.6, 'destroy': 19.6}, 'hp_cut_weights': {0: 1}, 'lit_wild_lines_only': 'cells', 'wild_skin_chance': 0.2, 'chest_upgrade_tier_weights': {'bac': 60, 'vang': 30}, 'wild_lit_bias': 1.0, 'wild_skin_lit_bias': 1.0, 'weapon_lit_bias': 0.6, 'wild_multi_weights': {1: 76.51622816858138, 2: 15.330005, 3: 9.01765, 4: 2.6790573624278164, 5: 1.3395286812139082, 10: 0.17860382416185444}, 'wild_power_drop_chance': 0.0, 'tumble_reset_scope': 'bonus', 'chest_gift_multi_chance': {'dong': 0.039446699969417985, 'bac': 0.05259559995922399, 'vang': 0.048978753889825186, 'do': 0.06530500518643359}, 'wild_flash_chance': 0.08, 'chest_gift_power_chance': {'dong': 0.18, 'bac': 0.3, 'vang': 0.4, 'kimcuong': 0.45, 'do': 0.4}, 'chest_bag_value_weights': {1: 0.4999995, 2: 0.1870084812, 3: 0.0993645876, 4: 0.0634422802, 5: 0.0447959932, 6: 0.0337092519, 8: 0.0215226758, 10: 0.0151969576, 12: 0.0114358011, 15: 0.0080747109, 20: 0.0051555396, 25: 0.0036402777, 30: 0.0027393307, 40: 0.0017490073, 50: 0.0012349575, 100: 0.000418957, 150: 0.0002226075, 200: 0.0001421304, 250: 0.0001003569, 500: 3.40459e-05, 1000: 1.155e-05, 25000: 1e-06}, 'chest_tier_bags': {'dong': {1: 30.816645064473896, 2: 34.75765853401745, 3: 30.357068521893286, 4: 23.373816567181354}, 'bac': {5: 30.816645064473896, 8: 29.840474989267456, 10: 27.54632682057528, 12: 21.272392797832865, 15: 15.170049869518284}, 'vang': {20: 35.82156889587, 25: 14.915910488357797, 30: 8.224279206378064, 40: 3.199955033559681, 50: 1.411437829844994}, 'do': {100: 47.76209186116001, 150: 20.022412482280824, 200: 10.715815462475579, 250: 6.537749978706237, 500: 3.474696256643199, 1000: 1.0009617835819866, 25000: 0.01}}, 'chest_multi_weights': {2: 64.45315813334003, 3: 30, 4: 9, 5: 2.1242948282000005, 10: 0.6372884484600001}, 'destroy_weight_by_alive': {3: 1.6, 2: 1.2, 1: 0.7, 0: 0.3}, 'chain_block': {4: [2, 0.6], 5: [2, 0.6], 6: [1, 0.8], 3: [2, 0.5], 1: [2, 0.3]}, 'shuffle_mult_weights': {2: 60, 3: 25, 4: 8, 5: 5, 10: 2}, 'last_hit_base': 0.005, 'last_hit_scale': 0.03, 'tumble_acc_rule': 'if2x', 'endless_hp_step_choices': [0, 5, 10, 15]}, 'treasure_hunt': {'treasure_kind_weights': {'coin': 83, 'magnet': 1.5, 'clover': 2.218, 'golden': 0.4, 'star': 0, 'global': 0, 'scatter': 1.6}, 'coin_value_weights': {0.2: 40, 0.5: 30, 1.0: 150, 2.0: 14, 3.0: 9, 4.0: 6, 5.0: 4, 6.0: 3, 8.0: 2, 10.0: 1.4, 12.0: 1, 15.0: 0.6, 20.0: 0.4, 25.0: 0.2, 30.0: 0.12, 40.0: 0.06, 50.0: 0.03, 100.0: 0.008, 150.0: 0.003, 200.0: 0.0015, 250.0: 0.001, 500.0: 0.0003, 1000.0: 0.0001, 25000.0: 0.004}, 'global_factor_weights': {2: 50, 3: 30, 5: 20}, 'golden_factor_weights': {2: 50, 3: 40, 5: 10}, 'star_value_weights': {5.0: 40, 10.0: 40, 20.0: 20}, 'treasure_round_kind_mult': {'clover': [0, 1.0], 'golden': [0, 1.0], 'scatter': [1, 0.4], 'global': [1, 0.15]}, 'clover_factor_weights': {2: 75, 3: 20, 4: 5}, 'treasure_clover_vanishes': True}, 'heroic': {'wild_mult_weights': {2: 45, 3: 30, 4: 15, 5: 8, 10: 2}, 'wild_event_weights': {'multiplier': 45, 'coin': 35, 'power': 20}, 'chest_gift_count_weights': {'dong': {1: 1}, 'bac': {2: 1}, 'vang': {3: 1}, 'kimcuong': {3: 1}}, 'treasure_kind_weights': {'coin': 98, 'magnet': 0.2, 'clover': 0.5, 'golden': 0, 'star': 0, 'global': 0, 'scatter': 0}, 'coin_value_weights': {0.2: 40, 0.5: 30, 1.0: 25, 2.0: 8, 3.0: 4, 4.0: 2.5, 5.0: 1.5, 6.0: 1, 8.0: 0.6, 10.0: 0.4, 12.0: 0.25, 15.0: 0.15, 20.0: 0.1, 25.0: 0.009, 30.0: 0.0045, 40.0: 0.0021, 50.0: 0.0009, 100.0: 0.00024, 150.0: 8.999999999999999e-05, 200.0: 4.4999999999999996e-05, 250.0: 3e-05, 500.0: 9e-06, 1000.0: 3e-06, 25000.0: 2e-07}, 'wild_coin_value_weights': {20.0: 45, 25.0: 12, 30.0: 12, 40.0: 9, 50.0: 9, 75.0: 5, 100.0: 4, 150.0: 2, 200.0: 1.2, 250.0: 0.6, 500.0: 0.5, 1000.0: 0.15}, 'guarantee_symbol_weights': {'W': 1}, 'global_factor_weights': {2: 40, 3: 40, 5: 20}, 'hp_cut_weights': {0: 10, 5: 20, 10: 70}, 'wild_multi_weights': {2: 90, 3: 10}, 'wild_power_drop_chance': 0.0, 'chest_gift_multi_chance': {'dong': 0.1, 'bac': 0.15, 'vang': 0.2, 'do': 0.2}, 'wild_flash_chance': 0.1}}
        self.tier_stage_min_coin = {}
        self.bonus_min_weapons_chance = {}
        self.tier_hp_tilt = {'super': 0, 'epic': 0}
        self.chest_coin_min = 'stage'
        self.stage_min_chest_count = {'1': 1, '2': 1, '3': 1, '4': 1, '5': 3, '6': 3}
        self.stage_chest_weights = {'bonus': {1: {'dong': 92, 'bac': 6, 'vang': 1.8}, 2: {'dong': 92, 'bac': 6, 'vang': 1.8}}, 'super': {1: {'dong': 92, 'bac': 6, 'vang': 1.8}, 2: {'dong': 92, 'bac': 6, 'vang': 1.8}}}
        self.chest_gift_count_weights = {'dong': {1: 1}, 'bac': {2: 1}, 'vang': {3: 1}, 'kimcuong': {3: 1}}
        self.chest_sure_coin_tiers = []
        self.chest_power_new_only = True
        self.wild_multi_weights = {1: 90, 2: 6, 3: 3, 5: 1}
        self.wild_power_drop_chance = 0.0
        self.chest_order = ['dong', 'bac', 'vang']
        self.stage_min_chest = {0: 'dong', 1: 'dong', 2: 'dong', 3: 'bac', 4: 'vang', 5: 'vang', 6: 'vang'}
        self.tumble_multi = True
        self.treasure_kind_weights = {'coin': 95, 'magnet': 0.4, 'clover': 2.483, 'golden': 0.04, 'star': 0, 'global': 0, 'scatter': 1}
        self.chest_power_immediate = True
        self.boss_drop_chance = 0.0
        self.chest_display_names = {'dong': 'green', 'bac': 'blue', 'vang': 'purple', 'do': 'red'}
        self.chest_bags = True
        self.wild_flash_chance = 0.05
        self.power_reserve_cap = 1
        self.wild_flash_needs_room = True
        self.chest_rule = 'v4'
        self.stage_hp_range = {0: [10, 20], 1: [15, 25], 2: [25, 40], 3: [40, 55], 4: [55, 75], 5: [75, 100], 6: [75, 100]}
        self.tumble_combine = 'add'
        self.coin_excluded_values = [6]
        self.lit_wild_lines_only = 'cells'
        self.power_pick_weights = {'shuffle': 30, 'upgrade': 20, 'transform': 25, 'replace': 15, 'destroy': 10}
        self.chest_gift_power_chance = {'dong': 0.15, 'bac': 0.25, 'vang': 0.35, 'kimcuong': 0.45, 'do': 0.35}
        self.bonus_min_total_win = {'epic': 600.0}
        self.symbol_damage = {'L1': 1, 'L2': 1, 'L3': 1, 'L4': 1, 'H1': 2, 'H2': 2, 'H3': 3, 'H4': 3, 'H5': 4, 'W': 5}
        self.wild_skin_damage = 5
        self.weapon_self_damage = 5
        self.action_order = 'doc'
        self.transform_skips_weapons = False
        self.shuffle_rule = 'doc'
        self.arrow_rule = 'table'
        self.bonus_tiers = {'bonus': {'spins': 6, 'start_stage': 1}, 'super': {'spins': 7, 'start_stage': 1}, 'epic': {'spins': 8, 'start_stage': 1}, 'legendary': {'spins': 10, 'start_stage': 5}}
        self.tier_stage_reel = {'epic': {1: 'EPX_S1', 2: 'EPX_S2', 3: 'EPX_S3', 4: 'EPX_S4', 5: 'EPX_S5', 6: 'EPX_E'}, 'super': {1: 'SUPX_S1', 2: 'SUPX_S2', 3: 'SUPX_S3', 4: 'SUPX_S4', 5: 'SUPX_S5', 6: 'SUPX_E'}}
        self.bonus_min_weapons = {}
        self.epic_opening_treasure_on = False
        self.bonus_min_total_win_mode = 'topup'
        self.bonus_big_spins = {'epic': {'pace': 600, 'chance': 0.8, 'burst_weights': {1: 60, 2: 40}, 'max_bursts': 2, 'type_weights': {'wilds': 0, 'weapons': 70, 'line': 30}, 'min_multi_wilds': 2, 'min_weapons': 3, 'from_spin': 3}}
        self.bonus_rescue_scatter = {'epic': {'spins_left': 2, 'below': 600.0, 'max': 3}}
        self.epic_min_coin = 0
        # Max Win books per tier = gap to the tier mean (LH8 90.3 -> 91, SP17 240.2 -> 245, EP34 1904 -> 2045); long-run check pending
        self.tier_maxwin_rate = {'bonus': 2.8e-05, 'super': 0.000194, 'epic': 0.00611}

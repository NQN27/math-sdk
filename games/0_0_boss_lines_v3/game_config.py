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
        # Q9: later Endless bosses: previous HP + one of these.
        self.endless_hp_step_choices = list(range(0, 55, 5))
        # Q7: number of low symbols removed AT each stage (cumulative, by stage).
        self.stage_removed_lows = {0: 0, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, ENDLESS: 4}
        self.stage_min_chest = {0: "dong", 1: "dong", 2: "dong", 3: "bac", 4: "vang",
                                5: "kimcuong", ENDLESS: "kimcuong"}
        self.stage_min_coin = {0: 0.2, 1: 0.2, 2: 1, 3: 1, 4: 5, 5: 20, ENDLESS: 20}
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
        self.weapon_factor_weights = {1: 30, 2: 20, 3: 14, 4: 10, 5: 8, 6: 6, 7: 4, 8: 3, 9: 3, 10: 2}
        self.arrow_base = 3
        self.arrow_k_choices = [round(0.05 * i, 2) for i in range(1, 11)]
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
        self.treasure_hunt_min_coin = 1
        self.treasure_skips_scatter_cells = True  # Q28 (answered) / N7
        # Q23 trial (designer idea 2026-10-11, NOT approved yet): Bonus tiers listed here clear
        # the lit cells at the start of every free spin after the first, so a Treasure only uses
        # cells lit during the spin that cleared the stage. The Scatter cells that triggered the
        # Bonus are lit for the first spin only. Empty = Q23 as answered (lit for the whole Bonus).
        self.lit_reset_each_spin_tiers = ()
        self.epic_min_coin = 5  # N6: no Dong coins during Epic free spins
        self.epic_opening_treasure_stage = 2  # N5: Epic starts with a Treasure "as if stage 2 was cleared"
        # Per-Bonus-tier replacements for the weight tables above (coin_value_weights,
        # treasure_kind_weights, clover/golden/global_factor_weights), e.g.
        # {"epic": {"treasure_kind_weights": {...}}}; key "treasure_hunt" = Treasure hunt
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
        self.tier_mix = {"buy3": {3: 97.5, 4: 2.4, 5: 0.1}, "buy4": {4: 97.5, 5: 2.5}}
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
        # Designer 2026-10-08: minimum total Bonus win per tier, topped up at Bonus end.
        self.bonus_min_total_win = {"epic": 600.0}
        # Weapons guaranteed on each free spin's opening board (designer 2026-10-07;
        # was 3 Wild-or-weapon for both, which drove Super to ~1068x vs 240x).
        self.bonus_min_weapons = {"super": 1, "epic": 2}
        # Which symbol fills a guaranteed slot (Heroic: any; Super/Epic: weapons only); placeholder.
        self.guarantee_symbol_weights = {"W": 70, "AR": 10, "BM": 8, "SW": 8, "LT": 4}
        self.heroic_min_wild_or_weapon = 5
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
                                                 scatter_triggers=dict(self.tier_mix["buy3"]))),
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
        # 96.65x and buy4 97.5/2.5 pays 290.0x; the designer's small gap (0.05x / 0.10x) is left to the
        # trigger spin's own line wins.
        self.tier_mean_targets = {"bonus": 91.0, "super": 245.0, "epic": 2045.0}
        for name, cost, triggers in (("buy3", 100.0, self.tier_mix["buy3"]), ("buy4", 300.0, self.tier_mix["buy4"])):
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

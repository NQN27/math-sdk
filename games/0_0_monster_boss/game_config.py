"""Monster Cluster Boss Battle game configuration file/setup"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


class GameConfig(Config):
    """Singleton Monster Cluster Boss Battle game configuration class."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "0_0_monster_boss"
        self.provider_number = 0
        self.working_name = "Monster Cluster Boss Battle"
        self.wincap = 5000.0
        self.win_type = "cluster"
        self.rtp = 0.97
        self.construct_paths()

        # Game Dimensions
        self.num_reels = 5
        # Optionally include variable number of rows per reel
        self.num_rows = [5] * self.num_reels
        # Board and Symbol Properties
        # Tiers rebalanced for a 25-cell (5x5) board - top tier ceiling == board size.
        t1, t2, t3, t4 = (5, 5), (6, 8), (9, 12), (13, 25)
        pay_group = {
            (t1, "H1"): 5.0,
            (t2, "H1"): 12.5,
            (t3, "H1"): 25.0,
            (t4, "H1"): 60.0,
            (t1, "H2"): 2.0,
            (t2, "H2"): 5.0,
            (t3, "H2"): 10.0,
            (t4, "H2"): 40.0,
            (t1, "H3"): 1.3,
            (t2, "H3"): 3.2,
            (t3, "H3"): 7.0,
            (t4, "H3"): 30.0,
            (t1, "H4"): 1.0,
            (t2, "H4"): 2.5,
            (t3, "H4"): 6.0,
            (t4, "H4"): 20.0,
            (t1, "L1"): 0.6,
            (t2, "L1"): 1.5,
            (t3, "L1"): 4.0,
            (t4, "L1"): 10.0,
            (t1, "L2"): 0.4,
            (t2, "L2"): 1.2,
            (t3, "L2"): 3.5,
            (t4, "L2"): 8.0,
            (t1, "L3"): 0.2,
            (t2, "L3"): 0.8,
            (t3, "L3"): 2.5,
            (t4, "L3"): 5.0,
            (t1, "L4"): 0.1,
            (t2, "L4"): 0.5,
            (t3, "L4"): 1.5,
            (t4, "L4"): 4.0,
        }
        self.paytable = self.convert_range_table(pay_group)

        self.include_padding = True
        self.special_symbols = {"wild": ["W"], "scatter": ["S"]}

        # 3 scatters -> Normal Free Spins, 4 scatters -> VIP Free Spins.
        # (VIP free spins are additionally distinguished at runtime by drawing from
        # the more generous FR0_VIP reelset instead of FR0 - see bet mode distributions below.)
        # Any count above 4 (possible on a 25-cell board with multiple scatters
        # landing on the same reel) is treated the same as 4 (VIP tier) so lookups
        # never fail for higher organically-accumulated scatter counts during
        # freegame retriggers.
        self.freespin_triggers = {
            self.basegame_type: {3: 8, **{k: 12 for k in range(4, 26)}},
            self.freegame_type: {3: 5, **{k: 8 for k in range(4, 26)}},
        }
        self.anticipation_triggers = {
            self.basegame_type: min(self.freespin_triggers[self.basegame_type].keys()) - 1,
            self.freegame_type: min(self.freespin_triggers[self.freegame_type].keys()) - 1,
        }

        # --- Boss Battle mechanic (base game, new feature) ----------------------
        # 3 bosses sit above the board, each "owning" a zone of reels (0-indexed).
        # Boss1: reels 0-2 (cols 1-3), Boss2: reels 1-3 (cols 2-4), Boss3: reels 3-4 (cols 4-5)
        self.boss_zones = {1: (0, 2), 2: (1, 3), 3: (3, 4)}
        # HP pool per boss. Damage dealt = winning cluster's paid win amount (post
        # grid/global multiplier) for every boss whose zone overlaps the cluster's
        # reels. Calibrated (see readme.txt) so that defeating all 3 bosses in a
        # single base-game spin sequence is an uncommon but reachable bonus event.
        self.boss_max_hp = 20.0
        # A cluster that spans every reel (touches reel 0 through reel num_reels-1)
        # deals bonus damage: its damage is multiplied before being applied to every
        # boss zone it overlaps (which, given the zone layout above, is always all 3).
        self.boss_full_span_damage_multiplier = 2.0
        # Instant base-game bonus win (in bet multiples) awarded when all 3 bosses
        # are reduced to 0 HP within a single spin sequence. Kept as a base-game
        # win (not a free-spin trigger) - see award_boss_bonus() in
        # game_executables.py for why a separate free-spin session isn't viable here.
        self.boss_defeat_bonus_multiplier = 20.0

        # --- Boss Battle mechanic (free spins - replaces the template's grid
        # multiplier escalation entirely). Same 3 column-zone bosses as the base
        # game, but scaled to survive across a whole free-spin session rather
        # than one spin sequence, and respawning as a fresh wave every time all 3
        # are cleared - so the fight is the free spin round's core mechanic for
        # its full duration, not a one-off. Runs identically for Normal and VIP;
        # VIP's advantage comes from FR0_VIP's reel weighting (more wilds/highs,
        # fewer lows -> bigger/more frequent damage per tumble -> more waves
        # cleared per session), not a separate numeric multiplier.
        self.freegame_boss_max_hp = 6.0
        # Instant reward for defeating a single boss within a wave (paid once per
        # boss per wave, in addition to the wave-clear bonus below).
        self.boss_defeat_reward_multiplier = 30.0
        # Additional instant bonus for clearing all 3 bosses in a wave, on top of
        # the 3 individual per-boss rewards already paid. A fresh wave spawns
        # immediately afterward for the rest of the free spin round.
        self.boss_wave_clear_bonus_multiplier = 70.0

        reels = {"BR0": "BR0.csv", "FR0": "FR0.csv", "FR0_VIP": "FR0_VIP.csv", "WCAP": "WCAP.csv"}
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(os.path.join(self.reels_path, f))
        mode_maxwins = {"base": 5000, "bonus": 5000}

        self.bet_modes = [
            BetMode(
                name="base",
                cost=1.0,
                rtp=self.rtp,
                max_win=mode_maxwins["base"],
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=mode_maxwins["base"],
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1, "FR0_VIP": 1, "WCAP": 5},
                            },
                            "scatter_triggers": {3: 1, 4: 2},
                            "force_wincap": True,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame_normal",
                        quota=0.07,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1},
                            },
                            "scatter_triggers": {3: 1},
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame_vip",
                        quota=0.03,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0_VIP": 1},
                            },
                            "scatter_triggers": {4: 1},
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="0",
                        quota=0.4,
                        win_criteria=0.0,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                # Needed in case a boss-defeat bonus fires during this
                                # criteria; such outcomes are then discarded/retried by
                                # check_repeat() since win_criteria requires a 0 final win.
                                self.freegame_type: {"FR0": 1},
                            },
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.5,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                # Natural home of the boss-battle bonus trigger: an
                                # ordinary, non-forced base spin whose tumbles defeat
                                # all 3 bosses grants a Normal free spin session here.
                                self.freegame_type: {"FR0": 1},
                            },
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
            BetMode(
                name="bonus",
                cost=200,
                rtp=self.rtp,
                max_win=mode_maxwins["bonus"],
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=mode_maxwins["bonus"],
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1, "FR0_VIP": 1, "WCAP": 5},
                            },
                            "mult_values": {
                                self.basegame_type: {
                                    2: 10,
                                    3: 20,
                                    4: 30,
                                    5: 20,
                                    10: 20,
                                    20: 20,
                                    50: 10,
                                },
                                self.freegame_type: {
                                    2: 10,
                                    3: 20,
                                    4: 30,
                                    5: 20,
                                    10: 20,
                                    20: 20,
                                    50: 10,
                                },
                            },
                            "scatter_triggers": {3: 1, 4: 2},
                            "force_wincap": True,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame_normal",
                        quota=0.45,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1},
                            },
                            "scatter_triggers": {3: 1},
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame_vip",
                        quota=0.55,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0_VIP": 1},
                            },
                            "scatter_triggers": {4: 1},
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    ),
                ],
            ),
        ]

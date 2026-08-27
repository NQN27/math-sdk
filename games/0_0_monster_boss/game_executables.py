from game_calculations import GameCalculations
from src.calculations.cluster import Cluster
from game_events import boss_damage_event, boss_bonus_event
from src.events.events import update_freespin_event


class GameExecutables(GameCalculations):
    """Game dependent grouped functions."""

    def reset_grid_mults(self):
        """Initialize the (unused, always-zero) grid position multiplier scaffold
        required by evaluate_clusters_with_grid's shared board_mult calculation
        (game_calculations.py) - kept at all-zero since this game replaced the
        template's escalating multiplier mechanic with the boss battle/wave
        systems below; board_mult always resolves to 1 as a result."""
        self.position_multipliers = [
            [0 for _ in range(self.config.num_rows[reel])] for reel in range(self.config.num_reels)
        ]

    # --- Boss Battle mechanic (base game) --------------------------------------
    def reset_boss_battle(self):
        """Initialize/reset the 3 boss HP pools. Called at the start of every new
        base-game spin sequence (i.e. every attempt inside run_spin's repeat loop),
        so boss damage never persists across separate spins/games."""
        self.boss_hp = {boss_id: self.config.boss_max_hp for boss_id in self.config.boss_zones}
        self.bosses_defeated = False

    def apply_boss_damage(self):
        """Apply the current tumble's winning-cluster damage to whichever bosses'
        column zones the clusters overlap. Only relevant during base-game play -
        the boss battle is not part of the free spin feature.

        Damage dealt per winning cluster = that cluster's paid win amount (i.e. the
        symbol win including grid/global multipliers - see readme.txt for rationale).
        A cluster spanning every reel (touching reel 0 through the last reel) deals
        bonus damage: its damage value is multiplied by
        config.boss_full_span_damage_multiplier before being applied to every boss
        zone it overlaps.
        """
        if self.gametype != self.config.basegame_type:
            return

        if self.win_data.get("totalWin", 0) > 0 and not self.bosses_defeated:
            last_reel = self.config.num_reels - 1
            for win in self.win_data["wins"]:
                reels_hit = {pos["reel"] for pos in win["positions"]}
                full_span = 0 in reels_hit and last_reel in reels_hit
                damage = win["win"]
                if full_span:
                    damage *= self.config.boss_full_span_damage_multiplier

                for boss_id, (lo_reel, hi_reel) in self.config.boss_zones.items():
                    if self.boss_hp[boss_id] <= 0:
                        continue
                    if reels_hit & set(range(lo_reel, hi_reel + 1)):
                        self.boss_hp[boss_id] = max(0.0, self.boss_hp[boss_id] - damage)

            if all(hp <= 0 for hp in self.boss_hp.values()):
                self.bosses_defeated = True

        boss_damage_event(self, self.boss_hp, self.config.boss_max_hp, self.bosses_defeated)

    def check_bosses_defeated(self) -> bool:
        """True once all 3 bosses have been reduced to 0 HP within the current
        base-game spin sequence."""
        return self.bosses_defeated

    def run_freespin_from_base(self, scatter_key: str = "scatter") -> None:
        """Override the base Executables version to additionally tag the trigger
        record with a 'tier' field (normal/vip), so the optimizer's fence conditions
        can distinguish the two scatter-count-based criteria - a plain 'symbol':
        'scatter' match is ambiguous between them (3 scatters = normal, 4+ = vip)."""
        count = self.count_special_symbols(scatter_key)
        tier = "normal" if count == 3 else "vip"
        self.record(
            {
                "kind": count,
                "symbol": scatter_key,
                "tier": tier,
                "gametype": self.gametype,
            }
        )
        self.update_freespin_amount()
        self.run_freespin()

    def award_boss_bonus(self):
        """Defeating all 3 bosses awards an instant bonus win, added directly to
        the current base-game spin (NOT a separate free-spin session).

        This must stay a base-game win rather than triggering free spins: the
        engine's analytics/optimizer tooling attributes each simulation's fence
        purely by which Distribution criteria generated it (see
        write_data.make_lookup_pay_split, which records gamestate.criteria
        verbatim). Boss-defeat is an unforced event that can happen during an
        otherwise-ordinary 'basegame'-criteria spin, and a nonzero FREE-game win
        recorded under that criteria hard-fails utils/game_analytics's
        make_split_win_distribution ("Non-Zero FreeGame win in baseGame Fence"),
        since that criteria has no dedicated fence to reassign it to and no
        forced-outcome mechanism exists to give it one (unlike scatter counts,
        boss damage can't be forced onto a board). Keeping the reward as a
        base-game win sidesteps that structural conflict entirely.
        """
        bonus_amount = self.config.boss_defeat_bonus_multiplier
        self.win_manager.update_spinwin(bonus_amount)
        self.record(
            {
                "kind": "bossBattleWon",
                "symbol": "boss",
                "gametype": self.gametype,
            }
        )
        boss_bonus_event(self, bonus_amount)

    # --- Boss Battle mechanic (free spins) -------------------------------------
    def reset_freegame_boss_wave(self):
        """Spawn/respawn a fresh wave of 3 bosses at full HP. Called at the start
        of every free-spin session (reset_fs_spin) and again immediately whenever
        a wave is fully cleared, so the fight continues for the rest of the
        round. Unlike the base-game battle, HP persists across every spin/tumble
        within the session - it only resets between waves or at session start."""
        self.fs_boss_hp = {boss_id: self.config.freegame_boss_max_hp for boss_id in self.config.boss_zones}
        self.fs_boss_rewarded = set()

    def apply_freegame_boss_damage(self):
        """Free-spin equivalent of apply_boss_damage: same column-zone damage and
        full-span bonus math, but against the free-spin boss wave's own HP pool
        (self.fs_boss_hp), which survives across the whole session rather than
        resetting every spin. Replaces the 0_0_cluster template's escalating grid
        multiplier as this game's free-spin mechanic.

        Defeating an individual boss pays config.boss_defeat_reward_multiplier
        instantly (once per boss per wave); clearing all 3 additionally pays
        config.boss_wave_clear_bonus_multiplier, then a fresh wave spawns.
        """
        if self.win_data.get("totalWin", 0) > 0:
            last_reel = self.config.num_reels - 1
            for win in self.win_data["wins"]:
                reels_hit = {pos["reel"] for pos in win["positions"]}
                full_span = 0 in reels_hit and last_reel in reels_hit
                damage = win["win"]
                if full_span:
                    damage *= self.config.boss_full_span_damage_multiplier

                for boss_id, (lo_reel, hi_reel) in self.config.boss_zones.items():
                    if self.fs_boss_hp[boss_id] <= 0:
                        continue
                    if reels_hit & set(range(lo_reel, hi_reel + 1)):
                        self.fs_boss_hp[boss_id] = max(0.0, self.fs_boss_hp[boss_id] - damage)

            for boss_id in list(self.fs_boss_hp.keys()):
                if self.fs_boss_hp[boss_id] <= 0 and boss_id not in self.fs_boss_rewarded:
                    self.fs_boss_rewarded.add(boss_id)
                    reward = self.config.boss_defeat_reward_multiplier
                    self.win_manager.update_spinwin(reward)
                    self.record(
                        {"kind": "bossDefeated", "symbol": "boss", "bossId": boss_id, "gametype": self.gametype}
                    )
                    boss_bonus_event(self, reward)

        wave_cleared = all(hp <= 0 for hp in self.fs_boss_hp.values())
        boss_damage_event(self, self.fs_boss_hp, self.config.freegame_boss_max_hp, wave_cleared)

        if wave_cleared:
            bonus = self.config.boss_wave_clear_bonus_multiplier
            self.win_manager.update_spinwin(bonus)
            self.record({"kind": "bossWaveCleared", "symbol": "boss", "gametype": self.gametype})
            boss_bonus_event(self, bonus)
            self.reset_freegame_boss_wave()

    def get_clusters_update_wins(self):
        """Find clusters on board and update win manager."""
        clusters = Cluster.get_clusters(self.board, "wild")
        return_data = {
            "totalWin": 0,
            "wins": [],
        }
        self.board, self.win_data = self.evaluate_clusters_with_grid(
            config=self.config,
            board=self.board,
            clusters=clusters,
            pos_mult_grid=self.position_multipliers,
            global_multiplier=self.global_multiplier,
            return_data=return_data,
        )

        Cluster.record_cluster_wins(self)
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        self.win_manager.tumble_win = self.win_data["totalWin"]

    def update_freespin(self) -> None:
        """Called before a new reveal during freegame."""
        self.fs += 1
        update_freespin_event(self)
        self.win_manager.reset_spin_win()
        self.tumblewin_mult = 0
        self.win_data = {}

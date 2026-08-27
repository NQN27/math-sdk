from game_override import GameStateOverride


class GameState(GameStateOverride):
    """Core function handling simulation results."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            # Reset simulation variables and draw a new board based on the betmode criteria.
            self.reset_book()
            self.draw_board()

            self.get_clusters_update_wins()
            self.apply_boss_damage()
            self.emit_tumble_win_events()

            while self.win_data["totalWin"] > 0 and not (self.wincap_triggered):
                self.tumble_game_board()
                self.get_clusters_update_wins()
                self.apply_boss_damage()
                self.emit_tumble_win_events()

            self.set_end_tumble_event()

            if self.check_bosses_defeated():
                # Defeating all 3 bosses awards an instant base-game bonus win,
                # added to this spin before it's committed to basegame_wins - see
                # award_boss_bonus() docstring for why this must stay a base-game
                # win rather than a separate free-spin session.
                self.award_boss_bonus()

            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition() and self.check_freespin_entry():
                self.run_freespin_from_base()

            self.evaluate_finalwin()
            self.check_repeat()

        self.imprint_wins()

    def run_freespin(self):
        self.reset_fs_spin()
        while self.fs < self.tot_fs:
            self.update_freespin()
            self.draw_board()

            self.get_clusters_update_wins()
            self.apply_freegame_boss_damage()
            self.emit_tumble_win_events()
            while self.win_data["totalWin"] > 0 and not (self.wincap_triggered):
                self.tumble_game_board()
                self.get_clusters_update_wins()
                self.apply_freegame_boss_damage()
                self.emit_tumble_win_events()

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition():
                self.update_fs_retrigger_amt()

        self.end_freespin()

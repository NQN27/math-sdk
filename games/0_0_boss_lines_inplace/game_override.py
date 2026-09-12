from game_bonus import GameBonus


class GameStateOverride(GameBonus):
    """Override/extend universal state.py functions with this game's own
    book-reset requirements."""

    def reset_book(self) -> None:
        """Reset per-book state, including a fresh boss battle (stage 1,
        freshly-rolled bosses - see game_executables.reset_boss_battle), a
        fresh Power system (global_multi_total back to 0/inactive, FIFO
        queue emptied - see game_executables.reset_power_system), and
        (Phase 3) a fresh Bonus/Scatter-tally state (see
        game_bonus.reset_bonus_state - Player HP/tier/etc only ever exist
        DURING an active Bonus session; the base boss-battle/Power resets
        here are also what every Bonus session's OWN reset looks like, just
        called again from game_bonus.run_bonus_session instead, since a
        session spans many of this file's "spins" worth of internal Bonus
        spins with that state deliberately NOT reset per-internal-spin)."""
        super().reset_book()
        self.pass_exploded_positions = []
        # Phase 4: Ultimate Power/God Mode start at a forced, randomly-
        # chosen stage (see game_executables.resolve_feature_start_stage) -
        # every other bet mode ("base"/"ante"/"buy3"/"buy4", none of which
        # appear in self.config.feature_spin_start_stage_choices) resolves
        # to the SAME literal `1` reset_boss_battle's own default already
        # used, with NO extra randomness consumed (dict.get on a name not in
        # the dict short-circuits before any random.choice call) - so this
        # is byte-for-byte unchanged for "base".
        self.reset_boss_battle(start_stage=self.resolve_feature_start_stage())
        self.reset_power_system()
        self.reset_bonus_state()

    def assign_special_sym_function(self) -> None:
        """No per-symbol-creation special behaviour needed this phase (Wild
        substitution is handled entirely by src.calculations.lines.Lines;
        Wild's 2x-damage rule is resolved at explode-time in
        game_calculations.evaluate_and_explode, not at symbol-creation
        time)."""
        self.special_symbol_functions = {}

from game_executables import GameExecutables


class GameStateOverride(GameExecutables):
    """Per-book state resets for Boss Lines v3."""

    def reset_book(self) -> None:
        super().reset_book()
        self.in_bonus = False
        self.bonus_tier = None
        self.free_spins_left = 0
        self.heroic = False
        self.treasure_hunt = False
        self.no_scatter_spin = False
        self.force_wincap = False
        self.global_mult = 0
        self.reserve = {p: 0 for p in self.config.power_names}
        self.lit = set()
        self.last_endless_hp = None
        self.bosses = []
        self.stage = None
        self.stage_cleared = False
        self.reel_name = "BR0"
        self.enhance = [[0] * 5 for _ in range(6)]
        self.wild_mult = {}
        self.darkened = set()
        self.spin_had_scatter = False
        self.actions = 0
        self.accidental_bonus = False
        self.cap_hits = {}

    def assign_special_sym_function(self) -> None:
        self.special_symbol_functions = {}

    def check_repeat(self) -> None:
        super().check_repeat()
        if self.repeat:
            return
        win_criteria = self.get_current_betmode_distributions().get_win_criteria()
        if self.accidental_bonus:
            self.repeat = True
        elif (self.config.reject_wincap_outside_wincap_fence and self.criteria != "wincap"
              and self.final_win >= self.config.wincap):
            self.repeat = True
        elif win_criteria is None and self.final_win == 0 and self.criteria == "basegame":
            self.repeat = True

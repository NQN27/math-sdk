"""Phase D part 1: stage 0 (base/ante boss fight) + new Bonus trigger rule."""


def patch(path, pairs):
    t = open(path, encoding='utf-8').read()
    for a, b in pairs:
        assert t.count(a) == 1, (path, a[:60], t.count(a))
        t = t.replace(a, b)
    open(path, 'w', encoding='utf-8').write(t)


patch('game_config.py', [
    ('        self.boss_stage_table = {\n', '''        self.boss_stage_table = {
            # v2 stage 0 (base/ante spins): every boss has FIXED HP 20 (see
            # game_executables.roll_stage_bosses's stage-0 branch).
            0: {"boss1": (1, 20.0), "boss2": (1, 20.0), "boss3": (1, 20.0)},
'''),
    ('self.use_flat_damage = {"normal": False, "super": True, "hidden": False}',
     'self.use_flat_damage = {"normal": False, "super": True, "hidden": False, "base": True}'),
    ('self.bonus_scatter_tier_by_count = {3: "normal", 4: "super", 5: "hidden"}',
     '''# v2: Bonus is triggered by clearing the stage-0 bosses; the scatter
        # count on that spin picks the tier: <3 -> Bonus (normal), 3 -> Super,
        # 4 -> Mega (internal name "hidden"), 5+ -> instant Maxwin.
        self.bonus_scatter_tier_by_count = {0: "normal", 1: "normal", 2: "normal", 3: "super", 4: "hidden"}
        self.bonus_maxwin_scatter_count = 5'''),
    ('self.freegame_trigger_count_weights = {3: 92, 4: 7.8, 5: 0.2}',
     'self.freegame_trigger_count_weights = {0: 92, 3: 7.8, 4: 0.2}  # v2: scatter count -> tier shifted (0=Bonus,3=Super,4=Mega)'),
    ('self.buy4_scatter_count_weights = {4: 97.5, 5: 2.5}', 'self.buy4_scatter_count_weights = {3: 97.5, 4: 2.5}'),
    ('        self.chest_upgrade_chance = ', '''        # Stage 0 (base/ante): drops draw from EVERY chest's multis plus 0x.
        self.chest_stage0_zero_weight = 40
        self.chest_upgrade_chance = '''),
])

patch('game_executables.py', [
    ('''        base = self.config.boss_stage_table[stage]
        lo, hi = self.config.boss_variance_range''', '''        base = self.config.boss_stage_table[stage]
        if stage == 0:
            # v2: base/ante boss fight - fixed HP, no variance.
            self.boss_dam = {b: base[b][0] for b in self.config.boss_ids}
            self.boss_hp = {b: float(base[b][1]) for b in self.config.boss_ids}
            self.boss_hp_max = {b: float(base[b][1]) for b in self.config.boss_ids}
            self.boss_alive = {b: True for b in self.config.boss_ids}
            self.stage_defeat_order = []
            return
        lo, hi = self.config.boss_variance_range'''),
    ('''        if betmode_name is None:
            return 1
        choices = self.config.feature_spin_start_stage_choices.get(betmode_name)
        return random.choice(choices) if choices else 1''', '''        if betmode_name is None:
            return 0
        choices = self.config.feature_spin_start_stage_choices.get(betmode_name)
        return random.choice(choices) if choices else 0  # v2: base/ante fight at stage 0'''),
    ('''        weights = cfg.chest_type_weights_by_stage[min(stage, cfg.max_stage)]
        if top_last:''', '''        if stage == 0:
            pool = {0: cfg.chest_stage0_zero_weight}
            for name in cfg.chest_order:
                pool.update(cfg.chest_multi_weights[name])
            self.last_chest_type = "stage0"
            tier = get_random_outcome(pool)
            return tier, float(tier)
        weights = cfg.chest_type_weights_by_stage[min(stage, cfg.max_stage)]
        if top_last:'''),
    ('''        next_stage = stage + 1
        if next_stage > self.config.max_stage:''', '''        next_stage = stage + 1
        if stage == 0:
            # v2: clearing the base/ante boss fight is what qualifies the
            # spin for a Bonus (see gamestate.run_spin); the fight ends here.
            self.base_bosses_cleared = True
            self.boss_system_active = False
            return
        if next_stage > self.config.max_stage:'''),
])

patch('game_calculations.py', [
    ('        flat_damage_tier = getattr(self, "bonus_tier", None)\n', '        flat_damage_tier = getattr(self, "bonus_tier", None) or "base"\n'),
])

patch('game_bonus.py', [
    ('''        return self.config.bonus_scatter_tier_by_count.get(len(self.scatter_columns))''',
     '''        n = len(self.scatter_columns)
        if not getattr(self, "base_bosses_cleared", False):
            return None  # v2: no Bonus unless the stage-0 bosses were all defeated
        if n >= self.config.bonus_maxwin_scatter_count:
            return "maxwin"
        return self.config.bonus_scatter_tier_by_count.get(n)'''),
])

patch('game_override.py', [
    ('        super().reset_book()\n', '        super().reset_book()\n        self.base_bosses_cleared = False\n'),
])

patch('gamestate.py', [
    ('''            tier = self.resolve_bonus_tier()
            if tier is not None:
                if self.criteria == "freegame":''', '''            tier = self.resolve_bonus_tier()
            if tier == "maxwin":
                # v2: 5 scatters + all stage-0 bosses defeated = instant Maxwin,
                # only ever produced on the dedicated "wincap" fence.
                if self.criteria == "wincap":
                    self.award_win(self.config.wincap)
                else:
                    self.repeat = True
            elif tier is not None:
                if self.criteria == "freegame":'''),
])
print("d1 patched")

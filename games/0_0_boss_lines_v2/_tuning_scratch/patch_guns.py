"""Phase C part 2: guns replace Booster. Run once from the game folder."""
b = open('game_bonus.py', encoding='utf-8').read()


def rb(a, c):
    global b
    assert b.count(a) == 1, (a[:50], b.count(a))
    b = b.replace(a, c)


rb('''        return self.count_symbols_on_board("EL") > 0 or self.count_symbols_on_board("BO") > 0''',
   '''        return (
            self.count_symbols_on_board("EL") > 0
            or self.count_symbols_on_board("GS") > 0
            or self.count_symbols_on_board("GL") > 0
        )

    def _activate_guns(self) -> list:
        """v2 guns (replace Booster). Each gun on the board fires once, is
        consumed (exploded), and deals damage = a random 10%..100% step of
        the LARGEST current Max HP among the bosses it can hit, rounded,
        min gun_min_damage. Short gun ("GS"): only the boss owning its
        column. Long gun ("GL"): every alive boss. Last-hit (execute) roll
        applies to Short gun damage only, not Long gun. Returns fired
        [(reel, row, kind, damage)] for the event."""
        cfg = self.config
        fired = []
        guns = []
        for kind in ("GS", "GL"):
            for p in self.get_symbol_positions(kind)[kind]:
                guns.append((p["reel"], p["row"], kind))
        for r, ro, kind in sorted(guns):
            self.board[r][ro].explode = True
            if not self.boss_system_active:
                continue
            if kind == "GS":
                boss = self.route_boss_for_column(r)
                targets = [boss] if self.boss_alive.get(boss, False) else []
            else:
                targets = [bid for bid in cfg.boss_ids if self.boss_alive.get(bid, False)]
            if not targets:
                fired.append((r, ro, kind, 0))
                continue
            top_hp = max(self.boss_hp_max[t] for t in targets)
            dmg = max(cfg.gun_min_damage, int(round(random.choice(cfg.gun_pct_choices) * top_hp)))
            original_stage = self.stage
            for t in targets:
                if self.stage != original_stage or not self.boss_alive.get(t, False):
                    break  # a kill this gun caused already cleared the stage
                col = next(c for c, bid in cfg.boss_primary_zone.items() if bid == t)
                pass_start_hp = dict(self.boss_hp)
                self._pass_boss_damage_totals = {}
                self.deal_damage_to_boss(col, dmg)
                if kind == "GS" and self._pass_boss_damage_totals:
                    self.resolve_pass_last_hit(pass_start_hp)
            self._pass_boss_damage_totals = {}
            fired.append((r, ro, kind, dmg))
        return fired''')
# replace the BO block in _activate_elixir_booster
rb('''        bo_positions = sorted((p["reel"], p["row"]) for p in self.get_symbol_positions("BO")["BO"])
''', '''        bo_positions = []  # v2: Booster removed, see _activate_guns
''')
rb('''        if bo_positions:
            for r, ro in bo_positions:
                self.board[r][ro].explode = True
            self.booster_pending_for_next_spin = True
            booster_activated_event(self, bo_positions)

        if el_positions or bo_positions:''', '''        fired = self._activate_guns()
        if fired:
            gun_activated_event(self, fired)

        if el_positions or fired:''')
rb('    booster_activated_event,', '    gun_activated_event,')
open('game_bonus.py', 'w', encoding='utf-8').write(b)

ev = open('game_events.py', encoding='utf-8').read()
ev += '''

GUN_ACTIVATED = "gunActivated"


def gun_activated_event(gamestate, fired):
    """v2: guns fired this pass. `fired` = [(reel, row, kind, damage)],
    kind "GS" (short, one column's boss) or "GL" (long, all bosses)."""
    event = {
        "index": len(gamestate.book.events),
        "type": GUN_ACTIVATED,
        "guns": [
            {"reel": r, "row": _padded_row(gamestate, ro), "kind": kind, "damage": dmg}
            for r, ro, kind, dmg in fired
        ],
    }
    gamestate.book.add_event(event)
'''
open('game_events.py', 'w', encoding='utf-8').write(ev)
print("ok")

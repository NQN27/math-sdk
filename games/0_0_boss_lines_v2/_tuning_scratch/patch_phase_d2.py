"""Phase D part 2: Coin mechanic, Full board coin, God Mode changes, last-hit +3%."""
import csv
import glob


def patch(path, pairs):
    t = open(path, encoding='utf-8').read()
    for a, b in pairs:
        assert t.count(a) == 1, (path, a[:70], t.count(a))
        t = t.replace(a, b)
    open(path, 'w', encoding='utf-8').write(t)


# (config part already applied; coin block relocated after the chest block)
# ---------------- reels: put Power Coin into reels ----------------
n = 0
for f in glob.glob('reels/*.csv'):
    rows = list(csv.reader(open(f, newline='')))
    for i, r in enumerate(rows):
        for j, x in enumerate(r):
            if x == "PUP" and 0 < j < 5:
                n += 1
                if n % 3 == 0:
                    r[j] = "PCN"
    csv.writer(open(f, 'w', newline='')).writerows(rows)

# ---------------- executables ----------------
patch('game_executables.py', [
    ('''            "upgrade": self.power_upgrade,''', '''            "upgrade": self.power_upgrade,
            "coin": self.power_coin,'''),
    ('''        if getattr(self.config, "use_inplace_tumble", False):
            self._tumble_board_in_place()''', '''        # v2 coin mechanic: remember every cell position that has vanished.
        vc = getattr(self, "vanished_cells", None)
        if vc is not None:
            for r in range(self.config.num_reels):
                for ro in range(self.config.num_rows[r]):
                    if self.board[r][ro].explode:
                        vc.add((r, ro))
        if getattr(self.config, "use_inplace_tumble", False):
            self._tumble_board_in_place()'''),
    ('''            for col in (1, 2, 3):  # columns 2,3,4 (1-indexed) = reel index 1,2,3''',
     '''            for col in range(1, self.config.num_reels - 1):  # v2: every inner column'''),
    ('''            chance = (1 - hp_frac) * self.config.boss_last_hit_scale + self.config.boss_last_hit_base_chance''',
     '''            chance = (1 - hp_frac) * self.config.boss_last_hit_scale + self.config.boss_last_hit_base_chance
            if (
                getattr(self, "in_bonus", False)
                and self.config.use_spin_budget.get(getattr(self, "bonus_tier", None), False)
                and self.spins_remaining <= 0
                and not getattr(self, "spin_had_scatter", False)
            ):
                chance += self.config.boss_last_hit_final_spin_bonus  # v2: final spin, no scatter'''),
])

# append coin methods to executables
e = open('game_executables.py', encoding='utf-8').read()
e += '''
    # --- v2 Coin mechanic ---------------------------------------------------
    def power_coin(self) -> None:
        """Power Coin connected: the coin mechanic runs LAST, at static state
        (see gamestate.run_spin / game_bonus.run_one_bonus_spin)."""
        self.coin_pending = True
        power_activated_event(self, "coin", {})

    def _make_coin_cell(self, kind: str):
        """Build the Symbol for one coin-mechanic cell type."""
        cfg = self.config
        if kind == "coin":
            sym = self.create_symbol("CN")
            sym.has_prize = True
            sym.prize = get_random_outcome(cfg.coin_multi_weights)
        elif kind == "chest":
            sym = self.create_symbol("CH")
        elif kind == "clover":
            sym = self.create_symbol("CV")
            sym.has_prize = True
            sym.prize = get_random_outcome(cfg.coin_clover_factor_weights)
        elif kind == "global":
            sym = self.create_symbol("CG")
            sym.has_prize = True
            sym.prize = get_random_outcome(cfg.coin_global_factor_weights)
        elif kind == "scatter":
            sym = self.create_symbol("SC")
        elif kind == "gun_s":
            sym = self.create_symbol("GS")
        else:
            sym = self.create_symbol("GL")
        return sym

    def run_coin_phase(self, full_board: bool = False) -> None:
        """v2 Coin mechanic. Every vanished cell (every cell when
        `full_board`) becomes a coin-mechanic cell, then, in order:
        clover (x its 8 neighbours' coin values and gun damage) ->
        global multi (adds to the session-long global total) -> chest
        (collects all coins, empties them, re-drops coins once) -> guns fire
        -> scatter (+1 spin per scatter in Bonus, counts toward the trigger
        in base) -> coins are paid, x the global multi total. Coin payouts
        ignore drop-boss multis; gun damage ignores global multi."""
        cfg = self.config
        self.coin_pending = False
        if full_board:
            cells = [(r, ro) for r in range(cfg.num_reels) for ro in range(cfg.num_rows[r])]
        else:
            cells = sorted(getattr(self, "vanished_cells", set()))
        if not cells:
            return
        weights = dict(cfg.coin_cell_weights)
        if self.get_current_betmode_name() == "godmode":
            weights.pop("scatter", None)  # God Mode has no scatter, even via coins
        grid = {}
        for r, ro in cells:
            grid[(r, ro)] = get_random_outcome(weights)
            self.board[r][ro] = self._make_coin_cell(grid[(r, ro)])

        def neighbours(r, ro):
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if (dr or dc) and (r + dr, ro + dc) in grid:
                        yield (r + dr, ro + dc)

        gun_mult = {}
        for (r, ro), kind in sorted(grid.items()):
            if kind == "clover":
                f = self.board[r][ro].prize
                for pos in neighbours(r, ro):
                    k = grid[pos]
                    if k == "coin":
                        self.board[pos[0]][pos[1]].prize *= f
                    elif k in ("gun_s", "gun_l"):
                        gun_mult[pos] = gun_mult.get(pos, 1) * f
        for (r, ro), kind in sorted(grid.items()):
            if kind == "global":
                self.global_multi_total += self.board[r][ro].prize

        collected = 0.0
        if any(k == "chest" for k in grid.values()):
            for pos, k in sorted(grid.items()):
                if k == "coin":
                    collected += self.board[pos[0]][pos[1]].prize
                    grid[pos] = "empty"
            for pos, k in sorted(grid.items()):
                if k == "empty" and random.random() < cfg.coin_chest_redrop_chance:
                    grid[pos] = "coin"
                    self.board[pos[0]][pos[1]] = self._make_coin_cell("coin")

        fired = []
        for (r, ro), kind in sorted(grid.items()):
            if kind in ("gun_s", "gun_l"):
                dmg = self._fire_gun(r, "GS" if kind == "gun_s" else "GL", gun_mult.get((r, ro), 1))
                fired.append((r, ro, "GS" if kind == "gun_s" else "GL", dmg))
        if fired:
            gun_activated_event(self, fired)

        n_scatter = sum(1 for k in grid.values() if k == "scatter")
        if n_scatter:
            self.spin_had_scatter = True
            if getattr(self, "in_bonus", False):
                if self.config.use_spin_budget.get(self.bonus_tier, False):
                    self.spins_remaining += n_scatter
            else:
                for (r, ro), k in grid.items():
                    if k == "scatter":
                        self.scatter_columns.add(r)

        coin_sum = collected + sum(self.board[r][ro].prize for (r, ro), k in grid.items() if k == "coin")
        g = self.global_multi_total if self.global_multi_total > 0 else 1
        paid = self.award_win(coin_sum * g) if coin_sum > 0 else 0.0
        coin_phase_event(
            self,
            {
                "fullBoard": full_board,
                "cells": [{"reel": r, "row": ro, "kind": k} for (r, ro), k in sorted(grid.items())],
                "coinSum": coin_sum,
                "globalMulti": g,
                "paid": paid,
            },
        )
'''
open('game_executables.py', 'w', encoding='utf-8').write(e)

# bonus: refactor gun firing into _fire_gun, hook coin phase
b = open('game_bonus.py', encoding='utf-8').read()
a0 = b.index('        for r, ro, kind in sorted(guns):')
a1 = b.index('        return fired', a0)
b = b[:a0] + '''        for r, ro, kind in sorted(guns):
            self.board[r][ro].explode = True
            fired.append((r, ro, kind, self._fire_gun(r, kind, 1)))
''' + b[a1:]
b = b.replace('''    def _activate_guns(self) -> list:''', '''    def _fire_gun(self, r: int, kind: str, mult: float = 1) -> int:
        """Fire one gun in column `r`; returns the damage dealt (0 if it had
        no living target). `mult` is a Clover factor. Short gun ("GS") hits
        the column's boss and may trigger the last-hit roll; long gun ("GL")
        hits every alive boss and never last-hits."""
        cfg = self.config
        if not self.boss_system_active:
            return 0
        if kind == "GS":
            boss = self.route_boss_for_column(r)
            targets = [boss] if self.boss_alive.get(boss, False) else []
        else:
            targets = [bid for bid in cfg.boss_ids if self.boss_alive.get(bid, False)]
        if not targets:
            return 0
        top_hp = max(self.boss_hp_max[t] for t in targets)
        dmg = max(cfg.gun_min_damage, int(round(random.choice(cfg.gun_pct_choices) * top_hp)))
        dmg = int(round(dmg * mult))
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
        return dmg

    def _activate_guns(self) -> list:''', 1)
old_start = b.index('        """v2 guns (replace Booster).')
open('game_bonus.py', 'w', encoding='utf-8').write(b)

patch('game_bonus.py', [
    ('''            if self._board_has_elixir_or_booster():
                self._activate_elixir_booster()''', '''            if getattr(self, "coin_pending", False):
                self.run_coin_phase()
                passes += 1
                continue
            if self._board_has_elixir_or_booster():
                self._activate_elixir_booster()'''),
    ('''        self.win_manager.reset_spin_win()
        self.pass_exploded_positions = []
        self.chain_pass_count = 0''', '''        self.win_manager.reset_spin_win()
        self.pass_exploded_positions = []
        self.vanished_cells = set()
        self.coin_pending = False
        self.spin_had_scatter = False
        self.chain_pass_count = 0'''),
])

patch('game_override.py', [
    ('        self.base_bosses_cleared = False\n', '        self.base_bosses_cleared = False\n        self.vanished_cells = set()\n        self.coin_pending = False\n        self.spin_had_scatter = False\n'),
])

patch('game_events.py', [
    ('GUN_ACTIVATED = "gunActivated"', 'GUN_ACTIVATED = "gunActivated"\nCOIN_PHASE = "coinPhase"'),
])
ev = open('game_events.py', encoding='utf-8').read()
ev += '''

def coin_phase_event(gamestate, details):
    """v2 coin mechanic resolved: cell kinds, coin sum, global multi, payout."""
    event = {"index": len(gamestate.book.events), "type": COIN_PHASE, **details}
    gamestate.book.add_event(event)
'''
open('game_events.py', 'w', encoding='utf-8').write(ev)

# gamestate: coin phase at static state + full-board feature spin
patch('gamestate.py', [
    ('''            self.accumulate_scatter_columns()
            reveal_event(self)

            self.evaluate_and_explode()
            self.emit_tumble_win_events()
            self.emit_pass_extra_events()

            passes = 1''', '''            self.accumulate_scatter_columns()
            reveal_event(self)

            # v2 Feature spin ("godmode" bet mode): sometimes the bought spin
            # is the Full-board-coin variant instead of God Mode.
            full_board = (
                self.get_current_betmode().get_name() == "godmode"
                and random.random() < self.config.feature_full_board_coin_chance
            )
            if full_board:
                self.run_coin_phase(full_board=True)
                self.win_data = {"totalWin": 0, "wins": []}
                self.win_manager.tumble_win = 0.0
            else:
                self.evaluate_and_explode()
            self.emit_tumble_win_events()
            self.emit_pass_extra_events()

            passes = 1'''),
    ('''            if passes >= self.config.max_resolve_passes:
                warnings.warn(''', '''            # v2: the coin mechanic activates LAST, at static state.
            if getattr(self, "coin_pending", False) and not self.wincap_triggered:
                self.run_coin_phase()
            if passes >= self.config.max_resolve_passes:
                warnings.warn('''),
    ('import warnings\n', 'import random\nimport warnings\n'),
])
patch('game_executables.py', [
    ('from game_events import (', 'from game_events import (\n    coin_phase_event,\n    gun_activated_event,'),
])
print("d2 patched")

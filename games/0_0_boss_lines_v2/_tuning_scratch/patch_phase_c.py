"""One-shot Phase C patch (2026-09-30). Run once from the game folder."""
import glob
import csv

# ---------------- config ----------------
s = open('game_config.py', encoding='utf-8').read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (a[:60], s.count(a))
    s = s.replace(a, b)


rep('self.power_immediate_names = {"PWM": "wild_multi", "PGM": "global_multi", "PMX": "maxwin"}',
    'self.power_immediate_names = {"PMX": "maxwin"}')
a = s.index('        self.power_fifo_names = {')
b = s.index('        }\n', a) + len('        }\n')
s = s[:a] + '''        # v2 (DESIGN_CHANGES_v2.md sec 2): Mystery/Big Symbol/Extra Power/Alter
        # removed; Global Multi no longer a board symbol (Coin mechanic only,
        # Phase D); Wild Multi is now a delayed FIFO power; Upgrade added.
        self.power_fifo_names = {"PWM": "wild_multi", "PXW": "extra_wild", "PUP": "upgrade"}
''' + s[b:]
rep('"booster": ["BO"],', '"gun": ["GS", "GL"],  # v2: guns replace Booster ("BO")')
rep('"SC": "Scatter", "EL": "Elixir", "BO": "Booster",',
    '"SC": "Scatter", "EL": "Elixir", "GS": "Short Gun", "GL": "Long Gun", "PUP": "Upgrade",')
rep('        self.extra_wild_count_range = (3, 10)', '''        # v2 Wild Multi (delayed power): factor rolled at activation and
        # applied to every cell of ONE randomly chosen symbol on the board.
        self.wild_multi_factor_weights = {2: 40, 3: 25, 5: 15, 10: 10, 20: 6, 50: 3, 100: 1}
        # v2 Upgrade power: 1-3 random ordinary cells become H5 or Wild.
        self.upgrade_count_range = (1, 3)
        self.upgrade_target_weights = {"H5": 1, "W": 1}
        # v2 Extra Wild may land Power symbols too (never in first/last col).
        self.extra_wild_power_chance = 0.3
        self.extra_wild_power_choices = ["PWM", "PUP"]
        # v2 guns: damage = pct of the largest current Max HP among the
        # bosses the gun can hit, pct uniform over 10%..100%, min 5.
        self.gun_pct_choices = [round(0.1 * i, 1) for i in range(1, 11)]
        self.gun_min_damage = 5
        self.extra_wild_count_range = (3, 10)''')
open('game_config.py', 'w', encoding='utf-8').write(s)

# ---------------- reels ----------------
for f in glob.glob('reels/*.csv'):
    rows = list(csv.reader(open(f, newline='')))
    out = []
    for i, r in enumerate(rows):
        r = list(r)
        for j, x in enumerate(r):
            if x == "BO":
                r[j] = "GS" if (i + j) % 2 else "GL"
            elif x == "PBS":
                r[j] = "PUP"
            elif x == "PMY":
                r[j] = "PWM"
            elif x in ("PGM", "PXP", "PAL"):
                r[j] = "PUP" if (i % 2) else "PWM"
        if i % 15 == 7 and r[0] != "SC":
            r[0] = "W"
        if r[0].startswith("P") and r[0] != "PMX":
            r[0] = "W"
        if r[5].startswith("P"):
            r[5] = "W"
        out.append(r)
    csv.writer(open(f, 'w', newline='')).writerows(out)

# ---------------- executables ----------------
e = open('game_executables.py', encoding='utf-8').read()
i = e.index('    def power_extra_wild(self) -> None:')
e = e[:i] + '''    def power_extra_wild(self) -> None:
        """3-10 random cells (any column, never overwriting an existing
        Wild/Power) become Wild - or, with extra_wild_power_chance, a Power
        symbol (Power never lands in the first/last column, so those cells
        always take a plain Wild)."""
        cfg = self.config
        n = random.randint(*cfg.extra_wild_count_range)
        cells = self._open_power_placement_cells()
        random.shuffle(cells)
        chosen = cells[:n]
        placed = []
        for r, ro in chosen:
            name = "W"
            if 0 < r < cfg.num_reels - 1 and random.random() < cfg.extra_wild_power_chance:
                name = random.choice(cfg.extra_wild_power_choices)
            self.board[r][ro] = self.create_symbol(name)
            placed.append({"reel": r, "row": ro, "symbol": name})
        power_activated_event(self, "extra_wild", {"count": len(chosen), "placements": placed})

    def power_wild_multi(self) -> None:
        """v2 delayed Wild Multi: pick one symbol currently on the board
        (L1-L4 / H1-H5 / W), roll a factor and stamp it on EVERY cell of
        that symbol. The factor lives on the Symbol object (`cell_mult`), so
        it follows the cell through tumbles and vanishes with it; a fresh
        board (next spin) starts clean. Stacks additively on a cell that
        already has one."""
        cfg = self.config
        candidates = set()
        for r in range(cfg.num_reels):
            for ro in range(cfg.num_rows[r]):
                nm = self.board[r][ro].name
                if nm == "W" or nm in cfg.normal_paying_symbols:
                    candidates.add(nm)
        if not candidates:
            return
        target = random.choice(sorted(candidates))
        factor = get_random_outcome(cfg.wild_multi_factor_weights)
        cells = []
        for r in range(cfg.num_reels):
            for ro in range(cfg.num_rows[r]):
                sym = self.board[r][ro]
                if sym.name == target:
                    cur = getattr(sym, "cell_mult", 1)
                    sym.cell_mult = factor if cur <= 1 else cur + factor
                    cells.append({"reel": r, "row": ro, "mult": sym.cell_mult})
        power_activated_event(self, "wild_multi", {"symbol": target, "factor": factor, "cells": cells})

    def power_upgrade(self) -> None:
        """v2 Upgrade: 1-3 random ordinary paying cells become H5 or Wild."""
        cfg = self.config
        n = random.randint(*cfg.upgrade_count_range)
        cells = [
            (r, ro)
            for r in range(cfg.num_reels)
            for ro in range(cfg.num_rows[r])
            if self.board[r][ro].name in cfg.normal_paying_symbols
        ]
        random.shuffle(cells)
        changed = []
        for r, ro in cells[:n]:
            name = get_random_outcome(cfg.upgrade_target_weights)
            self.board[r][ro] = self.create_symbol(name)
            changed.append({"reel": r, "row": ro, "symbol": name})
        power_activated_event(self, "upgrade", {"count": len(changed), "changes": changed})
'''


def rp(a, b):
    global e
    assert e.count(a) == 1, (a[:50], e.count(a))
    e = e.replace(a, b)


rp('''            "extra_wild": self.power_extra_wild,
            "extra_power": self.power_extra_power,
            "big_symbol": self.power_big_symbol,
            "mystery": self.power_mystery,
            "alter": self.power_alter,''', '''            "wild_multi": self.power_wild_multi,
            "extra_wild": self.power_extra_wild,
            "upgrade": self.power_upgrade,''')
rp('''        for r in range(1, self.config.num_reels):
            for ro in range(self.config.num_rows[r]):
                if not self.board[r][ro].check_attribute("wild"):
                    cells.append((r, ro))
        return cells''', '''        for r in range(self.config.num_reels):  # v2: Wild may land in any column
            for ro in range(self.config.num_rows[r]):
                if not self.board[r][ro].check_attribute("wild"):
                    cells.append((r, ro))
        return cells''')
rp('''        eligible = self._open_power_placement_cells()
        random.shuffle(eligible)
        for r, ro in eligible[:needed]:''', '''        # v2: Power never lands in the first/last column.
        eligible = [c for c in self._open_power_placement_cells() if 0 < c[0] < self.config.num_reels - 1]
        random.shuffle(eligible)
        for r, ro in eligible[:needed]:''')
open('game_executables.py', 'w', encoding='utf-8').write(e)

# ---------------- calculations ----------------
c = open('game_calculations.py', encoding='utf-8').read()


def rc(a, b):
    global c
    assert c.count(a) == 1, (a[:50], c.count(a))
    c = c.replace(a, b)


rc('''                if ptype == "wild_multi":
                    wild_multi_cells.append(cell)
                elif ptype == "global_multi":''', '''                if ptype == "global_multi":''')
a = c.index('        # --- Wild Multi: one factor roll per physical cell')
b = c.index('        # --- Global Multi: immediate activation')
c = c[:a] + c[b:]
a = c.index('        adjusted_total = 0.0\n        wild_multi_line_events = []')
b = c.index('        adjusted_total = round(adjusted_total, 2)')
c = c[:a] + '''        # v2: a line's cells that carry a Wild-Multi factor (cell_mult, see
        # game_executables.power_wild_multi) ADD together into one line
        # factor; no factored cell -> x1. Global Multi (coin mechanic only)
        # still multiplies on top.
        adjusted_total = 0.0
        for win in win_data["wins"]:
            factors = []
            for pos in win["positions"]:
                m = getattr(self.board[pos["reel"]][pos["row"]], "cell_mult", 1)
                if m > 1:
                    factors.append(m)
            line_factor = sum(factors) if factors else 1
            adjusted = win["win"] * line_factor * effective_global
            win["win"] = round(adjusted, 2)
            win["meta"]["powerLineFactor"] = line_factor
            win["meta"]["globalMultApplied"] = effective_global
            adjusted_total += win["win"]

''' + c[b:]
rc('''        if wild_multi_line_events:
            power_activated_event(self, "wild_multi", {"lines": wild_multi_line_events})

''', '')
rc('''            self.deal_damage_to_boss(r, damage)''', '''            damage *= getattr(self.board[r][ro], "cell_mult", 1)  # v2: damage x per-cell factor
            self.deal_damage_to_boss(r, damage)''')
open('game_calculations.py', 'w', encoding='utf-8').write(c)
print("patched")

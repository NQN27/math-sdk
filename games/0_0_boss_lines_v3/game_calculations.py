"""Board drawing, in-place refill, line evaluation and payout for Boss Lines v3.

Cell-bound state (Enhance factors, lit cells, held cells) is keyed by
(column, row): destroyed cells are refilled IN PLACE (QUESTIONS.md Q0), so a
cell keeps its identity for the whole spin.
"""

import random

from src.executables.executables import Executables
from src.calculations.lines import Lines
from src.calculations.statistics import get_random_outcome
from src.events.events import wincap_event
from game_events import emit, pos


class GameCalculations(Executables):
    """Board / lines / payout helpers."""

    # ---- symbol helpers ---------------------------------------------------------
    def is_basic(self, sym) -> bool:
        return sym is not None and sym.name in self.config.basic_symbols

    def is_wild(self, sym) -> bool:
        return sym is not None and sym.name == "W"

    def is_weapon(self, sym) -> bool:
        return sym is not None and sym.name in self.config.weapon_symbols

    def is_scatter(self, sym) -> bool:
        return sym is not None and sym.name == "SC"

    def make_symbol(self, name: str):
        """Create a symbol; weapons other than Arrow carry a damage factor."""
        sym = self.create_symbol(name)
        if name in ("BM", "SW", "LT"):
            sym.prize = get_random_outcome(self.config.weapon_factor_weights)
        return sym

    def all_cells(self):
        return self.config.cells_by_priority

    def scatter_count(self) -> int:
        return sum(1 for c in range(6) for r in range(5) if self.is_scatter(self.board[c][r]))

    def scatter_allowed(self, c: int, r: int) -> bool:
        """Max 1 Scatter per column and max 5 on the board (ignoring cell (c, r) itself)."""
        if getattr(self, "no_scatter_spin", False):
            return False
        col_has = any(self.is_scatter(self.board[c][rr]) for rr in range(5) if rr != r)
        total = sum(1 for cc in range(6) for rr in range(5)
                    if (cc, rr) != (c, r) and self.is_scatter(self.board[cc][rr]))
        return not col_has and total < self.config.max_scatters_on_board

    def weapon_allowed(self, name: str, c: int) -> bool:
        """Section 7: no new weapons once every boss of the stage is dead (or
        there are no bosses), and no Arrow in a column whose boss is dead."""
        bosses = getattr(self, "bosses", [])
        if not any(b["alive"] for b in bosses):
            return False
        if name == "AR":
            b = next((x for x in bosses if c in x["zone"]), None)
            return b is not None and b["alive"]
        return True

    def coin_label(self, value: float) -> str:
        for bound, label in self.config.coin_label_bounds:
            if value < bound:
                return label
        return "maxwin"

    def draw_symbol_for(self, c: int, r: int):
        """Fresh symbol for one cell from the current reel's column `c`."""
        strip = self.config.reels[self.reel_name][c]
        for _ in range(500):
            name = strip[random.randrange(len(strip))]
            if name == "SC" and not self.scatter_allowed(c, r):
                continue
            if name in self.config.weapon_symbols and not self.weapon_allowed(name, c):
                continue
            return self.make_symbol(name)
        raise RuntimeError("could not draw a symbol")

    # ---- board drawing -----------------------------------------------------------
    def _window(self, strip, start):
        n = len(strip)
        return [strip[(start + i) % n] for i in range(5)]

    def draw_board(self, reel_name: str, force_scatters=None) -> None:
        """Draw the opening board from `reel_name`. `force_scatters`=N forces
        exactly N columns to show a Scatter (others none). Natural boards are
        capped at 5 Scatters: a 6th (only possible in column 6) is redrawn."""
        self.reel_name = reel_name
        reels = self.config.reels[reel_name]
        n_cols = self.config.num_reels
        positions = [random.randrange(len(reels[c])) for c in range(n_cols)]
        if force_scatters is not None:
            sc_cols = [c for c in range(n_cols) if "SC" in reels[c]]
            chosen = set(random.sample(sc_cols, min(force_scatters, len(sc_cols))))
            for c in range(n_cols):
                strip = reels[c]
                if c in chosen:
                    stop = random.choice([i for i, s in enumerate(strip) if s == "SC"])
                    positions[c] = (stop - random.randrange(5)) % len(strip)
                else:
                    for _ in range(500):
                        if "SC" not in self._window(strip, positions[c]):
                            break
                        positions[c] = random.randrange(len(strip))
        self.board = [[self.make_symbol(n) for n in self._window(reels[c], positions[c])] for c in range(n_cols)]
        if self.no_scatter_spin:
            for c in range(n_cols):
                for r in range(5):
                    if self.is_scatter(self.board[c][r]):
                        self.board[c][r] = self.draw_symbol_for(c, r)
        if self.scatter_count() > self.config.max_scatters_on_board:
            c = n_cols - 1
            for r in range(5):
                if self.is_scatter(self.board[c][r]):
                    self.board[c][r] = self.draw_symbol_for(c, r)
        self.reel_positions = positions
        self.padding_position = positions
        self.anticipation = [0] * n_cols
        if self.config.include_padding:
            self.top_symbols = [self.make_symbol(reels[c][(positions[c] - 1) % len(reels[c])]) for c in range(n_cols)]
            self.bottom_symbols = [self.make_symbol(reels[c][(positions[c] + 5) % len(reels[c])]) for c in range(n_cols)]
        self.get_special_symbols_on_board()

    # ---- lines ------------------------------------------------------------------------
    def evaluate_lines(self) -> list:
        """Paytable-only wins (no multipliers) on the current board. None
        cells never occur here: the board is always fully refilled first."""
        return Lines.get_lines(self.board, self.config)["wins"]

    def global_factor(self) -> float:
        """Global multiplier counter starts at 0x but pays as 1x."""
        return self.global_mult if self.global_mult > 0 else 1

    def line_factor(self, win) -> tuple:
        cells = [(p["reel"], p["row"]) for p in win["positions"]]
        enh = [self.enhance[c][r] for c, r in cells if self.enhance[c][r] > 0]
        enhance_f = sum(enh) if enh else 1
        wms = [self.wild_mult[cell] for cell in cells if cell in self.wild_mult]
        if not wms:
            wild_f = 1
        elif self.config.wild_mult_combine == "add":
            wild_f = sum(wms)
        else:
            wild_f = 1
            for m in wms:
                wild_f *= m
        return enhance_f, wild_f

    def pay_lines(self, wins) -> float:
        """Step (5): line pay x sum(Enhance) x Wild multiplier x Global."""
        g = self.global_factor()
        total = 0.0
        out = []
        for w in wins:
            ef, wf = self.line_factor(w)
            amount = round(w["win"] * ef * wf * g, 4)
            total += amount
            out.append({"line": w["meta"]["lineIndex"], "symbol": w["symbol"], "kind": w["kind"],
                        "base": w["win"], "enhance": ef, "wildMult": wf, "globalMult": g, "win": amount,
                        "positions": [pos(self, p["reel"], p["row"]) for p in w["positions"]]})
        paid = self.award(total)
        emit(self, "lineWins", wins=out, total=paid)
        return paid

    # ---- wallet --------------------------------------------------------------------------
    def award(self, amount: float) -> float:
        """Add to the round total; stop everything once the 25,000x Maxwin is
        reached (the counter is capped at exactly wincap)."""
        if amount <= 0 or self.wincap_triggered:
            return 0.0
        room = self.config.wincap - self.win_manager.running_bet_win
        if amount >= room:
            amount = room
            self.win_manager.update_spinwin(amount)
            self.wincap_triggered = True
            wincap_event(self)
            return amount
        self.win_manager.update_spinwin(amount)
        return amount

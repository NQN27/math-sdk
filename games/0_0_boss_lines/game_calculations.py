"""Core per-pass resolve logic: payline evaluation + whole-board symbol
explode + boss damage/reward bookkeeping + Power connection scan/Wild-Multi
math (Phase 2).

Combines src/calculations/lines.py's Lines.get_lines() (payline evaluation,
reused unchanged) with a game-specific whole-board "explode" rule that is
NOT part of the standard Lines/Cluster/Tumble toolkit: whenever a symbol
wins via ANY payline, every symbol of that same type ANYWHERE on the board
explodes and deals boss damage (not just the copies inside the winning
line). This file only computes/marks explosions and boss bookkeeping for a
single resolve pass on the CURRENT board; the physical removal/refill is
still done by the unmodified src/calculations/tumble.py Tumble.tumble_board()
(called from gamestate.py between passes).

Phase 2 adds: a Power-connection scan over this pass's winning-line
positions (see class docstring below), Wild Multi's per-line multiplicative
math (computed here - it's pure win-amount arithmetic, a "calculation");
Global Multi's accumulator update, Maxwin's wincap-fence activation, and the
5 FIFO-group powers' collection/activation are bookkeeping and live in
game_executables.py (called from here via `self`, same pattern Phase 1
already used to call deal_damage_to_boss from this file).
"""

import math
import random

from src.executables.executables import Executables
from src.calculations.lines import Lines
from src.calculations.statistics import get_random_outcome
from game_events import power_activated_event


class GameCalculations(Executables):
    """Game-specific win/board-explode/boss-damage/Power evaluation."""

    def award_win(self, amount: float) -> float:
        """Add `amount` (bet-multiplier units) to the current spin's running
        win, honoring the non-wincap headroom guard: on any criteria OTHER
        than "wincap", running_bet_win is never allowed to reach config.wincap.

        This matters because the boss-defeat reward-drop table can chain
        several 2000x/5000x top-tier drops within a single long cascade
        (multiple stage clears in one spin) - without this guard a
        "basegame"/"0" criteria spin could legitimately accumulate to
        exactly wincap purely by chance, contaminating that fence with a
        wincap-magnitude book the optimizer never expects there (this is the
        exact mistake flagged in QUESTIONS_FOR_YOU.md: Maxwin/wincap-sized
        wins must ONLY ever originate from the dedicated "wincap" fence).
        Phase 2 adds a second source of large non-wincap wins (Global Multi
        scaling up boss reward-drops) that makes this guard's role even more
        important than in Phase 1 - see readme.txt's clamp-event measurement.

        The floor-to-nearest-$0.10 quantization below only runs when the
        headroom guard actually had to shrink `amount` - applying it
        unconditionally to every award (even when nowhere near the cap)
        previously shaved a cent off of ~0.2% of spins purely from ordinary
        float-summation noise (e.g. 0.5+0.3 == 0.7999999999999999 in
        double precision), an unintended RTP leak caught via a harness
        instrumentation pass - see readme.txt.
        """
        if amount <= 0:
            return 0.0
        if self.criteria != "wincap":
            headroom = self.config.wincap - self.win_manager.running_bet_win - 0.05
            if headroom <= 0:
                self.power_clamp_events = getattr(self, "power_clamp_events", 0) + 1
                return 0.0
            if amount > headroom:
                amount = math.floor(headroom * 10) / 10.0
                self.power_clamp_events = getattr(self, "power_clamp_events", 0) + 1
                if amount <= 0:
                    return 0.0
        self.win_manager.update_spinwin(amount)
        return amount

    def effective_global_mult(self) -> float:
        """Global Multi's effective multiplier for THIS moment: the raw
        accumulated total if any Global Multi has been activated this spin
        (additive across activations, never resets mid-spin), else 1 (no
        effect) - see game_executables.activate_global_multi_cells. Applies
        to line-win payout only, for the rest of the spin - deliberately NOT
        applied to boss-defeat reward-drops (see
        game_executables.on_boss_defeated) or boss damage, so PGM can never
        inflate the cash/HP side of a boss kill."""
        return self.global_multi_total if self.global_multi_total > 0 else 1

    def _both_ways_reversed_wins(self, forward_win_data) -> list:
        """Phase 3 (Hidden-tier Bonus only): evaluate Lines.get_lines AGAIN
        against a column-reversed view of the current board (right-to-left),
        remap each win's positions back to ORIGINAL board coordinates
        (reversed-board reel index r -> original reel index num_reels-1-r),
        and return that list of wins ready to merge straight into the
        forward pass's win_data["wins"] - deliberately BEFORE the Power
        connection scan / whole-board-explode section run (see
        evaluate_and_explode below), so both directions are treated
        completely uniformly by everything downstream (Wild Multi/Global
        Multi/FIFO connection scanning, whole-board explode + damage, event
        emission, the resolve loop's own continuation check) with no special
        casing needed - a physical cell that is part of BOTH a forward and a
        reversed winning line (e.g. a symmetric full-line 5-of-a-kind, which
        the source spec explicitly calls out as intentionally double-paid)
        still only counts once for Wild-Multi/whole-board-explode purposes,
        since those are keyed by physical (reel, row) and naturally dedup
        regardless of which pass discovered the cell.
        """
        reversed_board = list(reversed(self.board))
        reversed_win_data = Lines.get_lines(reversed_board, self.config)
        if reversed_win_data["totalWin"] <= 0:
            return []
        n = self.config.num_reels
        remapped = []
        for win in reversed_win_data["wins"]:
            new_win = dict(win)
            new_win["positions"] = [{"reel": n - 1 - pos["reel"], "row": pos["row"]} for pos in win["positions"]]
            new_win["meta"] = dict(win["meta"])
            new_win["meta"]["direction"] = "rtl"
            remapped.append(new_win)
        return remapped

    def evaluate_and_explode(self, both_ways: bool = False) -> None:
        """Evaluate all 15 paylines on the CURRENT board, apply Power
        connection effects (Wild Multi math here; Global Multi/Maxwin/FIFO
        bookkeeping delegated to game_executables.py), then apply the
        whole-board explode + boss damage/reward rule. Sets self.win_data,
        self.pass_exploded_positions (superset of winning lines' positions,
        for the board-explode event) and drains this pass's Power
        connections into self.global_multi_total / self.power_queue /
        wincap activation as appropriate.

        `both_ways` (Phase 3, Hidden-tier Bonus only): also evaluate the
        board right-to-left and fold any additional wins straight into
        win_data/totalWin BEFORE anything else in this function (or the
        caller's resolve-loop continuation check) reads them - see
        _both_ways_reversed_wins above for why merging early, rather than
        paying the reversed total out via a second independent award_win
        call, was chosen: it makes every downstream step (Power scanning,
        explode, event totals, loop continuation) treat both directions
        identically for free.
        """
        win_data = Lines.get_lines(self.board, self.config)
        if both_ways:
            reversed_wins = self._both_ways_reversed_wins(win_data)
            if reversed_wins:
                win_data["wins"] = win_data["wins"] + reversed_wins
                win_data["totalWin"] = round(win_data["totalWin"] + sum(w["win"] for w in reversed_wins), 2)
        self.win_data = win_data
        Lines.record_lines_wins(self)
        self.pass_exploded_positions = []

        if win_data["totalWin"] <= 0:
            self.win_manager.tumble_win = 0.0
            return

        # --- Power connection scan --------------------------------------
        # Walk winning lines in line-index order (win_data["wins"] already
        # iterates config.paylines in increasing key order - see
        # Lines.get_lines), positions left-to-right within a line. Dedup by
        # physical cell: a cell shared by >1 payline "connects" once per
        # pass. This ordering IS the FIFO collection order the spec asks
        # for ("the one in the lower-indexed payline is collected first").
        seen_cells = set()
        wild_multi_cells = []
        global_multi_cells = []
        maxwin_cells = []
        fifo_cells = []  # ordered list of (reel, row, power_type)
        for win in win_data["wins"]:
            for pos in win["positions"]:
                cell = (pos["reel"], pos["row"])
                if cell in seen_cells:
                    continue
                seen_cells.add(cell)
                name = self.board[cell[0]][cell[1]].name
                ptype = self.config.power_type_by_symbol.get(name)
                if ptype is None:
                    continue
                if ptype == "wild_multi":
                    wild_multi_cells.append(cell)
                elif ptype == "global_multi":
                    global_multi_cells.append(cell)
                elif ptype == "maxwin":
                    maxwin_cells.append(cell)
                else:
                    fifo_cells.append((cell[0], cell[1], ptype))

        # --- Wild Multi: one factor roll per physical cell (reused across
        # every line that cell is part of); multiple Wild Multi cells
        # within the SAME winning line multiply together, not add. Affects
        # payout only, never boss damage (damage is computed further down
        # from the fixed wild_damage_multiplier, entirely independently). --
        wild_multi_rolls = {
            cell: get_random_outcome(self.config.power_multi_factor_weights) for cell in wild_multi_cells
        }

        # --- Global Multi: immediate activation - update the accumulator
        # now so it applies to the REST of this same pass's wins (its own
        # line's payout included) as well as every later pass this spin. --
        if global_multi_cells:
            self.activate_global_multi_cells(global_multi_cells)

        effective_global = self.effective_global_mult()

        # --- Recompute every line's win with Wild Multi + Global Multi
        # applied, and the pass total from those adjusted amounts. ---------
        adjusted_total = 0.0
        wild_multi_line_events = []
        for win in win_data["wins"]:
            line_factor = 1
            touched = []
            for pos in win["positions"]:
                cell = (pos["reel"], pos["row"])
                if cell in wild_multi_rolls:
                    line_factor *= wild_multi_rolls[cell]
                    touched.append(cell)
            adjusted = win["win"] * line_factor * effective_global
            win["win"] = round(adjusted, 2)
            win["meta"]["powerLineFactor"] = line_factor
            win["meta"]["globalMultApplied"] = effective_global
            adjusted_total += win["win"]
            if touched:
                wild_multi_line_events.append(
                    {
                        "lineIndex": win["meta"]["lineIndex"],
                        "factor": line_factor,
                        "positions": [{"reel": c[0], "row": c[1]} for c in touched],
                    }
                )

        adjusted_total = round(adjusted_total, 2)
        win_data["totalWin"] = adjusted_total
        self.win_manager.tumble_win = adjusted_total

        if wild_multi_line_events:
            power_activated_event(self, "wild_multi", {"lines": wild_multi_line_events})

        self.award_win(adjusted_total)

        # --- Whole-board explode + damage (Phase 1 rule, extended: ANY
        # wild-attribute cell - "W" or any of the 8 Powers - substitutes
        # like Wild for the 2x-highest-symbol-replaced damage rule). -------
        winning_names = set()
        wild_replaced_by = {}  # (reel, row) -> set of symbol names it substituted for
        for win in win_data["wins"]:
            name = win["symbol"]
            winning_names.add(name)
            for pos in win["positions"]:
                r, ro = pos["reel"], pos["row"]
                if self.board[r][ro].check_attribute("wild"):
                    wild_replaced_by.setdefault((r, ro), set()).add(name)

        exploding = []  # (reel, row, kind, ref_symbol_name)
        for r in range(self.config.num_reels):
            for ro in range(self.config.num_rows[r]):
                sym = self.board[r][ro]
                if sym.name in winning_names:
                    exploding.append((r, ro, "normal", sym.name))
        for (r, ro), names in wild_replaced_by.items():
            best = max(names, key=lambda n: self.config.symbol_rank_order.index(n))
            exploding.append((r, ro, "wild", best))

        # Deterministic, column-major order so mid-pass boss deaths/stage
        # clears correctly re-route damage for later instances in this same
        # pass (per spec: "if a redirect already happened earlier in this
        # same resolve loop ... use the redirected target").
        exploding.sort(key=lambda t: (t[0], t[1]))

        for r, ro, kind, ref_name in exploding:
            self.board[r][ro].explode = True
            lo, hi = self.config.symbol_damage_range[ref_name]
            damage = random.uniform(lo, hi)
            if kind == "wild":
                damage *= self.config.wild_damage_multiplier
            self.deal_damage_to_boss(r, damage)

        self.pass_exploded_positions = [{"reel": r, "row": ro} for (r, ro, _, _) in exploding]

        # --- Maxwin power: immediate activation, ends the spin. Structurally
        # unreachable outside the "wincap" fence (see reels/WCAP.csv vs
        # reels/BR0.csv) - activate_maxwin_power still hard-gates on
        # self.criteria as a second line of defence (same two-layer pattern
        # Phase 1 used for the reward-drop Maxwin tier). -------------------
        if maxwin_cells:
            self.activate_maxwin_power(maxwin_cells)

        # --- FIFO group: enqueue, in collection order, for one-at-a-time
        # activation between tumble passes (see gamestate.py). -------------
        if fifo_cells:
            self.enqueue_fifo_powers(fifo_cells)

"""Phase 3: scatter-triggered 3-tier Bonus engine (Player-HP-gated
multi-spin loop) + the 2 Bonus-exclusive collectibles (Elixir/Booster).

Layered entirely on top of the existing base-spin cascade engine
(game_calculations.evaluate_and_explode / game_executables.py's boss-battle
+ Power system) - a Bonus session is just that SAME engine run spin after
spin, with three things now persisted ACROSS those internal spins instead of
reset each time (boss/stage state, Global Multi - see
game_executables.reset_boss_battle/reset_power_system, both only called ONCE
per session here, not once per internal spin), plus a brand-new Player HP
resource that only exists during Bonus and decides when the session ends.

Scope note (see readme.txt): this file intentionally does NOT build Ante/
Ultimate Power/God Mode/direct-buy-3+/direct-buy-4+ (Phase 4's job) - but
`run_bonus_session`'s only tier-specific inputs (starting stage, Player HP
pool, Power-rate reel, Both-Ways flag) are all looked up from
game_config.py's bonus_* dicts, so Phase 4 can add new entry points that
plug different starting conditions into the SAME `run_bonus_session`/
`run_one_bonus_spin` machinery without changing this file.
"""

import random
import warnings

from game_executables import GameExecutables
from src.events.events import reveal_event
from src.calculations.statistics import get_random_outcome
from game_events import (
    bonus_trigger_event,
    bonus_spin_start_event,
    bonus_counterattack_event,
    bonus_end_event,
    player_hp_state_event,
    spin_budget_state_event,
    elixir_activated_event,
    gun_activated_event,
    boss_state_event,
)


class GameBonus(GameExecutables):
    """Scatter tally (across the whole base-spin cascade) + the Bonus
    session loop + Elixir/Booster."""

    # --- Per-book reset ------------------------------------------------------
    def reset_bonus_state(self) -> None:
        """Called once per book attempt from game_override.reset_book -
        Player HP/Bonus-tier state does not exist outside an active Bonus
        session, so this is also what it looks like "at rest" for every
        Base/Ante/feature-spin book."""
        self.in_bonus = False
        self.player_hp = 0.0
        self.player_hp_max = 0.0
        # EXPERIMENTAL (use_spin_budget) - see game_config.py's docstring.
        # Stays 0 for the whole book outside an active spin-budget session,
        # same "at rest" convention as player_hp above.
        self.spins_remaining = 0
        self.scatter_columns = set()
        self.booster_pending_for_next_spin = False
        self.booster_multiplier_current_spin = 1.0
        self.bonus_tier = None
        self.bonus_spin_count = 0
        self.bonus_end_reason = None
        self.stage6_loop_count = 0
        # Bosses defeated so far in the CURRENT Bonus session (incremented in
        # game_executables.on_boss_defeated). Only run_bonus_session's
        # finishing-blow guard reads it - see that method's comment for why
        # `stage_defeat_order` can NOT be used for this.
        self.bonus_kill_count = 0

    # --- Scatter tally (base-spin side only) ----------------------------------
    def accumulate_scatter_columns(self) -> None:
        """Add every column CURRENTLY showing a Scatter to the running,
        never-shrinking set of columns seen so far this spin - called after
        the initial reveal AND after every tumble refill of the outer base
        spin (see gamestate.run_spin), so Scatters that land mid-cascade
        count too, matching the spec's "finalized after cascade reaches
        static state" rule. A set that only ever grows is immune to a LATER
        Extra Wild/Extra Power placement overwriting a Scatter cell (it
        already landed - that already counts, regardless of what happens to
        the cell afterwards), and naturally caps at 5 (5 columns) via the
        reel strip's own "max 1 Scatter/column" spacing guarantee - no extra
        clamping needed. Never called during a Bonus session's internal
        spins (Scatter isn't on FR0/FR1/FR2, and there is no Bonus
        retrigger)."""
        for col in range(self.config.num_reels):
            for row in range(self.config.num_rows[col]):
                if self.board[col][row].check_attribute("scatter"):
                    self.scatter_columns.add(col)
                    break

    def resolve_bonus_tier(self):
        """None (no trigger) / "normal" / "super" / "hidden", from this
        spin's final Scatter column count."""
        n = len(self.scatter_columns)
        if not getattr(self, "base_bosses_cleared", False):
            return None  # v2: no Bonus unless the stage-0 bosses were all defeated
        if n >= self.config.bonus_maxwin_scatter_count:
            return "maxwin"
        return self.config.bonus_scatter_tier_by_count.get(n)

    # --- Phase 4: floor-forced (guaranteed minimum, overshoot allowed)
    # Scatter board - ORIGINALLY used by the buy-3+/buy-4+-scatter direct
    # bonus-buy modes. Phase 4 v2 (see QUESTIONS_FOR_YOU.md) replaced that
    # usage with an exact-count force_special_board draw from an explicit
    # tier-mix weight table (game_config.py's buy3_scatter_count_weights/
    # buy4_scatter_count_weights, applied in gamestate.run_spin) - an EXACT
    # required composition (92/7.6/0.4 / 95/5) cannot coexist with this
    # function's "let it overshoot naturally" semantics. Left defined,
    # unused, rather than deleted (same convention as FR0-2.csv/PWR1.csv).
    def force_min_scatter_board(self, min_count: int) -> None:
        """Force exactly `min_count` DISTINCT reels to a Scatter stop (picked
        from that reel's own strip - never an invented position), leaving
        every OTHER reel to draw a completely ordinary random stop from the
        SAME reelstrip. Unlike `src.calculations.board.Board.
        force_special_board` (which enforces an EXACT final count and
        retries - via an unbounded `while True` - until it gets one, making
        it structurally unusable for "at least N, overshoot OK": forcing
        min_count=3 there would reject-and-redraw forever on the ~7% of
        attempts where one of the 2 un-forced reels ALSO naturally lands a
        Scatter), this calls `force_board_from_reelstrips` directly with a
        PARTIAL stop-position dict (only `min_count` of the 5 reels are
        pinned - see src.calculations.board.Board.force_board_from_reelstrips,
        which already draws any reel absent from that dict fully at random),
        so a natural extra Scatter on one of the un-forced reels simply
        overshoots the tier upward (Normal -> Super/Hidden) instead of
        triggering a retry - exactly the spec's "guaranteed minimum, roll the
        real count with a floor, don't cap it" requirement. One deterministic
        call, no retry loop, no risk of the infinite-loop landmine
        `force_special_board` would hit if reels ran out of un-forced
        capacity (see readme.txt's Phase 3 section for that documented
        landmine - this deliberately avoids reusing that primitive here)."""
        conditions = self.get_current_distribution_conditions()
        reelstrip_id = get_random_outcome(conditions["reel_weights"][self.gametype])
        reelstops = self.get_syms_on_reel(reelstrip_id, "scatter")
        possible_reels = [i for i in range(self.config.num_reels) if len(reelstops[i]) > 0]
        n = min(min_count, len(possible_reels))
        chosen_reels = random.sample(possible_reels, n)
        force_stop_positions = {r: random.choice(reelstops[r]) for r in chosen_reels}
        self.force_board_from_reelstrips(reelstrip_id, force_stop_positions)

    # --- Reel-selection override (Phase 4 plug point) -------------------------
    def get_current_distribution_conditions(self) -> dict:
        """Wraps the base implementation with a per-(tier, stage) reel
        override for the freegame_type key ONLY, active only while
        `self.in_bonus` (i.e. only during an active Bonus session - see
        run_bonus_session below). Looked up LIVE from
        `config.bonus_tier_stage_reel[self.bonus_tier][self.stage]` every
        call (not cached once at session start) so the reel automatically
        follows `self.stage` as it advances mid-session - including the
        endless stage-6 tail, where `self.stage` stays pinned at 6 across
        every loop, so it naturally keeps resolving to the same stage-6
        reel with no extra bookkeeping. Returns a shallow copy, never
        mutating the underlying dict in place - that dict is literally the
        singleton BetMode/Distribution's own `_conditions` object (see
        src.config.distributions.Distribution / src.state.state.
        GeneralGameState.get_current_distribution_conditions), and mutating
        it would leak across every later simulation that reuses the same
        Distribution (the exact singleton-leak class of bug this project's
        notes repeatedly warn about for `self.config`)."""
        conditions = super().get_current_distribution_conditions()
        if getattr(self, "in_bonus", False):
            forced_reel = self.config.bonus_tier_stage_reel[self.bonus_tier][self.stage]
            conditions = dict(conditions)
            conditions["reel_weights"] = dict(conditions["reel_weights"])
            conditions["reel_weights"][self.config.freegame_type] = {forced_reel: 1}
        return conditions

    # --- Elixir / Booster ------------------------------------------------------
    def _board_has_elixir_or_booster(self) -> bool:
        return (
            self.count_symbols_on_board("EL") > 0
            or self.count_symbols_on_board("GS") > 0
            or self.count_symbols_on_board("GL") > 0
        )

    def _fire_gun(self, r: int, kind: str, mult: float = 1) -> int:
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
            fired.append((r, ro, kind, self._fire_gun(r, kind, 1)))
        return fired

    def _activate_elixir_booster(self) -> None:
        """Both activate together, right as a Bonus spin's resolve loop is
        about to declare static state (see run_one_bonus_spin): mark every
        current EL/BO cell exploded (the next tumble_game_board() call
        refills them exactly like any other explode), heal Player HP per
        Elixir instance (rolled/applied in board-scan order - each
        instance's 10%-100% roll is of Player HP's CURRENT value AT THAT
        MOMENT, so a second Elixir this same activation heals off of the
        first one's already-applied result, capped at max, rounded to the
        nearest 10), and set the x2-boss-damage flag for the NEXT bonus spin
        if 1 or more Boosters are present (no stacking beyond x2 - see
        game_config.py's booster_damage_multiplier docstring for the
        "immediately-following spin" interpretation call)."""
        el_positions = sorted((p["reel"], p["row"]) for p in self.get_symbol_positions("EL")["EL"])
        bo_positions = []  # v2: Booster removed, see _activate_guns

        spin_budget_mode = self.config.use_spin_budget.get(self.bonus_tier, False)
        for r, ro in el_positions:
            self.board[r][ro].explode = True
            if spin_budget_mode:
                # Repurposed (see game_config.py's use_spin_budget
                # docstring): Player HP is never granted/spent in this
                # mode, so a %-of-current-HP heal has nothing to act on -
                # grant spins instead of letting Elixir become a silent
                # no-op collectible.
                #
                # BUG FOUND (2026-09-20, via Super's own baseline
                # measurement - mean 372.10x vs 240.77x target, safety_cap
                # hit in 0.5% of sessions, max spins observed=500): this
                # grant had NO suppression for repeat endless-stage6 loops,
                # unlike the identical stage-clear grant in
                # game_executables.clear_stage - Elixir can land on ANY
                # spin including every loop of an endless tail (Super/
                # Hidden only; Normal's own stage6_endless_tiers=False made
                # this dormant/harmless there), so a session unlucky enough
                # to keep drawing Elixir during a long tail could extend
                # its own budget indefinitely, all the way to
                # bonus_safety_cap_spins - exactly the unbounded-farming
                # class of bug game_config.py's use_spin_budget docstring
                # already warned the stage-clear grant needed guarding
                # against, just missed here. Same guard applied now.
                if not (
                    self.stage == self.config.max_stage and getattr(self, "stage6_loop_count", 0) > 0
                ):
                    self.spins_remaining += self.config.elixir_spin_budget_grant.get(self.bonus_tier, 0)
                elixir_activated_event(self, (r, ro), 0.0, self.player_hp)
            else:
                lo, hi = self.config.elixir_heal_pct_range
                pct = random.uniform(lo, hi)
                round_to = self.config.elixir_heal_round_to
                raw_heal = self.player_hp * pct
                heal = round(raw_heal / round_to) * round_to
                new_hp = min(self.player_hp_max, self.player_hp + heal)
                actual_healed = new_hp - self.player_hp
                self.player_hp = new_hp
                elixir_activated_event(self, (r, ro), actual_healed, self.player_hp)

        fired = self._activate_guns()
        if fired:
            gun_activated_event(self, fired)

        if el_positions or fired:
            if spin_budget_mode:
                spin_budget_state_event(self)
            else:
                player_hp_state_event(self)

    # --- One internal Bonus spin ----------------------------------------------
    def run_one_bonus_spin(self, both_ways: bool) -> None:
        """One Bonus 'spin': the SAME cascade engine a base spin uses
        (payline eval + whole-board explode/damage + Power FIFO/immediate
        activation - see game_calculations.evaluate_and_explode /
        gamestate.run_spin), but: boss/stage state and Global Multi are NOT
        reset here (only once, at run_bonus_session's start - persisted
        across every spin in this session per spec), the board is drawn
        from this session's fixed tier reel (see
        get_current_distribution_conditions above) with self.gametype
        already set to freegame_type, `both_ways` is threaded through to
        evaluate_and_explode, and the loop's continuation condition gets one
        extra disjunct for Elixir/Booster (see class docstring / spec:
        activation happens at the exact moment a pass has produced no new
        wins/connections AND the FIFO queue is empty - i.e. right as the
        loop is about to declare static state - not immediately on
        collection)."""
        self.win_manager.reset_spin_win()
        self.pass_exploded_positions = []
        self.vanished_cells = set()
        self.coin_pending = False
        self.spin_had_scatter = False
        self.chain_pass_count = 0
        self.chain_block_pending = False
        self.create_board_reelstrips()
        # BUG FIX (found via a bounded direct-call harness, not left as a
        # surprise - see readme.txt's Phase 3 section): `removed_symbols`
        # persists for the WHOLE Bonus session (unlike a base spin, where it
        # always starts empty - see game_override.reset_book), so every
        # internal spin AFTER the first one can freely draw a straight
        # create_board_reelstrips() initial reveal that still contains a
        # symbol an EARLIER spin in this same session already removed (the
        # raw reel strip has no idea about `removed_symbols` - only
        # `enforce_removed_symbols` does). game_executables.tumble_game_board
        # already re-enforces this after every TUMBLE, but that alone isn't
        # enough if this spin's very first reveal has zero wins (no tumble
        # ever happens that spin) - which is exactly what was observed: a
        # since-removed low-pay symbol sitting untouched on the board at
        # session end. Enforcing once more right after the initial reveal
        # closes that gap.
        self.enforce_removed_symbols()
        reveal_event(self)

        self.evaluate_and_explode(both_ways=both_ways)
        self.emit_tumble_win_events()
        self.emit_pass_extra_events()

        passes = 1
        while not self.wincap_triggered and passes < self.config.max_resolve_passes:
            has_win = self.win_data["totalWin"] > 0
            has_fifo = bool(self.power_queue)
            if has_win or has_fifo:
                self.tumble_game_board()
                self.activate_next_power()
                self.evaluate_and_explode(both_ways=both_ways)
                self.emit_tumble_win_events()
                self.emit_pass_extra_events()
                passes += 1
                continue
            if getattr(self, "coin_pending", False):
                self.run_coin_phase()
                passes += 1
                continue
            if self._board_has_elixir_or_booster():
                self._activate_elixir_booster()
                self.tumble_game_board()
                self.evaluate_and_explode(both_ways=both_ways)
                self.emit_tumble_win_events()
                self.emit_pass_extra_events()
                passes += 1
                continue
            break
        if passes >= self.config.max_resolve_passes:
            warnings.warn(
                f"\nHit max_resolve_passes ({self.config.max_resolve_passes}) on a "
                f"Bonus spin (sim {self.sim}, criteria {self.criteria}, tier "
                f"{self.bonus_tier}) - forcing this spin's cascade to end.\n"
            )
            if self.power_queue:
                # Defensive-only: by construction, "static state" (the
                # ordinary loop-exit condition) requires an EMPTY queue, so
                # this can only be reached via the max_resolve_passes safety
                # valve above - which "should never be hit by a legitimate
                # board" (see game_config.max_resolve_passes docstring).
                # Unlike a base spin (where reset_book/reset_power_system
                # gives every attempt a fresh empty queue), a Bonus session
                # does NOT reset the Power queue between its own internal
                # spins (see run_bonus_session - only Boss/Global Multi state
                # is meant to persist, never leftover FIFO powers), so
                # without this, a queue non-empty at this rare safety-valve
                # exit would otherwise silently leak into the NEXT internal
                # spin's resolve loop instead of vanishing with this one.
                warnings.warn(
                    f"\n{len(self.power_queue)} Power(s) still queued when "
                    f"max_resolve_passes was hit (sim {self.sim}) - clearing "
                    "rather than leaking into the next Bonus spin.\n"
                )
                self.power_queue = []

        self.set_end_tumble_event()
        self.win_manager.update_gametype_wins(self.gametype)

    # --- Full Bonus session ----------------------------------------------------
    def run_bonus_session(self, tier: str) -> None:
        """Entry point, called from gamestate.run_spin once the base spin's
        cascade reaches static state with a final Scatter tally of 3+ (see
        resolve_bonus_tier). Grants Player HP, sets the starting stage/Both-
        Ways flag (reel is now chosen live per-stage - see
        get_current_distribution_conditions), then loops internal spins
        until Player HP<=0, the endless stage-6 tail also ends (wincap), or
        the defensive safety cap is hit.

        Design decision (supersedes the earlier "stop the session the
        instant stage 6 clears" behavior): stage 6 no longer goes dormant
        permanently. Every time its 3 bosses are cleared, `clear_stage`
        still grants its usual +50/+50 Player HP (unconditional on
        in_bonus, not stage-specific) and still rolls the stage-6 reward-
        drop, but instead of ending the session we immediately re-roll a
        fresh stage-6 trio and keep going - Dam AND HP both scaled up by
        `stage6_dam_escalation ** stage6_loop_count` each additional loop
        (see game_config.py) so the tail is bounded by rising risk, not by
        a hardcoded stop. Scaling HP too (not just Dam) matters for a
        strong-damage tier: the counter-attack damage step below only
        fires if the freshly-rolled trio is STILL ALIVE at the end of that
        spin (see the `continue` a few lines down) - a trio that's usually
        one-shot-cleared within its own rolling spin never reaches that
        step at all, so Dam's escalation would have nothing to act on
        without also escalating HP to make the trio survive past spin 1
        more often as loops accumulate. `self.stage` stays pinned at 6
        throughout (so the reel/reward-drop pool used stays stage 6's),
        only `self.stage6_loop_count` advances.

        This endless tail is per-tier gated via
        `config.stage6_endless_tiers` (see the config comment for the
        measured detail)."""
        self.in_bonus = True
        self.bonus_tier = tier
        self.gametype = self.config.freegame_type
        both_ways = self.config.bonus_both_ways[tier]

        spin_budget_mode = self.config.use_spin_budget.get(tier, False)
        if spin_budget_mode:
            # EXPERIMENTAL (use_spin_budget) - see game_config.py's
            # docstring. Player HP is never granted/read/spent in this
            # mode; it stays at 0.0 for event-schema compatibility only
            # (bonus_trigger_event/player_hp_state_event/bonus_end_event
            # still fire unchanged - see below).
            self.spins_remaining = self.config.spin_budget_initial.get(tier, 8)
            self.player_hp = 0.0
            self.player_hp_max = 0.0
        else:
            granted = random.choice(self.config.bonus_player_hp_choices[tier])
            if self.config.use_flat_damage.get(tier, False):
                # Flat-damage system's damage values (flat_symbol_damage,
                # flat_wild_damage, flat_boss_counterattack_damage) are all
                # small whole integers - Player HP must stay an integer too,
                # not a stray decimal from multiplying by a fractional rescale
                # factor (e.g. 200*0.026=5.2).
                granted = round(granted * self.config.flat_damage_player_hp_initial_mult.get(tier, 1.0))
            self.player_hp = float(granted)
            self.player_hp_max = float(granted)
        self.booster_pending_for_next_spin = False
        self.booster_multiplier_current_spin = 1.0
        self.stage6_loop_count = 0
        self.bonus_kill_count = 0

        start_stage = self.config.bonus_start_stage[tier]
        self.reset_boss_battle(start_stage=start_stage)
        # Global Multi (and the FIFO queue, though that's always empty
        # between spins by construction anyway) reset ONCE here for the
        # whole session - persisted across every one of this session's own
        # internal spins, per spec ("giu nguyen HP boss va Global Multi").
        self.reset_power_system()

        bonus_trigger_event(self, tier, self.player_hp, self.player_hp_max, start_stage)
        player_hp_state_event(self)
        if spin_budget_mode:
            spin_budget_state_event(self)
        boss_state_event(self)

        spin_count = 0
        end_reason = "safety_cap"
        while (
            (self.spins_remaining > 0 if spin_budget_mode else self.player_hp > 0)
            and spin_count < self.config.bonus_safety_cap_spins
        ):
            spin_count += 1
            # Booster's x2/x3-boss-damage flag (set at the END of the
            # PREVIOUS spin, if a Booster was collected there) applies for
            # this entire spin, then is consumed (never stacks further) -
            # see game_config.py's booster_damage_multiplier docstring.
            # Tier-scoped (2026-08-28) - `self.bonus_tier` is always set by
            # this point (line ~324 above), Booster only ever exists during
            # an active Bonus session, so no "default" fallback is needed
            # here (unlike power_multi_factor_weights, which also has to
            # cover base-game combat).
            self.booster_multiplier_current_spin = (
                self.config.booster_damage_multiplier[self.bonus_tier] if self.booster_pending_for_next_spin else 1.0
            )
            self.booster_pending_for_next_spin = False

            bonus_spin_start_event(self, spin_count)
            self.run_one_bonus_spin(both_ways)

            # --- Rescue roll (2026-09-04, per-spin safety net - see
            # game_config.bonus_rescue_roll's docstring for the full
            # design/validation history). `.get()` returns None for any tier
            # not in the config dict, so this is a no-op unless configured.
            rescue_cfg = self.config.bonus_rescue_roll.get(tier)
            if (
                rescue_cfg is not None
                and self.win_manager.running_bet_win < rescue_cfg["floor"]
                and random.random() < rescue_cfg["trigger_prob"]
            ):
                current = self.win_manager.running_bet_win
                topup = round(
                    random.uniform(max(0.0, rescue_cfg["floor"] - current), rescue_cfg["band_high"] - current), 2
                )
                # Same reset/award/file bracket as the low-HP execute check
                # below - run_one_bonus_spin already filed ITS OWN spin_win
                # into freegame_wins at its own end (line ~293), so award_win
                # here would otherwise add to a spin_win that never gets
                # filed, reaching running_bet_win but not the basegame/
                # freegame split (see that check's own comment for the exact
                # assertion failure this causes if skipped).
                self.win_manager.reset_spin_win()
                self.award_win(topup)
                self.win_manager.update_gametype_wins(self.gametype)

            # NOTE: the last-hit/execute chance is no longer a per-spin
            # check here - as of 2026-09-17 it's rolled PER HIT, inside
            # game_executables.deal_damage_to_boss (see game_config.py's
            # boss_last_hit_base_chance/_scale docstring for the exact
            # formula). No open/close win_manager bracket is needed for it
            # here since on_boss_defeated only ever fires there from
            # within evaluate_and_explode's own normal per-instance damage
            # loop (already inside run_one_bonus_spin's own bracket), never
            # after run_one_bonus_spin has already closed its books.

            if self.wincap_triggered:
                end_reason = "wincap"
                break

            if spin_budget_mode:
                # EXPERIMENTAL (use_spin_budget) - see game_config.py's
                # docstring. UNCONDITIONAL: every internal spin taken
                # always costs exactly 1, regardless of what the
                # boss_system_active branch below does with it this same
                # iteration (a stage-clear, an endless-stage6-reroll
                # `continue`, or a boss_counterattack_grace spin - none of
                # those get to skip this, unlike the old HP-counterattack
                # block they'd have skipped). A spin budget has no
                # escalating counter-pressure the way HP-vs-boss_dam does,
                # so any conditional skip here would let super/hidden farm
                # the endless tail for free up to bonus_safety_cap_spins.
                self.spins_remaining -= 1
                spin_budget_state_event(self)

            if not self.boss_system_active:
                if not self.config.stage6_endless_tiers.get(tier, False):
                    # This tier is excluded from the endless tail (see
                    # stage6_endless_tiers in game_config.py) - stage 6
                    # clearing ends the session, same as the original
                    # "stop the session the instant stage 6 clears"
                    # behavior.
                    end_reason = "stage_cleared"
                    break
                # Stage 6 just cleared (clear_stage already granted its
                # +50/+50 HP and paid the stage-6 reward-drop) - endless
                # tail: re-roll a fresh stage-6 trio, scale Dam AND HP up
                # for this next loop, and keep going instead of ending the
                # session.
                #
                # BUG FOUND (measurement, not assumption): escalating only
                # Dam did almost nothing for a strong-damage tier like
                # Hidden - the counter-attack damage step below only runs
                # if the freshly-rolled trio is STILL ALIVE at the end of
                # this spin (see the `continue` above, which skips it
                # entirely the instant `boss_system_active` goes False
                # again). For Hidden, a fresh stage-6 trio is usually
                # one-shot-cleared within the SAME spin it's rolled
                # (measured: ~1.17 spins/loop at low escalation), so the
                # damage step - and therefore Dam's escalation multiplier -
                # never even gets a chance to apply on most loops,
                # regardless of how extreme the multiplier is. Escalating
                # HP too forces the trio to actually survive past the first
                # spin more often as loops accumulate, so the damage step
                # (and Dam's escalation) actually fires with meaningful
                # frequency instead of being skipped almost every time.
                self.stage6_loop_count += 1
                self.boss_system_active = True
                self.roll_stage_bosses(self.config.max_stage)
                escalation = self.config.stage6_dam_escalation[tier] ** self.stage6_loop_count
                self.boss_dam = {b: v * escalation for b, v in self.boss_dam.items()}
                self.boss_hp = {b: v * escalation for b, v in self.boss_hp.items()}
                self.boss_hp_max = {b: v * escalation for b, v in self.boss_hp_max.items()}
                # Same counter-attack grace as an ordinary clear_stage
                # transition (see game_executables.clear_stage) - this
                # re-roll doesn't go through clear_stage, so it needs its
                # own grant. Per game designer: every endless-tail loop
                # gets its own 1-static-state grace, same as a real stage
                # transition.
                self.boss_counterattack_grace = True
                # See game_executables.reset_boss_battle's comment: targets
                # the NEXT spin's opening board draw, not this one.
                self.grace_deadspin_pending = True
                boss_state_event(self)
                continue

            if spin_budget_mode:
                # EXPERIMENTAL (use_spin_budget) - Player HP is never
                # spent in this mode (see game_config.py's docstring for
                # why Elixir/HP become dead levers here); the loop's own
                # while-condition (spins_remaining > 0) is what actually
                # ends the session. This explicit break only matters for a
                # correct end_reason LABEL on the one iteration that empties
                # the budget - the safety-net check after the loop (below)
                # covers the case where an earlier `continue` in the
                # boss_system_active branch above skipped straight past
                # this line on that same iteration.
                if self.spins_remaining <= 0:
                    end_reason = "spins_depleted"
                    break
                continue

            if self.boss_counterattack_grace:
                # This trio's first static state since it was rolled - no
                # counter-attack this spin, consumed once.
                self.boss_counterattack_grace = False
                total_damage = 0.0
            elif self.config.use_flat_damage.get(tier, False):
                total_damage = sum(
                    self.config.flat_boss_counterattack_damage for b in self.config.boss_ids if self.boss_alive[b]
                )
                self.player_hp -= total_damage
            else:
                total_damage = sum(self.boss_dam[b] for b in self.config.boss_ids if self.boss_alive[b])
                self.player_hp -= total_damage
            bonus_counterattack_event(self, total_damage, self.player_hp)
            player_hp_state_event(self)
            if self.player_hp <= 0:
                end_reason = "hp_depleted"
                break

        # Safety net: if the loop exited via its own while-condition
        # (spins_remaining already hit 0 on an iteration whose body took an
        # early `continue` above - e.g. an endless-stage6 reroll on the
        # exact same spin the budget emptied - rather than the explicit
        # `break` a few lines up), end_reason is still stuck at the
        # "safety_cap" default from initialization. Correct it here rather
        # than trying to cover every such interleaving inline above.
        if spin_budget_mode and end_reason == "safety_cap" and self.spins_remaining <= 0:
            end_reason = "spins_depleted"

        self.bonus_spin_count = spin_count
        self.bonus_end_reason = end_reason

        bonus_end_event(self, tier, spin_count, self.player_hp, end_reason)

        self.in_bonus = False
        self.gametype = self.config.basegame_type

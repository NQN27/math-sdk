"""Boss battle / stage system + Power system bookkeeping, layered on top of
game_calculations.evaluate_and_explode's per-instance damage rolls / Wild
Multi math.

Boss state (stage, 3 bosses' Dam/HP, removed low-pay symbols, pruned
reward-drop tiers) lives entirely on the gamestate instance and is reset
fresh every spin (see game_override.reset_book) - Phase 1 has no cross-spin
persistence (that is Phase 3's job). Power state (global_multi_total,
power_queue) is likewise per-spin only, reset in the same place. Never
mutate self.config here - it is a process-wide singleton (see
game_config.GameConfig.__new__); every Power effect that changes the board
does so on `self.board`/gamestate-instance data only.
"""

import random
import warnings
from copy import copy

from game_calculations import GameCalculations
from src.calculations.statistics import get_random_outcome
from src.events.events import tumble_board_event
from game_events import (
    board_explode_event,
    boss_state_event,
    boss_defeated_event,
    stage_clear_event,
    power_connected_event,
    power_activated_event,
    power_state_event,
    player_hp_state_event,
    spin_budget_state_event,
)


class GameExecutables(GameCalculations):
    """Game-dependent grouped functions: boss/stage system + removed-symbol
    board enforcement."""

    # --- Phase 4: forced starting stage (Ultimate Power/God Mode) ----------
    def resolve_feature_start_stage(self) -> int:
        """1 for every bet mode except Ultimate Power/God Mode (see
        game_config.feature_spin_start_stage_choices - a dict keyed by bet-
        mode NAME, only ever containing those 2 entries), which roll
        uniformly among their configured stage choices. Called from
        game_override.reset_book, BEFORE reset_boss_battle - `dict.get` on a
        name not present in the config dict returns None immediately, with
        no `random.choice` call at all, so "base"'s own RNG-call sequence
        for reset_boss_battle is completely unaffected by this.

        Reads `self.betmode` directly (NOT via get_current_betmode(), which
        loops config.bet_modes looking for a name match and returns None if
        `self.betmode` isn't set yet) - GeneralGameState.__init__ calls
        reset_book() once during construction, BEFORE anything ever sets
        `self.betmode` (that only happens later, from run_sims/create_books
        or a direct-call harness), so this must tolerate "not set yet"
        without raising."""
        betmode_name = getattr(self, "betmode", None)
        if betmode_name is None:
            return 1
        choices = self.config.feature_spin_start_stage_choices.get(betmode_name)
        return random.choice(choices) if choices else 1

    # --- Controlled Deadspin Routing -----------------------------------------
    def create_board_reelstrips(self) -> None:
        """Override of src.calculations.board.Board.create_board_reelstrips:
        draws the board exactly as before (the Pool/Reel Strips/Distribution
        are completely untouched), then applies the SAME Controlled Deadspin
        Routing algorithm (see _route_column_force_deadspin) from one of two
        independent triggers, each with its own chance:

        1. Base game spins (self.gametype == basegame_type): this bet mode's
           `deadspin_force_chance` - see game_config.py.
        2. A Bonus session's "grace spin" (2026-08-18, per game designer):
           NOT the same spin covered by `boss_counterattack_grace` - that
           flag is set AND consumed within the spin that clears a stage
           (the new trio's first static state is the END of that spin - it
           isn't even alive yet when that spin's own board gets drawn here).
           Instead this targets `grace_deadspin_pending`, which is set at
           the same moment but read-and-cleared right here, so it naturally
           lands on the NEXT spin's opening reveal - the first time the new
           trio is faced from a clean board. That spin gets a real chance at
           being quiet, via `bonus_grace_deadspin_chance`, matching the
           "breather" intent (skip counter-attack, then a good shot at a
           dead follow-up) as closely as the routing hook allows.
        """
        super().create_board_reelstrips()
        if self.gametype == self.config.basegame_type:
            betmode_name = getattr(self, "betmode", None)
            chance = self.config.deadspin_force_chance.get(betmode_name, 0.0)
        elif getattr(self, "in_bonus", False) and getattr(self, "grace_deadspin_pending", False):
            self.grace_deadspin_pending = False
            chance = self.config.bonus_grace_deadspin_chance
        elif getattr(self, "in_bonus", False):
            # EXPERIMENTAL (2026-09-06): per-tier, per-stage deadspin chance,
            # applied every ordinary (non-grace) Bonus spin within a
            # configured stage - reuses the same Controlled Deadspin Routing
            # primitive as the base-game/grace cases above, just keyed by
            # (tier, stage) instead of bet mode or the one-time grace flag.
            # Slows that stage's clear speed (fewer wins -> fewer boss-damage
            # instances per spin -> more spins needed -> more counterattacks
            # survived), pushing more of the funnel's death mass INTO that
            # stage instead of letting sessions coast past it. See
            # game_config.bonus_stage_deadspin_chance's docstring for
            # measured effect.
            tier = getattr(self, "bonus_tier", None)
            # GATED TO use_spin_budget (2026-09-16, see
            # bonus_stage_deadspin_chance's docstring in game_config.py) -
            # stays 0.0 for the live HP-based/flat-damage systems even if
            # this dict has nonzero entries, so populating it for the
            # spin-budget economy can't silently regress those already-
            # validated systems.
            if self.config.use_spin_budget.get(tier, False):
                chance = self.config.bonus_stage_deadspin_chance.get(tier, {}).get(self.stage, 0.0)
            else:
                chance = 0.0
        else:
            return
        routed_any = False
        if chance > 0:
            for col in (1, 2, 3):  # columns 2,3,4 (1-indexed) = reel index 1,2,3
                if random.random() < chance:
                    routed_any = True
                    self._route_column_force_deadspin(col)

        # EXPERIMENTAL (2026-09-06): the "reverse deadspin" counterpart to
        # bonus_stage_deadspin_chance above - per-tier, per-stage chance to
        # bias a column toward CONNECTING to its neighbor instead of
        # breaking, via _route_column_force_connect. Independent of the
        # deadspin roll above (a stage would normally be configured with
        # only one of the two, not both, but nothing stops trying both at
        # once). Built to ease stages that are overshooting their death%
        # target (too many dying there) - the opposite problem
        # bonus_stage_deadspin_chance was built for.
        if getattr(self, "in_bonus", False):
            tier = getattr(self, "bonus_tier", None)
            connect_chance = self.config.bonus_stage_connect_chance.get(tier, {}).get(self.stage, 0.0)
            if connect_chance > 0:
                for col in (1, 2, 3):
                    if random.random() < connect_chance:
                        routed_any = True
                        self._route_column_force_connect(col)
        if routed_any:
            self.get_special_symbols_on_board()

    def _route_column_force_deadspin(self, col: int) -> None:
        """Luong A (Force Deadspin): redraw column `col`'s stop position from
        a deterministically pre-filtered list of positions that cannot
        extend ANY payline running through column `col-1`'s ALREADY-FIXED
        board content - a single O(reel length) scan up front, never a
        reject-and-reroll while loop, so there is no infinite-loop risk even
        if the reel has zero valid candidates (falls back to leaving the
        natural draw untouched in that rare case, counted in
        self._deadspin_route_fallback_count for visibility).

        A candidate stop position is valid only if, for EVERY row of this
        column, ALL of the following hold (both directions of the Wild-
        substitution gap the naive "compare symbol names" spec would miss):
          - none of column `col-1`'s neighboring rows (r-1, r, r+1, clamped
            to the board edges - see the spec's row-window matrix) are
            Wild/Power-attribute (a Wild there would connect to ANY symbol
            here, so no candidate at this column can safely avoid it),
          - this column's own candidate symbol at that row is not itself
            Wild/Power-attribute (a Wild here would just as surely extend
            whatever run reaches it, regardless of column `col-1`'s
            content),
          - and this column's own candidate symbol's NAME does not equal any
            of those neighboring symbols' names.
        """
        prev_col = col - 1
        strip = self.reelstrip[col]
        n = len(strip)
        prev_rows = self.board[prev_col]
        num_rows = self.config.num_rows[col]

        def neighbor_rows(row):
            return range(max(0, row - 1), min(num_rows - 1, row + 1) + 1)

        prev_window_info = []
        for row in range(num_rows):
            names = set()
            any_wild = False
            for r in neighbor_rows(row):
                sym = prev_rows[r]
                if sym.check_attribute("wild"):
                    any_wild = True
                    break
                names.add(sym.name)
            prev_window_info.append((names, any_wild))

        valid_positions = []
        for pos in range(n):
            ok = True
            for row in range(num_rows):
                names, any_wild = prev_window_info[row]
                if any_wild:
                    ok = False
                    break
                candidate_name = strip[(pos + row) % n]
                if candidate_name == "W" or candidate_name in self.config.power_symbol_names:
                    ok = False
                    break
                if candidate_name in names:
                    ok = False
                    break
            if ok:
                valid_positions.append(pos)

        if not valid_positions:
            self._deadspin_route_fallback_count = getattr(self, "_deadspin_route_fallback_count", 0) + 1
            return

        new_pos = random.choice(valid_positions)
        self.reel_positions[col] = new_pos
        for row in range(num_rows):
            self.board[col][row] = self.create_symbol(strip[(new_pos + row) % n])
        if self.config.include_padding:
            self.top_symbols[col] = self.create_symbol(strip[(new_pos - 1) % n])
            self.bottom_symbols[col] = self.create_symbol(strip[(new_pos + num_rows) % n])

    def _route_column_force_connect(self, col: int) -> None:
        """EXPERIMENTAL (2026-09-06, game designer's idea): inverse of
        _route_column_force_deadspin above - redraw column `col`'s stop
        toward a position that DOES connect to column `col-1`'s already-
        fixed content, instead of guaranteeing it can't.

        NOT a symmetric guarantee the way deadspin's is: breaking one column
        already caps the whole board's kindCount below the paytable minimum
        (a hard, board-wide guarantee of zero wins), but making one column
        "connect" to its neighbor only raises the LOCAL match probability at
        one row - a full payline win still needs every other column to line
        up too. Useful as a soft assist lever, not a forced-win mechanic.

        Same conservative row-window (r-1,r,r+1) as the deadspin routine,
        inverted: a candidate position is accepted if ANY of its own window
        rows either lands Wild/Power-attribute, or matches a name already
        present in that row's column `col-1` window (ignoring Wild neighbors
        there, same as deadspin does, since a Wild neighbor already connects
        to anything - not a useful target to "match" against specifically).
        """
        prev_col = col - 1
        strip = self.reelstrip[col]
        n = len(strip)
        prev_rows = self.board[prev_col]
        num_rows = self.config.num_rows[col]

        def neighbor_rows(row):
            return range(max(0, row - 1), min(num_rows - 1, row + 1) + 1)

        prev_window_names = []
        for row in range(num_rows):
            names = set()
            for r in neighbor_rows(row):
                sym = prev_rows[r]
                if not sym.check_attribute("wild"):
                    names.add(sym.name)
            prev_window_names.append(names)

        connecting_positions = []
        for pos in range(n):
            ok = False
            for row in range(num_rows):
                candidate_name = strip[(pos + row) % n]
                if candidate_name == "W" or candidate_name in self.config.power_symbol_names:
                    ok = True
                    break
                if candidate_name in prev_window_names[row]:
                    ok = True
                    break
            if ok:
                connecting_positions.append(pos)

        if not connecting_positions:
            self._connect_route_fallback_count = getattr(self, "_connect_route_fallback_count", 0) + 1
            return

        new_pos = random.choice(connecting_positions)
        self.reel_positions[col] = new_pos
        for row in range(num_rows):
            self.board[col][row] = self.create_symbol(strip[(new_pos + row) % n])
        if self.config.include_padding:
            self.top_symbols[col] = self.create_symbol(strip[(new_pos - 1) % n])
            self.bottom_symbols[col] = self.create_symbol(strip[(new_pos + num_rows) % n])

    # --- Boss battle setup -------------------------------------------------
    def reset_boss_battle(self, start_stage: int = 1) -> None:
        """(Re)start the boss fight at `start_stage` with freshly-rolled
        bosses. Called at the start of every spin (see
        game_override.reset_book, always start_stage=1 there for every bet
        mode except Ultimate Power/God Mode - see resolve_feature_start_stage
        above) and again at the start of every Bonus SESSION (see
        game_bonus.run_bonus_session, which may pass start_stage=2/3 for the
        Super/Hidden tiers - a plain skip-ahead: no earlier stage's clear-
        effects (symbol removal/tier pruning) are pre-applied, only the
        starting stage number and its own freshly-rolled bosses change, per
        the task spec's plain reading)."""
        self.stage = start_stage
        self.boss_system_active = True
        self.removed_symbols = set()
        self.pruned_tiers = set()
        # Counter-attack grace (2026-08-17, per game designer): a freshly-
        # rolled boss trio does NOT get to counter-attack after its very
        # first static state - only from the SECOND static state onward
        # (with this same trio) does the normal per-spin counter-attack
        # resume. Deliberately NOT granted here at session start (only real
        # stage transitions via clear_stage grant it - see there and
        # game_bonus.run_bonus_session's endless stage-6 tail re-roll),
        # so stage 1 (or Super/Hidden's stage 2/3 opening stage) is
        # unaffected and behaves exactly as before.
        self.boss_counterattack_grace = False
        # Separate from boss_counterattack_grace above: that flag is set AND
        # consumed within the SAME spin that clears a stage (the new trio's
        # own first static state falls at the end of that spin - see the
        # comment there), so create_board_reelstrips never sees it True for
        # any spin's INITIAL reveal (the trio isn't even alive yet when that
        # spin's board is drawn). This flag instead targets the NEXT spin's
        # opening reveal - the first time the new trio is faced from a clean
        # board - and is read-and-cleared inside create_board_reelstrips
        # itself (2026-08-18, per game designer: also route the grace-spin's
        # deadspin check through Luong A).
        self.grace_deadspin_pending = False
        self.roll_stage_bosses(self.stage)

    def roll_stage_bosses(self, stage: int) -> None:
        """Roll fresh Dam/HP for all 3 bosses at the given stage: base value
        * uniform(0.75, 1.25), Dam rounded to the nearest integer, HP rounded
        to the nearest multiple of 10. Reroll (all 3 together) if the 3 HPs'
        spread ((max-min)/max) exceeds boss_hp_spread_max."""
        base = self.config.boss_stage_table[stage]
        lo, hi = self.config.boss_variance_range
        tier = getattr(self, "bonus_tier", None)
        if tier and self.config.use_flat_damage.get(tier, False):
            tier_mult = self.config.flat_damage_boss_hp_mult.get(tier, 1.0)
            # Per-stage override (dict keyed by stage) lets one tier's
            # funnel be reshaped stage-by-stage without touching the shared
            # boss_stage_table itself - falls back to the tier's flat scalar
            # for any stage not explicitly listed.
            hp_mult = tier_mult.get(stage, 1.0) if isinstance(tier_mult, dict) else tier_mult
        else:
            hp_mult = 1.0
        hp, dam = {}, {}
        for _ in range(self.config.boss_hp_reroll_attempts):
            for b in self.config.boss_ids:
                base_dam, base_hp = base[b]
                dam[b] = int(round(base_dam * random.uniform(lo, hi)))
                hp[b] = int(round(base_hp * hp_mult * random.uniform(lo, hi) / 10.0) * 10)
            max_hp, min_hp = max(hp.values()), min(hp.values())
            if max_hp <= 0 or (max_hp - min_hp) / max_hp <= self.config.boss_hp_spread_max:
                break

        self.boss_dam = dam
        self.boss_hp = {b: float(hp[b]) for b in self.config.boss_ids}
        self.boss_hp_max = dict(hp)
        self.boss_alive = {b: True for b in self.config.boss_ids}
        self.stage_defeat_order = []

    # --- Column -> boss routing ("scenario 1") ------------------------------
    def route_boss_for_column(self, col: int) -> str:
        """Which boss a given column currently routes damage to."""
        if col in self.config.boss_primary_zone:
            return self.config.boss_primary_zone[col]
        primary, fallback = self.config.boss_fallback_zone[col]
        return primary if self.boss_alive[primary] else fallback

    def deal_damage_to_boss(self, col: int, damage: float) -> None:
        """Route one exploding instance's damage to whichever boss `col`
        currently points to (re-evaluated live, so a mid-pass boss death or
        stage clear correctly re-routes later instances in this same pass).
        Already-defeated bosses and a dormant (post-stage-6) boss system take
        no damage.

        Phase 3: `booster_multiplier_current_spin` (default 1, only ever !=1
        during a Bonus spin that follows one where a Booster was collected -
        see game_bonus.run_one_bonus_spin) doubles every damage roll for the
        WHOLE of that one spin's resolve loop, exactly like
        wild_damage_multiplier already does for Wild-substituted damage -
        the two stack multiplicatively if both apply to the same instance."""
        if not self.boss_system_active:
            return
        boss_id = self.route_boss_for_column(col)
        if not self.boss_alive.get(boss_id, False):
            return
        damage *= getattr(self, "booster_multiplier_current_spin", 1.0)
        self.boss_hp[boss_id] = max(0.0, self.boss_hp[boss_id] - damage)
        if self.boss_hp[boss_id] <= 0:
            self.on_boss_defeated(boss_id)

    # --- Boss defeat / reward-drop / stage clear ----------------------------
    def on_boss_defeated(self, boss_id: str) -> None:
        """A boss's HP just reached 0: roll+pay its instant reward-drop, and
        if it is the 3rd (last) boss defeated in this stage, clear the
        stage."""
        self.boss_alive[boss_id] = False
        self.stage_defeat_order.append(boss_id)
        # Session-scoped kill tally, reset per book (reset_bonus_state) and
        # per Bonus session (run_bonus_session). Base-game combat increments
        # it too; nothing outside a Bonus session reads it.
        self.bonus_kill_count += 1
        is_last_of_stage = len(self.stage_defeat_order) == 3

        tier, amount = self.roll_reward_drop(is_last_of_stage, self.stage)
        # Design decision (supersedes the earlier Phase 2 behavior): Global
        # Multi (PGM) must NOT scale boss-defeat reward-drops - it only
        # multiplies ordinary line payout, same as it never scales boss
        # damage (see game_calculations.py's whole-board-explode section).
        # This keeps boss HP a real "wall": neither PGM nor Wild Multi can
        # inflate the cash side of a boss kill, only line wins.
        awarded = self.award_win(amount)
        self.record(
            {
                "kind": "bossDefeated",
                "symbol": "boss",
                "stage": self.stage,
                "gametype": self.gametype,
            }
        )
        boss_defeated_event(self, boss_id, is_last_of_stage, tier, awarded)

        if is_last_of_stage:
            self.clear_stage(self.stage)

        boss_state_event(self)

    def roll_reward_drop(self, is_last_of_stage: bool, stage: int):
        """Roll one reward from the 21-tier table, honoring: tiers pruned by
        earlier stage-clears this spin; the top-3 tiers (2000/5000/Maxwin)
        reserved for whichever boss is defeated LAST within a stage; stage 6's
        last-defeated boss instead rolling ">=500x" from a fixed subset; and
        the Maxwin(=wincap) tier NEVER being eligible outside the dedicated
        "wincap" criteria fence (see game_calculations.award_win's docstring
        for why - this is the exact bug this project's notes warn about) -
        EXCEPT for one narrow, deliberate carve-out (see below).

        Design decision - "natural" Max-Win path via the stage-6 chest: ONLY
        the stage-6-last-boss pool gets a small extra chance at the Maxwin
        tier even on a non-"wincap" criteria (self.config.
        stage6_chest_natural_maxwin_weight - tiny, ~1-in-500k per chest-open,
        pending final calibration). This is intentionally NOT the same as
        actually winning wincap: award_win's headroom guard still clamps the
        payout to just under whatever's left of running_bet_win's headroom
        (same as any other large reward-drop) - it does NOT set
        wincap_triggered and does NOT end the spin early, because that
        entire mechanism is hard-gated on self.criteria=="wincap"
        elsewhere (see activate_maxwin_power / award_win's docstring) and
        deliberately was not touched here - bypassing that gate would let a
        non-"wincap" book actually reach the literal wincap value, which is
        exactly the previously-fixed bug this project's notes warn about.
        The player-facing result is "an exceptionally large win, at the
        20000x TIER label" rather than a true, spin-ending Max Win - a real
        Max Win still only ever comes from the dedicated "wincap" fence.

        Tier-aware table (2026-08-14/15): Normal- and Super-tier Bonus
        sessions each use their own dedicated, hard-tuned table
        (config.reward_drop_weights_normal_bonus / _super_bonus - see
        game_config.py for each tier's hard-tuning rationale) - base-game
        combat and Hidden Bonus keep the shared, uncompressed table
        unchanged. KNOWN SIMPLIFICATION, not a bug: `self.pruned_tiers`
        (stage-clear progression, see clear_stage/stage_clear_pruned_tiers)
        is still populated with the SHARED table's ORIGINAL-scale values
        (1,2,3,...) regardless of tier, so for Normal/Super-bonus
        specifically (whose pools use remapped keys) this pruning is a
        no-op - low tiers stay reachable slightly longer than the shared-
        table design intends. This was already true of the exact
        configuration each tier's hard-tuned mean was measured against, so
        "fixing" it now would change calibrated behavior without
        re-verification - left as a documented, deliberate non-fix pending
        a follow-up pass, not silently patched over."""
        if getattr(self, "in_bonus", False) and self.bonus_tier == "normal":
            weights = self.config.reward_drop_weights_normal_bonus
            top_tiers = self.config.reward_drop_top_tiers_normal_bonus
            stage6_last_tiers = self.config.reward_drop_stage6_last_tiers_normal_bonus
            # Normal-only: keep the stage-6 chest pool TRULY exclusive (never
            # also drawable on a regular/other-stage kill). Scoped to this
            # branch alone so base-game combat and Hidden Bonus - whose
            # stage6_last_tiers has always been (and was calibrated/locked
            # with) some leakage into the regular pool via tier-value
            # collisions - are byte-for-byte unaffected. This exclusivity is
            # what keeps the stage-6-clear "second peak" visually distinct in
            # Normal's payout distribution (see game_config.py's
            # reward_drop_weights_normal_bonus comment for the full story).
            exclusive_chest_tiers = stage6_last_tiers
        elif getattr(self, "in_bonus", False) and self.bonus_tier == "super":
            weights = self.config.reward_drop_weights_super_bonus
            top_tiers = self.config.reward_drop_top_tiers_super_bonus
            stage6_last_tiers = self.config.reward_drop_stage6_last_tiers_super_bonus
            # Super-only, same rationale as Normal above (see game_config.py's
            # reward_drop_weights_super_bonus comment for Super's hard-tuning
            # story) - scoped to this branch alone so base-game combat and
            # Hidden Bonus are byte-for-byte unaffected.
            exclusive_chest_tiers = stage6_last_tiers
        else:
            weights = self.config.reward_drop_weights
            top_tiers = self.config.reward_drop_top_tiers
            stage6_last_tiers = self.config.reward_drop_stage6_last_tiers
            exclusive_chest_tiers = set()
        maxwin_tier = int(self.config.wincap)
        is_stage6_chest = stage == self.config.max_stage and is_last_of_stage

        if is_stage6_chest:
            pool = {k: w for k, w in weights.items() if k in stage6_last_tiers}
        else:
            pool = {k: w for k, w in weights.items() if k not in self.pruned_tiers and k not in exclusive_chest_tiers}
            if not is_last_of_stage:
                pool = {k: w for k, w in pool.items() if k not in top_tiers}

        if self.criteria != "wincap":
            pool = {k: w for k, w in pool.items() if k != maxwin_tier}
            if is_stage6_chest:
                pool[maxwin_tier] = self.config.stage6_chest_natural_maxwin_weight
        elif is_last_of_stage and maxwin_tier in pool:
            # Dedicated wincap fence: bias hard toward Maxwin so the fence
            # (which redraws the whole spin until final_win == wincap)
            # converges in a reasonable number of repeats.
            pool = {
                k: (
                    self.config.wincap_force_maxwin_weight
                    if k == maxwin_tier
                    else self.config.wincap_force_other_weight
                )
                for k in pool
            }

        if not pool:
            pool = {min(weights.keys()): 1}

        tier = get_random_outcome(pool)
        return tier, float(tier)

    def clear_stage(self, stage: int) -> None:
        """Apply stage N's clear effect (remove a low-pay symbol from play +
        prune its reward-drop tiers for the rest of this spin) and advance to
        stage N+1 with a freshly-rolled trio of bosses - or, past stage 6,
        leave the boss system dormant for the rest of this spin (design
        decision, see readme.txt: there is no stage 7)."""
        removed_symbol = self.config.stage_clear_removed_symbol.get(stage)
        pruned = self.config.stage_clear_pruned_tiers.get(stage, [])
        self.pruned_tiers.update(pruned)
        if removed_symbol:
            self.removed_symbols.add(removed_symbol)
            self.enforce_removed_symbols()

        next_stage = stage + 1
        if next_stage > self.config.max_stage:
            self.boss_system_active = False
            next_stage = None
        else:
            self.roll_stage_bosses(next_stage)
            self.stage = next_stage
            # This freshly-rolled trio is exempt from counter-attack at its
            # own first static state (see reset_boss_battle's comment) -
            # covers every real stage transition (1->2 .. 5->6). The
            # endless stage-6 tail's own re-roll (game_bonus.
            # run_bonus_session) sets this same flag separately, since that
            # re-roll does not go through clear_stage.
            self.boss_counterattack_grace = True
            # See reset_boss_battle's comment: this targets the NEXT spin's
            # opening board draw (this spin's board already exists - the new
            # trio was born mid-cascade).
            self.grace_deadspin_pending = True

        # Phase 3: every stage-clear DURING a Bonus session (any of the
        # multiple spins in it, not just the first) grants +50 to Player
        # HP's CURRENT value AND +50 to its MAX independently (never auto-
        # refills to the new max - e.g. 750/800 -> 800/850, not 850/850).
        # This is on top of the symbol-removal/tier-pruning effect above,
        # which applies completely unchanged in Bonus.
        #
        # EXCEPTION - endless stage-6 tail: this grant is suppressed for
        # every REPEAT clear of stage 6 (self.stage6_loop_count > 0 at the
        # moment this fires - it's bumped by run_bonus_session AFTER this
        # runs, so it still reads as 0 on the very first stage-6 clear,
        # which still gets its +50 same as every other stage). Without
        # this, the tail's own escalating Dam (stage6_dam_escalation) has
        # to "outrace" a HP top-up every single loop, which measurement
        # (hp_pool_sweep_endless.py) showed made even aggressive escalation
        # (x3.0+) unable to bound hidden tier's average session payout back
        # near its target - the +50/loop heal was fighting the escalation
        # mechanic by design intent, not adding a real risk/reward choice.
        if getattr(self, "in_bonus", False) and not (
            stage == self.config.max_stage and getattr(self, "stage6_loop_count", 0) > 0
        ):
            tier = getattr(self, "bonus_tier", None)
            if tier and self.config.use_spin_budget.get(tier, False):
                # EXPERIMENTAL (use_spin_budget) - see game_config.py's
                # docstring. Direct analogue of the +50 Player HP grant
                # below, but Player HP is never granted/spent in this mode -
                # deliberately sharing this method's outer guard (suppressed
                # on endless-stage6-tail REPEAT clears) for the same reason
                # the HP grant is: an unbounded per-loop grant would let the
                # endless tail extend the spin budget forever with nothing
                # to offset it, since a spin count (unlike HP-vs-boss_dam)
                # has no escalating counter-pressure of its own.
                lo, hi = self.config.spin_budget_per_stage_clear.get(tier, (0, 0))
                self.spins_remaining += random.randint(lo, hi)
                spin_budget_state_event(self)
            else:
                hp_bonus = 50.0
                if tier and self.config.use_flat_damage.get(tier, False):
                    # Same integer-HP reasoning as the initial grant in
                    # game_bonus.run_bonus_session.
                    hp_bonus = round(hp_bonus * self.config.flat_damage_player_hp_bonus_mult.get(tier, 1.0))
                self.player_hp += hp_bonus
                self.player_hp_max += hp_bonus
                player_hp_state_event(self)

        stage_clear_event(self, stage, removed_symbol, pruned, next_stage)

    # --- Removed-symbol board enforcement -----------------------------------
    def tumble_game_board(self) -> None:
        """Override of src.executables.executables.Executables.tumble_game_board
        (the SDK's plain remove-and-refill-from-reelstrip step): also purge
        any stage-removed symbol the raw reel-strip refill just pulled back
        onto the board.

        BUG FIX: `enforce_removed_symbols`'s own docstring always claimed
        this happens "again after every tumble refill" (to catch the reel
        strip pulling a since-removed symbol back onto the board on a LATER
        tumble/spin), but no caller anywhere actually did this - it was
        previously invoked exactly once, from clear_stage(), at the moment a
        symbol is newly removed. That purges existing on-board copies at
        that instant, but every subsequent tumble_game_board() call (every
        remaining pass of the SAME base spin, and - far more consequentially
        - every one of a Bonus session's many later internal spins, since
        `removed_symbols` persists for the whole session, see
        game_bonus.run_bonus_session) drew straight from the ordinary reel
        strip with no such filtering, so a stage-removed low-pay symbol could
        (and, empirically, does) reappear on the board and keep paying/
        exploding for the rest of the spin/session - directly contradicting
        the spec's "loai 1 bieu tuong tra thuong thap... chi ap dung ben
        trong phien bonus dang chay" (removed symbol stays removed for the
        rest of the session it was removed in). Overriding this single
        method (called from both gamestate.run_spin's base-spin loop and
        game_bonus.run_one_bonus_spin's Bonus-internal-spin loop - the only
        two tumble call sites in this game) fixes both in one place instead
        of patching every call site individually.
        """
        if getattr(self.config, "use_inplace_tumble", False):
            self._tumble_board_in_place()
        else:
            super().tumble_game_board()
        self.enforce_removed_symbols()
        if getattr(self, "in_bonus", False):
            self._maybe_apply_chain_block()

    def _tumble_board_in_place(self) -> None:
        """EXPERIMENTAL (2026-09-04, game designer's idea): replace exploded
        symbols in their own row/column - nothing else moves - instead of
        the SDK's default cascade/gravity refill (src.calculations.tumble.
        tumble_board, which drops surviving symbols down and refills from the
        top). Requested to make line-pay behavior easier to reason about:
        cascades let symbols realign into brand-new lines across passes
        (falling together can connect symbols that weren't adjacent before),
        which compounds line-hit frequency in a way that's hard to isolate
        from a single lever. In-place replace only refreshes the exact cells
        that exploded, so each pass's line-hit rate is closer to independent
        per-cell odds.

        SAFE BY CONSTRUCTION per a full dependency audit (2026-09-04) before
        this was written, not by assumption:
          - The resolve loop (gamestate's per-spin pass loop, both directions
            of _both_ways_reversed_wins) re-derives every win position FRESH
            from the live board every single pass - nothing anywhere assumes
            a row/col index from a previous pass survives a tumble.
          - Every one of this game's OWN board-mutating mechanics (the 5 FIFO
            Power handlers, _route_column_force_deadspin, chain_block,
            enforce_removed_symbols) already writes board[r][ro] by absolute
            position with no gravity assumption - none of them needed to
            change for this.
          - reel_positions[reel] normally encodes "board is a contiguous
            window into reelstrip[reel]" - decrementing it per replacement
            (same as the SDK's own tumble_board) breaks that window property
            after the first tumble, but nothing reads it again afterward
            except the ONE-TIME initial padding-positions event (already
            fired before any tumble happens) - confirmed via repo-wide
            search, not assumed.
          - `board_before_tumble` (SDK writes it, never reads it anywhere -
            confirmed via repo-wide search) is kept here for parity but is
            dead weight either way.
        Symbol SOURCE is unchanged from the SDK's own approach (sequential
        pull from the same per-reel weighted reelstrip, via self.create_symbol
        so special-symbol functions/Power assignment still run) - only the
        DESTINATION changes (the exploded cell itself, not always the top of
        the column) - so this doesn't alter per-symbol selection statistics,
        only board layout/adjacency after a pass.

        KNOWN GAP, not yet resolved: tumble_board_event's `new_symbols_from_
        tumble` payload is a per-reel LIST with no row attached - the
        frontend currently infers landing row from gravity (drop count from
        the top). This still populates that same list (so the event doesn't
        crash or misreport counts), but a frontend/animation update is
        needed separately to actually render "replace in place" instead of
        "fell from the top" - this commit is math-side only.
        """
        self.board_before_tumble = copy(self.board)
        self.new_symbols_from_tumble = [[] for _ in range(len(self.board))]
        for reel, column in enumerate(self.board):
            for row, sym in enumerate(column):
                if not sym.explode:
                    continue
                reel_pos = (self.reel_positions[reel] - 1) % len(self.reelstrip[reel])
                self.reel_positions[reel] = reel_pos
                new_name = self.reelstrip[reel][reel_pos % len(self.reelstrip[reel])]
                new_sym = self.create_symbol(new_name)
                self.board[reel][row] = new_sym
                self.new_symbols_from_tumble[reel].append(new_sym)
        tumble_board_event(self)

    def _maybe_apply_chain_block(self) -> None:
        """Chain-block reactive check (see game_config.chain_block_threshold/
        chain_block_step docstring) - MUST run after enforce_removed_symbols
        above, never before: a removed-symbol resample could otherwise
        overwrite/undo a just-forced-dead column and accidentally reconnect a
        win, defeating the guarantee (found via the 2026-08-19 rebalance
        proposal's own JS-demo debugging history).

        Rolls (or, if a prior pass's forced-deadspin attempt found no safe
        column and left chain_block_pending set, unconditionally retries)
        whether to force a column dead this pass. Tries columns 1-3 in random
        order, stopping at the first one _route_column_force_deadspin
        actually manages to redraw (detected via its fallback counter not
        incrementing); if all three hit the fallback, the attempt carries
        over to the next pass instead of being dropped.
        """
        triggered = getattr(self, "chain_block_pending", False)
        if not triggered:
            tier = getattr(self, "bonus_tier", None)
            if tier and self.config.use_spin_budget.get(tier, False):
                # EXPERIMENTAL (2026-09-16) - see game_config.py's
                # spin_budget_chain_block_threshold/_step docstring for why
                # this is a separate override rather than editing the
                # shared chain_block_threshold/chain_block_step directly.
                threshold = self.config.spin_budget_chain_block_threshold.get(tier, self.config.chain_block_threshold)
                step = self.config.spin_budget_chain_block_step.get(tier, self.config.chain_block_step)
            else:
                threshold = self.config.chain_block_threshold
                step = self.config.chain_block_step
            extra = getattr(self, "chain_pass_count", 0) - threshold
            if extra < 0:
                return
            chance = min(1.0, step * (extra + 1))
            if random.random() >= chance:
                return
            triggered = True

        self.chain_block_pending = False
        cols = [1, 2, 3]
        random.shuffle(cols)
        blocked = False
        for col in cols:
            before = getattr(self, "_deadspin_route_fallback_count", 0)
            self._route_column_force_deadspin(col)
            after = getattr(self, "_deadspin_route_fallback_count", 0)
            if after == before:
                blocked = True
                break
        if blocked:
            self.get_special_symbols_on_board()
        else:
            self.chain_block_pending = True

    def enforce_removed_symbols(self) -> None:
        """Replace every board cell currently showing a stage-removed symbol
        with a fresh resample from that column's own reel strip. Called
        immediately when a symbol is removed (purges existing copies off the
        board, so cells can't go permanently dead) and again after every
        tumble refill for the rest of the spin (in case reel continuation
        pulls the same now-removed symbol back in)."""
        if not self.removed_symbols:
            return
        for r in range(self.config.num_reels):
            for ro in range(self.config.num_rows[r]):
                if self.board[r][ro].name in self.removed_symbols:
                    self.board[r][ro] = self.resample_valid_symbol(r)

    def resample_valid_symbol(self, reel: int):
        """Draw a replacement symbol for `reel` from that SAME reel's strip
        at a fresh random offset, rejecting removed-paytable symbols AND
        every Wild-like symbol - plain "W" AND all 8 Power names (never
        mutates self.config.reels - only ever reads it). Rejecting "W" alone
        was a documented prior-build fix (avoid inflating wild density via
        symbol-removal reroll); Phase 2 extends the same reject-set to the 8
        Power names, since this helper is now ALSO reused by Mystery/Alter
        (game_executables' FIFO power handlers below) where the spec calls
        for a "normal paying symbol" reroll specifically - letting a Power
        symbol slip back in here would both inflate wild-like density AND
        (on the WCAP reel, which carries "PMX") risk resurrecting a Maxwin
        power outside its intended activation path.

        Uses a filtered-pool draw rather than reject-sampling: with 9
        rejected names now instead of 1, a fixed number of retries could
        plausibly exhaust without success on a heavily-loaded strip (e.g.
        WCAP), silently falling through to a wild-like symbol - filtering
        the strip's own values up front and drawing from that instead has
        no such failure mode."""
        strip = self.reelstrip[reel]
        # Phase 3: excludes "SC" too (see config.resample_exclude_names) -
        # this reroll must never conjure a Scatter back onto the board
        # either (no-op on FR0/FR1/FR2, which never carry "SC" at all).
        pool = [s for s in strip if s not in self.config.resample_exclude_names and s not in self.removed_symbols]
        if not pool:
            # Degenerate fallback (should not happen with this game's reels -
            # every column always has plenty of non-wild-like, non-removed
            # symbols): fall back to any non-wild-like/non-Scatter symbol,
            # ignoring the removed-symbol exclusion, rather than ever
            # emitting Wild/Power/Scatter.
            pool = [s for s in strip if s not in self.config.resample_exclude_names] or list(strip)
        name = pool[random.randrange(0, len(pool))]
        return self.create_symbol(name)

    # --- Per-pass event/bookkeeping helper ----------------------------------
    def emit_pass_extra_events(self) -> None:
        """Emit the board-wide explode event (superset of the winning
        lines' own positions) and a boss-state snapshot, once per resolve
        pass, after the line-win events (see gamestate.py)."""
        if self.pass_exploded_positions:
            board_explode_event(self, self.pass_exploded_positions)
        boss_state_event(self)
        power_state_event(self)

    # =========================================================================
    # Power system (Phase 2)
    # =========================================================================

    def reset_power_system(self) -> None:
        """(Re)start the Power system fresh for a new spin - called from
        game_override.reset_book alongside reset_boss_battle.
        global_multi_total is the raw accumulated Global Multi bonus (0 =
        inactive/no effect - see game_calculations.effective_global_mult);
        power_queue is the FIFO queue of collected-but-not-yet-activated
        powers (list of type keys, e.g. "extra_wild") awaiting one-at-a-time
        activation between tumble passes (see gamestate.py)."""
        self.global_multi_total = 0
        self.power_queue = []
        self.power_clamp_events = 0

    # --- Immediate-group activation ------------------------------------------
    # Wild Multi is pure win-amount arithmetic and stays in
    # game_calculations.evaluate_and_explode (it never touches boss/board
    # bookkeeping). Global Multi and Maxwin are bookkeeping and live here.

    def activate_global_multi_cells(self, cells) -> None:
        """One or more Global Multi cells connected this pass (already
        deduplicated by physical cell by the caller) - each independently
        rolls an increment from the shared factor list and adds it to the
        running total, in column-major order for determinism.
        power_multi_factor_weights is tier-scoped (2026-08-28) - "default"
        covers base-game combat (self.bonus_tier is None there)."""
        multi_weights = self.config.power_multi_factor_weights.get(
            getattr(self, "bonus_tier", None) or "default", self.config.power_multi_factor_weights["default"]
        )
        for r, ro in sorted(cells):
            added = get_random_outcome(multi_weights)
            self.global_multi_total += added
            power_activated_event(
                self,
                "global_multi",
                {"position": {"reel": r, "row": ro}, "added": added, "newTotal": self.global_multi_total},
            )

    def activate_maxwin_power(self, cells) -> None:
        """Maxwin power connected this pass: grab the game's Maxwin (wincap)
        and end the spin right there. Routes through the EXACT SAME
        wincap-fence mechanism as the boss-defeat reward-drop's Maxwin tier
        (see roll_reward_drop below / game_calculations.award_win): this
        only actually pays out when self.criteria == "wincap". The Maxwin
        Power symbol ("PMX") is structurally excluded from the base "BR0"
        reel (see reels/BR0.csv - it only appears on reels/WCAP.csv) so this
        should never be reached under any other criteria; the check below is
        a second, defensive layer of the same kind Phase 1 already applied
        to the reward-drop Maxwin tier (never pay 20000x under a non-wincap
        fence). award_win's amount deliberately overshoots running_bet_win
        past config.wincap - the SDK's existing update_final_win()
        overshoot-then-clamp (`min(running_bet_win, wincap)`) is what turns
        that into exactly wincap as the final payout, and the very next
        emit_tumble_win_events()/evaluate_wincap() call in gamestate.py's
        loop sets wincap_triggered, which is what actually stops further
        resolve passes ("ends the entire spin right there")."""
        r, ro = sorted(cells)[0]
        if self.criteria != "wincap":
            warnings.warn(
                "\nMaxwin power symbol connected under non-'wincap' criteria "
                f"(sim {self.sim}, criteria {self.criteria}) - this should be "
                "structurally impossible (PMX is excluded from reels/BR0.csv); "
                "no-op'd as a defensive measure, no win paid.\n"
            )
            power_connected_event(self, "maxwin", r, ro)
            return
        awarded = self.award_win(self.config.wincap)
        power_activated_event(self, "maxwin", {"position": {"reel": r, "row": ro}, "awarded": awarded})

    # --- FIFO-group collection/activation ------------------------------------

    def enqueue_fifo_powers(self, fifo_cells) -> None:
        """Append this pass's newly-connected FIFO-group powers to the
        queue, in collection order (already correct by construction - see
        game_calculations.evaluate_and_explode's scan: line-index order,
        then left-to-right within a line, deduplicated by physical cell)."""
        for r, ro, ptype in fifo_cells:
            self.power_queue.append(ptype)
            power_connected_event(self, ptype, r, ro)

    def _fifo_power_handlers(self) -> dict:
        """Type-key -> handler dispatch table, shared by activate_next_power
        (one-at-a-time, the default for every bet mode) and
        activate_all_queued_powers (Phase 4's God Mode drain-all override -
        see below)."""
        return {
            "extra_wild": self.power_extra_wild,
            "extra_power": self.power_extra_power,
            "big_symbol": self.power_big_symbol,
            "mystery": self.power_mystery,
            "alter": self.power_alter,
        }

    def activate_next_power(self) -> bool:
        """Pop and activate exactly ONE power from the front of the FIFO
        queue (the default for every bet mode except God Mode - see
        activate_all_queued_powers below). Returns True if a power was
        activated (board mutated), False if the queue was empty. Dispatches
        purely on the STORED type key, never by re-reading a board cell - by
        the time a queued power is popped, tumble or an earlier-activated
        Power may already have overwritten the cell it was originally
        collected from."""
        if not self.power_queue:
            return False
        ptype = self.power_queue.pop(0)
        handler = self._fifo_power_handlers()[ptype]
        handler()
        self.get_special_symbols_on_board()
        return True

    def activate_all_queued_powers(self) -> bool:
        """Phase 4 (God Mode only - see gamestate.run_spin's
        power_drain_all_modes check): drain the ENTIRE FIFO queue in one
        step, activating every currently-queued power back-to-back, THEN
        re-evaluate the board once (the caller's very next
        evaluate_and_explode call) - matching the spec's "activate ALL of
        them simultaneously/together in one step instead of one-at-a-time".
        Each individual handler still runs in strict FIFO collection order
        (a well-defined, deterministic sequence), just without waiting for
        an intervening tumble/re-evaluation between them. Returns True if
        anything was activated, False if the queue was already empty - same
        contract as activate_next_power, so gamestate.py's branch can call
        either interchangeably."""
        if not self.power_queue:
            return False
        handlers = self._fifo_power_handlers()
        while self.power_queue:
            ptype = self.power_queue.pop(0)
            handlers[ptype]()
        self.get_special_symbols_on_board()
        return True

    # --- Placement helper -----------------------------------------------------

    def _open_power_placement_cells(self) -> list:
        """Cells eligible for Extra Wild/Extra Power placement: any cell NOT
        on column 0 (reel index 0 - Wild/Power never land there) whose
        CURRENT symbol is not already Wild/Power (never overwrites an
        existing Wild/Power cell; ordinary paying symbols ARE valid targets
        and get overwritten - the task spec is explicit about this: "avoid
        overwriting existing Wild/Power", nothing more)."""
        cells = []
        for r in range(1, self.config.num_reels):
            for ro in range(self.config.num_rows[r]):
                if not self.board[r][ro].check_attribute("wild"):
                    cells.append((r, ro))
        return cells

    # --- Phase 4: Ultimate Power/God Mode Power-count guarantee ------------
    def guarantee_min_power_landed(self, min_count: int) -> None:
        """Top up the CURRENT board (called right after it is drawn, before
        the first evaluate_and_explode of the spin - see gamestate.run_spin)
        so at least `min_count` Power symbols (any of the 8 PWM/PGM/PMX/PXW/
        PXP/PBS/PMY/PAL names - plain "W" does NOT count, the spec is
        specifically about Power) are present. Landing on the very first
        reveal trivially satisfies "at least N Power symbols land within
        the spin" (the spin's OWN first reveal already IS part of the spin)
        without needing to track a running tally across later tumble/FIFO-
        placement passes - deliberately the simplest correct reading, not
        an approximation. No-op if the natural/forced draw already met the
        floor (this reel - PWR0/WCAP - is already Power/Wild-dense, so this
        is expected to be a small top-up most of the time, not the primary
        mechanism - see readme.txt for the measured natural count).

        Counts a local scan of `self.config.power_symbol_names` directly,
        deliberately WITHOUT adding a new `config.special_symbols` category
        for this - config.special_symbols is singleton, process-wide data
        read by every bet mode's board draws, and a local scan needs no
        config change at all (lower-risk, per readme.txt)."""
        current = sum(
            1
            for r in range(self.config.num_reels)
            for ro in range(self.config.num_rows[r])
            if self.board[r][ro].name in self.config.power_symbol_names
        )
        if current >= min_count:
            return
        needed = min_count - current
        # Maxwin ("PMX") stays excluded from any board mutation outside the
        # dedicated "wincap" criteria - the same rule already enforced for
        # Extra Power's own candidate pool (power_extra_power above) and
        # roll_reward_drop's tier pool; this top-up must not become a new,
        # unguarded way to hand out a live Maxwin power on an ordinary
        # "0"/"basegame" board.
        candidates = [k for k in self.config.power_symbol_names if k != "PMX" or self.criteria == "wincap"]
        eligible = self._open_power_placement_cells()
        random.shuffle(eligible)
        for r, ro in eligible[:needed]:
            self.board[r][ro] = self.create_symbol(random.choice(candidates))
        self.get_special_symbols_on_board()

    # --- The 5 FIFO power effects ----------------------------------------------

    def power_extra_wild(self) -> None:
        """3-10 random ordinary Wilds land on currently-non-Wild/Power cells
        (never column 0)."""
        n = random.randint(*self.config.extra_wild_count_range)
        cells = self._open_power_placement_cells()
        random.shuffle(cells)
        chosen = cells[:n]
        for r, ro in chosen:
            self.board[r][ro] = self.create_symbol("W")
        power_activated_event(
            self,
            "extra_wild",
            {"count": len(chosen), "positions": [{"reel": r, "row": ro} for r, ro in chosen]},
        )

    def power_extra_power(self) -> None:
        """2-4 new Power symbols (any type EXCEPT Extra Power itself) land
        on currently-non-Wild/Power cells (never column 0). Maxwin is
        excluded from the candidate pool outside the "wincap" criteria - a
        deliberate safety measure (not explicit in the source doc, but
        required by the hard "Maxwin only via the wincap fence" rule) -
        letting Extra Power hand out a live, activatable Maxwin symbol on an
        ordinary basegame board would be exactly the RTP-fence leak this
        project's notes repeatedly warn against; excluding it from the pool
        here is the same defensive pattern as roll_reward_drop's tier-pool
        filter and activate_maxwin_power's criteria gate."""
        n = random.randint(*self.config.extra_power_count_range)
        candidates = [k for k in self.config.power_symbol_names if k != "PXP"]
        if self.criteria != "wincap":
            candidates = [k for k in candidates if k != "PMX"]
        cells = self._open_power_placement_cells()
        random.shuffle(cells)
        chosen = cells[:n]
        placements = []
        for r, ro in chosen:
            sym_name = random.choice(candidates)
            self.board[r][ro] = self.create_symbol(sym_name)
            placements.append({"reel": r, "row": ro, "powerType": self.config.power_type_by_symbol[sym_name]})
        power_activated_event(self, "extra_power", {"count": len(chosen), "placements": placements})

    def power_big_symbol(self) -> None:
        """One 2x2/3x3/4x4/5x5 block of a single random normal paying
        symbol lands at a random position fully on the board, overwriting
        everything in its footprint (including Wild/Power cells - the
        spec's "coverage" rationale carves out no exception here, unlike
        Extra Wild/Extra Power). No column restriction: Big Symbol is a
        normal paying symbol, not Wild/Power. Excludes any symbol already
        removed-from-play by an earlier stage clear this spin (same
        exclusion resample_valid_symbol already applies for Mystery/Alter -
        Big Symbol must not resurrect a symbol the stage-clear system says
        shouldn't exist on the board anymore this spin)."""
        size = get_random_outcome(self.config.big_symbol_size_weights)
        candidates = [s for s in self.config.normal_paying_symbols if s not in self.removed_symbols]
        sym_name = random.choice(candidates or self.config.normal_paying_symbols)
        max_start = self.config.num_reels - size
        r0 = random.randint(0, max_start)
        ro0 = random.randint(0, max_start)
        for r in range(r0, r0 + size):
            for ro in range(ro0, ro0 + size):
                self.board[r][ro] = self.create_symbol(sym_name)
        power_activated_event(
            self, "big_symbol", {"size": size, "symbol": sym_name, "topLeft": {"reel": r0, "row": ro0}}
        )

    def power_mystery(self) -> None:
        """5-20 cells, EACH independently rerolled to its own random normal
        paying symbol (drawn from that column's own reel-strip weights via
        resample_valid_symbol - the same weighted-draw source Alter uses;
        see readme.txt for why this "each cell independent" reading was
        chosen over an older, superseded shared-reveal mystery design). Any
        board cell is eligible - Mystery reveals normal paying symbols, not
        Wild/Power, so the column-0 restriction (which only applies to
        Wild/Power) doesn't apply here."""
        n = random.randint(*self.config.mystery_count_range)
        all_cells = [(r, ro) for r in range(self.config.num_reels) for ro in range(self.config.num_rows[r])]
        random.shuffle(all_cells)
        chosen = all_cells[: min(n, len(all_cells))]
        revealed = []
        for r, ro in chosen:
            self.board[r][ro] = self.resample_valid_symbol(r)
            revealed.append({"reel": r, "row": ro, "symbol": self.board[r][ro].name})
        power_activated_event(self, "mystery", {"count": len(chosen), "revealed": revealed})

    def power_alter(self) -> None:
        """Scan the whole board: any Wild/Power cell (Scatter doesn't exist
        yet this phase, per the spec's own caveat) is left untouched; every
        other (normal paying symbol) cell is independently rerolled from
        that column's own reel-strip weights (resample_valid_symbol - the
        same weighted-draw approach tumble refill uses, just as independent
        per-cell draws rather than a "continue the strip position" pull,
        since there is no physical gravity event here - confirmed directly
        with the user)."""
        rerolled = []
        for r in range(self.config.num_reels):
            for ro in range(self.config.num_rows[r]):
                if not self.board[r][ro].check_attribute("wild"):
                    self.board[r][ro] = self.resample_valid_symbol(r)
                    rerolled.append({"reel": r, "row": ro, "symbol": self.board[r][ro].name})
        power_activated_event(self, "alter", {"count": len(rerolled)})

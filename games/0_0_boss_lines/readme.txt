# Boss Lines - Phase 1 (REBUILD v2)

Rebuilt from scratch per D:\Stake Engine\QUESTIONS_FOR_YOU.md's "REBUILD TOAN
BO - Boss Lines v2" section (the docx-derived spec that superseded the
earlier, now-discarded Phase 1-3 line-pay-only build). Any prior partial
state found in this directory before this rebuild was ignored, per task
instructions.

Scope of this phase: a base-spin TUMBLE + LINE-PAY cascade engine, INCLUDING
the full boss/stage system (3 bosses, 6-stage Dam/HP table, whole-board
symbol explode + damage, 21-tier reward-drop table, wincap-forced Maxwin
routing) - all resetting fresh to stage 1 at the start of every spin (no
cross-spin persistence; that is Phase 3's job). Explicitly OUT of scope:
Power system, Scatter/Bonus, Ante/feature-spin buy modes, Elixir/Booster,
the Player-HP-gated bonus continuation loop.

## Architecture

5x5 board, 15 fixed paylines (own design - not specified beyond "15 lines,
continuous left-to-right"; a mix of straights/V-shapes/zigzags/W-shapes, see
game_config.py's self.paylines), 9 paying symbols (L1-L5 = 10/J/Q/K/A,
H1-H4 = Mini/Minor/Major/Grand) + Wild (never on column 1/reel index 0).
No Scatter symbol this phase.

Per-spin resolve loop (gamestate.py run_spin):
  1. Draw the board directly via Board.create_board_reelstrips() (NOT the
     framework's draw_board(), which references config.freespin_triggers/
     scatter anticipation logic this game doesn't use at all this phase).
  2. game_calculations.evaluate_and_explode(): reuse
     src.calculations.lines.Lines.get_lines() UNCHANGED for payline
     evaluation. For every winning payline, mark EVERY board cell of that
     same symbol name as `explode = True` - not just the copies inside the
     winning line (the game's core non-standard rule). Any Wild cell that
     was part of a winning line's positions also explodes, dealing 2x the
     damage of a roll from the highest-paytable-value symbol it substituted
     for (across all lines it took part in this pass, if more than one).
     Every exploding instance rolls its OWN independent damage value from
     its symbol's range and is routed to a boss by ITS OWN column (not the
     winning line's column), per the "scenario 1" zone routing, evaluated
     live so a same-pass boss death/stage-clear correctly re-routes later
     instances.
  3. game_executables.py's boss/stage bookkeeping (deal_damage_to_boss ->
     on_boss_defeated -> roll_reward_drop / clear_stage) runs inline as each
     instance's damage is applied.
  4. src.calculations.tumble.Tumble.tumble_board() (UNCHANGED) physically
     removes exploded symbols and refills from that column's own reel strip
     - this is what keeps everything RTP-tunable via the reel CSV rather
     than ad-hoc random draws.
  5. Repeat from step 2 until a pass produces zero total line-win (the
     spin's "static state" - boss actions only ever happen as a byproduct of
     a winning pass, so "zero win" alone is a sufficient exit condition; no
     separate FIFO/pending-action queue is needed this phase, unlike the
     Power-system-era spec language in QUESTIONS_FOR_YOU.md which doesn't
     apply here).

## Boss / stage system

3 bosses, 6-stage Dam/HP table (exact values from the spec). Column->boss
routing ("scenario 1", now confirmed in the source doc too):
  col0 -> boss1 always; col2 -> boss2 always; col4 -> boss3 always
  col1 -> boss1 while alive, else boss2; col3 -> boss3 while alive, else boss2
A boss already at 0 HP deals/takes no further damage. Boss "Dam" (counter-
attack power) is rolled and stored per the spec's variance rule for
structural completeness, but has NO gameplay effect this phase - there is no
Player-HP pool for it to attack yet (that's Phase 3-only, per
QUESTIONS_FOR_YOU.md's architecture correction).

Variance: each boss's stage Dam/HP = base * uniform(0.75, 1.25), Dam rounded
to the nearest integer, HP to the nearest multiple of 10, rerolling all 3
bosses together (up to 60 attempts) until (max_HP-min_HP)/max_HP <= 0.35.

Defeating a boss immediately rolls ONE reward from the 21-tier table
(1x..5000x + Maxwin=20000x=wincap), excluding: tiers pruned by earlier
stage-clears this spin; the top-3 tiers (2000/5000/Maxwin), reserved for
whichever of the 3 bosses in a stage is defeated LAST (chronologically, any
of the 3); and - critically - the Maxwin(=wincap) tier is EXCLUDED FROM THE
POOL ENTIRELY whenever the current simulation criteria isn't "wincap" (see
"Wincap routing" below). Clearing all 3 bosses in a stage applies that
stage's effect (permanently remove a low-pay symbol from the board for the
rest of this spin + prune the given reward tiers) and advances to a
freshly-rolled next stage. Stage 6's last-defeated boss instead rolls
">=500x" from {500,1000,2000,5000,Maxwin} (spec's special case) rather than
a further-pruned normal list. After stage 6 clears, there is no stage 7:
`boss_system_active` goes False and the boss system stays dormant for the
rest of that spin (design decision, undocumented beyond "decide sensibly" -
tumbling/line-pay continues completely normally, symbols just never deal
boss damage again this spin).

Symbol removal is implemented as REROLL, never as a mutation of
`self.config.reels` (a process-wide singleton - see GameConfig.__new__):
`game_executables.enforce_removed_symbols` scans the WHOLE board (not just
newly-tumbled cells) and replaces any cell showing a removed symbol with a
fresh resample from that SAME column's own reel strip, rejecting both
removed names AND "W" (this Wild-exclusion is a documented fix carried over
from an earlier build of this game that is worth repeating: allowing "W" as
a valid reroll target would silently inflate wild density). This is called
immediately when a symbol is newly removed (purges existing on-board copies,
so cells can never go permanently "dead" for lack of anywhere to explode to)
and is idempotent so it's safe to call again after every tumble refill too.

## Wincap / Maxwin routing (the mistake this project's notes warn about)

The reward-drop table's "Maxwin" tier is the literal wincap value (20000).
It must NEVER be paid directly on an ordinary "basegame"/"0"-criteria spin -
doing so would inject a wincap-magnitude book into a fence the RTP optimizer
never expects one in, silently breaking calibration (this exact mistake was
made and fixed in an earlier build of this same game per
QUESTIONS_FOR_YOU.md, and the instructions explicitly warned not to repeat
it). Two layers of defence:
  1. `game_executables.roll_reward_drop` excludes the Maxwin tier from the
     roll pool entirely whenever `self.criteria != "wincap"`.
  2. `game_calculations.award_win` additionally enforces a hard headroom
     guard on every non-"wincap" win addition (line-pay AND reward-drop): if
     `amount` would push `running_bet_win` to/past `config.wincap`, it is
     clamped down to the remaining headroom, floored to the nearest valid
     $0.10 payout increment. This covers the case exclusion #1 alone
     doesn't: the reward table can independently chain several ordinary
     2000x/5000x top-tier drops across multiple stage clears within one long
     cascade (each such drop is a legitimate result of the normal,
     non-Maxwin pool) - 4 such drops alone would already reach 20000 without
     ever touching the Maxwin tier. The floor-quantization only runs when
     the guard actually had to shrink `amount` - an earlier version applied
     it unconditionally to EVERY award (even nowhere near the cap), which a
     harness instrumentation pass caught silently shaving a cent off ~0.2%
     of spins from ordinary float-summation noise (e.g. 0.5+0.3 ==
     0.7999999999999999 in double precision, so floor(...*10)/10 rounded
     that DOWN to 0.7 instead of the intended 0.8) - an unintended RTP leak,
     now fixed by only quantizing on the genuinely-clamped path.
     `gamestate.run_spin` additionally asserts
     `running_bet_win < config.wincap` at the end of every non-"wincap"
     spin as a belt-and-braces check. This assertion held across the full
     100k-sim optimized run with zero violations, and a dedicated harness
     instrumentation pass confirmed the guard's clamp path is never actually
     exercised at 100k/BR0 scale (0 clamp events - stage 2, the deepest
     stage reached at that scale, never accumulates anywhere near 20000
     through ordinary reward drops) - a correctness backstop for a path
     that simply hasn't fired yet at this scale, not dead code with no real
     trigger condition (the same 0-clamp-events result held even when
     re-tested against the heavily-loaded WCAP reel under non-forced
     criteria, which reaches stage 6 - see below).

On the dedicated "wincap" fence (criteria=="wincap", `force_wincap: True`,
its own heavily-loaded "WCAP" reel set), the mechanism is the standard
overshoot-then-clamp trick already built into this SDK
(`GeneralGameState.update_final_win`: `final = round(min(running_bet_win,
wincap), 2)`) combined with the Distribution's `win_criteria=20000`, which
makes `check_repeat` redraw the whole spin until it lands on
`running_bet_win >= wincap` (then the min() clamps it to exactly 20000).
`roll_reward_drop` biases hard toward the Maxwin tier specifically on this
fence's last-defeated-boss roll (weight 5000 vs 0.01 for everything else in
the eligible pool) so this converges quickly - measured via a standalone
harness (not the real pipeline) at avg 2.2 repeats/accepted-book, max 5,
across 30 sampled attempts; every one of the 30 converged on exactly a
20000x final win, confirmed reaching stage clear 1 first (30/30) via boss
defeats before rolling Maxwin (30/30 Maxwin-tier rolls observed). Confirmed
end-to-end in the real 100k-sim optimized run too: `max_win: 2000000` (cents
units = 20000.00x) appears in the shipped lookup table/stats, and the
non-wincap-criteria assertion above never fired.

## RTP fences / optimizer setup

Single "base" bet mode this phase (cost 1.0, wincap 20000, target RTP 0.60 -
PROVISIONAL: this base-mode fence will eventually be retuned as one part of
a larger combined budget (final target 0.967, split with a Bonus mode added
in Phase 3), per task instructions). Three fences:
  - "wincap": quota 0.0005, rtp 0.001, `force_wincap: True`, own "WCAP" reel.
  - "0": quota 0.65 (chosen to roughly match the measured natural zero-win
    rate, ~64%), rtp 0, `win_criteria=0.0` forces exact-zero redraws.
  - "basegame": quota 0.3495, rtp 0.599 (the remainder), `hr = 1/quota`
    (this SDK's required fence formula per project notes: for a fence with
    sampling quota q needing target RTP contribution r, set both hr=1/q and
    rtp=r explicitly - NOT hr="x" without av_win, and never hr=1.0 for more
    than one simultaneous non-wincap fence).
`verify_optimization_input`'s exact-sum assertion holds: 0.001 + 0 + 0.599 =
0.600 = the bet mode's own target RTP.

No volatility scaling was ultimately needed - measured 3-star limits at
100k sims came in with large margins: etl40b=0.253 (limit 0.9), etl10k=0.001
(limit 0.8), cvar=182.18 (limit 800), prob5k=0.0 (limit 1e-2), prob10k=0.0
(limit 0.5e-2), rtp=0.6 (limit 0.967, this being a hard-coded ceiling in
utils/rgs_verification.py unrelated to this game's own lower provisional
target). A small ConstructScaling entry is still included in
game_optimization.py (mild upweight on tiny 0.1-1x wins, mild downweight on
the 500-5000x band) as a conservative shape adjustment; it was not required
to pass any limit and can be removed/retuned freely in a later pass.

## Validation results (see also the harness scripts used - not checked in,
scratch-only, per task instructions)

Small scale (2k, then 20k, optimization ON): RTP hit exactly 0.6 both times,
zero warnings/errors, `[FAST PATH] ... SHA-256 OK, payout hash OK`.

Full 100k-sim run (`run.py`, all four run_conditions True, via
run_boss_lines.bat for the MSVC toolchain env-vars the Rust optimizer needs
on this machine): exit code 0, zero Tracebacks/errors/warnings in the full
log. Final measured stats (games/0_0_boss_lines/library/stats_summary.json,
re-run after the award_win float-precision fix below):
  rtp=0.6 (exact match to target), average_win=0.6, std=8.32,
  prob5k=0.0, prob10k=0.0, etl40b=0.255, etl10k=0.001, cvar=176.11
  -> all comfortably within the {"prob5k":1e-2,"prob10k":0.5e-2,
  "etl40b":0.9,"etl10k":0.8,"cvar":800} 3-star limits.

Cascade-length and stage-reached histograms (measured via a standalone
in-process harness calling gamestate.run_spin() directly - not the
multi-threaded pipeline - at 100k RAW/unforced "basegame"-criteria sims, i.e.
the natural pre-optimization distribution the game mechanics themselves
produce):
  zero-win fraction: 0.6399 (matches the "0" fence's 0.65 quota well)
  cascade length (tumble-passes per spin):
    1: 63991   2: 24585   3: 7841   4: 2478   5: 782
    6: 233     7: 68      8: 15     9: 7
  (mean ~1.6 passes; a 9-pass cascade is the longest observed in 100k
  samples - short cascades dominate, exactly as the spec's own hypothesis
  anticipated for a whole-board-explode design: "cascades may resolve
  faster than typical tumble games")
  stage reached: {1: 99642, 2: 358}  (0.358% of spins reach stage 2; stage
  3+ was NOT observed in 100k raw/BR0 samples - reaching it requires
  clearing an entire second wave of 3 bosses within the SAME spin's
  cascade. This was NOT left as an untested assumption: a second harness
  run swapped in the heavily-loaded WCAP reel under the SAME unforced
  "basegame" criteria (no wincap/win_criteria pressure - purely a higher-
  damage board, still requiring the stage-chain logic to actually work) at
  5000 sims, and stage 3+ WAS reached: {1: 2643, 2: 1536, 3: 598, 4: 146,
  5: 58, 6: 19} - i.e. deep stage chaining (up to stage 6, the maximum) is
  demonstrated to work correctly, it is simply rare under the standard BR0
  reel's ordinary damage output and wasn't sampled at 100k there.
  boss-defeats-per-spin: {0: 96286, 1: 2597, 2: 759, 3: 354, 4: 2, 5: 2}
  Maxwin-tier(20000) rolls under non-"wincap" criteria: 0 / 100000 (confirms
  the exclusion in roll_reward_drop held with zero exceptions at this scale)
  award_win headroom-guard clamp events under non-"wincap" criteria: 0 / 100000
  (BR0) and 0 / 5000 (WCAP, stage 6) - the guard is a verified-present
  correctness backstop (see above), just not yet naturally triggered at
  these scales; it is not dead/untested code, it simply has no realistic
  trigger short of several top-tier reward drops chaining in one spin.

## Design decisions made that weren't fully specified

  - The 15 payline shapes (game_config.py self.paylines): own design, not
    specified beyond "15 lines, continuous left-to-right" - a mix of 5
    straights, 2 full diagonals, and 8 V/zigzag/W shapes.
  - Reel symbol weights (reels/BR0.csv, reels/WCAP.csv): generated via a
    scratch script (not checked in) with hand-picked relative weights
    (low-pay symbols weighted heaviest, descending to high-pay, Wild at a
    moderate weight on columns 2-5 only); BR0 uses weights tuned for
    ordinary play, WCAP is heavily loaded toward high-pay symbols + Wild
    specifically to make the wincap fence converge quickly (see above).
    These are freely retunable without touching any game logic.
  - Reward-drop tier weights (game_config.py reward_drop_weights): the spec
    gives the 21 tier VALUES but not their relative probabilities - weighted
    heavily toward the lower tiers (geometric-ish decay), consistent with
    "boss defeats should mostly award small/medium drops, huge ones rare".
  - Wild's "highest symbol it replaced" when a single wild cell is part of
    MULTIPLE simultaneous winning lines with different matched symbols (only
    possible because paylines can share cells): resolved as the highest-
    paytable-rank symbol among ALL lines that specific wild cell took part in
    this pass (one damage roll per exploding wild cell, not one per line it
    touched) - a reasonable reading of the spec's line-scoped wording that
    still produces exactly one damage instance per physical exploding cell,
    consistent with how ordinary paying symbols explode exactly once
    regardless of how many lines/reasons triggered it.
  - After stage 6 clears, the boss system simply goes dormant
    (`boss_system_active = False`) for the rest of that spin - tumbling/
    line-pay continues completely normally, but no further boss damage/
    reward-drops/stage effects occur. (Per the task's own instruction to
    "decide sensibly what happens next" - the older, pre-rebuild "auto-
    Maxwin-and-stop" behaviour documented for a since-superseded "stage 7"
    design does NOT apply to this rebuild's 6-stage table.)
  - The J (L2) paytable's spec values 0.15x/0.75x are not representable on
    the RGS's required $0.10 payout increment (verify_lookup_format hard-
    asserts `payout_cents % 10 == 0`) - rounded to the nearest valid value:
    0.15 -> 0.2, 0.75 -> 0.8 (0.3 already valid, unchanged). Every other
    symbol's spec values already land exactly on a $0.10 increment.
  - Boss HP is stored/displayed as a float (damage rolls aren't integers),
    while the boss's baseline max-HP is always a multiple of 10 per the
    variance-rounding rule - only the baseline/max value is quantized, not
    the running HP as it's damaged, since the spec doesn't ask for that.
  - `run_freespin()` is implemented as a `NotImplementedError` stub purely
    to satisfy the abstract base class - there is no free-game feature this
    phase, so it is never actually invoked.

## Deferred to Phase 3 (per Phase 1 task scope)

Scatter/Bonus (3-tier), Ante/Ultimate-Power/God-Mode/buy-N-scatter
feature-spin bet modes, Elixir/Booster (Bonus-only special symbols), the
Player-HP pool and its bonus-continuation loop, and cross-spin persistence
of boss/stage state (Bonus only - base/ante/feature spins correctly reset
boss/stage state fresh every spin per the confirmed architecture in
QUESTIONS_FOR_YOU.md). The Power system below was Phase 1's only deferred
item that has now been built (Phase 2).

---

# Phase 2 - the Power system (8 Wild-attached effect types)

Extends the Phase 1 engine above - nothing in Phase 1 was discarded, only
extended. See `D:\Stake Engine\QUESTIONS_FOR_YOU.md`'s Phase 2 task
description for the full spec.

## Architecture

A Power is "a Wild with an extra effect attached": it is registered under
`config.special_symbols["wild"]` alongside plain "W" (see game_config.py),
which makes `src.calculations.lines.Lines.get_lines` and the existing
Wild-substitution/2x-damage logic in `game_calculations.evaluate_and_explode`
treat it EXACTLY like Wild for free - no changes needed to Lines or
Symbol. The 8 Power symbol names (never on column 0, same rule as "W"):

  PWM = Wild Multi     (immediate)     PXW = Extra Wild   (FIFO)
  PGM = Global Multi   (immediate)     PXP = Extra Power  (FIFO)
  PMX = Maxwin         (immediate)     PBS = Big Symbol   (FIFO)
                                        PMY = Mystery      (FIFO)
                                        PAL = Alter        (FIFO)

(8 types, not 9 - the task header says "9 types" but the spec text itself
only ever lists these 8; the most sensible reading is plain Wild + 8 Powers
= 9 wild-like symbols total, not a 9th Power type. Built exactly these 8.)

Immediate-group powers (Wild Multi/Global Multi/Maxwin) activate inline,
inside the SAME resolve pass they connect in - no queueing. FIFO-group
powers (Extra Wild/Extra Power/Big Symbol/Mystery/Alter) are collected into
`self.power_queue` in collection order (line-index order, then
left-to-right within a line, deduplicated by physical board cell) and
popped/activated ONE AT A TIME between a tumble and the next payline
re-evaluation (see gamestate.py's resolve loop):

  evaluate -> explode/damage -> tumble -> pop-and-activate-one-power -> re-evaluate -> ...

repeated until a full pass produces no win AND the queue is empty ("static
state"). Every FIFO handler mutates the board, so the queue is guaranteed
to drain in finitely many steps.

Split across files, mirroring Phase 1's own calculations/executables split:
  - `game_calculations.evaluate_and_explode`: the Power connection scan
    (which cells connected this pass, classified into immediate/FIFO) and
    Wild Multi's per-line multiplicative math (pure win-amount arithmetic).
  - `game_executables.py`: Global Multi's accumulator, Maxwin's activation,
    the FIFO queue's enqueue/pop/dispatch, and the 5 FIFO effect handlers
    (`power_extra_wild`, `power_extra_power`, `power_big_symbol`,
    `power_mystery`, `power_alter`).
  - `game_events.py`: 3 new custom event types (`powerConnected`,
    `powerActivated`, `powerState`), same pattern as Phase 1's
    boss/stage events.

## The 8 effects

- **Wild Multi**: one factor roll (from a shared weighted list, see below)
  per physical Wild-Multi cell, reused across every winning line that cell
  is part of; multiple Wild Multi cells within the SAME line multiply
  together (not add). Payout only, never boss damage - damage still comes
  from the fixed `wild_damage_multiplier` (2x), computed completely
  independently.
- **Global Multi**: each activation adds a rolled increment to
  `self.global_multi_total` (starts at 0/inactive each spin, never resets
  mid-spin). `game_calculations.effective_global_mult()` returns that total
  if positive, else 1 - applied to every line win AND every boss-defeat
  reward-drop (`game_executables.on_boss_defeated`) for the rest of the spin.
- **Maxwin (power)**: routes through the EXACT SAME wincap mechanism Phase 1
  already built for the reward-drop Maxwin tier - `award_win(wincap)`
  overshoots `running_bet_win`, the SDK's existing
  `update_final_win`/`min(running_bet_win, wincap)` clamp produces exactly
  wincap as the final payout, and the very next `evaluate_wincap()` call
  (already wired into gamestate.py's loop) sets `wincap_triggered`, which is
  what actually stops further resolve passes. Structurally unreachable
  outside the "wincap" fence: "PMX" is excluded from `reels/BR0.csv`
  entirely (only appears on `reels/WCAP.csv`) and from Extra Power's
  candidate pool whenever `criteria != "wincap"`; `activate_maxwin_power`
  additionally hard-gates on `self.criteria` as a second, defensive layer
  (verified via a dedicated harness: forcing a "PMX" cell under
  "basegame" criteria correctly no-ops with zero payout and a warning).
- **Extra Wild**: 3-10 (uniform) new "W" symbols on cells that are column
  != 0 and not already Wild/Power - OVERWRITES ordinary paying symbols in
  those cells (the spec's wording only excludes "already Wild/Power", not
  "already occupied" - every board cell always holds some symbol).
- **Extra Power**: 2-4 (uniform) new Power symbols, any type except Extra
  Power itself, same placement rule as Extra Wild. Maxwin is excluded from
  the candidate pool whenever `criteria != "wincap"` - a deliberate safety
  measure (not explicit in the source doc) required by the hard "Maxwin
  only via the wincap fence" rule; without it, Extra Power could hand out a
  live, activatable Maxwin symbol on an ordinary basegame board.
- **Big Symbol**: one 2x2/3x3/4x4/5x5 block of a single random normal
  paying symbol at a random position fully on the board, overwriting
  everything in its footprint (including Wild/Power - no exception, unlike
  Extra Wild/Extra Power). Size is NOT uniform (see design decisions
  below). Excludes any symbol already removed-from-play by an earlier
  stage clear this spin (same exclusion `resample_valid_symbol` already
  applied for Mystery/Alter).
- **Mystery**: 5-20 (uniform) cells, chosen uniformly from all 25 board
  cells (no column restriction - it reveals normal symbols, not
  Wild/Power), EACH independently rerolled to its own symbol via
  `resample_valid_symbol` (that column's own reel-strip weights).
- **Alter**: full-board scan; any Wild/Power cell is left untouched, every
  other cell independently rerolled via `resample_valid_symbol`.

`resample_valid_symbol` (game_executables.py) was extended from rejecting
just "W" to rejecting the full `config.wild_like_names` set (all 8 Powers
too) plus stage-removed symbols - it is now reused by Mystery/Alter as well
as the original stage-clear symbol-removal enforcement, so a "normal paying
symbol" reroll must never be able to produce a Wild-like symbol. Switched
from reject-sampling (fixed retry count) to a filtered-pool draw, since a
fixed retry count that previously only needed to avoid 1 name now needs to
avoid 9 - a filtered draw has no exhaustion failure mode.

## Validation results (100k sim, full `run.py` pipeline via `run_boss_lines.bat`)

Two independent full 100k runs (before and after a late correctness fix to
Big Symbol's removed-symbol exclusion, see below) both completed with exit
code 0 and zero Tracebacks/errors/warnings in the entire log; format checks
passed both times (`[FAST PATH] base: SHA-256 OK, payout hash OK,
entries=100000`). Final run's measured stats
(games/0_0_boss_lines/library/stats_summary.json):

  rtp=0.6 (exact match to the 0.60 target), average_win=0.6, std=8.078
  prob5k=0.0, prob10k=0.0, etl40b=0.298, etl10k=0.001, cvar=162.778
  max_win=2000000 (cents) = exactly 20000.00x

All comfortably within the {"prob5k":1e-2, "prob10k":0.5e-2, "etl40b":0.9,
"etl10k":0.8, "cvar":800} 3-star limits - actually somewhat LOWER
(less volatile) than Phase 1's own pre-Power numbers (etl40b=0.255,
cvar=176.11), despite Power's wider raw win distribution, because of the
ConstructScaling downweight added below.

Per-Power-type trigger frequency and cascade-length histograms (standalone
harness calling `gamestate.run_spin()` directly - not the optimized
pipeline - 50000 raw/unforced "basegame"-criteria sims, i.e. the natural
pre-optimization distribution the mechanics themselves produce):

  Power ACTIVATED, % of spins with >=1 activation this spin:
    extra_wild    1.558%   extra_power  1.508%   global_multi 1.452%
    mystery       1.346%   alter        1.320%   big_symbol   1.306%
    wild_multi    1.252%
  (roughly 1-in-65 to 1-in-80 spins per type - "noticeable but not
  overwhelming", per the task's own framing; Maxwin power: 0/50000 at this
  natural BR0 scale, as designed - it only exists on reels/WCAP.csv)

  Big Symbol size distribution (653 activations): {2: 259, 3: 189, 4: 140,
  5: 65} - matches the intended 40/30/20/10 weighting (see below) closely.

  resolve-loop length (tumble-passes per spin), 50000 raw sims:
    1:30427  2:12788  3:4280  4:1483  5:583  6:236  7:106  8:56
    9:22  10:12  11:5  12:1  14:1
  (mean ~1.66 passes; longest observed cascade is 1 pass longer than
  Phase 1's own 9-pass maximum at similar scale - Power's board-mutating
  FIFO effects modestly extend the tail, as expected, without changing the
  overall "short cascades dominate" shape.)

  stage-reached (50000 raw sims): {1: 49260, 2: 671, 3: 66, 4: 3}
  award_win headroom-guard clamp events (non-"wincap" criteria): 0/50000
  non-"wincap"-criteria books > 1000x: 4/50000 (0.008%)

Maxwin power dedicated end-to-end test (standalone harness, criteria
forced to "wincap"/WCAP reel, 4000 sims): the Maxwin POWER (not the
reward-drop Maxwin tier) activated in 1051/4000 (26.3%) of sims; ALL 4000
sims in that fence converged to exactly `final_win == 20000.0` regardless
of which of the two Maxwin paths fired. A second test forced a "PMX" cell
onto a board under "basegame" criteria directly (bypassing the reel-strip
exclusion, to test the defensive layer specifically): `activate_maxwin_power`
correctly no-op'd with `running_bet_win` staying at 0.0 and a warning
raised - confirms the safety net actually works, not just that the reel
exclusion makes it unnecessary.

## A real RTP blowout caught and fixed during tuning (not left as a surprise)

The FIRST reel-density attempt (2 occurrences of each of the 7 non-Maxwin
Power types per column, on all 4 eligible columns, with a UNIFORM roll
among Wild Multi/Global Multi's 7 factor values) measured a raw/natural RTP
of **17.78** at 2000 direct sims - a ~30x blowout versus the 0.60 target.
Diagnosed via an isolation test (temporarily forcing
`power_multi_factors=[1]` to neutralize Wild Multi/Global Multi's math
entirely): pure added wild-like DENSITY alone (no multiplier stacking) was
already responsible for a raw RTP of ~4.85 (whole-board-explode chains far
more readily with more Wild-like symbols on the board, each with its own
chance to trigger further boss kills/reward-drops); the multiplier stacking
(Wild Multi's per-line product, Global Multi's uncapped additive-for-the-
rest-of-the-spin total applied to reward-drops as large as 5000x) then
compounded that further to 17.78.

Fixed by cutting BOTH levers rather than just one:
  1. Reel density cut ~4x: from 2/type/column on all 4 eligible columns
     down to 1/type/column on only 2 of the 4 (reel indices 2 and 4 -
     still never column 0/1, just a deliberately narrower subset of the
     allowed columns for density control).
  2. Wild Multi/Global Multi's factor roll switched from uniform-among-{2,
     3,4,5,6,8,10} (mean 5.43) to a weighted table heavily favouring 2x
     (`power_multi_factor_weights = {2:50,3:25,4:12,5:6,6:3,8:2,10:1}`,
     mean 3.0) - the spec gives only the value SET, not relative
     probabilities (same situation Phase 1 already had for the 21-tier
     reward-drop table), so this is a deliberate, documented tuning choice.

This brought the raw/natural RTP down to ~1.8-2.3 (measured at both 3000
and 50000 direct sims) - about 3-4x Phase 1's own 0.60 baseline, a gap of
the same ORDER as (not dramatically larger than) what Phase 1 itself
already had to absorb when the wincap was raised 4x (5000->20000) and
needed a ConstructScaling fix. The `game_optimization.py` scaling was
correspondingly broadened from Phase 1's 2-band hint into a 4-band
downweight spanning the whole 0.1-5000 win range (see game_optimization.py)
to help the optimizer's own per-book reweighting search reach the
UNCHANGED 0.599 basegame RTP target without leaning so hard on the
smallest wins that volatility limits would break - the 100k results above
confirm it worked with margin to spare.

## Design decisions / assumptions made that weren't fully specified

  - **Power reel-appearance frequency** (not specified in the source doc):
    tuned empirically to the density described above (1 occurrence of each
    of the 7 non-Maxwin types per column, on reel indices 2 and 4 of
    `reels/BR0.csv` only; "PMX" itself only ever on `reels/WCAP.csv`, ~1.2%
    per column there) - see the RTP-blowout section above for how this
    number was reached, not guessed at.
  - **Wild Multi/Global Multi factor weighting** (the doc gives values, not
    probabilities): `power_multi_factor_weights` above, chosen for
    volatility control per the RTP-blowout diagnosis.
  - **Big Symbol size weighting** (spec allows uniform "unless you have
    reason to weight otherwise"): `{2:40, 3:30, 4:20, 5:10}`, descending -
    a 5x5 Big Symbol clears the ENTIRE board (every payline becomes one
    5-of-a-kind, all 25 cells explode), a much bigger single-event swing
    than 2x2, so a mild descending weight was chosen upfront as a
    volatility precaution, then confirmed reasonable by the 100k volatility
    numbers above (no further correction was needed).
  - **Mystery's reroll source** (the doc only explicitly specifies "each
    cell independently rerolled to its own random normal symbol" for
    Mystery, and explicitly specifies "reuse the reel-strip weights" for
    Alter specifically): chose to have Mystery ALSO draw from
    `resample_valid_symbol` (that column's own reel-strip weights) rather
    than a flat uniform-among-9 pick, for consistency with Alter and with
    tumble-refill's own weighted-draw convention - flagged here as an
    assumption since the doc didn't say so explicitly for Mystery.
  - **Extra Wild/Extra Power placement overwrites ordinary paying
    symbols** in eligible (non-column-0, non-Wild/Power) cells - this is
    the task's own explicit wording ("avoid overwriting existing
    Wild/Power", nothing about avoiding ordinary symbols), not an
    assumption, but flagged here because it differs from an OLDER,
    now-superseded placement assumption on record earlier in
    QUESTIONS_FOR_YOU.md (from before this phase's precise wording existed).
  - **God Mode's future "activate all queued powers simultaneously"
    override was NOT built** (out of scope, per the task) - the FIFO
    design (`activate_next_power` pops exactly one type key per call) is
    structured so that override can be added later as an alternate
    "activate everything currently queued" entry point without touching
    the collection/enqueue logic at all.
  - **Fence quota retune**: `game_config.py`'s "0"/"basegame" Distribution
    quotas moved from Phase 1's 0.65/0.3495 to 0.60/0.3995, matching the
    ~0.61 raw zero-win fraction measured after Power was added (mirrored
    1:1 into `game_optimization.py`'s `hr=1/0.3995`, per
    `verify_optimization_input`'s exact-sum requirement). The target RTP
    split itself (wincap 0.001 / "0" 0 / basegame 0.599, summing to the
    unchanged self.rtp=0.600) was left exactly as Phase 1 had it, per the
    task's own instruction to keep targeting ~0.60 provisionally.
  - A late correctness fix, made before the FINAL 100k run reported above:
    `power_big_symbol`'s symbol choice originally could resurrect a
    stage-removed low-pay symbol (e.g. placing a block of "L1" after stage
    1 had already removed it for the rest of the spin) - `resample_valid_
    symbol` already excluded removed symbols for Mystery/Alter/stage-clear
    enforcement, but Big Symbol used a separate, unfiltered
    `random.choice(config.normal_paying_symbols)`. Fixed by excluding
    `self.removed_symbols` there too.

## Deferred (out of this phase's scope, per the task)

Scatter/Bonus (3-tier), Ante/Ultimate-Power/God-Mode/buy-N-scatter
feature-spin bet modes, Elixir/Booster, the Player-HP bonus loop, and
cross-spin persistence of boss/stage/Power state (all Phase 3+, unchanged
from Phase 1's own deferred list).

---

# Phase 3 - Scatter/Bonus (3-tier), Player HP loop, Elixir/Booster

This picks up a build that a PREVIOUS agent session left mostly complete but
never finished validating - it stalled (no progress for 600s, killed) while
manually testing the freegame/Bonus path with ad-hoc, uncapped test loops.
The inherited code (`game_bonus.py`, and the Phase 3 additions to
`gamestate.py`/`game_config.py`/`game_executables.py`/`game_events.py`) was
NOT discarded or rebuilt - it was audited, several real bugs were found and
fixed (below), and it was validated through the same official
`run.py`/`run_boss_lines.bat` pipeline Phase 1/2 used, never through
hand-rolled state forcing. See
`D:\Stake Engine\QUESTIONS_FOR_YOU.md`'s "Phase 3 v2 - ket qua" section for
the Vietnamese-language summary of all this to the project owner.

## What actually caused the previous stall

Two real, reproducible defects were found - either one is a far better fit
for "hung/never finished" than "the reel doesn't have enough Scatters":

1. **A hard, deterministic crash, not a hang.** `game_config.py` registered
   "EL" (Elixir) and "BO" (Booster) in `symbol_display_names` and put them
   on `reels/FR0.csv`/`FR1.csv`/`FR2.csv`, but never added them anywhere in
   `self.special_symbols`. `GeneralGameState.create_symbol_map()`
   (src/state/state.py) only ever registers a symbol name if it appears as a
   paytable key OR somewhere in `special_symbols` - neither was true for
   "EL"/"BO", so `SymbolStorage` never built a `SymbolDefinition` for them,
   and every `create_symbol("EL")`/`create_symbol("BO")` call - which
   happens almost immediately once ANY Bonus session starts, since these
   symbols sit at ordinary density on the Bonus-only reels - raised
   `ValueError: Symbol 'EL'/'BO' is not registered`. Reproduced directly: the
   very FIRST `gamestate.run_spin()` call under `criteria="freegame"` in a
   bounded (30-iteration-capped) harness crashed on this. A prior session
   debugging this live, by hand, with ad-hoc retry/patch loops instead of
   just fixing the registration, is a much more plausible story for a
   multi-minute hang than reel density. FIXED (see "Bugs fixed" below).
2. **A genuine, unrelated infinite-loop landmine, confirmed to exist but NOT
   triggered by any of this game's actual production code paths.**
   `src/calculations/board.py`'s `force_special_board(force_criteria,
   num_force_syms)` has a bare `while True: ... break` with no iteration cap.
   If called with `force_criteria="scatter"` while `self.gametype` is
   `freegame_type` (as `game_bonus.run_bonus_session` sets it) and the active
   reel is one of `FR0`/`FR1`/`FR2` (Scatter-free BY DESIGN - Scatter must
   never appear in Bonus, see the "Cap nhat vong 3" section of
   QUESTIONS_FOR_YOU.md), `get_syms_on_reel` returns an empty stop-list on
   EVERY reel, `_force_special_board` places nothing, and the outer
   `while True` can never match `num_force_syms` - a mathematically
   guaranteed, unbounded infinite loop (0% success probability, not merely a
   rare one). This is a strong second candidate for exactly this kind of
   hang if a previous debugging session tried to hand-force a Scatter board
   while `self.gametype` had already been switched to Bonus. No production
   code path in this game ever does this (see the new scatter-forcing
   mechanism below, which only ever forces on the OUTER base-spin board,
   still on `BR0`/`WCAP`) - flagged here purely as a documented landmine for
   future debugging, not something that needed a code fix.
3. Reel Scatter density itself (`reels/BR0.csv`: 4 Scatters per 307-position
   column, ~1 per 76.75 on average) was investigated per the task's specific
   suggestion and found NOT to be the problem: it gives a perfectly
   reasonable natural P(>=3 simultaneous columns)~=0.26% (empirically
   measured, 30000-iteration bounded harness) - a normal-for-a-slot bonus
   trigger rate. The REAL problem with this density was narrower and
   different: conditional on triggering, the natural tier split was
   ~96.6% normal / ~3.4% super / ~0.047% hidden - Hidden (5 simultaneous
   Scatters) is proportionally astronomically rarer than Normal purely
   because hitting one more independent column is a multiplicative event
   (P(=4)/P(=3) and P(=5)/P(=4) both scale by roughly p/(1-p)~=0.07). That
   is a real tuning problem (see fix #2 below) but a DIFFERENT one than "not
   enough Scatters to ever force a board" - reel density was left alone.

## Bugs found in the inherited code and fixed (all reproduced and re-tested
## via bounded, timeout-safe harnesses - see "Validation approach" below)

1. **EL/BO symbol registration (crash)** - see stall cause #1 above. Fixed
   by adding `"elixir": ["EL"], "booster": ["BO"]` to `game_config.py`'s
   `self.special_symbols` dict. This does NOT give them "wild"/"scatter"
   semantics (`Symbol.assign_default_attribute`'s match statement has no
   case for these two flag names - see src/calculations/symbol.py), it only
   makes `create_symbol_map` register them; every actual Elixir/Booster
   check in `game_bonus.py` already matches by literal symbol name, not by
   attribute, so nothing else changed.
2. **The "freegame" fence never actually forced a Scatter trigger.**
   `gamestate.run_spin` drew its initial board via a plain
   `create_board_reelstrips()` call for EVERY criteria, including
   "freegame" - relying entirely on `check_repeat`'s existing
   `force_freegame and not triggered_freegame -> repeat` fallback
   (src/state/state.py) to reject-sample until a NATURAL 3+ Scatter spin
   happened. Combined with stall cause #3's tier skew, this meant: (a) the
   natural P(>=3)~=0.26% made this workable-but-wasteful for the "normal"
   tier at any real scale, and (b) Hidden-tier coverage was, for practical
   purposes, zero (an expected ~0.2 Hidden books out of a 400-book/100k
   quota) - Both Ways would have shipped completely unvalidated by the
   pipeline, and any ad-hoc manual attempt to force exactly a 5-Scatter
   board via naive retry-until-natural-match (not the SDK's own
   `force_special_board`) would need ~1/1.17e-6 ~= 850000 attempts on
   average - a very plausible slow-hang scenario in its own right, on top of
   the crash in bug #1. FIXED: `gamestate.run_spin` now calls
   `Board.force_special_board("scatter", N)` (the SAME mechanism the
   "wincap" fence already used) whenever the "freegame" fence's
   `force_freegame` condition is active, picking `N` from a new
   `game_config.freegame_trigger_count_weights = {3: 70, 4: 22, 5: 8}` table
   (a deliberate design choice, not derived from the reel - see "Design
   decisions" below). Forcing N=5 places Scatter on ALL 5 reels
   deterministically (guaranteed first-attempt success, no retry possible);
   N=3/4 leave 2/1 reels un-forced respectively, bounding the retry
   probability by how many reels remain random (never by how rare
   N-simultaneous-Scatter naturally is). Every OTHER criteria
   ("wincap"/"0"/"basegame") is unaffected - they still draw an ordinary
   board and rely on the existing accidental-trigger-forces-a-repeat
   fallback. Verified (300-book bounded harness): tier split now measures
   ~69% normal / ~23% super / ~8% hidden - all three tiers well represented.
3. **`enforce_removed_symbols` was never actually called "after every
   tumble", despite its own docstring claiming so.** It was previously
   invoked exactly once, from `clear_stage()`, at the instant a symbol is
   newly removed - but no caller anywhere re-ran it on subsequent tumbles.
   Within a single base spin this rarely mattered (few remaining passes),
   but across a Bonus SESSION (`removed_symbols` persists for the whole
   session, unlike a base spin) it meant a stage-removed low-pay symbol
   could freely reappear on the board via ordinary tumble refill and keep
   paying/exploding for the rest of the session - directly contradicting
   the spec ("loai 1 bieu tuong... chi ap dung ben trong phien bonus dang
   chay", i.e. removed stays removed for the rest of the session). FIXED:
   `game_executables.py` now overrides `tumble_game_board()` (the one
   method both `gamestate.run_spin` and `game_bonus.run_one_bonus_spin`
   call to tumble) to call `super().tumble_game_board()` then
   `self.enforce_removed_symbols()` - one override point fixes both call
   sites.
4. **A related, second gap in the same area**: even with fix #3 in place, a
   Bonus session's 2nd-and-later internal spins still start with a straight
   `create_board_reelstrips()` initial reveal (in
   `game_bonus.run_one_bonus_spin`) - if THAT reveal happens to have zero
   wins (no tumble ever runs that spin), a since-removed symbol from an
   EARLIER spin in the same session could sit untouched on the final board.
   Reproduced directly via a 300-book bounded harness with an instrumented
   "does the final board contain any name in removed_symbols" check: 440
   violations before fixing, 0 after. FIXED by also calling
   `self.enforce_removed_symbols()` immediately after
   `run_one_bonus_spin`'s initial `create_board_reelstrips()` call.
5. **Defensive-only fix, never observed to actually trigger**: the Power
   FIFO queue (`self.power_queue`) is guaranteed empty whenever a Bonus
   internal spin reaches genuine "static state" (that's the loop's own exit
   condition), but the `max_resolve_passes` safety-valve exit (documented as
   "should never be hit by a legitimate board") could theoretically leave it
   non-empty, and - unlike a base spin, which always starts with a freshly
   emptied queue - a Bonus session's internal spins do NOT reset the queue
   between spins (only Boss HP/Global Multi are meant to persist).
   `game_bonus.run_one_bonus_spin` now explicitly clears (and warns about)
   any leftover queue specifically on that safety-valve exit path, so a
   never-actually-observed edge case can't silently leak a queued Power into
   the next spin. `max_resolve_passes` (300) was never once hit in any
   measurement run in this phase (see below) - this is pure defense in
   depth, matching the existing pattern for that same safety valve
   elsewhere in this codebase.

## Validation approach (per task instructions - the official pipeline,
## always with explicit bounds/timeouts, never unbounded ad-hoc forcing)

Every manual test in this phase was a standalone script calling
`gamestate.run_spin()` directly with an explicit iteration cap AND a
wall-clock cap (checked every iteration, e.g. "stop after N iterations or
90 seconds, whichever first"), run under a shell `timeout` wrapper as a
second line of defence - so a still-broken path would produce a clean,
visible timeout/error instead of stalling silently again, per the task's own
explicit instruction. Pipeline-level validation (2k/20k smoke tests, then
the full 100k run) always went through the real `run.py`/`run_boss_lines.bat`
entry points, matching Phase 1/2's own established, previously-successful
approach - never through hand-set `self.criteria`/board state bypassing the
Distribution/criteria machinery.

## Scatter -> 3-tier Bonus trigger

`gamestate.run_spin` forces the outer (triggering) spin's initial reveal to
land exactly one of {3,4,5} Scatters (see bug fix #2 above) whenever the
"freegame" fence is active; every other criteria draws an ordinary board.
`game_bonus.accumulate_scatter_columns` (called after the initial reveal and
after every tumble, BEFORE that pass's Power activation) maintains a
never-shrinking set of columns seen showing a Scatter this whole cascade -
this ordering is what protects the tally from Extra Wild/Extra Power/Alter
overwriting a Scatter cell later in the same pass: the column already
counted before any Power effect gets a chance to touch it. `resolve_bonus_
tier` maps the final column count (3/4/5) to normal/super/hidden via
`bonus_scatter_tier_by_count`. A forced initial count can still legitimately
drift UP (never down) via a later cascade tumble landing a Scatter on a
previously-Scatter-free column - this is intentional (matches the spec's
"scatter chi tinh tong SAU KHI het cascade") and was left as designed, not
treated as a bug.

## Player HP / Bonus session loop (`game_bonus.run_bonus_session`/
## `run_one_bonus_spin`)

Matches the confirmed spec architecture exactly: Boss HP/stage state and
Global Multi are reset ONCE per session (not per internal spin - they
persist across every spin in the session), Player HP is granted from
`bonus_player_hp_choices[tier]` (uniform over the tier's multiple-of-50 set),
the starting stage is `bonus_start_stage[tier]` (1/2/3 for normal/super/
hidden - a plain skip-ahead, no earlier stage's clear-effects pre-applied),
and each spin's resolve loop runs the SAME base-spin cascade engine (payline
eval + whole-board explode/damage + Power) with one addition: Elixir/Booster
activate together at the exact moment a pass produces no new win/connection
AND the FIFO queue is empty (i.e. right as the loop is about to declare
static state, not immediately on collection - matches the "Cap nhat vong 3"
spec language precisely). After each internal spin, if the boss system is
still active, every currently-alive boss's Dam is summed and subtracted from
Player HP (the "counter-attack" mechanic) - this is what guarantees the loop
terminates (Player HP strictly decreases every spin unless the current
stage's 3 bosses are ALL already dead, which can only happen via a
same-spin stage-clear that immediately re-arms 3 fresh bosses). The
`bonus_safety_cap_spins=500` defensive cap was never once hit in any
measurement in this phase - see the stats below (max observed spins-per-
session was 48, out of a theoretical worst case the spec itself estimated at
~40 for the shallowest stage).

## Elixir / Booster

Elixir heals `player_hp * uniform(0.10, 1.00)` (of Player HP's CURRENT value
at the moment it's applied - a second Elixir in the same activation heals off
the first one's already-applied result), rounded to the nearest 10, capped
at `player_hp_max`. Booster sets a `booster_pending_for_next_spin` flag
(1+ Boosters collected together still only sets it once, no stacking); the
NEXT internal spin taken then applies `booster_damage_multiplier=2.0` to
EVERY boss-damage roll for that spin's ENTIRE resolve loop (stacks
multiplicatively with Wild's own 2x-damage rule if both apply to the same
exploding instance), then the flag is consumed. This "next-spin, not
this-spin" interpretation was carried over unchanged from the inherited
code's own documented reasoning (the spec's Vietnamese wording, "lien ke
TIEP THEO", most naturally reads as the spin AFTER the one Booster was
collected in, since that spin is already winding down when the flag is set)
- flagged here again as an interpretation, not a certainty, in case the
project owner wants it to apply retroactively to the very spin it was
collected in instead.

## Both Ways (Hidden tier only)

`game_calculations._both_ways_reversed_wins` evaluates `Lines.get_lines`
again against a column-reversed view of the board, remaps positions back to
original coordinates, and merges the results into the SAME pass's
`win_data["wins"]` list BEFORE any Power-connection scanning or whole-board
explode logic runs - so both directions are treated completely uniformly by
everything downstream, and a symmetric line that wins BOTH ways is correctly
paid twice (matching the spec's explicit "tra thuong 2 lan" callout) while
still only exploding/damaging each physical board cell once (dedup is keyed
by physical (reel,row), not by which direction discovered it). Audited this
phase specifically for double-counting bugs (Wild-Multi arithmetic, Global
Multi activation, whole-board-explode) - none found; each forward/reversed
win entry is adjusted and paid independently, matching the "2 separate
pays" semantics the spec calls for.

## RTP / optimizer - a real, UNRESOLVED problem (reported honestly, not
## papered over)

The base-spin engine (Phase 1/2, unchanged this phase) still hits its own
target RTP contribution exactly when it is the ONLY non-identity
("distribution"-type) fence being optimized - reconfirmed directly this
phase via a dedicated sanity test (freegame fence removed entirely, basegame
alone retargeted to the combined 0.601 budget wincap+basegame would have
without any freegame contribution): measured RTP = 0.601, matching target to
3 decimal places.

With the "freegame" fence ALSO present (any quota tried - 0.004, 0.02, and
0.15 were all tested, at hr 250/50/6.67 respectively), the FULL pipeline's
published RTP consistently lands at ~0.6071 - not the intended 0.967 - across
every configuration tried, at both 20k and 100k scale. What DOES change with
quota is how that ~0.607 total splits between the two fences: freegame's own
measured RTP contribution was 0.131 / 0.250 / 0.453 respectively (basegame's
correspondingly fell from ~0.474 to ~0.355 to ~0.153) - i.e. the two
non-identity fences are trading a seemingly FIXED overall "budget" against
each other, not each independently reaching its own declared av_win/hr
target. This was cross-checked directly against the published lookup table
(`library/lookup_tables/lookUpTableSegmented_base.csv`'s per-book criteria
labels joined against `library/publish_files/lookUpTable_base_0.csv`'s final
optimized per-book weights) each time, not inferred from the summary stats
alone.

Root-caused (to the extent this task's scope allows - NOT fixed, since it
lives in shared SDK infrastructure outside `games/0_0_boss_lines/`) to
`optimization_program/src/main.rs`'s joint "show pig" search: its selection
score (`run_simulation`) is a pure bankroll-survival metric (fraction of
5000 simulated trials where cumulative win over a 50/100/200-spin window
clears `pmb_rtp=1.0`, i.e. breaks even), not a direct RTP-matching objective
- and the overall bet-mode `rtp` value read from the config is, by direct
inspection, an unused parameter inside `create_show_pigs` (threaded through
but never referenced again in that function body). Each fence's own
per-candidate "pig" IS constructed to hit its own `avg_win` exactly (a
2-point linear interpolation between an over-shooting and an under-shooting
random candidate, `combine_distributions`, algebraically guaranteed to land
exactly on target) - but the JOINT random search across 2+ such fences
apparently doesn't reliably preserve that once several fences' contributions
are summed and re-scored against the bankroll-survival metric. This appears
to be a genuine limitation of this shared optimizer when 2+ non-identity
fences coexist in one bet mode, not something introduced by this game's own
logic - Phase 1/2's own single-fence setup (this exact optimizer, this exact
game's basegame mechanics) is proven correct by the sanity test above.

**Decision made**: rather than block indefinitely on a shared-infrastructure
limitation outside this task's authorized scope, quota=0.02 (hr=50, av_win
target 18.3) was kept as the final configuration - the most BALANCED of the
3 tested splits (freegame's 2nd-highest measured contribution, without
crushing basegame's own share as badly as quota=0.15 did), preserving as
much of the everyday base-spin experience's Phase-1/2-validated shape as
this limitation allows. The FINAL measured numbers from the 100k run under
this exact configuration are reported in QUESTIONS_FOR_YOU.md's "Phase 3 v2
- ket qua" section - stated plainly as the ACHIEVED result, not presented as
having met the 0.967 target, because it did not.

## Design decisions made that weren't fully specified (Phase 3)

  - **`freegame_trigger_count_weights = {3: 70, 4: 22, 5: 8}`**: the source
    doc gives the count->tier mapping but no relative trigger-tier
    probabilities (the same situation Phase 1/2 already had for the 21-tier
    reward-drop table and the Power-multi-factor table) - chosen to give the
    100k-scale pipeline meaningful sample coverage of all 3 tiers (Hidden
    included, for Both-Ways validation) rather than the ~0.047%-of-triggers
    natural rate that would make Hidden essentially unobservable at any
    workable scale.
  - **Elixir/Booster "next-spin" timing** - see above, carried over from the
    inherited code's own documented interpretation call, re-examined and
    left unchanged after independent audit.
  - **Bonus quota (0.02) / RTP split retune** - see the RTP section above;
    an accepted, honestly-reported shortfall, not a design preference.
  - Every OTHER Phase 3 design decision (stage-skip-ahead semantics on
    Super/Hidden start, Both-Ways merge-then-explode-once semantics, the
    counter-attack termination argument, HP-grant tables, reward-drop
    subset for stage 6, etc.) matches the confirmed spec in
    QUESTIONS_FOR_YOU.md exactly and needed no independent design choice.

## Deferred (still out of scope, unchanged)

Ante/Ultimate-Power/God-Mode/buy-N-scatter feature-spin bet modes remain
entirely unbuilt, per the task's own stated build order ("hoan thien + validate
base + bonus (core mechanic, khong co feature buy) truoc").

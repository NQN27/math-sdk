# Boss Lines — Game Mechanic Reference

Boss Lines is a Stake Engine math-sdk game (`0_0_boss_lines`) that layers a
boss-battle system on top of a payline slot: every payline win triggers a
**whole-board explode** of that symbol, which deals damage to one of three
bosses. The "cascade" here isn't a classic cluster-pays tumble — it's
**payline evaluation → whole-board symbol explode → boss damage → tumble
refill**, repeated until the board goes static.

This file documents *how the game plays*. It does not document tuning
history, current RTP/percentile targets, or why specific weights are set the
way they are — for that, `game_config.py`'s own comment blocks (especially
around `reward_drop_weights_normal_bonus`) are the source of truth, per
`CLAUDE.md`.

## Board & symbols

5 reels x 5 rows, 15 fixed paylines (`self.paylines`, straights/V/zigzag/W
shapes).

| Group | Symbols | Role |
|---|---|---|
| Low-pay | L1-L5 (10, J, Q, K, A) | Ordinary paytable symbols |
| High-pay | H1-H4 (Mini, Minor, Major, Grand) | Ordinary paytable symbols |
| Wild | W | Substitutes for paytable symbols in paylines |
| Power (immediate) | PWM, PGM, PMX | Wild Multi, Global Multi, Maxwin |
| Power (FIFO) | PXW, PXP, PBS, PMY, PAL | Extra Wild, Extra Power, Big Symbol, Mystery, Alter |
| Bonus-only | SC, EL, BO | Scatter (triggers Bonus), Elixir (heal), Booster (damage buff) |

## The core spin loop ("cascade")

One spin (`gamestate.run_spin`):

1. Draw a board. If the sampled fence is the dedicated `"freegame"`
   distribution (or a buy3/buy4 mode), the board is forced to land an exact
   scatter count instead of a free draw.
2. **Resolve pass**: evaluate all 15 paylines (`Lines.get_lines`) →
   Wild-Multi/Global-Multi math applied to line payouts → **whole-board
   explode**: every symbol anywhere on the board that won via ANY payline
   explodes (not just the copies inside the winning line) and deals damage
   to whichever boss its column routes to → any Maxwin/FIFO-power cells in
   the winning positions are collected.
3. **Tumble**: exploded cells are removed and refilled (unmodified
   `src/calculations/tumble.py`), one queued FIFO power activates.
4. Repeat from step 2.
5. The loop stops when a pass produces **zero payline win AND the FIFO
   power queue is empty** (static state), or a Maxwin power ends the spin,
   or a 300-pass structural safety cap is hit.
6. After static state, tally scatters seen across the whole spin. 3/4/5
   scatters map to Normal/Super/Hidden Bonus. Outside the `"freegame"`
   fence, an accidental 3+ scatter result is discarded and resimulated
   rather than allowed to leak Bonus into the wrong fence's RTP budget.

Boss damage from whole-board-explode is independent of line-payout
multipliers (Global Multi affects payout only, never damage or
reward-drops).

## Boss battle system

- 6 stages, each with 3 bosses (`boss1/boss2/boss3`), HP/damage rolled per
  boss from `config.boss_stage_table[stage]` with ±25% jitter, re-rolled as
  a trio (up to 60 attempts) until the 3 HPs' spread is within 35% of each
  other.
- **Column routing**: col 0/2/4 always hit boss1/boss2/boss3 respectively;
  col 1 hits boss1 while alive else boss2; col 3 hits boss3 while alive
  else boss2.
- **Boss defeat**: rolls a reward-drop payout (see below) and awards it
  immediately, independent of line pay. The 3rd boss defeated in a stage
  clears the stage: that stage's low-pay symbol is removed from play for
  the rest of the spin, a fresh trio rolls for the next stage, and (during
  an active Bonus session) Player HP's current AND max both increase by 50.
  Past stage 6, the boss system goes dormant for the rest of the spin.
- **Reward-drop table** (`roll_reward_drop`): a shared 21-tier weighted
  table (1x ... 20000x/"Maxwin"), swapped for `reward_drop_weights_normal_bonus`
  / `_super_bonus` inside the matching Bonus tier (Hidden shares the base
  table). The top 3 tiers of a table are reserved for a stage's *last*
  boss kill. The stage-6 last kill additionally unlocks a "chest" pool —
  for Normal/Super this chest is fully **exclusive** (its tiers are never
  drawable any other way); Hidden and base-game combat share tiers between
  chest and regular pool. The literal Maxwin tier is stripped from every
  pool except the dedicated `"wincap"` fence, with one narrow exception: the
  stage-6 chest keeps a tiny re-added chance at it (~1-in-500k per
  chest-open) so a non-wincap book can still land a very large (but
  headroom-clamped, non-session-ending) payout.

## Powers

| Symbol | Name | Group | Effect |
|---|---|---|---|
| PWM | Wild Multi | Immediate | One multiplier roll per connected cell; multiple cells in the same line multiply together. Payout only, never damage. |
| PGM | Global Multi | Immediate | Each connected cell adds to a running multiplier that persists and compounds for the rest of the spin. Payout only, never boss damage or reward-drops. |
| PMX | Maxwin | Immediate | Instantly awards the wincap and ends the spin. Structurally only reachable via the dedicated `WCAP.csv` reel. |
| PXW | Extra Wild | FIFO | Drops 3-10 plain Wilds on random open cells. |
| PXP | Extra Power | FIFO | Drops 2-4 new Power symbols (any type except itself) on random open cells. |
| PBS | Big Symbol | FIFO | Drops one 2x2 to 5x5 block of a single random paying symbol, overwriting anything in its footprint. |
| PMY | Mystery | FIFO | Rerolls 5-20 random cells, each independently, to a fresh paying symbol. |
| PAL | Alter | FIFO | Rerolls every non-Wild/Power cell on the board to a fresh paying symbol. |

FIFO powers queue in payline-then-left-to-right collection order and
activate one at a time between tumble passes (God Mode drains the whole
queue at once instead).

## Bonus tiers (Normal / Super / Hidden)

Entered by landing 3 (Normal), 4 (Super), or 5 (Hidden) scatters. Each is a
Player-HP-gated multi-spin session (`run_bonus_session`): every internal
spin runs the same cascade engine, boss/stage state and Global Multi persist
across the whole session, and each spin's un-avoided boss damage (see
chain-block, below, and counter-attack) is subtracted from Player HP. The
session ends when Player HP hits 0, when stage 6 clears (Normal only), via a
Maxwin, or (defensively) at a 500-spin safety cap.

| | Normal | Super | Hidden |
|---|---|---|---|
| Starting stage | 1 | 2 | 3 |
| Player HP pool | flat 200 | 300/350/400/450 | 200-500 |
| Both-ways pay | No | No | Yes (right-to-left too) |
| Stage-6 endless tail | No (session ends) | Yes | Yes |
| Extra mechanics | — | Rescue roll (safety net under 5x) | — |

Other session-wide mechanics: Elixir heals 10-100% of current Player HP;
Booster grants a x2/x3 boss-damage multiplier for the next spin; a session
that ends with zero boss kills gets one guaranteed finishing-blow kill on
the boss it got closest to defeating (paid through the normal reward table,
not a bonus payout).

## Experimental: in-place tumble (not adopted, forked out)

A game-designer idea exists to REPLACE this game's cascade/gravity refill
with an "in-place tumble": exploded symbols get a fresh random symbol in
their own cell, nothing falls or shifts. It was implemented behind a flag
(`game_config.use_inplace_tumble`, default `False` — production behavior
here is unaffected) and measured (n=8000, Super Bonus): mean -25.2%, median
-14.7%, median/mean ratio improves 46.3%->52.7% (more predictable, as
intended), but 0-5x/0-10x both get worse (undoes prior near-zero-tail
tuning). Not adopted here — a ~25% mean swing means every reward-table/
wild%/HP number in this folder would need a full re-tune pass, not a config
flip.

This has since been **forked into its own folder**, `games/0_0_boss_lines_inplace`
(same code, `use_inplace_tumble=True` by default there, its own README), so
it can be tuned and evaluated as a genuinely separate game rather than a
dormant flag here. See `TOWORK.md`'s "Blocking / high severity" section for
the full measured writeup and decision history.

## Chain-block (anti-streak)

Applies **only inside an active Bonus session**. Tracks consecutive
winning passes (`chain_pass_count`, resets to 0 on any non-winning pass).
Starting from the 2nd consecutive winning pass, each further pass rolls a
`min(1.0, chain_block_step * (consecutive_wins - threshold + 1))` chance to
force one column dead for that pass (picks from columns 1-3, retries next
pass if none could be routed safely). This is a flat constant, but its
*effective* suppression rate rises with stage, since the underlying
routing's success rate itself climbs from ~65% (stage 1) to ~95-99%
(stage 5-6).

## Bet modes

| Mode | Cost | What it does |
|---|---|---|
| `base` | 1x | Ordinary spin; Bonus can trigger naturally off scatters. |
| `ante` | 3x | Same engine, richer non-wincap reel, ~5x higher natural Bonus-trigger rate. |
| `ultimatepower` | 25x | Forced start at stage 3-6, no Scatter (no Bonus), guarantees 5+ Power symbols on reveal. |
| `godmode` | 500x | Same as Ultimate Power but forced start stage 4-6, drains the whole FIFO power queue per pass. |
| `buy3` | 100x | Direct Bonus buy — same 92/7.8/0.2 Normal/Super/Hidden mix as a natural 3-scatter trigger. |
| `buy4` | 300x | Direct Bonus buy — forced 4+ scatters (97.5% Super / 2.5% Hidden, no Normal). |

## Reels

| File(s) | Used for |
|---|---|
| `BR0.csv` | Base/ante/wincap-adjacent non-Bonus fences |
| `WCAP.csv` | The dedicated wincap fence (Scatter-free, richest density) |
| `Ante_BR0.csv` | Ante's own non-Bonus fences (richer than BR0) |
| `PWR0.csv` | Ultimate Power / God Mode non-Bonus fences |
| `PWR1.csv` | Unused — abandoned richer God Mode reel, kept on disk, not wired in |
| `FR0/FR1/FR2.csv` | Legacy Bonus reels, now only `FR0` survives as a cosmetic padding fallback |
| `BM_Reels.csv`, `Super_BM.csv`, `UP_Reels.csv` | Legacy non-per-stage Bonus pool reels, superseded below |
| `BM_Reels_S1..S6.csv` | Normal-tier Bonus reel, one per stage |
| `Super_BM_S2..S6.csv` | Super-tier Bonus reel, one per stage (starts at 2) |
| `UP_Reels_S3..S6.csv` | Hidden-tier Bonus reel, one per stage (starts at 3) |

Per-tier Bonus reels taper Wild/Power density down stage-by-stage to
counteract match density rising as stage-cleared symbols shrink the
surviving symbol pool.

## File map

| File | Contents |
|---|---|
| `game_config.py` | Board/symbol/paytable/bet-mode declarations, all tunable tables (reward-drop weights, HP pools, power weights, reels). |
| `gamestate.py` | Per-spin resolve loop, scatter tally, Bonus-tier dispatch. |
| `game_calculations.py` | Payline evaluation + Wild/Global Multi math + whole-board explode + boss damage dispatch for one resolve pass. |
| `game_executables.py` | Boss HP/stage system, reward-drop rolling, the 8 Powers, chain-block. |
| `game_bonus.py` | Bonus-session loop, Elixir/Booster, rescue roll, finishing blow. |
| `game_events.py` | Frontend event payload builders. |
| `game_optimization.py` | Optimizer fence/construct-scaling setup (RTP tuning inputs, not game logic). |
| `game_override.py` | `reset_book` and other per-book state resets. |
| `run.py` | Simulation/optimization/analysis/format-check entry point. |

## See also

- `CLAUDE.md` — working conventions for this folder (commit-at-checkpoints policy).
- `stake-engine.com/docs/approval-guidelines/math-verification` — the real
  RTP/volatility/exposure rules `utils/rgs_verification.py` reports against
  (post-hoc reporting only, no pass/fail gate — see that file's docstrings).

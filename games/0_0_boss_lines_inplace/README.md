# Boss Lines (in-place tumble) — fork, NOT retuned

This folder (`0_0_boss_lines_inplace`) is a fork of `games/0_0_boss_lines`
with exactly one mechanic changed: after a resolve pass, exploded symbols
are replaced with a fresh random symbol **in their own cell** — nothing
falls, nothing shifts — instead of the standard cascade/gravity refill
(remove survivors, drop them down, refill from the top).

Everything else — board size, paylines, boss battle system, the 8 Powers,
Bonus tiers, chain-block, bet modes, reels — is currently **identical** to
`0_0_boss_lines`. See that folder's `README.md` for the full mechanic
writeup; this file only covers what's different here.

## Why this exists

Game designer's idea: cascades let symbols realign into brand-new lines
across passes (falling together can connect symbols that weren't adjacent
before), which compounds line-hit frequency in a way that's hard to isolate
per lever. Replacing in place only refreshes the exact cells that exploded,
so each pass's line-hit rate is closer to independent per-cell odds —
intended to make line-pay behavior easier to reason about and tune.

Implemented and safety-audited as `game_executables._tumble_board_in_place`
(full dependency-safety writeup in that method's docstring — the resolve
loop, both-ways evaluation, and every board-mutating mechanic in this game
were confirmed gravity-agnostic, not assumed). Wired on by default here via
`game_config.use_inplace_tumble = True` (in `0_0_boss_lines`, the same flag
exists but defaults `False` — that folder's production behavior is
unaffected by any of this).

## Status: everything inherited is a known-wrong starting point

This fork's `game_config.py` (reward-drop tables, `bonus_player_hp_choices`,
wild%, boss HP, chain-block constants, etc.) was copied verbatim from
`0_0_boss_lines`, which was tuned against **cascade's** hit-rate/chain-depth
statistics. A single measurement on the original flag (n=8000, Super Bonus,
cascade OFF vs ON, everything else held identical) found:

- mean 238.24x -> 178.23x (-25.2%), median 110.24x -> 94.00x (-14.7%)
- median/mean ratio 46.3% -> 52.7% (more predictable — supports the goal)
- 0-5x hit rate 0.50% -> 0.80%, 0-10x 2.41% -> 3.19% (both worse)

None of the numbers in this fork's `game_config.py` have been re-tuned
against its own actual statistics yet. Treat every table here as a starting
point to measure and rebalance, not a validated baseline, until a real
tuning pass happens.

## Known gap: frontend rendering

`_tumble_board_in_place`'s event payload still reports new symbols per-reel
with no row attached (the same shape the SDK's gravity-based tumble event
uses) — a frontend currently animates this as "fell from the top," which
would visually misrepresent an in-place replace. This fork is **math-side
only**; a frontend/animation change is needed before this could ever be
player-facing.

## Relevant scratch history

Carried over from `0_0_boss_lines/_tuning_scratch/` (the scripts that
produced the numbers above): `inplace_tumble_test.py`,
`normal_inplace_baseline.py`, `normal_inplace_retune.py`,
`inplace_meandrop_diagnostic.py`, `normal_inplace_reels/`. See
`0_0_boss_lines/TOWORK.md`'s "Blocking / high severity" section for the
full decision history that led to forking this out instead of flipping the
flag in place.

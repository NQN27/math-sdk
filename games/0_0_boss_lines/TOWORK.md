# Boss Lines — Work Plan / Open Items

Living list of what's outstanding, most severe first. See `readme.txt` for
full narrative history/reasoning behind each item - this file is just the
tracker. Update this alongside `readme.txt` at the same checkpoints (see
`CLAUDE.md`'s "commit at checkpoints" rule).

**Testing on a new machine?** See `PIPELINE.md` for the full clone-to-
running-demo steps (both math-sdk and web-sdk) - verified end-to-end and
fully reproducible (regenerating the frontend files from the current
backend state produces byte-identical output to what's committed).

## Blocking / high severity

- [ ] **RTP optimizer doesn't hit target when 2+ non-identity fences coexist**
      (Phase 3, `math-sdk`). Base mode measures ~0.6071 RTP vs the 0.967
      target whenever the `freegame` fence is present alongside `basegame`
      - confirmed at 20k and 100k scale, root-caused to
      `optimization_program/src/main.rs`'s joint "show pig" search
      (bankroll-survival score, not a direct RTP-matching objective; shared
      SDK infra, out of this game's own scope to fix). Current mitigation
      is `quota=0.02` chosen as the most balanced of 3 tested splits - an
      accepted shortfall, not a fix. See readme.txt's "RTP / optimizer"
      section for the full investigation. **Needs a decision**: escalate to
      whoever owns `optimization_program/`, or accept permanently.

- [ ] **Super-tier Bonus reward table is an unscaled placeholder**, ~5x over
      its intended target. A flat K-rescale was tried and rejected as
      insufficient - needs the same full reshape Normal's table got in the
      2026-08-19 rebalance, not a quick multiplier tweak.

## Known, accepted-as-is (revisit only if priorities change)

- [ ] Normal Bonus stage-6 bucket has a measured gap vs the other stages'
      smooth progression (endless-tail specific). Accepted as shipped;
      re-measure with `_tuning_scratch/normal_bonus_full_stats.py` /
      `stage6_payout_histogram.py` before deciding whether it still matters.
- [ ] `HP_MULT`'s stage-1/stage-2 ordering is inverted (stage 1 > stage 2,
      the only such inversion in the table). Carried over from the ported
      candidate preset; correcting it hasn't been validated against the
      accepted target numbers, so left as-is.

## Frontend (web-sdk apps/boss-lines)

- [ ] **No real sprite/spine art for the Boss Lines theme yet** - every
      symbol renders via a placeholder shape+text (`SymbolShape.svelte`).
      Swap in real art once available; re-verify the win-animation
      completion signal still fires correctly once symbols become real
      spine animations instead of placeholders (the fix in
      `ReelSymbol.svelte` should keep working, but hasn't been exercised
      against real spine timing).
- [ ] **Spine win-celebration crash** - reproduces on this dev machine
      (headed AND headless Edge, GPU/WebGPU-related, near the very end of a
      Bonus session on the pre-existing, unmodified celebration animation).
      Not yet confirmed whether this reproduces on an actual target/staging
      deployment - check there before assuming it needs a code fix at all.
- [ ] `bookEventHandlerMap.ts`'s `paddingBoard: config.paddingReels[bookEvent.gameType]`
      has a pre-existing `tsc` type error (`{name:string}[][]` vs
      `RawSymbol[][] | undefined`) - predates this phase's changes, not
      re-investigated; harmless at runtime so far but worth a real type fix.
- [ ] `web-sdk` has no personal fork configured (only `origin` =
      `StakeEngine/web-sdk` upstream) - the frontend fixes from this phase
      are committed locally only, NOT pushed anywhere. Needs either a fork
      set up or explicit sign-off to push straight to upstream.

## Housekeeping

- [ ] `math-sdk` has uncommitted working-tree changes outside this phase's
      own commits: modified `_tuning_scratch/boss_lines_normal_slot_demo.html`,
      `_tuning_scratch/gen_stage_reels.py`, `optimization_program/src/setup.toml`,
      `src/calculations/symbol.py`, and a deleted
      `_tuning_scratch/boss_lines_normal_console_demo.html`. Review and
      either commit (if verified) or discard - don't let them sit
      indefinitely per this game's own CLAUDE.md guidance.
- [ ] Ante/Ultimate-Power/God-Mode/buy3/buy4 bet modes are structurally
      built (Phase 4) but should be double-checked for the same level of
      measured/validated rigor Normal Bonus and the base engine have had -
      not yet confirmed they've had an equivalent tuning pass.

## Deferred (still genuinely out of scope, no change)

- Nothing currently tracked here - the Phase 3 readme note claiming the
  feature-buy modes were deferred is now stale/superseded (see readme.txt's
  Phase 4 section); this file should be the place that stays current going
  forward instead.

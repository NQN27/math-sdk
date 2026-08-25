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

- [ ] **Super-tier Bonus is badly UNDER target, not over** (corrects the
      earlier "~5x over target" note below, which was measured against a
      stale/superseded target number). Fresh zero-override measurement
      2026-08-26 (n=5000): mean=28.91x vs the corrected 240.77x target
      (88% off), median=4.10x (target band 96-120x). Root-caused to TWO
      compounding, independently-real problems, not a simple reward-table
      rescale:
        1. `bonus_player_hp_choices["super"]=[300,350,400,450]` (starts at
           stage 2) was never adjusted for the 2026-08-19 rebalance that
           scaled the SHARED `boss_stage_table`'s HP/damage up 3.7x-7x per
           stage - only Normal's pool (bumped to flat 200) was updated to
           compensate. Measured stage-reach funnel (n=3000): 79.6% of
           sessions die AT stage 2, the very first stage Super faces, and
           only 0.4% ever reach stage 6.
        2. Measured per-counterattack HP loss (mean 72, n=2000) matches the
           stage-2 boss table's raw Dam sum (76) almost exactly - so Power
           effects are NOT amplifying damage taken, ruling that out as a
           cause. But Super's per-spin boss-damage OUTPUT (mean 89.43 for
           all 3 bosses combined, stage 2, immortal-boss harness) implies
           ~13+ spins needed just to clear stage 2's bosses ONCE - while
           the HP pool only survives ~4-6 counterattacks. Traced to
           `_tuning_scratch/gen_stage_reels.py`'s `STAGE_WILD_PCT`: Super's
           reels use only 8% Wild at stage 2 vs Normal's 23% at stage 1 -
           nearly 3x lower, directly suppressing Wild's 2x-damage-explosion
           contribution to boss damage.
      **CORRECTED 2026-08-26 (was wrong below)**: Power's relationship to
      boss damage was re-checked carefully at the user's request and the
      original claim here ("Power touches win amount/board state, never
      boss damage directly") is WRONG for the core mechanic. All 8 Power
      symbol names are registered under `special_symbols["wild"]`
      (`game_config.py:263`, `"wild": ["W"] + self.power_symbol_names`) -
      `Lines.get_lines` matches by that attribute, not literal name, so
      every Power symbol substitutes into paylines exactly like plain Wild.
      `game_calculations.py`'s own comment (line ~242-244) confirms this
      extends to damage: "ANY wild-attribute cell - W or any of the 8
      Powers - substitutes like Wild for the 2x-highest-symbol-replaced
      damage rule" - a Power symbol on a winning line deals the SAME
      `wild_damage_multiplier`-boosted (2.0x) damage a plain Wild would, on
      top of its own special effect. Breaking the 8 effects down by whether
      they ALSO add damage beyond that baseline: Wild Multi/Global
      Multi/Maxwin are genuinely damage-neutral (win-amount/spin-control
      bookkeeping only, per their own separate code comments); Big
      Symbol/Mystery/Alter only ever touch NORMAL paying-symbol cells,
      never wild-attribute ones, so they add no new damage source either -
      but Extra Wild (places 3-10 new real Wilds, `extra_wild_count_range`)
      and Extra Power (places 2-4 new Power symbols) DIRECTLY inject more
      wild-attribute cells that can explode for their OWN 2x-tier damage on
      a later resolve pass of the SAME spin - a real, compounding damage
      amplifier. This gives a real causal mechanism (not just correlation)
      for why unlocking Power in the A/B/C/D experiment below jumped mean
      from ~77x to ~202x, and confirms `POWER_FRAC_OF_WILD=0.35` does NOT
      dilute Super's damage output the way a naive reading of "35% goes to
      Power instead of pure Wild" might suggest - a Power symbol hits just
      as hard as the Wild it replaced, sometimes harder.
      **UPDATE 2026-08-26 - promising candidate found, NOT YET APPLIED.**
      Per the game designer's request ("check config, idea normal to apply
      for super, unlock power and endless mode, slowly investigate"), ran a
      4-condition isolated A/B via `_tuning_scratch/super_normal_idea_experiment.py`
      (in-memory reel substitution only, real CSVs untouched - see
      `stage1_density_experiment.py`'s established pattern) - HP pool left
      completely UNCHANGED in every condition, isolating Wild%/Power/endless
      alone (n=2000 each):
        - A) baseline (production as-is): mean=29.77x, median=4.10x,
          79.0% die at stage 2.
        - B) Super's reels rebuilt using NORMAL's wild% taper (23/16/10/4/2,
          aligned by "stages since bonus start" rather than raw stage
          number - Normal's own stage1-5 values reused for Super's
          stage2-6), Power OFF, endless OFF: mean jumps to **76.69x**,
          stage-2 death collapses to 5.5%. Wild% density alone was the
          dominant cause - not a joint HP+Wild% problem as first
          hypothesized below.
        - C) same reels + Power unlocked back to Super's real 35% fraction:
          mean **197.19x**. Power adds substantial extra value once the
          funnel isn't collapsing (it affects win amount / board state, not
          boss damage directly - confirmed via code reading, see the Power
          section above).
        - D) same + endless unlocked back to real ON (the full stack):
          mean **204.98x**, median **138.00x**. vs the 240.77x/96-120x
          target: mean is 14.9% off (just inside the project's usual 15%
          "OK" band), but median is too HIGH relative to mean (67.3% vs
          target 40-50%) - the payout distribution isn't skewed enough yet,
          almost certainly because `reward_drop_weights_super_bonus` has
          never been properly sampled before now (old baseline only reached
          stage 6 in 0.4-0.5% of sessions; candidate D reaches it in ~5%) -
          exactly the sequencing TOWORK.md already called for ("re-measure
          the funnel before touching the reward table").
      Safety-checked separately (`super_resolve_pass_safety_check.py`,
      n=3000, 34,041 internal spins): **zero** `max_resolve_passes` hits.
      This matters because condition D is the first time high wild% (23%)
      has ever been combined with a nonzero Power fraction (35%) in this
      game - history already found that exact kind of combo can blow up
      cascade-resolve-pass counts (that's why Hidden's taper was cut 0.769x)
      - so this was checked, not assumed.
      **CONFIRMED at n=8000** (was n=2000 above): results are stable, not
      small-sample noise - D) mean=206.12x, median=139.45x, stage-2 death
      3.4% (vs n=2000's 204.98x/138.00x/3.0% - within normal run-to-run
      variance). Safety check also re-confirmed at n=10000 (113,999
      internal spins): still zero `max_resolve_passes` hits.

      **APPLIED to production 2026-08-26**, per explicit go-ahead. Changed
      `_tuning_scratch/gen_stage_reels.py`'s `STAGE_WILD_PCT["super"]` from
      `{2:8,3:7,4:6,5:5,6:4}` to `{2:23,3:16,4:10,5:4,6:2}` (Normal's own
      taper, reused as-is) and regenerated ONLY
      `reels/Super_BM_S2.csv`...`Super_BM_S6.csv` (verified via `git status`
      that Normal's/Hidden's reel files were untouched - the generator
      script writes all 3 tiers' files from one `main()`, so this used a
      tier-scoped regeneration instead of running `main()` wholesale, to
      eliminate any chance of an accidental Normal/Hidden diff). HP pool
      and `stage6_endless_tiers` both left exactly as they were - only the
      Wild%/Power combination changed.

      **IMPORTANT DISCOVERY while verifying the real on-disk files**: the
      measured mean is NOT just a function of the target wild%, PSA for
      future tuning passes on this game. Re-measuring against the actual
      committed CSVs (seed 783-787, the deterministic sequence
      `gen_stage_reels.main()` naturally produces, since Super's 5 files
      are written right after Normal's 6 in `STAGE_WILD_PCT`'s dict order)
      gave mean=263.74-266.28x (n=5000 and n=8000, self-consistent) -
      noticeably HIGHER than the 206.12x measured against the scratch
      experiment's own reel files, which used a different, arbitrarily-
      chosen content seed (5101-5105) for the exact same target
      percentages. A third seed (42001-42005, picked only to probe this)
      gave mean=345.30x with stage-6 reach jumping to 14.9% (vs ~4-6% for
      the other two seeds) and a max payout of 19999.90x (essentially
      wincap). So at the SAME target wild%/power%, three different content
      seeds gave 206x / 264x / 345x - a real, confirmed cliff/seed-
      sensitivity, consistent with this same file's own "CLIFF FOUND" note
      on Normal's stage1/2 taper (also bisected against ONE fixed seed,
      never averaged across seeds - the established practice for this game,
      not a new problem introduced here). The seed actually committed
      (783-787, `main()`'s natural, reproducible sequence - not hand-picked
      to hit a number) measures **mean=263.74-266.28x vs the 240.77x
      target (~10-11% off, better than the scratch estimate's 14.9% off)**,
      median=177-180x (66.5-68.4% of mean, still too high vs the 40-50%
      target band - unchanged conclusion: needs a `reward_drop_weights_super_bonus`
      pass, now that stage 6 is reachable ~4-5% of the time instead of
      0.3-0.5%). Safety re-confirmed directly against these exact committed
      files at n=10000 (116,650 internal spins): zero `max_resolve_passes`
      hits.
      **Flag for any future reel-regeneration on this game**: because
      `gen_stage_reels.py`'s seed counter runs globally across ALL 3 tiers
      in one shared sequence, changing Normal's or Hidden's own
      `STAGE_WILD_PCT` entry (adding/removing a stage, or reordering the
      dict) would shift which seed Super's files land on, and per the
      finding above that can swing Super's mean by ~65% even at an
      unchanged target %. Re-verify Super's measured mean after ANY future
      regeneration that touches Normal or Hidden, not just after changes to
      Super's own entry.
      **Still open, not yet done**: `reward_drop_weights_super_bonus`
      re-tune to fix the median/mean skew now that stage 6 is reliably
      reachable; HP pool intentionally left untouched (current lean:
      correct call - Wild% alone got mean within ~11% of target without
      touching it, don't add a 3rd lever pre-emptively).

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

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

- [ ] **Normal Bonus SWITCHED LIVE to spin-budget (2026-09-17/20)** - per
      explicit request ("đổi sang từ HP sang spin trước"),
      `use_spin_budget["normal"]` flipped `False -> True`: Normal Bonus now
      ends via the fixed-spin-budget mechanic (see the earlier "fixed-
      spin-budget mechanic" item below for the mechanic itself), NOT the
      old Player-HP/counterattack system, as the real shipped default -
      not just an experiment anymore.
      Last-hit mechanic REDESIGNED twice this pass (see game_config.py's
      `boss_last_hit_base_chance`/`_scale` docstring for full detail): v1
      rolled per exploding CELL (measured 2-3x mean inflation across every
      tier - too frequent), v2 rolls ONCE per boss per PASS instead
      (aggregated - `game_executables.resolve_pass_last_hit`), which
      brought the inflation back down to near-zero. Formula unchanged:
      `chance = (1 - current_hp/max_hp) * scale + base_chance`, currently
      `scale=0.02`/`base=0.005`.
      `reward_drop_weights_normal_bonus` went through a 6-round combined
      pass this session (percentile-shape "shoulder" build via 100-1000
      tier weight/value boosts, then a K_low=0.884/K_high=1.39 SPLIT
      rescale relative to an intermediate K=0.78 uniform rescale - see the
      dict's own inline comments for the full round-by-round numbers) to
      land mean/median near explicit targets (mean=88.9x priority, median
      ~24x secondary). **CONFIRMED at n=20000 (twice, consistent): mean=
      88.20x (-0.45% vs 88.9 target), median=25.93x (+8.0% vs 24 target)**.
      Percentile shape vs. a separately-given target table still
      undershoots in the p60-p95 "shoulder" band (-13% to -48% depending
      on percentile - see the config's own round-by-round table) and at
      p99.5 (-39%) - accepted as a known gap once mean hit its priority
      target, not further chased this pass.
      **IMPORTANT COUPLING FOUND**: `reward_drop_weights_normal_bonus` is
      selected purely by `bonus_tier == "normal"` in
      `game_executables.py` - it is NOT gated by `use_spin_budget`. Since
      Normal is now live on spin_budget, this is currently moot (both
      paths agree), but if `use_spin_budget["normal"]` is ever flipped
      back to `False` for any reason, the live HP-based Normal Bonus would
      silently inherit this same heavily-rescaled table (last validated
      for the OLD HP-based system at 79.84x, iteration 9b) - re-verify
      that table's own fit before ever reverting the flag.
      Deadspin (`bonus_stage_deadspin_chance["normal"]`, per-stage) and
      the `spin_budget_chain_block_threshold`/`_step["normal"]` override
      both went through several measured rounds too (see their own
      config comments) - current values on disk (`{1:0.27, 2-6:0.38}`
      deadspin, chain-block `threshold=1`/`step=1.0`) reflect the actual
      committed state; trust `game_config.py` directly over this summary
      if they ever drift, per this file's own top-of-file convention.

- [x] **Super Bonus PORTED to spin-budget AND TUNED (2026-09-20/21)** - per
      explicit request ("add các config mới này cho super... mục tiêu như
      cũ với super"), same mechanic Normal switched to, targeting SUPER'S
      OWN pre-existing designer mean target (240.77x - NOT Normal's 88.9x).
      `use_spin_budget["super"]` flipped `False -> True`.
      Tuning history: `deadspin={2:0.22,3-6:0.38}`, `chain_step=0.80 ->
      0.288` first stabilized Super's RANDOM-RANGE-damage baseline to
      mean≈257-268x/stage6≈8-10% (best pre-flat-damage result). Then, per
      explicit request ("thử bộ Dam lên boss về 1-2 và HP boss 10-20-30..."),
      `use_flat_damage["super"]` flipped `False -> True` with a naive linear
      10/20/30/40/50 avg-boss-HP guess - **blew out to mean=1482.66x,
      stage6=75.27%** (bosses far too easy to kill relative to how much
      cumulative damage one whole-board-explode pass deals). Re-derived
      `flat_damage_boss_hp_mult["super"]` properly this time, mirroring
      Normal's own original flat-damage calibration method exactly
      (measure OLD-system vs NEW-flat-system avg damage/spin per stage,
      mult = 1/ratio - see that config's own comment for the full
      measured numbers and `_tuning_scratch/measure_super_old_damage_rate.py`
      / `measure_super_flat_damage_rate.py`). Also added, per explicit
      request ("cần phải tròn số chia hết cho 5", "boss ở vị trí số 2 cao
      nhất... 3 boss nên có số máu có thể random +5 hoặc -5"):
      `flat_damage_boss_hp_round["super"]=5` (round-to-5 instead of the
      shared round-to-10) and `flat_damage_boss_hp_jitter["super"]=5` (flat
      +-5 additive variance per boss, replacing the shared +-25%
      multiplicative `boss_variance_range` swing for this tier only - see
      `game_executables.roll_stage_bosses`). boss2>boss1>boss3 ordering is
      preserved automatically (a single per-stage scalar mult keeps
      `boss_stage_table`'s own existing per-boss ratio) - verified by
      direct sampling, all rolled values land on multiples of 5.
      Re-tuned `spin_budget_chain_block_step["super"]` (0.288 -> 0.35) to
      compensate the new boss-HP table's mean. **CONFIRMED at n=15000**:
      mean=226.36x, median=80.30x, stage-end%={2:13.79,3:41.6,4:28.36,
      5:7.91,6:8.34} - within this game's established sampling-noise band
      of the 240.77x target, stage6 lands almost exactly on the best
      random-range config's own 8.28%.
      **STAGE 6 EASED (2026-09-21)**, per explicit request ("so 6 dang nhay
      len cao qua"): stage6's raw-ratio HP (340/455/300) jumped ~2.06-2.22x
      over stage5 (165/205/140), much steeper than every earlier
      stage-to-stage step (~1.5-1.9x) - inherited from `boss_stage_table`'s
      own disproportionate stage6 jump (2.16x). Eased
      `flat_damage_boss_hp_mult["super"][6]` 0.1079 -> 0.0854, giving
      boss1=270/boss2=360/boss3=240 (~1.6-1.76x step from stage5 instead).
      CONFIRMED this does NOT reopen the stage6-reach blowout: n=8000,
      mean=230.43x (vs 230.96x before - unchanged) and stage-end%
      unchanged at 8.43% for stage6 - easing stage6's own HP only speeds up
      the endless tail once a session is already there, doesn't change how
      many sessions reach it (that's stage5 + cumulative spin budget).
      `reward_drop_weights_super_bonus` has NOT been touched at all -
      Super's economy is line-pay-DOMINATED (75.4% of total, the OPPOSITE
      of Normal's reward-drop-dominated split), so it almost certainly
      needs its own K-rescale/shoulder pass once priorities call for it, not
      a copy of Normal's approach.

- [ ] **REMOVED the finishing-blow guarantee, replaced with a rare low-HP
      execute chance (2026-09-16)**, per explicit request ("Bỏ cơ chế last
      hit đó đi thay vào đó là đổi sang cơ chế khi máu boss thấp có tỉ lệ
      last hit boss đó", "Cơ chế này sẽ rare để kích hoạt"). The old
      mechanic (`game_bonus.run_bonus_session`'s end-of-session "Finishing
      blow" block, added 2026-09-02) guaranteed a 0-kill session always got
      1 kill, specifically validated to hit Super/Hidden's "0-10x ~ 0%"
      designer requirement (4 seeds x 20,000 each, 0.0000% on every seed).
      That block is now DELETED entirely. Replacement: every ordinary
      internal Bonus spin, any ALIVE boss at or below `boss_low_hp_execute_
      threshold_pct` (15%) of its own max HP gets an independent
      `boss_low_hp_execute_chance` (5%, deliberately rare per explicit
      request) roll to be instantly finished off via the same
      `on_boss_defeated` path a real kill takes - see game_config.py's
      docstring for the full design (including why it reads boss_alive/hp
      fresh each loop iteration and breaks on `boss_system_active` going
      False, to avoid misfiring against a freshly-rolled next-stage trio
      under the same reused boss_ids).
      Applied identically to all 3 tiers per explicit request ("sẽ thay
      thế cho cả 3 trước mắt ko cần đo super hay hidden"), rather than
      scoping it to `use_spin_budget`/Normal only as first proposed.
      **THIS IS NOT A GUARANTEE** - sanity-checked n=2000/tier after the
      change (no crash, all 3 tiers): zero-kill rates now normal=20.35%,
      super=5.10%, hidden=28.35% (super/hidden are NOT comparable to the
      old 28.2%/4.0% figures from 2026-09-02 - too many tier-specific
      rebalances happened between then and now for a direct before/after
      read). **Needs a decision/re-measurement pass before shipping**:
      Super/Hidden's "0-10x ~ 0%" requirement is no longer met at all
      (28.2%/4.0%-era guarantee is gone) - either accept the requirement is
      no longer satisfied, or re-tune `boss_low_hp_execute_chance`/
      `_threshold_pct` per-tier if it still needs to be approximately met.
      Explicitly deferred by the user this pass ("ko cần đo super hay
      hidden chỉ cần note").

- [ ] **NEW, UNTUNED (2026-09-16): fixed-spin-budget mechanic**, per
      explicit game-designer request ("sửa lại cơ chế bỏ máu người chơi
      thay vào đó là số lượt spin cố định, lên stage sau thì + lượt spin" -
      replace the Player-HP/counterattack session-ending mechanic with a
      fixed spin budget, top up on stage clear). Implemented as
      `use_spin_budget` (per-tier, default OFF everywhere - same
      experimental-flag convention as `use_flat_damage`/
      `use_inplace_tumble`, see game_config.py's docstring for the full
      design, including why the per-spin decrement must be UNCONDITIONAL
      to keep the endless stage-6 tail bounded). Values per spec: Normal
      starts at 6 spins, +random(1,3) per stage clear (`spin_budget_
      initial`/`spin_budget_per_stage_clear` in game_config.py). Elixir
      repurposed to grant spins instead of a %-HP heal in this mode (was a
      dead-code risk otherwise - see the config docstring).
      Syntax/sanity-verified (`_tuning_scratch/spin_budget_test.py`, n=500,
      `use_spin_budget["normal"]=True`, everything else at its current
      committed state) - runs clean, no crash, no runaway (safety_cap never
      hit; end_reason splits 51.4% spins_depleted / 48.6% stage_cleared).
      **But the resulting economy is wildly off any prior target**: mean=
      882.71x, median=339.25x, avg spins/session=27.04 (vs production's own
      ~11), and 48.6% of sessions reach stage 6 (vs the tuned system's
      single-digit-percent reach rate) - because removing HP-based death
      removes the main way sessions used to end early; a session now only
      ends by running out of budget or by completing all 6 stages, and
      since clearing a stage is pure upside (never costs budget, only adds
      to it), sessions snowball forward far more than the old system ever
      allowed. `boss_stage_table`/`reward_drop_weights_normal_bonus` are
      still the OLD values tuned for the HP-vs-damage risk model - none of
      that carries over to a spin-budget model with no retuning. **Needs a
      decision before this is usable**: retune the initial/per-stage-clear
      spin numbers and/or the reward table for this mechanic specifically
      (same measure-iterate discipline as every other lever in this file),
      or treat these numbers as informational only until asked to tune
      further. Flag stays OFF in the committed config either way - this is
      a capability, not a live change.

      **STABILIZED 2026-09-16**, per explicit request ("tinh chỉnh deadspin
      và chain-block để back về ổn định", "ưu tiên giảm chain quá dài
      trước", "để tỉ lệ deadspin là 30% rồi tinh chỉnh block chain hợp
      lý"). Rather than editing the shared `chain_block_threshold`/
      `chain_block_step` (already validated for the live HP-based/flat-
      damage systems at 2/0.26 - iteration 9b, n=40000), added a
      `use_spin_budget`-ONLY override pair (`spin_budget_chain_block_
      threshold`/`_step`) so tightening chain-block for this economy can't
      silently regress those already-locked systems - see game_config.py's
      docstring. Same gating applied to `bonus_stage_deadspin_chance`
      (previously ungated, would have affected every tier/system the
      instant it went non-zero) - now reads 0.0 unless `use_spin_budget` is
      on for that tier.
      Deadspin fixed at 30% flat across all 6 stages (per spec) with
      chain-block as the tuned lever (per spec, chain-block prioritized
      first): swept `spin_budget_chain_block_step` at threshold=1 from
      0.35 to 0.80 (n=1500 each) - 0.35->219.47x mean, 0.45->163.66x,
      0.55->131.17x, 0.65->115.37x, 0.80->81.04x (threshold=0/step=0.60 was
      tried first and overshot the other way, 54.47x). **LOCKED: threshold=
      1, step=0.80** - CONFIRMED at n=4000: mean=87.09x, median=25.10x,
      ratio=28.8%, avg spins/session=12.27 (close to production's own
      ~11), stage-end% {1:60.1, 2:29.5, 3:5.88, 4:1.07, 5:0.53, 6:2.92}
      (stage6 reach now close to production's own low-single-digit rate,
      down from the untuned pass's 49.67%), safety_cap never hit.
      Scratch: `_tuning_scratch/spin_budget_test.py`.
      **Still open**: median (25.10x) sits below the live system's own
      ~30-40x target band - not separately chased this pass since no
      explicit median constraint was given this time (unlike the earlier
      flat-damage mean-under-85 pass, where "giữ median" was explicit).
      Flag stays OFF in the committed config regardless.

- [ ] **PENDING DECISION (handoff, 2026-09-04): in-place tumble mechanic,
      implemented + tested but NOT adopted.** Game designer's idea: replace
      exploded symbols in their own cell (nothing else moves) instead of the
      SDK's cascade/gravity refill (drop survivors, refill from top) -
      motivation was making line-pay hit-rate easier to reason about
      (cascades let symbols realign into brand-new lines across passes,
      compounding hit frequency in a way that's hard to isolate per lever).
      Implemented as `game_config.use_inplace_tumble` (defaults **False** -
      current production behavior is completely unaffected right now) +
      `game_executables._tumble_board_in_place` (see that method's docstring
      for the full dependency-safety audit - confirmed via a dedicated
      repo-wide review, not assumed, that the resolve loop, both-ways
      evaluation, and every one of this game's own board-mutating mechanics
      are gravity-agnostic and needed no changes).
      Sanity-tested clean: 200 base spins + 200 Super Bonus sessions, zero
      crashes, board column size held correct every time
      (`_tuning_scratch/inplace_tumble_test.py`).
      Measured economic impact (n=8000, Super Bonus, same seeds, cascade OFF
      vs ON, everything else identical to the current committed state):
        mean 238.24x -> 178.23x (-25.2%), median 110.24x -> 94.00x (-14.7%),
        median/mean ratio 46.3% -> 52.7% (DOES get more consistent/
        predictable - supports the designer's stated goal), avg spins/
        session 11.04 -> 10.44, 0-5x 0.50% -> 0.80%, 0-10x 2.41% -> 3.19%
        (both WORSE, i.e. this erases the near-zero-tail work from
        756f968/a27f6be if adopted without a re-tune).
      **Why this isn't a lever, it's a re-tune trigger**: a ~25% mean swing
      from a board-refill mechanic change means every reward-table/wild%/HP
      number tuned for Normal, Super, AND Hidden this whole project was
      calibrated against cascade's specific hit-rate/chain-depth statistics.
      Adopting this for real needs a full re-tune pass across all 3 tiers,
      not a config flip.
      **DECIDED 2026-09-12: forked out instead of (a)/(b) above.** Rather
      than flip the flag here (which would force the full re-tune project
      onto this game's own tuning history) or leave it permanently dormant,
      the idea now lives in its own game folder, `games/0_0_boss_lines_inplace`
      (`use_inplace_tumble=True` there by default; this folder keeps `False`,
      completely unaffected). That fork's own README states plainly that
      every reward-table/HP/wild% number it inherited is a known-wrong
      starting point until it gets its own tuning pass - this item is
      CLOSED for `0_0_boss_lines` itself; any further in-place-tumble work
      happens in the fork, tracked by its own TOWORK-equivalent going
      forward, not here.

- [ ] **Normal Bonus percentile-distribution retune - open, iteration 11 is
      current state, NOT confirmed better than iteration 10.** Target
      (game designer-specified, see `reward_drop_weights_normal_bonus`'s
      own inline iteration log for full history): p50=37.5, p60~50,
      p70~67.5, p75=80, p80~105, p85=140, p90=200, p95=350, p99~800-1000,
      p99.5~2500, p99.9>=5000+, mean<=90 ceiling, all measured at n>=35000
      with sessions >=20000x (Max Win) excluded from percentiles and
      tracked as a separate rate (target ~1-in-35000).
      Iteration 10 (verified, n=35000): mean=89.00 (under the 90 ceiling),
      p50-p75 essentially exact, p85-p99.9 all undershooting target -
      chain_block_step=0.26 traded tail richness for that mean/body
      precision.
      Iteration 11 (currently on disk, per this session's commit): pushed
      1-8 tiers +20% and regrew 100-250 back toward ~2.2x to target
      p85/p90/p95 while freeing budget from p10-p40. Measured result was
      mixed, not a clean win: mean marginally exceeded the ceiling (90.13)
      and p85/p90/p95 barely moved - weaker than iteration 10 by the
      numbers, but left in place rather than reverted since neither was
      declared final.
      **Needs a decision**: revert to iteration 10's values (verified,
      under ceiling, but tail undershoots) as the accepted checkpoint, or
      continue iterating toward p85-p99.9 (this has resisted ~11 rounds of
      hand-tuning the reward table + chain-block step - a genuinely
      different lever, not another reward-table pass, may be needed to move
      the tail without moving mean/body).

- [ ] **PENDING, IN PROGRESS (2026-09-05/06): flat/deterministic damage
      system, replacing the random-range damage-to-boss/damage-to-player
      system.** Game designer's idea, per-tier switch
      (`game_config.use_flat_damage`, currently `{"normal": False, "super":
      False, "hidden": False}` - production behavior completely unaffected).
      Fully wired at all 5 call sites (verified 2026-09-12, not assumed):
      damage-to-boss (`game_calculations.evaluate_and_explode` ->
      `flat_symbol_damage`/`flat_wild_damage`), boss HP scaling
      (`game_executables.roll_stage_bosses` -> `flat_damage_boss_hp_mult`),
      counter-attack damage, initial Player HP grant, and the +50
      stage-clear HP bonus (all three in `game_bonus.py` ->
      `flat_boss_counterattack_damage`/`flat_damage_player_hp_initial_mult`/
      `flat_damage_player_hp_bonus_mult`).
      **HP RESCALED AND MEASURED 2026-09-13** - was mean=1087x (over 12x too
      high) at the original un-validated 0.08/0.08 multipliers. Also fixed a
      real bug found along the way: the player-HP grant/bonus were never
      rounded to an integer, inconsistent with every other flat-damage value
      (`flat_symbol_damage`/`flat_wild_damage`/`flat_boss_counterattack_damage`
      are all small whole integers) - both call sites now `round()` the
      result. Grid-searched the actual integer (initial HP, per-stage bonus
      HP) pairs directly (boss_hp_mult held at the already-derived 0.113):
      (9,2)=34.71x, (10,2)=48.79x, (9,3)=54.66x, (11,2)=66.57x,
      **(10,3)=88.92x**, (12,2)=105.09x, (11,3)=130.33x - confirms the
      documented cliff is really a staircase over rounded integer HP,
      dominated by the per-stage bonus (it compounds every stage cleared).
      (10,3) applied to production, CONFIRMED at n=15000: mean=86.41x
      (inside the ~85-90 target band), stage-death% 55.6/32.0/8.4/2.0/0.4/1.6
      (smooth monotonic decay). `flat_damage_player_hp_initial_mult["normal"]`/
      `_bonus_mult["normal"]` are now `10/200`/`3/50` exactly (not
      approximations - chosen so rounding is a no-op).
      **Still open**: this matches the OLD system's MEAN only, not its
      percentile SHAPE - measured ratio here is median/mean=30.8%
      (p50=26.6/p75=48.8/p90=93.4/p95=166.2/p99=2282.1), more tail-skewed
      than the ~37-42% ratio the random-damage system targets.
      `reward_drop_weights_normal_bonus` is untouched by this pass - getting
      the OLD system's percentile shape under flat damage too would need
      its own dedicated reward-table retune, same conclusion in-place-tumble
      already reached for a different mechanic change. Once that's decided,
      this is at the same kind of decision point in-place-tumble reached
      (adopt via a dedicated retune, or leave shelved) - not there yet
      before this measurement pass, is now. Scratch:
      `_tuning_scratch/flat_damage_measure.py`, `flat_damage_trace.py`,
      `flat_damage_sweep.py`/`flat_damage_sweep2.py`/`flat_damage_sweep3.py`.

      **DISCOVERED 2026-09-13 while auditing every Normal parameter**: this
      whole (10,3) rescale only targeted MEAN. A separate, earlier, more
      detailed effort (see the Controlled Deadspin Routing section's
      `bonus_stage_deadspin_chance`/`bonus_stage_connect_chance` comments)
      had already established a game-designer stage-death% TARGET for this
      system - s1=38.30/s2=32.70/s3=16.45/s4=7.40/s5=3.60/s6<=5 - and a
      prior candidate (initial_mult=0.060/bonus_mult=0.04, never actually
      applied to production) that hit s1/s6 but overshot s2 and undershot
      s3-s5. (10,3)'s own measured funnel (55.6/32.0/8.4/2.0/0.4/1.6) is
      MORE front-loaded at s1 than even that prior candidate - the mean-only
      grid search had no visibility into this target.
      **Boss-side lever added and tried, per explicit go-ahead ("sua
      distribution cua boss mot chut de hop config")**: `flat_damage_boss_hp_mult`
      now accepts a per-stage dict (game_executables.roll_stage_bosses reads
      `.get(stage, 1.0)`), not just a flat scalar - lets one tier's funnel
      be reshaped stage-by-stage without touching the shared
      `boss_stage_table`. Eased stages 1-2 only, 0.113->0.105 (~7% easier).
      CONFIRMED this moves the right direction (n=800: shape-error vs
      target 36.6->28.0, s2 lands almost exactly on target) but does NOT
      fully close the gap - s3-s5 stay meaningfully under target
      (~10-11/2.7-3.1/0.2-0.4 vs 16.45/7.4/3.6) and mean is noisy/elevated
      at this setting (93.08x at n=800, 109.95x at n=5000 - both above the
      ~85-90x band, not tightly converged between sample sizes either).
      **Not iterated further past this point** - some more aggressive
      per-stage candidates tried during this pass (e.g. easing stage 1 down
      to 0.07-0.095) took over 90-100 seconds for even n=800/1500 and had to
      be abandoned, confirming this system's documented cliff-sensitivity
      extends to the boss side too, not just player HP.
      **Needs a decision**: keep iterating stage-by-stage (own real time
      cost per the abandoned candidates above), populate the still-empty
      `bonus_stage_deadspin_chance`/`bonus_stage_connect_chance` levers
      instead (the mechanism this was originally built for, per the
      Controlled Deadspin Routing comments), or accept (10,3) + this modest
      s1/s2 ease as "improved but not exact" and move on. Scratch:
      `_tuning_scratch/flat_damage_stage_sweep.py`. Stage-death funnel is
      STILL front-loaded as of the line-pay/reward-drop rebalance below
      (unchanged by that pass - it doesn't touch HP/boss config at all).

      **LINE-PAY / REWARD-DROP REBALANCE 2026-09-13, per explicit request**
      ("sua lai giua ti le payout cua line vs boss"). Measured split first
      (`_tuning_scratch/payout_component_split_normal_flatdamage.py`,
      n=3000-5000): flat-damage's line-pay was only 22.2% of total
      (23.60x), reward-drop 77.8% (82.53x) - production/cascade's own split
      is 27.4%/72.6% for comparison, so flat-damage was already MORE
      reward-drop-skewed than the system it's supposed to reproduce.
      Isolated-effect test first: doubling `self.paytable` alone barely
      moved p99 (3094->2923x) - confirms line-pay isn't what drives the
      tail, only mean/median scale with it.
      **`self.paytable` rescaled x1.3 - this is GAME-WIDE (shared by every
      bet mode and Super/Hidden Bonus too), done anyway per explicit
      go-ahead since those haven't had their own post-rescale
      re-verification pass yet and are being treated as "not yet redone,
      will be redone later" for this build - do not assume base/ante/
      Ultimate Power/God Mode/buy3/buy4/Super/Hidden's previously-recorded
      RTP/volatility numbers in this file are still accurate until they get
      their own fresh measurement pass.**
      Reward-drop's high tiers cut alongside it: 300/350/600/1000 weights
      -40% further (on top of iteration 9's cut), and the chest tiers'
      VALUES reduced (400/500/800/1500/2500/4000 -> 275/425/675/950/1100/
      1500, weights unchanged) - value cuts were needed, not just weight
      cuts, since a weight-only test (same 6 weights x0.55, values
      unchanged) left p99 at 3210, essentially unmoved - cutting weight
      only relocates a large-VALUE tail to a higher percentile, it doesn't
      shrink the tail's dollar size. Hit a real bug picking the first
      replacement values (250/350/1000 collided with EXISTING regular-tier
      keys, silently overwritten via dict `.update()` - caught before
      applying, redone with values that don't collide with any of this
      table's other 29 keys, asserted in the measurement harness so it
      can't recur silently).
      CONFIRMED at n=20000: mean=95.28x (close to the ~90 ceiling), p50-p95
      track target closely (33.31/61.36/88.49/207.61 vs targets
      37.5/80/140/350 - now sometimes under rather than over), p99
      1967.43x (down from 3210x pre-rebalance, still ~2.5x over the
      800-1000 target - improved, not fully closed), p99.5=2186.44 (close
      to 2500 target), p99.9=2587.73 (under the 5000+ target). Stage-death
      funnel unchanged by this pass (still front-loaded, see above - this
      rebalance only touched paytable/reward-drop, not HP/boss config).
      **Still open**: p99 not fully closed (own further iteration needed,
      same cliff-sensitivity risk as every other lever here), and the
      game-wide paytable change means base/ante/Ultimate Power/God Mode/
      buy3/buy4/Super/Hidden all need their own fresh RTP/volatility
      measurement before any of their previously-recorded numbers in this
      file can be trusted again.

      **MEAN-UNDER-85 PASS 2026-09-14**, per explicit request, with an
      explicit constraint: keep median (~33) unchanged - user confirmed
      that value was already good, don't disturb it. Tried the historically
      reliable cascade-era lever first (boost 1-8 tiers +30%) - it barely
      moved mean (95.28->98.78, WRONG direction, likely noise-dominated at
      that lever's actual effect size here) AND dragged median down
      (33.31->32.20) - abandoned immediately since disturbing median was
      explicitly unwanted.
      Switched to 100-250 (doesn't govern median - median is dominated by
      the much-more-frequent 1-8/10-80 tiers - but does meaningfully feed
      mean via the many sessions that get a handful of kills without going
      deep) cut -60% (17/13.5/11/7.5/8/4.3 -> x0.40), paired with a further
      chest-VALUE cut (275/425/675/950/1100/1500 -> 210/320/500/700/800/1050,
      ~25-30% further down from the previous pass). CONFIRMED at n=20000: mean
      95.28->83.62x (target achieved), median 33.31->33.45x (essentially
      unchanged, as required), p99 1967->1581x (continued improvement,
      still above the 800-1000 target - same open item as before, not
      solved by this pass either). Needed 3 rounds to land safely under 85
      (mean=84.99 at one intermediate cut was right at the boundary and
      risked flipping back over 85 on a different seed - pushed further for
      real margin rather than accepting a razor-thin pass). Scratch:
      `_tuning_scratch/flat_damage_mean_under_85.py`.

      **STAGE 5/6 FUNNEL RESHAPE 2026-09-14**, per explicit request after
      seeing the chest/regular-reward-drop split (measured via
      `_tuning_scratch/payout_component_split_chest.py`): flat-damage
      reached the chest in 2.27% of sessions vs production's 0.67% (3.4x
      more often) - the actual reason chest was still 20.8% of total payout
      here vs production's 9.8%, even after the value cuts above. User
      wanted s5's share higher, s6's lower, without moving mean/median.
      `flat_damage_boss_hp_mult["normal"][5]`: 0.113 -> 0.40 - needed a much
      bigger jump than expected to matter (0.15 and 0.22 were tried first
      and only nudged s5/s6 by <1pp each - this lever has its own
      threshold/nonlinearity, same as everything else HP-related in this
      system). Hardening stage 5 alone dropped mean to 71.54x (fewer
      chest-reaching sessions), so restored the 100-250 tier weights and
      chest tier values (both cut in the mean-under-85 pass above) most of
      the way back toward their pre-that-pass levels to compensate, rather
      than stacking two separate mean-reducing cuts that were now fighting
      the same underlying effect from different angles.
      CONFIRMED at n=20000 against the real committed file: s5 0.62->1.71%
      (~2.8x higher), s6 2.30->1.26% (now under even production's own
      1.37%), mean 83.62->83.13x (essentially unchanged), median
      33.45->33.90x (essentially unchanged). p99 drifted back up a little
      (1581->1868x) as an expected side effect of relaxing the chest-value
      cut - still well below the original 3210x this whole arc started
      from, but this specific number is now a byproduct of the funnel fix,
      not something separately re-optimized this pass.
      **Still open**: p99 (1868x vs the 800-1000 target) and the overall
      stage funnel (s1 still ~50% vs the designer target's 38.30%) remain
      the two threads left in this system - both flagged above, unchanged
      by this specific pass.

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

      **REWARD TABLE REDESIGNED 2026-08-27** - closes the item above, per
      explicit request: "i like the mean and median but the distribution i
      want it alike the normal bonus with 3 vertices." Key finding first
      (`_tuning_scratch/payout_component_split_super.py`, n=8000): Super's
      economy is **line-pay-DOMINATED** (197.12x, 75.4% of the 261.58x
      total) - the OPPOSITE of Normal's likely reward-drop-dominated split
      - because Super survives far more spins/session than Normal AND has
      Power's Wild/Global Multi compounding line-pay in a way Normal's
      `power_frac=0.0` reels never do. This constrains what the reward
      table alone can achieve: it only ever moves the ~64x reward-drop
      slice, not the dominant ~197x line-pay slice.
      Tested 3 candidates (all in-memory overrides, real files untouched
      until the final apply):
        1. Normal's exact table plugged onto Super as-is: mean=304.84x
           (overshoots - Super rolls far more often than Normal per
           session, so the same table produces more EV here).
        2. Normal's table SHAPE (weights unchanged) with every VALUE
           rescaled by K=0.5985 to hit the ~64x reward-drop budget:
           mean=249.82x, median=168.70x - close to target, but histogram
           showed only ONE visible peak (80-150x), same shape as before -
           the chest tiers (spread 239-2394x post-rescale) produced no
           visible bump.
        3. Same LOW/MID pool, but chest weight CONCENTRATED into a narrow
           900-1100x band instead of spread: mean=251.92x, median=168.55x -
           STILL no visible bump (that band's counts were lower than its
           own neighboring bins, i.e. not a local peak at all).
      Conclusion, directly demonstrated not just theorized: a genuine 3rd
      (chest) peak needs ~3-5x more EV concentrated there than the current
      ~64x budget allows without pushing total mean well past 266.84x -
      not achievable while also preserving current mean/median, since
      line-pay (the other 75%) isn't reward-table-adjustable.
      **Game designer's explicit decision when presented with this
      tradeoff**: keep current mean/median, accept 2 peaks (not 3) rather
      than let mean drift up to force a 3rd. Applied Candidate 2's table
      (K=0.5985) to production. A useful side effect of reusing Normal's
      exact chest WEIGHTS (28.37 total, only values rescaled): Super's
      chest-pool-weight-sum now exactly matches Normal's, which also fixes
      the earlier-flagged "Super's natural-maxwin rate running ~7x hotter
      than intended" finding (was 1-in-16,667, now shares Normal's
      calibrated ~1-in-23,509 rate) - not the primary goal of this pass,
      but a real, verified improvement (0 hits at n=15000, consistent with
      the lower rate).
      **CONFIRMED against the actual committed `game_config.py`** (not
      just the in-memory candidate) at n=15000: mean=249.24x, median=
      169.30x, ratio=67.9% - 6.6% below the original 266.84x target,
      within this project's usual 15% tolerance band. Chest tiers weight
      sum verified =28.37 (matches Normal exactly).
      **Not yet done**: a tighter K-fit closing that 6.6% gap fully was
      not pursued further (n=8000-scale iterations showed this specific
      gap is within normal run-to-run sampling noise at that n) - revisit
      with a larger-n sweep if exact mean precision becomes a priority.

      **RE-CONFIRMED at n=100,000 2026-08-26** (per the game designer's own
      request - endless mode + Power make this distribution volatile
      enough that 5000-10000 might not have converged). Ran as 10 foreground
      chunks of 10,000 (`_tuning_scratch/super_n100k_chunk.py`, appending to
      `super_n100k_payouts.txt`/`super_n100k_summary.json`) rather than one
      long background call, after a first attempt at one single n=100000
      background run got silently killed by the environment before its
      first 10k-session checkpoint - the same "long-lived background
      process doesn't survive a gap between turns" failure class already
      seen with the Storybook dev server earlier in this project; chunking
      into foreground calls that each finish within one turn sidesteps it.
      Every one of the 10 chunks landed within a tight band of the others
      (chunk means 262.92-271.96x, chunk medians 176.45-179.50x, chunk
      stage-funnels all within ~1pp of each other) - confirms the smaller-
      sample estimates above were NOT noise. Full n=100,000 aggregate:
      **mean=266.84x** (240.77x target, 10.83% off), **median=178.40x**
      (66.9% of mean, same skew-too-high-vs-target-band finding as before -
      still needs the reward-table pass), **stdev=350.53x** (coefficient of
      variation 1.31 - genuinely volatile, as flagged), percentiles
      p90=540.30x/p95=764.50x/p99=1570.50x/max=19999.90x, stage-reach
      funnel s2=4.76%/s3=13.83%/s4=45.98%/s5=31.49%/s6=3.95% (stable across
      every chunk). Safety: **zero** `max_resolve_passes` hits across
      1,165,077 internal spins - the strongest confirmation yet that the
      new high-wild%+35%-power combination is safe.

      **FUNNEL + DISTRIBUTION RE-TUNE 2026-08-28**, per an explicit target
      shape from the game designer: stage-death% s2~10/s3~30/s4~35/s5~20/
      s6~5, plus a stage-6 endless clear-chance curve of
      `max(5%, 25% - N*0.5%)` (N = loops already cleared going into that
      attempt). Baseline going in (n=15000): s2=4.82/s3=13.87/s4=45.89/
      s5=31.33/s6=4.09, attempt#1 clear-chance only 10.6% (the base,
      unescalated stage-6 trio was already too hard, independent of
      escalation entirely).

      **Levers used, in order tried:**
      1. Wild% taper reshape (`_tuning_scratch/super_funnel_reshape.py`) -
         iterative single-lever tuning. Found and fixed a real harness bug
         along the way: the scratch reel-generation seed was keyed to the
         candidate's tag string, so EVERY candidate silently re-randomized
         ALL 5 stages' reel content, even stages whose wild% target didn't
         change - confounding every "isolate one lever" comparison with
         the already-known reel-content-seed sensitivity. Fixed by keying
         the seed to (stage, target wild%) instead. After the fix, also
         discovered a real (not artifact) HP-depletion coupling effect:
         hardening an EARLY stage costs survivors more HP for every LATER
         stage too (more spins needed to clear it = more counterattacks
         land), confirmed by holding downstream reel content byte-identical
         across two tests and still seeing a later stage's death% shift
         when only an earlier stage's wild% changed.
      2. `stage6_dam_escalation["super"]`: 1.20 -> 1.06. The old value
         crashed the endless-clear-chance curve almost immediately
         (attempt#2=4.6%, attempt#3=0%) against the requested gentle
         decay; 1.06 tracks it much better (survives 6 attempts deep
         instead of crashing by #3).
      3. `power_multi_factor_weights` and `booster_damage_multiplier`
         (Wild Multi/Global Multi factor table, and Booster's boss-damage
         multiplier) - found to be a SURPRISINGLY effective lever for the
         funnel shape, more so than direct wild% tuning for stage 5
         specifically (s5's OWN wild% was tested at 5/7/8.5/11% with NO
         monotonic response - survivors reaching s5 are already too
         HP-depleted for its own density to matter; restoring the wider
         Power Multi table + raising Booster to 3x closed most of that gap
         instead). **Real cross-tier regression caught before applying**:
         both these config values were GLOBAL, not tier-scoped - applying
         Super's new values regressed Normal from ~80x to 141.82x mean
         (measured directly). Fixed properly (not worked around) by
         tier-scoping both: `power_multi_factor_weights` is now
         `{"default": ..., "normal": ..., "hidden": ...}` (all = the prior
         global "temp test" value, unchanged) plus `"super"`: the restored
         original wider table; `booster_damage_multiplier` is now
         `{"normal": 2.0, "super": 3.0, "hidden": 2.0}`. Required editing
         the actual consumption sites (`game_calculations.py`'s Wild Multi
         roll, `game_executables.activate_global_multi_cells`,
         `game_bonus.py`'s booster-multiplier-current-spin assignment,
         `game_events.booster_activated_event`), not just config values -
         verified Normal is byte-behavior-unchanged after the refactor
         (n=8000: mean=78.69x, consistent with prior ~80x measurements).

      **A second, separate reel-content-seed surprise caught before
      committing**: the production reel-regeneration process
      (`gen_stage_reels.py`'s `main()`, which lands Super's 5 files on a
      running seed counter - 783-787, since Normal's 6 files come first in
      the dict) produced a MEANINGFULLY DIFFERENT result (n=15000:
      mean=304.43x, median ratio 37.9% - below the 40-50% target band, s2
      nearly double at 19.21%) than the scratch-tested seed
      (`super_funnel_reshape.py`'s stage+pct-keyed formula) that all the
      tuning above was actually validated against (mean=232.50x, median
      ratio 46.2%). Caught by re-verifying against the real committed
      files before calling this done - did NOT commit the main()-generated
      reels. Fixed by copying the exact validated scratch reel files
      (seed = 6000 + stage*1000 + round(pct*10)) directly into
      `reels/Super_BM_S2-6.csv` instead, and added an explicit warning in
      `gen_stage_reels.py` so a future `main()` run doesn't silently
      regress this again.

      **FINAL, verified against the actual committed files** (n=15000):
      mean=235.29x, median=107.85x (45.8% of mean - inside the 40-50%
      target band), funnel s2=10.13%/s3=27.59%/s4=34.60%/s5=18.68%/
      s6=8.99% (4 of 5 stages within ~2.5pp of target; s6-reach is the one
      persistent gap, target 5%, not fully closed), endless-curve
      attempt#1-3 running a bit hot (34.7%/35.5%/29.5% vs target
      25%/24.5%/24%) while attempts 4+ undershoot, line-pay/reward-drop
      split 174.49x(74.2%)/61.00x(25.9%) (still line-pay-dominated, same
      structural finding as the reward-table pass above).
      **Still open**: s6-reach and the endless-curve's early-attempt
      overshoot were not fully closed (accepted per game designer
      decision after diminishing-returns iteration); Hidden Bonus's own
      under-target state remains uninvestigated.

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

- [x] ~~`math-sdk` has uncommitted working-tree changes outside this
      phase's own commits...~~ **STALE, checked 2026-09-12**: none of
      `_tuning_scratch/boss_lines_normal_slot_demo.html`,
      `_tuning_scratch/gen_stage_reels.py`, `optimization_program/src/setup.toml`,
      or `src/calculations/symbol.py` are dirty in `git status` anymore -
      committed at some point in this project's normal commit cadence since
      this item was written. `boss_lines_normal_console_demo.html` no longer
      exists on disk. No action needed.
- [ ] **Current actual uncommitted state (re-checked 2026-09-12)**: this
      game's `_tuning_scratch/` has real untracked/modified scratch content
      from the Super-tier funnel/reward-table work above (`super_funnel_reshape.py`
      modified; ~80 `Super_BM_S*_*.csv` reel candidates, `super_s2_lever_test.py`,
      `wild_damage_measure.py`, finishing-blow/rescue-roll/flat-damage
      diagnostic scripts, all untracked) - per this game's own CLAUDE.md,
      scratch doesn't need committing on the same cadence as production
      files; left as-is, flagging only so it isn't mistaken for lost work.
- [ ] Ante/Ultimate-Power/God-Mode/buy3/buy4 bet modes are structurally
      built (Phase 4) but should be double-checked for the same level of
      measured/validated rigor Normal Bonus and the base engine have had -
      not yet confirmed they've had an equivalent tuning pass.

## Deferred (still genuinely out of scope, no change)

- Nothing currently tracked here - the Phase 3 readme note claiming the
  feature-buy modes were deferred is now stale/superseded (see readme.txt's
  Phase 4 section); this file should be the place that stays current going
  forward instead.

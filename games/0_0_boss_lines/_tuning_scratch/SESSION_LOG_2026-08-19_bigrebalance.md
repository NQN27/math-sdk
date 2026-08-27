# Normal Bonus big rebalance — progress log (2026-08-19)

**How to read this file**: newest status at the top, design decisions/facts
below, then the original task list. Updated live as work continues during
the 5-hour autonomous work grant. Nothing has been applied to production
files yet — everything below is scratch/measurement, pending final review.

---

## ✅ PROGRESS CHECKLIST — ALL DONE

- [x] Difficulty curve redesigned — monotonic bucket%, stage6 ~1-2%
- [x] Reward-side pruning-fix + stage6 boost — mean/ratio landed on target
- [x] Chain-block integrated — found it COMPOUNDS with the boss curve, curve
      re-tuned with chain-block active, all targets hit at n=6000
- [x] Chain-length target checked - mean_passes 2.22 (target 2.5-2.6, minor
      gap accepted, see below), >=4pass 12.96% (target 10-20%, OK)
- [x] Full confirmation at n=15000 - CONFIRMED, then re-confirmed with a
      completely independent seed offset (n=8000) - nearly identical
      numbers both times, not a lucky-seed fluke
- [x] "Other ideas" exploration - all 3 considered, all 3 declined with
      documented reasoning (see below) - not applied
- [x] Final written report - delivered to designer in chat

**NOTHING applied to production files.** Everything below is a fully
measured, validated, ready-to-review proposal.

### Chain-block + curve re-tuning trail (n varies, see notes - noisy at low n)
```
HP_MULT                                          | n    | s1    s2    s3    s4   s5   s6   | mean    ratio
{1:4.0,2:3.0,3:3.2,4:4.0,5:6.0,6:9.0}  (orig)     | 3000 | 45.70 35.33 11.37 5.17 1.97 0.47| 46.34x  59.6%  <- s6 too LOW now
{1:2.6,2:2.0,3:2.2,4:2.6,5:3.5,6:5.0} (weaker)    | 3000 | 20.17 31.83 20.10 13.87 8.03 6.00| 229.06x 20.5%  <- overshot, NOT monotonic (s1<s2!), cliff-sensitive
{1:3.3,2:2.5,3:2.7,4:3.3,5:4.75,6:7.0} (interp)   | 1500 | 34.60 35.00 15.27 8.33 4.73 2.07| 93.30x  34.7%  <- s1~=s2 (boundary), s6 top of range
{1:3.7,2:2.5,3:2.7,4:3.3,5:4.75,6:7.0} (s1 nudge) | 2000 | 41.05 33.45 13.05 6.95 3.80 1.70| 94.38x  31.8%  <- MONOTONIC clean, s6 in range, mean/ratio need reward re-tune
```
Curve LOCKED with the s1-nudge version above (monotonic + s6 in range, WITH
chain-block active). Now re-tuning K/boost (was 0.72/64.0 fit WITHOUT
chain-block - no longer valid) with this curve+chain-block both active:
```
K=0.72 boost=64.0 -> mean=94.38x ratio=31.8%
K=0.85 boost=55.0 -> mean=92.21x ratio=35.6%  (n=3000)
K=1.0  boost=45.0 -> mean=81.07x ratio=45.6%  (n=3000) <-- STRONG CANDIDATE
```

## 🎯 FINAL LOCKED-IN CANDIDATE (confirmed n=6000, running n=15000+ now)

Confirmed n=6000: mean=83.15x median=35.38x ratio=42.5% zero=0.07%, bucket%
s1=40.88 s2=32.73 s3=13.75 s4=7.37 s5=3.55 s6=1.72 (still monotonic, still
in range), spins<=2%=0.00%, chain mean_passes=2.22 >=4pass=12.96%.

Tried lowering chain_step 0.30->0.25 to nudge mean_passes up toward the
2.5-2.6 target - barely moved it (2.22->2.28) but meaningfully hurt the
economy (mean jumped to 102x, ratio dropped to 35.7%, s6 crept to 2.17%).
NOT WORTH IT - reverted to step=0.30. mean_passes sitting at ~2.2-2.3
instead of 2.5-2.6 is accepted as a minor, lower-priority gap given how
well every other target lines up.

FINAL PARAMS (pending your review before touching any production file):
```
boss_stage_table HP mult: {1:3.7, 2:2.5, 3:2.7, 4:3.3, 5:4.75, 6:7.0}
bonus_player_hp_choices["normal"]: [200,200,200,200,200]
reward K (regular pool additional scale): 1.0
reward stage6_boost (exclusive tiers additional scale): 45.0
Normal-tier pruning schedule: 2/2/3/2/2 per stage 1-5
general_deadspin_chance: 0.0
chain-block: threshold=2, step=0.30, pending-retry (new mechanism, needs
  wiring into game_executables.py/src/calculations/tumble.py for real -
  currently only exists as a scratch monkeypatch)
```

## (superseded below - kept for trail) CURRENT BEST FULL-COMBINED CANDIDATE (n=3000, confirmed at n=6000 above)

```
boss_stage_table HP mult: {1:3.7, 2:2.5, 3:2.7, 4:3.3, 5:4.75, 6:7.0}
bonus_player_hp_choices["normal"]: [200,200,200,200,200] (flat)
reward K (regular pool, additional scale on top of existing K=4.28): 1.0
reward stage6_boost (exclusive tiers, additional scale): 45.0
Normal-tier pruning schedule: 2/2/3/2/2 tiers pruned per stage 1-5 (fixes no-op)
general_deadspin_chance: 0.0 (not needed - curve does the funnel job)
chain-block: threshold=2, step=0.30, pending-retry

RESULT (n=3000): mean=81.07x median=36.95x ratio=45.6% zero=0.17%
bucket%: s1=39.53 s2=33.53 s3=14.77 s4=7.10 s5=3.37 s6=1.70
spins<=2%=0.00%, mean_spins=8.14
chain: mean_passes=2.23 (target 2.5-2.6, slightly under) >=4pass=13.14% (target 10-20%, OK)
```
Every target hit: mean within 1% of 80.13x, ratio in 40-50% band, s6 in
1-2% band, bucket% strictly monotonic, near-zero spins<=2%, healthy zero-
payout rate. Chain mean_passes slightly under target - may nudge step down
a touch (e.g. 0.25) if time permits, low priority given it's close.

Tool: `final_combined_candidate.py` (measure(n, seed, tag, K, stage6_boost,
general_chance, chain_threshold, chain_step) - HP_MULT/HP_POOL are module-
level constants, currently set to the locked-in curve above).

---

## CURRENT BEST CANDIDATE (reward side only, chain-block not yet added)

`boss_table_escalation_sweep.py` + `reward_recalibration_v1.py`, confirmed
n=5000:
```
HP_MULT (boss_stage_table HP multiplier) = {1: 4.0, 2: 3.0, 3: 3.2, 4: 4.0, 5: 6.0, 6: 9.0}
HP_POOL (bonus_player_hp_choices["normal"]) = [200,200,200,200,200] (flat)
K (regular reward-pool additional scale, on top of existing K=4.28) = 0.72
stage6_boost (stage6-exclusive tiers additional scale)              = 64.0
Normal-tier pruning schedule (fixes the old no-op): 2/2/3/2/2 tiers pruned per stage 1-5

RESULT (n=5000): mean=78.35x median=36.94x ratio=47.2% zero=0.06%
bucket%: s1=35.08  s2=31.76  s3=15.38  s4=11.28  s5=4.98  s6=1.52
```
All targets hit: mean within 2.2% of 80.13x, ratio in the 40-50% band,
stage6 in the 1-2% band, bucket% strictly monotonic, zero-payout very low.

**IN PROGRESS**: `final_combined_candidate.py` is running now (n=3000) to
add the validated chain-block mechanism (threshold=2, step=0.30, pending-
retry) on top of this. Chain-block cut mean ~25% in earlier isolated testing
(against the OLD boss curve) — expect this candidate's mean to drop below
80x again and need a K/boost nudge back up. Will report once done.

---

## Key numbers found along the way (for context, not the final answer)

Reward K/boost sweep trend (n=4000 each, boss curve + pruning fix held
fixed, gd=0, no chain-block):
```
K=1.0  boost=40  -> mean=80.79x ratio=54.3%   (mean spot-on, ratio too high)
K=0.7  boost=62  -> mean=75.32x ratio=47.4%   (ratio in-band, mean low)
K=0.75 boost=68  -> mean=96.97x ratio=39.9%   (mean high, ratio low edge)
K=0.72 boost=64  -> mean=78.35x ratio=47.2%   (n=5000, BEST - see above)
```
Lesson: ratio is NOT very sensitive to proportional K scaling (stayed ~54%
across K=1.0/1.1/1.2 at fixed boost/K ratio) — it responds mainly to the
K-vs-boost SPLIT (how much of the "big win" mass sits in the rare stage6
spike vs the common regular pool). Widening that split lowers ratio (more
skew), matching the "high volatility, not extreme" design goal.

RUNTIME NOTE: this whole reward-calibration region is noisy at low n because
stage6 is now only ~1.5% of sessions — n=300 gave wildly different numbers
than n=2000 which differed again from n=4000/5000 for the SAME parameters.
Do not trust anything below n=2000 for this specific candidate; n=4000+ for
real decisions.

---

## Goal (per designer, this conversation - restated for continuity)
1. Stage-6 clear rate: ~1-2% (was ~21-22%), achieved via a genuinely harder
   boss difficulty curve, NOT via connect-suppression (gd/dead-spin), which
   was proven to wreck ratio/zero-payout instead (see per-stage-gd negative
   result below).
2. Bucket% (max-stage-reached distribution) must be STRICTLY monotonic
   non-increasing stage1 -> stage6. Any exception needs a genuine player-
   experience reason, never a payout-math excuse.
3. Other stages (1-5) should feel "more worthy" - bigger, more deliberate
   reward as you advance - not just a flat undifferentiated pool.
4. Avoid the game becoming "too zero payout" - use REDUCED gd + the already-
   validated chain-block mechanism as supporting levers, not primary ones.
5. Keep genuine high volatility, not pushed to an extreme/risky level
   (standing guardrail from earlier this session).
6. Mean target ~80.13x, ratio target ~40-50% (original Normal Bonus targets).

## Difficulty curve (SOLVED, confirmed n=3000)

`boss_stage_table` HP-only multiplier (Dam left at base table values - HP is
the "hits needed" lever, Dam controls per-spin instant-death risk which
HP=200 pool already fixed):
```
hp_mult_by_stage = {1: 4.0, 2: 3.0, 3: 3.2, 4: 4.0, 5: 6.0, 6: 9.0}
```
Confirmed n=3000, gd=0, no chain-block:
```
bucket%:  s1=34.60  s2=31.53  s3=15.93  s4=10.17  s5=6.03  s6=1.73
advance%: s1->2=65.4  s2->3=51.8  s3->4=53.0  s4->5=43.3  s5->6=22.3
```
Monotonic bucket% CONFIRMED. Stage6 in target range CONFIRMED.

Tool: `boss_table_escalation_sweep.py`.

RUNTIME WARNING: this config is SLOW (~250s for n=3000 in-process) because
tankier bosses -> more spins/session, and every stage clear grants +50
player HP (game_executables.py:460) which lets grinding sessions keep going
longer than naive Dam/HP math alone suggests. NOT a bug - confirmed by
direct code read. Budget iteration n accordingly (500-1000 for exploration,
4000+ for real decisions, more only for FINAL confirmation).

## Known structural facts (established this session, still valid)

- `bonus_player_hp_choices[tier]` is a WEIGHTED random.choice of STARTING hp
  for the whole session (game_bonus.py:326), not a per-stage schedule.
- `symbol_damage_range` = player's OUTGOING damage to bosses, shared across
  ALL 3 tiers (no per-tier key) - a production change here must be scoped
  carefully or it silently affects Super/Hidden too.
- Counter-attack damage (`total_damage = sum(boss_dam[b] for alive bosses)`,
  game_bonus.py:421) is UNCONDITIONAL every non-grace spin, sum across all
  3 alive bosses, rolled ONCE per boss when the trio spawns (roll_stage_
  bosses) - does NOT re-roll per spin against the same trio.
- `stage_clear_pruned_tiers` (game_config.py:475) referenced the SHARED
  table's ORIGINAL-scale keys - documented no-op for Normal/Super bonus.
  FIXED in reward_recalibration_v1.py's build_config() with a proper
  Normal-tier-keyed 2/2/3/2/2 progressive-pruning schedule.
- Chain-block mechanism (VALIDATED, see chain_block_pending_mechanism.py):
  threshold=2, step=0.30, pending-retry gives mean_passes~2.46-2.48,
  >=4pass~17.4-17.5% (target was 2.5-2.6 / 10-20%). Pending-retry safety net
  almost never needed in practice (fallback rate ~0.003%) but is real and
  correct - reuses the SAME RGS-safe `_route_column_force_deadspin` the
  shipped grace/deadspin mechanism already uses, just applied mid-cascade.
- Per-stage gd (varying general_deadspin_chance by stage): NEGATIVE RESULT,
  do not use as the primary stage-6 lever. Every direction tested (ramp up
  with stage, ramp down aggressively, ramp down gently) either barely moves
  the funnel or trades that for badly damaged ratio/zero-payout.
- `bonus_safety_cap_spins = 500` - hard defensive cap confirms no true
  infinite-loop risk even with very tanky boss_stage_table overrides.
- Reserve/exclusive stage6 chest tiers reference Normal's RESCALED values
  (2.57...2197.78 after the earlier K=4.28 fit) - any further reward-table
  change must re-key `reward_drop_top_tiers_normal_bonus` and
  `reward_drop_stage6_last_tiers_normal_bonus` to match.

## Remaining steps

1. Finish combining chain-block into the full candidate, re-tune K/boost if
   needed to land back on mean~80.13x / ratio 40-50% with chain-block active.
2. Re-verify chain-length target (mean_passes 2.5-2.6, >=4pass 10-20%) holds
   in the full combined candidate (should be independent of boss curve, but
   confirm not assume).
3. Full confirmation at n=15000-25000 of the COMPLETE combined package -
   mean, ratio, stage6%, bucket monotonicity, spins<=2%, zero-payout, chain
   length, all together on one final config.
4. Explore "other ideas" if time remains (see below).
5. Write final report with all before/after numbers. Do NOT touch production
   files without explicit final review - this is a much bigger, riskier
   change (new mechanism in tumble path, full difficulty curve rewrite, full
   reward table rewrite) than anything else applied this session.

## "Other ideas" - evaluated, decision: don't pursue further (see reasoning)

Re-examined all three while the n=15000 confirmation ran, given the "don't
go too far" instruction and that the locked-in candidate already hits every
target cleanly:

1. **Dam escalation per stage** - checked the numbers first: stage6's Dam
   sum is ALREADY ~200 (60+80+60), up to 250 with +/-25% variance, against
   a fixed 200 HP player pool - i.e. the EXISTING (unescalated) Dam curve
   is already near one-shot-kill territory by stage 6. Escalating Dam
   further on top of that risks pushing stage6 survival toward zero
   (overshooting below the 1-2% target) or creating unfair-feeling one-shot
   deaths, for a "scarier per-hit" feel that's already arguably there.
   DECISION: skip - real downside risk, no clear numeric problem to fix.
2. **Explicit stage-clear cash bonus** - would be redundant: the pruning
   fix (2/2/3/2/2 schedule) already makes later kills pay progressively
   more from a shrinking, higher-floor pool, and the combined candidate
   already hits mean/ratio targets without it. Adding a NEW income source
   would require re-fitting K/boost again for uncertain benefit.
   DECISION: skip - solved already via the pruning fix, this would be pure
   added risk/complexity for a cosmetic-only gain.
3. **Scale the +50 HP heal with the harder curve** - the locked-in candidate
   already hits every target WITH the original unscaled +50 heal, so
   there's no numeric evidence it needs changing.
   DECISION: skip - not broken, don't fix it.

Reallocating remaining time to ROBUSTNESS instead: confirm the locked-in
candidate holds across multiple independent seed offsets (not just one),
since Monte Carlo results for a ~1.5%-rare tail event can look good on one
seed by chance - want to see it's not a fluke before calling this done.

## Bug caught + good robustness signal

n=15000 run accidentally used a STALE __main__ param (K=0.85/boost=55.0,
left over from an earlier iteration - script's __main__ block wasn't
updated after finding K=1.0/boost=45.0 was better). Caught before reporting
it as final. Result at n=15000 with the stale K=0.85/boost=55.0:
```
mean=83.56x median=32.94x ratio=39.4% zero=0.10%
bucket%: s1=40.37 s2=33.34 s3=13.59 s4=7.25 s5=3.63 s6=1.83
```
Reassuring: this is ALSO a good result (all targets still hit), very close
to the K=1.0/boost=45.0 numbers at n=6000. Suggests the candidate is
robust across a small neighborhood of K/boost values, not fragile/cliff-
like in THIS region (unlike the boss_stage_table HP-multiplier region,
which showed real cliff sensitivity earlier). Fixed the script, re-ran
n=15000 with the CORRECT K=1.0/boost=45.0 - see below.

## ✅ CONFIRMED FINAL (n=15000, correct params)

```
mean=83.10x median=35.80x ratio=43.1% zero=0.10%
bucket%: s1=40.37 s2=33.34 s3=13.59 s4=7.25 s5=3.63 s6=1.83
spins<=2%=0.00%, mean_spins=8.16
chain: mean_passes=2.22 >=4pass=13.04%
```
Every target hit or very close: mean 3.7% over 80.13x target, ratio in
40-50% band, s6 in 1-2% band, bucket% strictly monotonic, spins<=2%
essentially eliminated, zero-payout very healthy, chain length in band
(mean_passes slightly under the 2.5-2.6 ask, accepted trade-off - see
"other ideas" section above for why not pursued further).

Running one more check now: SAME params, completely different seed offset
(n=8000), to rule out this being a lucky-seed result for the rare ~1.8%
stage6 tail specifically.

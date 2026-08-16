# Normal Bonus tuning - confirmed candidates (n=50000 unless noted)

## PRODUCTION IMPLEMENTATION WARNING (read before ever wiring this in)
`config.symbol_damage_range` is a single shared dict across ALL THREE
tiers (normal/super/hidden) - it is NOT tier-scoped in game_config.py.
Every scratch test here only ever simulates tier="normal" (measure()
hardcodes gs.run_bonus_session("normal")), so scaling this dict in a test
is safe and has zero effect on super/hidden simulation results. But if
hp200+none40+dmg45 is ever wired into REAL production code, the 0.45x
damage multiplier must be applied ONLY when tier=="normal" (e.g. a
per-tier damage multiplier dict, or scope the change to a normal-only
code path) - blindly setting config.symbol_damage_range = {scaled} would
also silently nerf Super and Hidden's combat math, which were tuned
separately and were never touched by any test in this file.
bonus_player_hp_choices and the chain-break weights are already correctly
tier-keyed/scoped, so only damage needs this care.

All results: chain-break = 4-tier weighted pool (sweep4 mode in
normal_3param_matrix_test.py): standard/lighter/lightest/none curves,
weights as noted. HP = flat unless noted. Damage = symbol_damage_range
multiplier (1.00 = production default).

## Leading candidate (user's favorite): hp75 + dmg+30%
- weights: std35/lighter30/lightest25/none10, HP=[75,75,100,100,100], dmg=1.30
- n=50000: mean=80.14x median=52.80x ratio=65.9% CV=1.32 zero=0.78% max=3144.1x
- session length (n=15000, hp75-set candidate, dmg=1.0 variant measured):
  mean_spins=4.05 median_spins=4, spins<=2=24.51% spins<=3=47.17%

## Reference points (n=50000)
- hp75 + dmg+0%:  mean=68.11x median=40.70x ratio=59.8% CV=1.38 zero=0.86% max=3128.7x
- hp100 + dmg+0%: mean=72.42x median=45.30x ratio=62.5% CV=1.28 zero=0.70% max=3081.2x

## Session length by HP (n=15000, current chain-break/dmg settings vary - see script)
- current production HP [50,50,50,100,100]: mean_spins=3.30 median=3, spins<=2=41.63%
- hp75-set candidate:                       mean_spins=4.05 median=4, spins<=2=24.51%
- HP=200 flat:                               mean_spins=6.41 median=6, spins<=2=8.87%

## HP=200 findings (n=15000)
- Reshuffling std/lighter/lightest weights (none fixed ~5-10%) barely moves
  anything: mean stuck 96-100x, ratio stuck 96-100%, regardless of severity mix.
- Raising the NONE tier's weight itself DOES work (mirrors the HP125 finding):
  none=10% -> mean=101.34 ratio=94.2% CV=0.92
  none=40% -> mean=114.75 ratio=83.8% CV=1.36  <- best shape found at HP200
  none=70% -> mean=124.73 ratio=76.6% CV=1.51
  But mean overshoots target badly at every point (101-125x vs 80-85x) -
  HP200 alone already produces too much mean even at dmg=1.0. Untested:
  damage REDUCTION (<1.0) to pull mean back down at HP200 (job killed
  before it produced output - not yet re-run).
- Across ALL HP200 variants tested, median stays pinned ~94-96x regardless
  of chain-break tuning - confirms median is HP-driven, not
  chain-break-driven (same finding as at HP125).

## CONFIRMED CANDIDATE (n=50000, user's pick - "i love this one"): hp200 + none40 + dmg45
(normal_hp200_candidate_confirm_n50k.py). Matches the loved hp75+dmg130 shape
closely while more than doubling spin count - no "force extra dead spins"
mechanic needed, just existing HP pool / CB weights / damage multiplier.

n=50000 confirmation (2026-08-17):
  hp75+dmg130 (loved):   mean=82.38x median=54.40x ratio=66.0% CV=1.32 zero=0.77% | spins mean=3.90 median=4 max=16 spins<=2=25.16%
  hp200+none40+dmg45:    mean=81.14x median=54.40x ratio=67.0% CV=1.12 zero=0.03% | spins mean=8.32 median=7 max=30 spins<=2=0.77%
Median landed EXACTLY equal (54.40x = 54.40x) at this scale. Mean within
1.5%. Spin count more than doubled (3.90->8.32), "dies in <=2 spins" felt-
bad rate crushed (25.16%->0.77%), zero-payout also crushed (0.77%->0.03%).
Percentile/distribution check done too (see full breakdown in the
n=50000 task log / confirm50k_*.csv files) - shape is a smooth, single-
hump distribution for both, no weird lumps introduced by the candidate.

Why it works: symbol_damage_range (player's kill speed) is independent of
boss_dam (counter-attack cost) - game_bonus.py:405-407 confirms counter-
attack is unconditional per spin and unrelated to player's damage output.
So cutting damage slows kills (needs more spins to clear stages = more
felt spins) WITHOUT changing HP's survival budget per spin, while HP200 +
none-tier CB weight brings mean/median back near target.

Runner-up (also converges, real dead-spin-rate lever instead of damage):
hp200+none25%+p_dead65% (raw dead-spin-rate injection, normal_hp200_deadspinrate_test2.py,
n=15000): mean=83.03x median=54.30x ratio=65.4% CV=1.32(exact match) zero=0.00%
| mean_spins=6.62. Close, but weaker spin-count gain than the damage-lever
candidate (6.62 vs 8.32) and needs a "discard/override the real reveal"
mechanic with its own RGS-replay-logging caveat (see conversation) - damage-
lever candidate above is simpler and stronger, treat as primary.

## Stage-reach ground truth (n=15000, normal_stage_reach_diagnostic.py)
IMPORTANT: the first version of this diagnostic had a real bug - it only
checked self.stage once per spin, missing mid-spin multi-stage clears (a
single spin's cascade CAN clear several fresh boss trios back to back if
damage output that pass is high enough - confirmed this really happens).
Fixed by wrapping clear_stage() directly instead of sampling self.stage
per-spin. Numbers below are POST-FIX and internally consistent
(stage6-reach >= stage_cleared, as it must be).

  hp75+dmg130:        max-stage-reach: S1=5.43% S2=11.35% S3=12.09% S4=12.90% S5=8.81% S6=49.42%
                       end: hp_depleted=55.56% stage_cleared=44.44%
  hp200+none40+dmg45: max-stage-reach: S1=1.99% S2=16.87% S3=23.80% S4=21.71% S5=10.10% S6=25.54%
                       end: hp_depleted=77.85% stage_cleared=22.15%

Non-obvious finding: hp200+none40+dmg45 is NOT simply "safer" - it reaches/
clears stage 6 LESS often than hp75+dmg130 (22.15% vs 44.44%) despite 2.5x
the HP and 2x+ the spins. hp75's high damage (1.30x) means once you survive
the early spins you tend to blow through stages fast (polarized: early death
or full clear). hp200's low damage (0.45x) shifts the WHOLE distribution
toward sustained mid-stage grinding (higher reach at stages 2-4) rather than
raising the full-clear rate - trading "fast win or fast death" for "longer,
steadier progress that more often ends mid-fight." Arguably an even better
match for the user's "feel like they're spinning more / playing more" ask
than raw spin-count alone would suggest.

## HP pool shape robustness (n=15000, normal_hp200_mixed_pool_test.py)
Candidate above uses a FLAT hp=[200]*5 pool (testing convenience), unlike
production's convention of a MIXED pool (e.g. current prod [50,50,50,100,100]).
Checked whether flattening it away from that convention hides anything:
  flat200:              mean=80.91x median=53.70x ratio=66.4% CV=1.12 zero=0.01%
  mixed_175_225:         mean=80.50x median=53.70x ratio=66.7% CV=1.14 zero=0.02%
  mixed_150_250:         mean=81.22x median=54.20x ratio=66.7% CV=1.16 zero=0.05%
  mixed_current_style:   mean=77.15x median=50.70x ratio=65.7% CV=1.22 zero=0.06%
All land within a few percent of each other - flat vs mixed HP pool doesn't
materially change the shape at HP~200. Flat-200 is a safe simplification,
not hiding a real difference.

## Demo/visualization note
An interactive HTML playback (boss_lines_normal_console_demo.html) was built
to let the user "feel" a bonus round. v1 used an invented, underpowered
per-hit damage model that produced 0% stage-clears for BOTH configs (caught
by the user testing it, not by me - see feedback_verify_before_shipping_demos
memory). v2 fixed this by driving stage-clear/death odds directly from the
real stage-reach hazard data above (not a guessed damage model) - verified
against the actual shipped file's own runFullSession (not a hand-retyped
copy) at n=20000: A mean=3.95(ref 3.90) cleared=44.35%(ref 44.44%), B
mean=8.30(ref 8.32) cleared=21.73%(ref 22.15%).

## Session-length padding - SOLVED (normal_filler_deadspin_test.py)
User's real ask (clarified): more FELT spins per bonus round, WITHOUT
touching HP cost, real connect probability, or total payout. Confirmed
empirically (n=8000, hp75+dmg30% candidate): filler dead-spins are 0 HP
cost / 0 payout events added on top of the real game loop via an
independent RNG stream - payout stats are byte-identical across every
fill_rate tested (mean=81.13x median=54.85x ratio=67.6% CV=1.23 zero=0.90%,
unchanged at fill_rate 0/0.3/0.5/0.8/1.0/1.5) while felt spin count scales:
  fill_rate 0.0 -> 3.91 spins (baseline, no fillers)
  fill_rate 0.3 -> 5.08 spins
  fill_rate 0.5 -> 5.87 spins
  fill_rate 0.8 -> 7.04 spins
  fill_rate 1.0 -> 7.81 spins (caps here w/ per-spin-Bernoulli model)
Recommended: fill_rate ~0.5-0.8 (roughly doubles felt spin count 3.9->6-7)
without changing the loved economy at all. Implementation note: if RGS
requires every counted spin to be a genuine RNG draw from the certified
reelset (not a bare counter increment), fillers need to be real harmless
reel draws in game_bonus.py - same math, different wiring.

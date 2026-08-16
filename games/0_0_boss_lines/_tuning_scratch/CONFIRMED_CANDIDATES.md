# Normal Bonus tuning - confirmed candidates (n=50000 unless noted)

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

## STRONG CANDIDATE: hp200 + none40 + dmg45 (real levers, no new mechanic)
(normal_spincount_verify.py, n=15000). Matches the loved hp75+dmg30% shape
within a few % on every stat while ~doubling spin count - no "force extra
dead spins" mechanic needed, just existing HP pool / CB weights / damage
multiplier.
  hp75+dmg130 (loved):        mean=80.08x median=52.00x ratio=64.9% CV=1.30 zero=0.85% | spins mean=3.88 median=4  max=15 spins<=2=25.30%
  hp200+none40%+dmg45%:       mean=80.46x median=54.00x ratio=67.1% CV=1.11 zero=0.01% | spins mean=8.26 median=7  max=28 spins<=2=0.71%
Why it works: symbol_damage_range (player's kill speed) is independent of
boss_dam (counter-attack cost) - game_bonus.py:405-407 confirms counter-
attack is unconditional per spin and unrelated to player's damage output.
So cutting damage slows kills (needs more spins to clear stages = more
felt spins, mean_spins 3.88->8.26) WITHOUT changing HP's survival budget
per spin, while HP200 + none-tier CB weight brings mean/median back near
target. Bonus: zero-payout also drops to near 0% (0.85%->0.01%).
Not yet done: n=50000 confirmation; distribution/percentile check;
comparison against the still-running raw-dead-spin-rate-injection sweep
(normal_hp200_deadspinrate_test2.py) which needed p_dead>60% and hadn't
converged as well as this by that point (mean_spins stayed ~6.5 flat
regardless of p_dead, since a forced-dead spin still counts as one full
spin/one full counter-attack in the outer loop - dead-spin-rate mainly
moves payout down, not spin count up; HP is what drives spin count).

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

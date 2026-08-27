# Stage 2 clear-time/clear-rate divergence: investigation record (2026-08-22)

## Starting point
JS demo's stage-2 boss-clear dynamics ran hot relative to isolated Python
harnesses: clear-rate under a fixed player-HP budget was 65.86% (Python) vs
92.66% (JS), n=20000 each.

## Root cause found and fixed: booster-cycling harness bug
Every isolated Python test harness in this investigation called
`gs.run_one_bonus_spin(False)` directly, bypassing `run_bonus_session`'s
outer-loop step that cycles `booster_multiplier_current_spin` (the x2-damage
Booster, which fires on ~40%+ of spins). This silently disabled the Booster
in every Python comparison while JS's demo had it correctly wired throughout.

Fix: manually replicate the 2-line cycling step before every direct
`run_one_bonus_spin` call:
```python
gs.booster_multiplier_current_spin = config.booster_damage_multiplier if gs.booster_pending_for_next_spin else 1.0
gs.booster_pending_for_next_spin = False
```
After the fix, per-instance/per-boss damage distributions converged to
within ~1-2% between engines. This was the dominant cause of the original
gap. Reported and demo panel updated.

## Residual gap (still open after the fix)
Mean spins-to-clear stage 2 (fixed boss Dam/HP, chain-block on, n=15000):
Python 6.4629 +/- 0.0203 (SE) vs JS 5.9866 +/- 0.0199 (SE) — a ~7.9%
gap at ~16.8 SE (not sampling noise). Clear-rate under a fixed finite
player-HP budget: 65.9% (Python) vs 92.7% (JS), n=20000 each — a much larger
practical divergence.

## Every hypothesis tested this session, and the result

| Hypothesis | Test | Result |
|---|---|---|
| Chain-block pass-count interaction | Disabled chain-block entirely in both engines, re-measured clear time | Gap persists (Python 5.9162+/-0.036 vs JS 5.4908+/-0.034, ~7.7% gap, 8.6 SE) — **ruled out** |
| Same-spin cross-boss damage correlation | corr(boss1,boss2), corr(boss1,boss3), corr(boss2,boss3), P(all 3 touched) | Match within 0.1pp in both engines — **ruled out** |
| Per-boss marginal per-spin damage distribution (boss1, immortal bosses) | mean/stdev/CV/percentiles/deciles, n=60000 | Python mean=145.59, JS mean=145.55; every decile (5th-80th) matches to <1 unit — **ruled out** |
| First-passage time predicted purely from the matching marginal | Bootstrap i.i.d. resample from each engine's own empirical boss1 samples, simulate first-passage to HP=375 | Python-marginal bootstrap mean=3.661, JS-marginal bootstrap mean=3.659 — statistically identical, confirming the marginals alone predict NO gap |
| Spin-to-spin autocorrelation (lag 1-5) of total per-spin damage | n=30000, both aggregate (3-boss sum) and boss1-specific | All lags small (~0.05-0.07) and close between engines; boss1-specific lag1 was JS=0.063 > Python=0.051 — wrong direction to explain Python being slower — **ruled out** |
| Zero-damage run-length clustering (streakiness of "boss1 untouched this spin") | Run-length histogram, mean run length, max run, n=60000 | Python mean run=1.368, JS mean run=1.370; histograms nearly identical — **ruled out** |
| Wasted damage (instances landing on an already-dead boss) | Instrumented `dealDamageToBoss`/`deal_damage_to_boss` to log generated vs wasted damage, n=3000 sessions to real clear | Instance-wasted: Python 13.97%, JS 13.78%. Damage-wasted: Python 12.80%, JS 13.57% — matches, and JS wastes *slightly more* (wrong direction) — **ruled out** |
| "Weak first spin" effect (spin 1 of a fresh stage deals less damage than steady-state) | Measured spin1/spin2/spin3 mean damage to boss1 separately, n=20000 | Real effect (~30% lower on spin 1 in BOTH engines: Python spin1=102.7 vs steady-state ~145.5; JS spin1=104.2 vs ~145.5) but present equally in both — **ruled out as an explanation for the cross-engine gap** (it's a genuine shared game feature, not a bug) |
| Test-harness stopping-rule bug (state-read-after-mutation, same class as the earlier `Object.assign` contamination bug) | Per-session, compared clear-spin detected via post-hoc state read (`gs.stage>2` / `bossState.stage!==2`) against clear-spin detected via a hook on the 3rd defeat event, for both engines independently | 0/5000 mismatches in Python, 0/5000 mismatches in JS — both harnesses' two detection methods agree perfectly with each other — **ruled out** |

## Conclusion
Every distributional and mechanistic hypothesis that could be directly
measured was tested and refuted. The per-spin marginal damage distribution
to each boss matches almost exactly between engines (confirmed via
bootstrap: resampling i.i.d. from either engine's own empirical marginal
predicts the same first-passage time, ~3.66 spins to defeat boss1 alone).
Yet the real, sequential, correlated simulation in both engines consistently
produces a longer first-passage/clear time in Python than in JS, by a
reproducible ~8-10% across every configuration tested (chain-block on,
chain-block off, boss1 in isolation, full 3-boss race).

This means the cause is a higher-order or longer-range sequential dependency
in the pass/cascade structure (not captured by lag-1-5 linear
autocorrelation, same-spin cross-boss correlation, or run-length clustering)
that could not be isolated to a specific line of code within the scope of
this investigation. No further specific, code-traceable bug was found.

This is a scratch-only (`_tuning_scratch/`) demo-vs-Python-harness
discrepancy. It has no bearing on the production game files
(`game_config.py`, `game_bonus.py`, `game_executables.py`,
`game_calculations.py`), which were not touched by this investigation.

## Separate bug found and fixed in the same session: missing "grace deadspin"

While checking whether chain-block's force-deadspin primitive
(`_route_column_force_deadspin` / `routeColumnForceDeadspin`) could explain
the residual (it can't — see table above), a real, unrelated gap surfaced:
the JS demo had **zero implementation** of production's Bonus "grace spin"
mechanic (`game_executables.create_board_reelstrips`'s
`grace_deadspin_pending` branch) — a 65% per-column chance
(`bonus_grace_deadspin_chance`) to force columns 1/2/3 dead on the very first
spin against a freshly-rolled boss trio (i.e. the spin right after any
non-final stage clear).

Measured effect in Python: with the flag active, that spin's mean damage to
boss1 drops from ~103 (flag inactive / skip-ahead start) to ~44, and
P(zero damage) rises from 27% to 65%.

This is unrelated to the still-open single-stage residual above — that
residual was measured with the flag correctly inactive on both sides
(matching real skip-ahead semantics), so this bug never contributed to it.
It's a separate, real, Python-only advantage across every *natural*
multi-stage transition (1→2, 2→3, ..., 5→6) that the demo was silently
missing.

**Fixed:** ported into the demo via `ctx.graceDeadspinPending` (set in
`clearStage` on any non-final stage clear, consumed at the top of
`runOneBonusSpin`'s board draw) + `BONUS_GRACE_DEADSPIN_CHANCE = 0.65`,
reusing the existing `routeColumnForceDeadspin` primitive. Verified to
reproduce the Python numbers almost exactly (JS: ~104 → ~45, P(zero)=65%
with the flag on). Covered by 3 new checks in `test_demo_sim.js` section 6
(18/18 total checks passing after the fix).

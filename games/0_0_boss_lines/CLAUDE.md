# Boss Lines (0_0_boss_lines) — working conventions

## Commit at checkpoints

This project has an extensive, valuable tuning history (Normal/Super/Hidden
Bonus reward tables, RTP optimization, reel fixes) that has mostly lived as
**uncommitted working-tree changes** since the initial "Add Boss Lines game"
commit. Long conversations get summarized/compacted over time, and a past
assistant session's memory of what it did is NOT reliable after that -
`git log`/`git diff`/file mtimes on disk are the only trustworthy record.

**Default behavior for any assistant working in this folder**: after any
change to `game_config.py`, `game_bonus.py`, `game_executables.py`,
`game_calculations.py`, or `reels/*.csv` that has been verified (measured and
confirmed correct, not just written), create a git commit capturing that
checkpoint with a clear message describing what was validated and the
measured numbers. Don't wait to be asked. This is a standing exception to
"only commit when explicitly asked" for this specific folder, because the
cost of losing track of validated state here (as has already happened at
least once - see `_tuning_scratch/results/segments_n100000_20260822_003530.json`,
a "final confirmed" candidate that was never committed or even applied to
`game_config.py`, and was later found to be measured under a contaminated
harness) is high and has already caused real confusion.

Do NOT commit `_tuning_scratch/` scratch/candidate scripts on the same
cadence - those are exploratory and can be numerous; use judgment (a commit
covering just the production files plus a short scratch note referencing
which script produced the numbers is usually right).

## Reference for the future

- `game_config.py`'s own comment blocks (especially around
  `reward_drop_weights_normal_bonus`) are the single most reliable source of
  truth for tuning history - read them IN FULL before assuming any external
  memory file or `_tuning_scratch/results/*.json` reflects current state.
- `final_combined_candidate.py` (and anything importing it, e.g.
  `reshape_segments_test.py`, `reshape_niceints_test.py`) applies
  `bonus_player_hp_choices["normal"] = [200]*5` and boss HP scaled 3.7x-7x,
  PLUS an active scratch-only chain-break mechanic - none of these three
  exist in real production. Any percentile/mean number from a script that
  imports `final_combined_candidate` needs re-verification against a clean,
  zero-override harness (e.g. `pure_production_percentile_check.py`) before
  it can be trusted as representative of the real game.

# Boss Lines v3 (0_0_boss_lines_v3) — working conventions

- Source of truth for the rules: `Proposal_2026-10-06.docx` (copied here) plus
  the answers recorded in `QUESTIONS.md`. Fixed numbers (paytable, damage,
  boss HP, paylines, coin values, mode costs) must not be changed without the
  game designer's approval (proposal section 7).
- Every ambiguous rule is a named flag in `game_config.py` tagged `Q<n>`;
  change the flag, not the logic, when an answer arrives.
- Run the rule tests after any change: `python -m pytest tests -q`
  (from this folder). They check hand-built boards against the proposal and
  read paylines/paytable/cell order straight from the .docx.
- Commit at verified checkpoints (tests passing + smoke run clean). Keep
  `_scratch/` out of commits unless a script is referenced by a result.
- `0_0_boss_lines` and `0_0_boss_lines_v2` are separate games; do not edit
  them from here.

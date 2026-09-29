# 0_0_boss_lines_v2 (fork of 0_0_boss_lines, spec: DESIGN_CHANGES_v2.md)

Forked 2026-09-30 so the tuned 0_0_boss_lines stays untouched. Every economy
number inherited from it is INVALID until re-tuned (smoke: Normal ~515x,
Super ~2400x, Hidden ~2250x mean).

## Phase status
- [x] A - base: 6x5 grid, L1-L4/H1-H5, new paytable (W row = placeholder =
      L4's), 15 paylines extended to 6 cols, boss zones cols 0-1/2-3/4-5 (no
      fallback), L5 removed from stage-clear schedule, Wild-anchored wins
      only clear their own cells, reels/*.csv converted (col 6 = copy of col 4
      with Powers -> W; L5 -> L4; every 2nd H4 -> H5; PLACEHOLDER density).
      Both Ways already sums both directions independently.
- [x] B - chest system (`use_chest_system`): dong/bac/vang/kim cuong/cau vong
      tables, one-time upgrade (`chest_upgrade_chance`), per-stage minimums
      (`chest_type_weights_by_stage`), stage 1 may drop nothing, rainbow only
      on the last boss of stage 5 (`rainbow_convert_chance`). Stages are now
      1-5 (old stage 6 removed; stage 5 is the loop). Boss base rows are
      shuffled per boss (boss 2 no longer always the biggest).
      Check: `_tuning_scratch/chest_check_v2.py`.
- [x] C - guns (GS short / GL long) replace Booster; Wild Multi is a delayed
      FIFO power stamping a factor on every cell of one symbol (SDK
      `multiplier` slot -> line factors add, damage x per cell); Upgrade power
      (PUP); Extra Wild can land Power; removed Mystery/Big/Extra Power/Alter
      and board Global Multi. Power never in col 1/6, Wild anywhere.
      Check: `_tuning_scratch/events_check_v2.py [normal|super|hidden]`.
- [x] D - stage 0 (base/ante: HP 20 x3, flat damage, drop pool = all chest
      multis + 0x); Bonus only triggers if all stage-0 bosses die, scatter
      count picks tier (<3 Bonus, 3 Super, 4 Mega, 5 Maxwin on wincap fence);
      Coin mechanic (Power Coin "PCN", runs last, cells: coin/chest/clover/
      global/scatter/short gun/long gun); Full board coin = 50% of the
      "godmode" bet mode spins (`feature_full_board_coin_chance`); God Mode =
      stage-5 boss, never advances, no scatter; last-hit +3% on the final
      Bonus spin without scatter. Check: `_tuning_scratch/modes_check_v2.py`,
      `base_check_v2.py`.
- [ ] E - TUNING (nothing tuned yet): RTP per mode, Bonus/Super/Mega means,
      chest/coin weights, HP tables, reels, stage-0 clear rate (~0.7%/spin
      natural), Maxwin frequency (`stage6_chest_natural_maxwin_weight` is a
      placeholder), optimizer fences (freegame fence now needs "boss cleared"
      + forced scatter count 0/3/4).

## Known Phase A gaps
- Paytable values like 0.15/0.25/1.25 are not multiples of 0.10 (RGS rule).
- Reel strips are mechanical conversions, not designed; Wild still absent
  from col 1 in the original strips.
- Damage: base/ante and Super use spec's flat 1/2/3; Normal/Hidden bonus still
  random-range (`use_flat_damage`).
- Smoke: `_tuning_scratch/smoke_v2.py N`, payout checks:
  `_tuning_scratch/payout_examples_v2.py`.

## Naming (display only - internal ids unchanged)
"hidden" = Mega Bonus, "normal" = Bonus, "godmode" bet mode = Feature spin
(God Mode or Full board coin).

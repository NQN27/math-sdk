"""Rule tests on hand-built boards (Proposal_2026-10-06.docx)."""
import random

import pytest

from conftest import set_board
from game_config import ENDLESS
from game_executables import round_half_up

FILLER = [
    "L1 L2 L3 L4 L1 L2",
    "L3 L4 L1 L2 L3 L4",
    "L2 L1 L4 L3 L2 L1",
    "L4 L3 L2 L1 L4 L3",
    "L1 L2 L3 L4 L1 L2",
]


def board_with_top(top):
    return [top] + FILLER[1:]


def line1(gs):
    return [w for w in gs.evaluate_lines() if w["meta"]["lineIndex"] == 1]


# ---- line pay ---------------------------------------------------------------
def test_best_of_wild_or_symbol(gs):
    set_board(gs, board_with_top("W W W H3 H4 L1"))
    (w,) = line1(gs)
    assert (w["symbol"], w["kind"], w["win"]) == ("H3", 4, 2.25)


def test_six_wilds_pay_25(gs):
    set_board(gs, board_with_top("W W W W W W"))
    (w,) = line1(gs)
    assert w["win"] == 25


def test_five_wilds_pay_as_symbol(gs):
    set_board(gs, board_with_top("W W W W W H5"))
    (w,) = line1(gs)
    assert (w["symbol"], w["kind"], w["win"]) == ("H5", 6, 20)


def test_line_factor_enhance_add_then_wild_then_global(gs):
    set_board(gs, board_with_top("H1 H1 W H1 L2 L3"))
    gs.enhance[0][0] = 2
    gs.enhance[1][0] = 3
    gs.wild_mult[(2, 0)] = 4
    gs.global_mult = 5
    (w,) = line1(gs)
    ef, wf = gs.line_factor(w)
    assert (ef, wf) == (5, 4)
    paid = gs.pay_lines([w])
    assert paid == pytest.approx(1.25 * 5 * 4 * 5)  # 4x H1 = 1.25


def test_global_zero_pays_as_one(gs):
    gs.global_mult = 0
    assert gs.global_factor() == 1


# ---- clear rule / damage ----------------------------------------------------
def test_connected_basic_clears_all_copies_wild_only_itself(gs):
    gs.spawn_stage(1)
    rows = board_with_top("H2 H2 W H2 L1 L2")
    rows[4] = "L3 H2 L3 L4 L1 W"  # H2 at (1,4) is a non-connected copy; W at (5,4) cannot connect
    set_board(gs, rows)
    destroyed = []
    gs.refill = lambda: destroyed.extend((c, r) for c, r in gs.all_cells() if gs.board[c][r] is None)
    gs.step_connect()
    assert (1, 4) in destroyed  # every H2 on the board
    assert (2, 0) in destroyed  # the connected Wild
    assert (5, 4) not in destroyed  # a Wild that did not connect stays


def test_damage_goes_to_boss_of_column(gs):
    gs.spawn_stage(3)
    for b in gs.bosses:
        b["hp"] = b["hp_max"] = 1000
    gs.deal_damage([(0, 0, 5), (1, 0, 5), (3, 2, 7), (5, 4, 2)], "test", last_hit=False)
    hp = {b["id"]: b["hp"] for b in gs.bosses}
    assert hp == {"boss1": 990, "boss2": 993, "boss3": 998}


def test_endless_single_boss_spans_all_columns(gs):
    gs.spawn_stage(ENDLESS)
    assert len(gs.bosses) == 1 and gs.bosses[0]["zone"] == tuple(range(6))
    assert 350 <= gs.bosses[0]["hp"] <= 400 and gs.bosses[0]["hp"] % 5 == 0
    first = gs.bosses[0]["hp"]
    gs.spawn_stage(ENDLESS)
    assert gs.bosses[0]["hp"] >= first


def test_stage_hp_ranges_and_multiple_of_5(gs, cfg):
    random.seed(1)
    for stage in range(0, 6):
        for _ in range(50):
            gs.spawn_stage(stage)
            lo, hi = cfg.stage_hp_range[stage]
            for b in gs.bosses:
                assert lo <= b["hp"] <= hi and b["hp"] % 5 == 0
            assert [b["zone"] for b in gs.bosses] == [(0, 1), (2, 3), (4, 5)]


# ---- weapons -------------------------------------------------------------------
def test_bomb_area_clipped_at_corner(gs):
    set_board(gs, ["BM H1 L1 L1 L1 L1", "H2 SC L1 L1 L1 L1"] + FILLER[2:])
    t = sorted(gs._weapon_targets(0, 0, "BM"))
    assert t == [(0, 1), (1, 0)]  # (1,1) is a Scatter, not paying


def test_sword_hits_row_and_wild(gs, cfg):
    set_board(gs, ["SW W AR L1 SC H2"] + FILLER[1:])
    t = sorted(gs._weapon_targets(0, 0, "SW"))
    assert t == [(1, 0), (3, 0), (5, 0)] if cfg.weapons_destroy_wild else [(3, 0), (5, 0)]


def test_weapon_factor_multiplies_damage(gs):
    gs.spawn_stage(4)
    for b in gs.bosses:
        b["hp"] = b["hp_max"] = 500
    set_board(gs, ["H3 H3 L1 L2 L3 L4", "BM H5 L1 L2 L3 L4"] + FILLER[2:])
    gs.board[0][1].prize = 4
    gs.refill = lambda: []
    gs.step_weapons()
    # bomb at (0,1) hits (0,0) H3, (1,0) H3, (1,1) H5, (0,2) L2, (1,2) L1 -> boss1
    assert gs.bosses[0]["hp"] == 500 - 4 * (2 + 2 + 3 + 1 + 1)


def test_arrow_formula_and_endless_halving(gs):
    gs.spawn_stage(5)
    b = gs.bosses[0]
    b["hp_max"] = 100
    random.seed(0)
    k = random.choice(gs.config.arrow_k_choices)
    random.seed(0)
    assert gs.arrow_damage(b) == round_half_up(3 + 100 * k)
    gs.stage = ENDLESS
    random.seed(0)
    assert gs.arrow_damage(b) == round_half_up((3 + 100 * k) / 2)


def test_round_half_up():
    assert round_half_up(12.5) == 13 and round_half_up(11.5) == 12 and round_half_up(2.49) == 2


# ---- powers ----------------------------------------------------------------------
def test_upgrade_turns_all_cells_same_target_and_keeps_enhance(gs):
    set_board(gs, ["H1 L1 L1 L1 L1 L1"] + FILLER[1:])
    random.seed(3)
    gs.enhance[0][0] = 7
    before = {(c, r): gs.board[c][r].name for c, r in gs.all_cells()}
    gs.power_upgrade()
    changed = [x for x in gs.all_cells() if gs.board[x[0]][x[1]].name != before[x]]
    targets = {gs.board[c][r].name for c, r in changed}
    assert len(targets) == 1 and targets <= {"H5", "W"}
    assert gs.enhance[0][0] == 7


def test_replace_rule_two_of_first_three_columns(gs):
    set_board(gs, [
        "H1 H1 L1 L2 L3 L4",
        "H2 L3 L1 L2 L3 L4",
        "L1 L3 H4 L2 L3 L4",
        "L1 L4 L4 L2 L3 H5",
        "L1 L4 L4 L2 L3 L4",
    ])
    elig = {gs.board[c][r].name for c, r in gs._replace_eligible()}
    # in >=2 of columns 1-3: H1 (c0,c1), L1 (c0,c2), L3 (c1? no: c1 has L3; c0? no) ...
    assert "H1" not in elig and "L1" not in elig and "L4" not in elig
    assert {"H2", "H4", "H5", "L2"} <= elig


def test_transform_skips_wild_weapon_and_scatter(gs, cfg):
    set_board(gs, ["W AR SC W W W"] + ["W W W W W W"] * 3 + ["W W W W W H1"])
    random.seed(5)
    gs.power_transform()
    assert gs.board[1][0].name == "AR" and gs.board[2][0].name == "SC"
    assert gs.board[5][4].name == "W"


def test_power_reserve_cap(gs, cfg):
    gs.reserve = {p: cfg.power_reserve_cap for p in cfg.power_names}
    assert gs.pick_power() is None


# ---- chests -----------------------------------------------------------------------
@pytest.mark.parametrize("tier,lo,hi", [("dong", 1, 3), ("bac", 2, 3), ("vang", 3, 3), ("kimcuong", 3, 3)])
def test_chest_gift_rules(gs, cfg, tier, lo, hi):
    gs.chest_upgrade_chance_backup = cfg.chest_upgrade_chance
    cfg.chest_upgrade_chance = 0.0
    try:
        random.seed(11)
        for in_bonus in (False, True):
            gs.in_bonus = in_bonus
            for _ in range(300):
                gs.reserve = {p: 0 for p in cfg.power_names}
                gs.book.events.clear()
                gs.open_chest({"id": "boss1", "chest": tier, "chest_opened": False})
                gifts = gs.book.events[-1]["gifts"]
                if gs.wincap_triggered:  # a 25,000x coin ends the round mid-chest
                    gs.win_manager.reset_end_round_wins()
                    gs.wincap_triggered = False
                    continue
                assert lo <= len(gifts) <= hi
                coins = [g for g in gifts if g["kind"] == "coin"]
                assert all(g["value"] >= cfg.coin_tiers[tier][0] for g in coins)
                if not in_bonus:
                    assert len(coins) == len(gifts)
                if tier in ("vang", "kimcuong"):
                    assert coins
                gs.win_manager.reset_end_round_wins()
                gs.wincap_triggered = False
    finally:
        cfg.chest_upgrade_chance = gs.chest_upgrade_chance_backup


# ---- scatter cap / board ---------------------------------------------------------
def test_scatter_cap_five_and_one_per_column(gs, cfg):
    all_sc = [["SC", "L1", "L1", "L1", "L1"] * 60 for _ in range(6)]  # every window shows a Scatter
    cfg.reels["_ALLSC"] = all_sc
    try:
        random.seed(2)
        gs.no_scatter_spin = False
        for _ in range(50):
            gs.draw_board("_ALLSC")
            assert gs.scatter_count() == 5
            assert not any(gs.is_scatter(gs.board[5][rr]) for rr in range(5))  # column 6 blocked
    finally:
        del cfg.reels["_ALLSC"]


def test_forced_scatter_count_exact(gs):
    random.seed(4)
    for n in (3, 4, 5):
        for _ in range(20):
            gs.draw_board("BR0", force_scatters=n)
            assert gs.scatter_count() == n
            for c in range(6):
                assert sum(gs.is_scatter(gs.board[c][r]) for r in range(5)) <= 1


def test_heroic_reel_has_no_scatter(cfg):
    assert all("SC" not in col for col in cfg.reels["HERO"])


def test_stage_reels_drop_removed_lows(cfg):
    for stage, reel in cfg.bonus_stage_reel.items():
        removed = cfg.low_symbols[: cfg.stage_removed_lows[stage]]
        syms = {s for col in cfg.reels[reel] for s in col}
        assert not (syms & set(removed)), (stage, reel)


# ---- treasure ------------------------------------------------------------------------
def test_treasure_coins_only_pays_sum_times_global(gs, cfg):
    saved = dict(cfg.treasure_kind_weights)
    cfg.treasure_kind_weights.clear()
    cfg.treasure_kind_weights.update({"coin": 1})
    try:
        set_board(gs, FILLER)
        gs.stage = 2
        gs.global_mult = 3
        cells = [(0, 0), (1, 0), (2, 0)]
        random.seed(9)
        paid = gs.run_treasure(cells, 1)
        total = sum(gs.board[c][r].prize for c, r in cells)
        assert all(gs.board[c][r].prize >= 1 for c, r in cells)
        assert paid == pytest.approx(total * 3)
    finally:
        cfg.treasure_kind_weights.clear()
        cfg.treasure_kind_weights.update(saved)


def test_treasure_first_round_guarantees_a_coin(gs, cfg):
    saved = dict(cfg.treasure_kind_weights)
    cfg.treasure_kind_weights.clear()
    cfg.treasure_kind_weights.update({"clover": 1})
    try:
        set_board(gs, FILLER)
        gs.stage = 1
        random.seed(1)
        gs.run_treasure([(0, 0), (1, 0)], 0.2)
        kinds = [gs.board[c][r].name for c, r in [(0, 0), (1, 0)]]
        assert "TC" in kinds
    finally:
        cfg.treasure_kind_weights.clear()
        cfg.treasure_kind_weights.update(saved)


def test_magnet_collects_and_cells_reappear(gs):
    set_board(gs, FILLER)
    gs.stage = 1
    cells = [(0, 0), (1, 0), (0, 1)]  # priority 1, 2, 3
    seq = iter(["magnet", "coin", "coin"])
    gs.roll_treasure_kind = lambda weights: next(seq, "coin")
    random.seed(2)
    paid = gs.run_treasure(cells, 0.2)
    mags = [e for e in gs.book.events if e["type"] == "treasureMagnet"]
    assert len(mags) == 1 and mags[0]["collected"] > 0
    assert len(mags[0]["cells"]) == 2  # both coins were collected
    fills = [e for e in gs.book.events if e["type"] == "treasureSymbols"]
    assert len(fills) == 2 and len(fills[1]["cells"]) == 2  # collected cells reappear
    final = sum(gs.board[c][r].prize for c, r in cells)
    assert paid == pytest.approx(final)


# ---- last hit / wincap -----------------------------------------------------------------
def test_last_hit_doubles_on_final_bonus_spin(gs):
    gs.in_bonus = True
    gs.free_spins_left = 0
    gs.spin_had_scatter = False
    assert gs.is_final_bonus_spin()
    gs.spin_had_scatter = True
    assert not gs.is_final_bonus_spin()


def test_award_caps_at_wincap(gs, cfg):
    gs.award(24990)
    paid = gs.award(500)
    assert paid == pytest.approx(10) and gs.wincap_triggered
    assert gs.win_manager.running_bet_win == pytest.approx(cfg.wincap)

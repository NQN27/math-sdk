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


def test_line_factor_enhance_add_wild_mul_then_global(gs):
    set_board(gs, board_with_top("H1 H1 W H1 L2 L3"))
    gs.enhance[0][0] = 2
    gs.enhance[1][0] = 3
    gs.wild_mult[(2, 0)] = 4
    gs.global_mult = 5
    (w,) = line1(gs)
    ef, wf = gs.line_factor(w)
    assert (ef, wf) == (5, 4)
    gs.wild_mult[(2, 0)] = 2
    gs.wild_mult[(1, 0)] = 5  # Q2: two Multiplier Wilds on one line multiply
    assert gs.line_factor(w)[1] == 10
    gs.wild_mult = {(2, 0): 4}
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
                d = cfg.boss_hp_offset.get(b["id"], {}).get(stage, 0)  # f17: boss3 -5 / -10
                assert lo + d <= b["hp"] <= hi + d and b["hp"] % 5 == 0
            assert [b["zone"] for b in gs.bosses] == [(0, 1), (2, 3), (4, 5)]


def test_boss_hp_offset(gs, cfg):
    old = cfg.boss_hp_offset
    try:
        cfg.boss_hp_offset = {"boss3": {1: -5, 2: -5, 3: -5, 4: -10, 5: -10}}
        random.seed(2)
        for stage in range(1, 6):
            for _ in range(40):
                gs.spawn_stage(stage)
                lo, hi = cfg.stage_hp_range[stage]
                d = cfg.boss_hp_offset["boss3"][stage]
                hp = {b["id"]: b["hp"] for b in gs.bosses}
                assert lo <= hp["boss1"] <= hi and lo <= hp["boss2"] <= hi
                assert lo + d <= hp["boss3"] <= hi + d and hp["boss3"] % 5 == 0
                assert gs.bosses[2]["hp_max"] == hp["boss3"]
    finally:
        cfg.boss_hp_offset = old


# ---- weapons -------------------------------------------------------------------
def test_bomb_area_clipped_at_corner(gs):
    set_board(gs, ["BM H1 L1 L1 L1 L1", "H2 SC L1 L1 L1 L1"] + FILLER[2:])
    t = sorted(gs._weapon_targets(0, 0, "BM"))
    assert t == [(0, 1), (1, 0)]  # (1,1) is a Scatter, not paying


def test_sword_hits_every_symbol_but_base_scatter(gs):
    set_board(gs, ["SW W AR L1 SC H2"] + FILLER[1:])
    gs.in_bonus = False
    # the Arrow at (2, 0) is another weapon: spared (designer 2026-10-21)
    assert sorted(gs._weapon_targets(0, 0, "SW")) == [(1, 0), (3, 0), (5, 0)]
    gs.in_bonus = True
    assert sorted(gs._weapon_targets(0, 0, "SW")) == [(1, 0), (3, 0), (4, 0), (5, 0)]


def test_bomb_spares_other_weapons_which_still_fire(gs):
    gs.spawn_stage(4)
    for b in gs.bosses:
        b["hp"] = b["hp_max"] = 500
    set_board(gs, ["BM AR L1 L2 L3 L4"] + FILLER[1:])
    gs.board[0][0].prize = 1
    gs.refill = lambda: []
    gs.step_weapons()
    # designer 2026-10-21: one weapon firing must not remove another; the Arrow next to the Bomb fires too
    assert any(e["type"] == "weapon" and e["weapon"] == "arrow" for e in gs.book.events)


def test_weapon_self_damage_and_arrow_last_hit(gs, cfg):
    old = (cfg.weapon_self_damage, cfg.arrow_last_hit_mult)
    try:
        cfg.weapon_self_damage = 3
        gs.spawn_stage(4)
        for b in gs.bosses:
            b["hp"] = b["hp_max"] = 500
        set_board(gs, ["L1 L2 L3 L4 L1 L2", "L3 L4 SW L2 L3 L4"] + FILLER[2:])
        gs.refill = lambda: []
        gs.step_weapons()
        # sword at (2,1) hits its row (5 cells, L=1 each): boss1 2, boss2 1+3 (own cell), boss3 2
        assert [b["hp"] for b in gs.bosses] == [498, 496, 498]
    finally:
        cfg.weapon_self_damage, cfg.arrow_last_hit_mult = old


def test_weapon_factor_is_always_1(gs, cfg):
    assert cfg.weapon_factor_weights == {1: 1}
    for name in ("BM", "SW", "LT"):
        assert gs.make_symbol(name).prize == 1


def test_weapon_factor_multiplies_damage(gs):
    gs.spawn_stage(4)
    for b in gs.bosses:
        b["hp"] = b["hp_max"] = 500
    set_board(gs, ["H3 H3 L1 L2 L3 L4", "BM H5 L1 L2 L3 L4"] + FILLER[2:])
    gs.board[0][1].prize = 4
    gs.refill = lambda: []
    gs.step_weapons()
    # bomb at (0,1) hits (0,0) H3, (1,0) H3, (1,1) H5, (0,2) L2, (1,2) L1 -> boss1, plus its own cell's damage
    assert gs.bosses[0]["hp"] == 500 - 4 * (2 + 2 + 3 + 1 + 1) - gs.config.weapon_self_damage


def test_arrow_formula_and_endless_divided_by_3(gs):
    gs.spawn_stage(5)
    b = gs.bosses[0]
    b["hp_max"] = 100
    random.seed(0)
    k = random.choice(gs.config.arrow_k_choices)
    random.seed(0)
    assert gs.arrow_damage(b) == round_half_up(3 + 100 * k)
    gs.stage = ENDLESS
    random.seed(0)
    assert gs.arrow_damage(b) == round_half_up((3 + 100 * k) / 3)


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


def test_transform_skips_wild_weapon_and_base_scatter(gs, cfg):
    set_board(gs, ["W AR SC W W W"] + ["W W W W W W"] * 3 + ["W W W W W H1"])
    random.seed(5)
    gs.in_bonus = False
    gs.power_transform()
    assert gs.board[1][0].name == "AR" and gs.board[2][0].name == "SC"
    assert gs.board[5][4].name == "W"


def test_transform_may_hit_scatter_in_bonus(gs):
    set_board(gs, ["W AR SC W W W"] + ["W W W W W W"] * 4)
    gs.in_bonus = True
    random.seed(5)
    gs.power_transform()
    assert gs.board[2][0].name == "W"


def test_destroy_keeps_wild_and_base_scatter(gs):
    gs.spawn_stage(1)
    set_board(gs, ["W SC AR H1 L1 L2"] + FILLER[1:])
    gs.in_bonus = False
    gs.power_destroy()
    assert gs.board[0][0].name == "W" and gs.board[1][0].name == "SC"
    assert gs.board[2][0] is None and gs.board[3][0] is None
    assert not gs.lit  # Destroy never lights cells
    set_board(gs, ["W SC AR H1 L1 L2"] + FILLER[1:])
    gs.in_bonus = True
    gs.power_destroy()
    assert gs.board[1][0] is None


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
    maps = [cfg.bonus_stage_reel] + list(cfg.tier_stage_reel.values())
    for stage, reel in [x for m in maps for x in m.items()]:
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
        first = [e for e in gs.book.events if e["type"] == "treasureSymbols"][0]
        assert "coin" in [c["kind"] for c in first["cells"]]
    finally:
        cfg.treasure_kind_weights.clear()
        cfg.treasure_kind_weights.update(saved)


def _seq_roller(seq):
    it = iter(seq)

    def roll(weights):
        k = next(it, "coin")
        return k if k in weights else "coin"
    return roll


def test_magnet_needs_two_coins_then_collects_and_cells_reappear(gs):
    set_board(gs, FILLER)
    gs.stage = 1
    cells = [(0, 0), (1, 0), (0, 1), (2, 0)]  # priority 1, 2, 3, 4
    gs.roll_treasure_kind = _seq_roller(["magnet", "coin", "coin", "magnet"])
    random.seed(2)
    paid = gs.run_treasure(cells, 0.2)
    fills = [e for e in gs.book.events if e["type"] == "treasureSymbols"]
    kinds = [c["kind"] for c in fills[0]["cells"]]
    assert kinds == ["coin", "coin", "coin", "magnet"]  # first magnet blocked: <2 coins yet
    mags = [e for e in gs.book.events if e["type"] == "treasureMagnet"]
    assert len(mags) == 1 and len(mags[0]["cells"]) == 3
    assert len(fills) == 2 and len(fills[1]["cells"]) == 3  # collected cells reappear
    assert paid == pytest.approx(sum(gs.board[c][r].prize for c, r in cells))


def test_star_adds_to_coins_then_becomes_a_coin(gs):
    set_board(gs, FILLER)
    gs.stage = 1
    cells = [(0, 0), (1, 0), (0, 1)]
    gs.roll_treasure_kind = _seq_roller(["coin", "coin", "star"])
    random.seed(4)
    paid = gs.run_treasure(cells, 0.2)
    star = [e for e in gs.book.events if e["type"] == "treasureStar"][0]
    first = [e for e in gs.book.events if e["type"] == "treasureSymbols"][0]["cells"]
    assert gs.board[0][1].name == "TC" and gs.board[0][1].prize == pytest.approx(star["value"])  # N3
    for c in first[:2]:
        assert gs.board[c["reel"]][c["row"] - 1].prize == pytest.approx(c["value"] + star["value"])
    assert paid == pytest.approx(sum(gs.board[c][r].prize for c, r in cells))


def test_clover_simultaneous_and_golden_whole_board(gs):
    set_board(gs, FILLER)
    gs.stage = 1
    cells = [(0, 0), (1, 0), (0, 1), (2, 0), (5, 4)]  # priority order; (5,4) is far away
    gs.roll_treasure_kind = _seq_roller(["coin", "clover", "clover", "golden", "coin"])
    random.seed(7)
    gs.run_treasure(cells, 0.2)
    ev = gs.book.events
    first = {(c["reel"], c["row"] - 1): c["value"] for c in
             [e for e in ev if e["type"] == "treasureSymbols"][0]["cells"]}
    clov = [e for e in ev if e["type"] == "treasureClover"][0]
    f1, f2 = [c["factor"] for c in clov["clovers"]]
    g = [e for e in ev if e["type"] == "treasureGoldenClover"][0]["factor"]
    assert gs.board[0][0].prize == pytest.approx(first[(0, 0)] * f1 * f2 * g)  # next to both clovers
    assert gs.board[5][4].prize == pytest.approx(first[(5, 4)] * g)  # only the golden clover
    # N10: activated clovers stay on their cells, inactive
    assert gs.board[1][0].name == "TV" and gs.board[0][1].name == "TV" and gs.board[2][0].name == "TV"
    assert len([e for e in ev if e["type"] == "treasureClover"]) == 1


def test_treasure_maxwin_check_stops(gs, cfg):
    set_board(gs, FILLER)
    gs.stage = 1
    gs.global_mult = 10
    gs.award(24000)
    gs.roll_treasure_kind = _seq_roller(["coin", "coin"])
    gs.force_wincap = True  # every coin = 25,000x
    gs.run_treasure([(0, 0), (1, 0)], 0.2)
    assert gs.wincap_triggered
    assert any(e["type"] == "treasureMaxwin" for e in gs.book.events)
    assert gs.win_manager.running_bet_win == pytest.approx(cfg.wincap)


def test_coin_labels(gs):
    assert [gs.coin_label(v) for v in (4, 5, 19, 20, 99, 100, 24999, 25000)] == \
        ["dong", "bac", "bac", "vang", "vang", "kimcuong", "kimcuong", "maxwin"]


def test_lit_rule_basic_only(gs):
    old = gs.config.lit_rule
    try:
        gs.config.lit_rule = "symbols"  # f17 uses "lines" (test_lit_rule_lines)
        gs.spawn_stage(1)
        set_board(gs, board_with_top("H2 H2 W H2 L1 L2"))
        gs.refill = lambda: []
        gs.step_connect()
        assert (2, 0) not in gs.lit  # connected Wild: destroyed but not lit
        assert (0, 0) in gs.lit and (1, 0) in gs.lit
    finally:
        gs.config.lit_rule = old


def test_lit_rule_lines(gs, cfg):
    """lit_rule "lines": only winning-line cells (Wild included) and fired weapons light; other copies of
    the connected symbol and cells hit by a weapon do not."""
    old = cfg.lit_rule
    try:
        cfg.lit_rule = "lines"
        gs.spawn_stage(1)
        rows = board_with_top("H2 H2 W H2 L1 L2")
        rows[4] = "L1 L2 L3 L4 L1 H2"  # a stray H2, in no winning line
        set_board(gs, rows)
        gs.lit = set()
        gs.refill = lambda: []
        gs.step_connect()
        wins_cells = {(0, 0), (1, 0), (2, 0), (3, 0)}
        assert wins_cells <= gs.lit
        assert (5, 4) not in gs.lit  # destroyed as a copy of H2, but not in the line
        assert gs.board[5][4] is None
        for b in gs.bosses:
            b["hp"] = b["hp_max"] = 500
        set_board(gs, ["H3 H3 L1 L2 L3 L4", "BM H5 L1 L2 L3 L4"] + FILLER[2:])
        gs.lit = set()
        gs.step_weapons()
        assert gs.lit == {(0, 1)}  # the bomb's own cell lights, the cells it destroys do not
    finally:
        cfg.lit_rule = old


def test_weapon_allowed_rules(gs):
    gs.spawn_stage(1)
    gs.bosses[2]["alive"] = False  # boss 3 dead -> no Arrow in columns 5-6
    assert gs.weapon_allowed("AR", 0) and not gs.weapon_allowed("AR", 5)
    assert gs.weapon_allowed("BM", 5)
    for b in gs.bosses:
        b["alive"] = False
    assert not gs.weapon_allowed("BM", 0) and not gs.weapon_allowed("AR", 0)


def test_epic_free_spin_coins_have_no_dong(gs):
    gs.in_bonus, gs.bonus_tier, gs.epic_opening = True, "epic", False
    random.seed(1)
    assert min(gs.draw_coin(0.2) for _ in range(500)) >= 5
    gs.epic_opening = True
    assert min(gs.draw_coin(0.2) for _ in range(500)) < 5


def test_chest_power_share_rises_with_tier(cfg):
    p = cfg.chest_gift_power_chance
    assert p["dong"] < p["bac"] < p["vang"] < p["kimcuong"]


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


# ---- Treasure hunt coin minimum (designer 2026-10-08: coins >= 1x) -------------
def test_treasure_hunt_min_coin_only_outside_bonus(gs, cfg):
    gs.treasure_hunt = True
    gs.stage = None
    assert gs.current_min_coin() == cfg.treasure_hunt_min_coin == 1
    gs.in_bonus, gs.stage = True, 5  # a Bonus entered from Treasure hunt keeps stage minimums
    assert gs.current_min_coin() == cfg.stage_min_coin[5]



# ---- Per-tier stage coin minimum (designer 2026-10-17, Super trial) --------------
def test_tier_stage_min_coin_overrides_one_tier(gs, cfg):
    old = cfg.tier_stage_min_coin
    try:
        cfg.tier_stage_min_coin = {"super": {2: 0.2}}
        gs.treasure_hunt, gs.in_bonus, gs.stage = False, True, 2
        gs.bonus_tier = "super"
        assert gs.current_min_coin() == 0.2
        gs.stage = 3  # other stages keep the proposal minimum
        assert gs.current_min_coin() == cfg.stage_min_coin[3]
        gs.bonus_tier, gs.stage = "bonus", 2  # other tiers keep it too
        assert gs.current_min_coin() == cfg.stage_min_coin[2] == 1
    finally:
        cfg.tier_stage_min_coin = old

def test_wild_skin_is_display_only(gs, cfg):
    """Display-only Wilds sit on cells of already-winning lines and change no outcome (with wild_skin_damage
    None; f17 gives them Wild damage 3, which changes boss damage on purpose)."""
    old = cfg.wild_skin_chance
    old_dmg = cfg.wild_skin_damage
    cfg.wild_skin_damage = None
    try:
        res, skins = {}, 0
        for ch in (0.0, 0.6):
            cfg.wild_skin_chance = ch
            out = []
            for i in range(15):
                random.seed(700 + i)
                gs.betmode, gs.criteria = "buy3", "freegame"
                gs.reset_book()
                gs.run_bonus("bonus", {(0, 1), (2, 2), (4, 3)})
                out.append(gs.win_manager.running_bet_win)
                if ch:
                    ev = gs.book.events
                    for k, e in enumerate(ev):
                        if e["type"] == "wildSkin":
                            skins += len(e["cells"])
                            nxt = next(x for x in ev[k + 1:] if x["type"] == "lineWins")
                            won = {(p["reel"], p["row"]) for w in nxt["wins"] for p in w["positions"]}
                            assert all((c["reel"], c["row"]) in won for c in e["cells"])
            res[ch] = out
        assert res[0.0] == res[0.6] and skins > 0
    finally:
        cfg.wild_skin_chance = old
        cfg.wild_skin_damage = old_dmg


def test_heroic_dead_spin_pays_zero(gs, cfg):
    saved = (cfg.heroic_dead_spin_chance, cfg.feature_heroic_chance)
    try:
        cfg.heroic_dead_spin_chance, cfg.feature_heroic_chance = 1.0, 1.0
        gs.betmode, gs.criteria = "feature", "basegame"
        left = 0
        for i in range(40):
            random.seed(900 + i)
            gs.reset_book()
            gs.run_feature_spin(gs.get_current_distribution_conditions())
            assert gs.win_manager.running_bet_win == 0
            reveal = next(e for e in gs.book.events if e["type"] == "reveal")
            wilds = [(c, r) for c in range(6) for r in range(5) if gs.board[c][r] is not None and gs.board[c][r].name == "W"]
            assert len(wilds) == cfg.heroic_min_wild_or_weapon
            left += any(c < 3 for c, _ in wilds)
            assert not any(gs.is_weapon(gs.board[c][r]) for c in range(6) for r in range(5))
            assert not any(e["type"] in ("lineWins", "weapon", "wildEvent", "wildEvents", "chestOpened") for e in gs.book.events)
        assert left > 0  # Wilds also land in columns 1-3
    finally:
        cfg.heroic_dead_spin_chance, cfg.feature_heroic_chance = saved


def test_heroic_dead_spin_natural_wilds(gs, cfg):
    """Keeping a Wild placement for many symbol redraws and weighting the left columns still builds
    0-pay boards with exactly the guaranteed Wilds, and puts plenty of them in columns 1-3."""
    saved = (cfg.heroic_dead_spin_chance, cfg.feature_heroic_chance, cfg.heroic_dead_symbol_tries,
             cfg.heroic_dead_wild_col_weights)
    try:
        cfg.heroic_dead_spin_chance, cfg.feature_heroic_chance = 1.0, 1.0
        cfg.heroic_dead_symbol_tries, cfg.heroic_dead_wild_col_weights = 20, [3, 3, 3, 1, 1, 1]
        gs.betmode, gs.criteria = "feature", "basegame"
        cols = [0] * 6
        for i in range(30):
            random.seed(1900 + i)
            gs.reset_book()
            gs.run_feature_spin(gs.get_current_distribution_conditions())
            assert gs.win_manager.running_bet_win == 0
            wilds = [(c, r) for c in range(6) for r in range(5) if gs.board[c][r] is not None and gs.board[c][r].name == "W"]
            assert len(wilds) == cfg.heroic_min_wild_or_weapon
            for c, _ in wilds:
                cols[c] += 1
        assert sum(cols[:3]) > 0.35 * sum(cols)
    finally:
        (cfg.heroic_dead_spin_chance, cfg.feature_heroic_chance, cfg.heroic_dead_symbol_tries,
         cfg.heroic_dead_wild_col_weights) = saved


def test_heroic_wild_events_fire_together(gs, cfg):
    saved = (cfg.feature_heroic_chance, cfg.heroic_dead_spin_chance)
    try:
        cfg.feature_heroic_chance, cfg.heroic_dead_spin_chance = 1.0, 0.0
        gs.betmode, gs.criteria = "feature", "basegame"
        grouped = 0
        for i in range(20):
            random.seed(3900 + i)
            gs.reset_book()
            gs.run_feature_spin(gs.get_current_distribution_conditions())
            assert not any(e["type"] == "wildEvent" for e in gs.book.events)  # never one by one in Heroic
            for e in gs.book.events:
                if e["type"] == "wildEvents":
                    grouped += 1
                    assert e["wilds"] and all(w["event"] in ("multiplier", "coin", "power") for w in e["wilds"])
        assert grouped > 0
    finally:
        cfg.feature_heroic_chance, cfg.heroic_dead_spin_chance = saved


def test_no_display_wilds_in_heroic(gs, cfg):
    saved = (cfg.wild_skin_chance, cfg.feature_heroic_chance, cfg.heroic_dead_spin_chance)
    try:
        cfg.wild_skin_chance, cfg.feature_heroic_chance, cfg.heroic_dead_spin_chance = 1.0, 1.0, 0.0
        gs.betmode, gs.criteria = "feature", "basegame"
        for i in range(30):
            random.seed(2900 + i)
            gs.reset_book()
            gs.run_feature_spin(gs.get_current_distribution_conditions())
            assert not any(e["type"] == "wildSkin" for e in gs.book.events)
    finally:
        cfg.wild_skin_chance, cfg.feature_heroic_chance, cfg.heroic_dead_spin_chance = saved


def test_treasure_round_kind_mult_holds_clover_back(gs, cfg):
    old = cfg.treasure_round_kind_mult
    try:
        cfg.treasure_round_kind_mult = {"clover": [0, 1], "golden": [0, 1]}
        gs.betmode, gs.criteria = "feature", "basegame"
        saved = cfg.feature_heroic_chance
        cfg.feature_heroic_chance = 0.0
        for i in range(40):
            random.seed(4900 + i)
            gs.reset_book()
            gs.run_feature_spin(gs.get_current_distribution_conditions())
            first = next(e for e in gs.book.events if e["type"] == "treasureSymbols")
            assert not any(c["kind"] in ("clover", "golden") for c in first["cells"])
        cfg.feature_heroic_chance = saved
    finally:
        cfg.treasure_round_kind_mult = old


def test_treasure_clover_vanishes_and_cell_refills(gs, cfg):
    old = cfg.treasure_clover_vanishes
    saved = cfg.feature_heroic_chance
    try:
        cfg.treasure_clover_vanishes, cfg.feature_heroic_chance = True, 0.0
        gs.betmode, gs.criteria = "feature", "basegame"
        refilled = 0
        for i in range(300):
            random.seed(5900 + i)
            gs.reset_book()
            gs.run_feature_spin(gs.get_current_distribution_conditions())
            gone = set()
            for e in gs.book.events:
                if e["type"] == "treasureClover":
                    gone |= {(c["reel"], c["row"]) for c in e["clovers"]}
                elif e["type"] == "treasureGoldenClover":
                    gone.add((e["position"]["reel"], e["position"]["row"]))
                elif e["type"] == "treasureSymbols":
                    refilled += len(gone & {(c["reel"], c["row"]) for c in e["cells"]})
                elif e["type"] == "treasureEnd":
                    break
        assert refilled > 0  # an activated Clover's cell gets a new symbol in the next round
    finally:
        cfg.treasure_clover_vanishes, cfg.feature_heroic_chance = old, saved


def test_heroic_line_mult(gs, cfg):
    old = cfg.heroic_line_mult_weights
    saved = cfg.feature_heroic_chance
    try:
        cfg.heroic_line_mult_weights = {7: 1}
        cfg.feature_heroic_chance = 1.0
        gs.betmode, gs.criteria = "feature", "basegame"
        seen = 0
        for i in range(20):
            random.seed(500 + i)
            gs.reset_book()
            gs.run_feature_spin(gs.get_current_distribution_conditions())
            ev = gs.book.events
            assert any(e["type"] == "heroicLineMult" and e["mult"] == 7 for e in ev)
            for e in ev:
                if e["type"] == "lineWins":
                    for w in e["wins"]:
                        assert w["lineMult"] == 7
                        assert abs(w["win"] - round(w["base"] * w["enhance"] * w["wildMult"] * w["globalMult"] * 7, 4)) < 1e-6
                        seen += 1
        assert seen > 0
        gs.reset_book()
        assert gs.line_mult == 1  # off again for the next book
    finally:
        cfg.heroic_line_mult_weights = old
        cfg.feature_heroic_chance = saved


def test_transform_wilds_fire_rarely_in_bonus(gs, cfg):
    """Designer 2026-10-22: in a Bonus a Wild made by the Transform power fires an event only with
    power_wild_event_chance; ordinary Wilds keep wild_event_chance."""
    saved = (cfg.power_wild_event_chance, cfg.wild_event_chance)
    try:
        cfg.power_wild_event_chance, cfg.wild_event_chance = 0.0, 1.0
        gs.in_bonus, gs.heroic, gs.bonus_tier = True, False, "bonus"
        gs.spawn_stage(3)
        gs.begin_spin()
        set_board(gs, ["W W W L1 L2 L3"] + FILLER[1:])
        wins = gs.evaluate_lines()
        gs.power_wilds = {(0, 0)}
        n0 = len(gs.book.events)
        gs.wild_events(wins)
        fired = [e["position"] for e in gs.book.events[n0:] if e["type"] == "wildEvent"]
        assert fired and all(not (p["reel"] == 0 and p["row"] == 1) for p in fired)  # (0,0) = the Transform Wild
        gs.in_bonus = False  # outside a Bonus the Transform Wild fires like any Wild
        n0 = len(gs.book.events)
        gs.wild_events(wins)
        assert any(e["type"] == "wildEvent" and e["position"]["reel"] == 0 for e in gs.book.events[n0:])
    finally:
        cfg.power_wild_event_chance, cfg.wild_event_chance = saved


def test_lit_reset_after_treasure(gs, cfg):
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tuning"))
    import tune_harness as H
    saved = cfg.lit_reset_after_treasure_tiers
    try:
        cfg.lit_reset_after_treasure_tiers = ("bonus",)
        seen = 0
        for i in range(40):
            H._one(gs, cfg, "bonus", i)
            ev = gs.book.events
            for k, e in enumerate(ev):
                if e["type"] == "treasureEnd" and k + 1 < len(ev) and ev[k + 1]["type"] == "litReset":
                    seen += 1
            if not gs.wincap_triggered:  # one reset per stage clear (Treasure ran, even on no lit cells)
                assert sum(e["type"] == "litReset" for e in ev) == sum(
                    1 for e in ev if e["type"] == "spinEnd" and e["stageCleared"])
        assert seen > 0
    finally:
        cfg.lit_reset_after_treasure_tiers = saved


def test_treasure_hunt_spin_coins_at_least_1x(gs, cfg):
    saved = cfg.feature_heroic_chance
    cfg.feature_heroic_chance = 0.0
    try:
        gs.betmode, gs.criteria = "feature", "basegame"
        seen = 0
        for i in range(30):
            random.seed(100 + i)
            gs.reset_book()
            gs.run_feature_spin(gs.get_current_distribution_conditions())
            for e in gs.book.events:
                if e["type"] == "bonusStart":
                    break
                if e["type"] == "treasureSymbols":
                    for c in e["cells"]:
                        if c["kind"] in ("coin", "star"):
                            assert c["value"] >= 1
                            seen += 1
        assert seen > 0
    finally:
        cfg.feature_heroic_chance = saved


def test_bonus_min_total_win_topup(gs, cfg):
    saved = dict(cfg.bonus_min_total_win)
    cfg.bonus_min_total_win["bonus"] = 5000.0
    try:
        gs.betmode, gs.criteria = "buy3", "freegame"
        for i in range(5):
            random.seed(200 + i)
            gs.reset_book()
            gs.run_bonus("bonus", {(0, 0), (1, 0), (2, 0)})
            top = [e for e in gs.book.events if e["type"] == "bonusMinWin"]
            won = gs.win_manager.freegame_wins
            assert gs.wincap_triggered or won >= 5000.0 - 1e-9
            if top:  # topped up exactly to the floor
                assert won == pytest.approx(5000.0) and top[0]["topUp"] > 0
    finally:
        cfg.bonus_min_total_win.clear()
        cfg.bonus_min_total_win.update(saved)


# ---- Treasure Star value table (tuning flag, 2026-10-17) -------------------------
def test_star_value_weights_own_table_and_fallback(gs, cfg):
    old = cfg.star_value_weights
    try:
        cfg.star_value_weights = {2: 1}
        gs.treasure_hunt, gs.in_bonus, gs.bonus_tier, gs.stage = False, False, None, 1
        assert gs._treasure_cell("star", 1).prize == 2
        assert gs._treasure_cell("star", 5).prize >= 5  # nothing >= 5 in the own table: coin table
        assert gs._treasure_cell("coin", 1).prize in cfg.coin_value_weights  # coins unaffected
    finally:
        cfg.star_value_weights = old

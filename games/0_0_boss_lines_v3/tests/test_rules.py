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


def test_tier_hp_tilt(gs, cfg):
    """The HP range is the same for every tier; tier_hp_tilt only changes how often each value comes up."""
    old = cfg.tier_hp_tilt
    try:
        cfg.tier_hp_tilt = {"super": 1.0, "bonus": -1.0}
        lo, hi = cfg.stage_hp_range[4]
        gs.in_bonus = True
        avg = {}
        for tier in ("super", "bonus"):
            gs.bonus_tier = tier
            random.seed(6)
            hps = []
            for _ in range(300):
                gs.spawn_stage(4)
                b = gs.bosses[0]
                d = cfg.boss_hp_offset.get("boss1", {}).get(4, 0)
                assert lo + d <= b["hp"] <= hi + d and b["hp"] % 5 == 0
                hps.append(b["hp"] - d)
            avg[tier] = sum(hps) / len(hps)
        assert avg["super"] > (lo + hi) / 2 + 3 and avg["bonus"] < (lo + hi) / 2 - 3
    finally:
        cfg.tier_hp_tilt = old
        gs.in_bonus, gs.bonus_tier = False, None


def test_hp_cut_weights(gs, cfg):
    """The HP cut is a per-boss draw (no cut stays possible); only its odds differ per tier."""
    old = dict(cfg.tier_weights)
    try:
        cfg.tier_weights = {**old, "super": {**old.get("super", {}), "hp_cut_weights": {0: 1, 10: 3}}}
        gs.in_bonus, gs.bonus_tier = True, "super"
        lo, hi = cfg.stage_hp_range[2]
        random.seed(3)
        cuts = set()
        for _ in range(200):
            gs.spawn_stage(2)
            b = gs.bosses[0]
            assert lo - 10 <= b["hp"] <= hi and b["hp"] % 5 == 0
            cuts.add(b["hp"] < lo)
        assert cuts == {True, False}
        gs.spawn_stage(0)
        assert all(b["hp"] == cfg.stage_hp_range[0][0] for b in gs.bosses)
    finally:
        cfg.tier_weights = old
        gs.in_bonus, gs.bonus_tier = False, None


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


def test_chest_coin_min_stage(gs, cfg):
    """chest_coin_min = "stage": a gold chest's coins only respect the stage minimum, not the gold tier floor."""
    old = cfg.chest_coin_min
    try:
        cfg.chest_coin_min = "stage"
        gs.in_bonus, gs.bonus_tier, gs.stage = True, "bonus", 2
        floor = gs.current_min_coin()
        random.seed(5)
        vals = []
        for _ in range(300):
            gs.reserve = {p: cfg.power_reserve_cap for p in cfg.power_names}  # no room -> every gift is a coin
            gs.book.events.clear()
            gs.open_chest({"id": "boss1", "chest": "vang", "chest_opened": False})
            vals += [g["value"] for g in gs.book.events[-1]["gifts"] if g["kind"] == "coin"]
            gs.win_manager.reset_end_round_wins()
            gs.wincap_triggered = False
        assert vals and min(vals) >= floor and min(vals) < cfg.coin_tiers["vang"][0]
    finally:
        cfg.chest_coin_min = old
        gs.in_bonus, gs.bonus_tier = False, None


def test_stage_chest_weights(gs, cfg):
    """Per tier + stage chest odds; the stage minimum chest still holds."""
    old = cfg.stage_chest_weights
    try:
        cfg.stage_chest_weights = {"bonus": {2: {"dong": 1, "vang": 1}, 3: {"dong": 5, "bac": 1}}}
        gs.in_bonus, gs.bonus_tier = True, "bonus"
        random.seed(2)
        seen2 = {gs._roll_chest(2) for _ in range(200)}
        seen3 = {gs._roll_chest(3) for _ in range(200)}
        assert seen2 == {"dong", "vang"} and seen3 == {"bac"}
        gs.bonus_tier = "super"  # no own table -> step weights from the stage minimum
        assert all(cfg.chest_order.index(gs._roll_chest(3)) >= 1 for _ in range(100))
    finally:
        cfg.stage_chest_weights = old
        gs.in_bonus, gs.bonus_tier = False, None


def test_stage_min_chest_count(gs, cfg):
    """stage_min_chest_count = 1: exactly one boss per stage is sure to get the stage minimum chest."""
    old = cfg.stage_min_chest_count
    try:
        cfg.stage_min_chest_count = 1
        random.seed(4)
        low = 0
        for _ in range(200):
            gs.spawn_stage(4)
            idx = [cfg.chest_order.index(b["chest"]) for b in gs.bosses]
            assert max(idx) >= cfg.chest_order.index("vang")
            low += sum(i < cfg.chest_order.index("vang") for i in idx)
        assert low > 200
    finally:
        cfg.stage_min_chest_count = old


def test_tumble_multi(gs, cfg):
    """Tumble mode (designer 2026-10-30): connecting Wild multis add up, boss multis from chests multiply the sum,
    and the spin's line pay x that multi is paid at spin end; no old Global; per-tier reset scope."""
    old = (cfg.tumble_multi, dict(cfg.tier_weights), cfg.chest_gift_multi_chance, cfg.chest_upgrade_chance)
    try:
        cfg.tumble_multi = True
        cfg.tier_weights = {**old[1], "bonus": {**old[1].get("bonus", {}), "wild_multi_weights": {3: 1},
                                                "wild_power_drop_chance": 0.0, "tumble_reset_scope": "spin"}}
        gs.in_bonus, gs.bonus_tier = True, "bonus"
        gs.global_mult = 4
        assert gs.global_factor() == 1  # the old Global no longer multiplies anything
        gs.spawn_stage(1)
        gs.begin_spin()
        gs.refill = lambda: []
        rows = board_with_top("H2 H2 W H2 L1 L2")
        set_board(gs, rows)
        gs.board[2][0] = gs.make_symbol("W")  # a 3x Multi Wild
        gs.book.events.clear()
        gs.step_connect()
        base = gs.tumble_base
        assert base > 0 and gs.tumble_wild == 3 and gs.win_manager.spin_win == 0  # nothing paid yet
        gs.tumble_boss = [2, 5]  # two boss multis multiply, left to right
        gs.settle_tumble()
        ev = [e for e in gs.book.events if e["type"] == "tumbleWin"][-1]
        assert ev["multi"] == 30 and abs(ev["paid"] - round(base * 30, 4)) < 1e-6
        gs.begin_spin()  # Normal: resets every spin
        assert gs.tumble_wild == 0 and gs.tumble_boss == []
        # chest boss multis respect the chest cap (bronze <= 3x)
        cfg.chest_gift_multi_chance = {"dong": 1.0, "bac": 1.0, "vang": 1.0}
        cfg.chest_upgrade_chance = 0.0
        random.seed(12)
        for _ in range(100):
            gs.tumble_boss = []
            gs.reserve = {p: 0 for p in cfg.power_names}
            gs.book.events.clear()
            gs.open_chest({"id": "boss1", "chest": "dong", "chest_opened": False})
            assert all(m <= 3 for m in gs.tumble_boss)
            gs.win_manager.reset_end_round_wins()
            gs.wincap_triggered = False
        # chest coins join the spin's pay and wait for the tumble multi
        cfg.chest_gift_multi_chance = {}
        gs.tumble_base = 0.0
        gs.reserve = {p: cfg.power_reserve_cap for p in cfg.power_names}  # no power room -> coins
        gs.book.events.clear()
        gs.open_chest({"id": "boss1", "chest": "bac", "chest_opened": False})
        assert gs.tumble_base > 0 and gs.win_manager.spin_win == 0
    finally:
        cfg.tumble_multi, cfg.tier_weights, cfg.chest_gift_multi_chance, cfg.chest_upgrade_chance = old
        gs.in_bonus, gs.bonus_tier = False, None
        gs.global_mult = 0
        gs.tumble_wild, gs.tumble_boss, gs.tumble_base = 0, [], 0.0
        del gs.refill


def test_money_bags_flash_wild_chest_names(gs, cfg):
    """Designer 2026-10-31: chest coins are money bags (>= 1x, named pinch/small/large/chest); a flashing Wild
    always gives a power when it connects, other Wilds none; chests show as green/blue/purple in events."""
    old = (cfg.chest_bags, cfg.chest_display_names, dict(cfg.tier_weights), cfg.chest_upgrade_chance, cfg.tumble_multi)
    try:
        cfg.chest_bags, cfg.tumble_multi = True, False
        cfg.chest_display_names = {"dong": "green", "bac": "blue", "vang": "purple"}
        cfg.chest_upgrade_chance = 0.0
        gs.in_bonus, gs.bonus_tier, gs.stage = True, "bonus", 1
        random.seed(21)
        kinds = set()
        for _ in range(300):
            gs.reserve = {p: cfg.power_reserve_cap for p in cfg.power_names}  # no power room -> bags
            gs.book.events.clear()
            gs.open_chest({"id": "boss1", "chest": "bac", "chest_opened": False})
            ev = gs.book.events[-1]
            assert ev["chest"] == "blue"
            for g in ev["gifts"]:
                assert g["kind"] == "bag" and g["value"] >= 1
                assert g["bag"] == gs.bag_kind(g["value"])
                kinds.add(g["bag"])
            gs.win_manager.reset_end_round_wins()
            gs.wincap_triggered = False
        assert {"pinch", "small"} <= kinds
        assert gs.bag_kind(4) == "pinch" and gs.bag_kind(5) == "small" and gs.bag_kind(50) == "large" and gs.bag_kind(100) == "chest"
        # flashing Wild
        cfg.tier_weights = {**old[2], "bonus": {**old[2].get("bonus", {}), "wild_multi_weights": {1: 1},
                                                "wild_power_drop_chance": 0.0, "wild_flash_chance": 1.0}}
        w = gs.make_symbol("W")
        assert getattr(w, "flash", False)
        gs.spawn_stage(1)
        gs.refill = lambda: []
        gs.reserve = {p: 0 for p in cfg.power_names}
        set_board(gs, board_with_top("H2 H2 W H2 L1 L2"))
        gs.board[2][0] = w
        gs.book.events.clear()
        gs.step_connect()
        assert sum(gs.reserve.values()) == 1
        cfg.tier_weights = {**old[2], "bonus": {**old[2].get("bonus", {}), "wild_multi_weights": {1: 1},
                                                "wild_power_drop_chance": 0.0, "wild_flash_chance": 0.0}}
        gs.reserve = {p: 0 for p in cfg.power_names}
        set_board(gs, board_with_top("H2 H2 W H2 L1 L2"))
        gs.board[2][0] = gs.make_symbol("W")
        gs.step_connect()
        assert sum(gs.reserve.values()) == 0  # a Wild that does not flash gives no power
        gs.win_manager.reset_end_round_wins()
    finally:
        cfg.chest_bags, cfg.chest_display_names, cfg.tier_weights, cfg.chest_upgrade_chance, cfg.tumble_multi = old
        gs.in_bonus, gs.bonus_tier = False, None
        gs.wincap_triggered = False
        if "refill" in gs.__dict__:
            del gs.refill


def test_multi_wild(gs, cfg):
    """Multi Wild mode: a Wild carries its multiplier from creation; connecting multiplies its line, no coin event."""
    old = dict(cfg.tier_weights)
    try:
        cfg.tier_weights = {**old, "bonus": {**old.get("bonus", {}), "wild_multi_weights": {3: 1},
                                             "wild_power_drop_chance": 0.0}}
        gs.in_bonus, gs.bonus_tier = True, "bonus"
        w = gs.make_symbol("W")
        assert w.prize == 3
        gs.spawn_stage(1)
        gs.refill = lambda: []
        set_board(gs, board_with_top("H2 H2 W H2 L1 L2"))
        gs.board[2][0] = w
        gs.book.events.clear()
        gs.step_connect()
        ev = [e for e in gs.book.events if e["type"] == "wildEvent"]
        assert ev and all(e["event"] == "multiplier" and e["factor"] == 3 for e in ev)
        lw = [e for e in gs.book.events if e["type"] == "lineWins"][0]
        assert any(x["wildMult"] == 3 for x in lw["wins"])
        gs.win_manager.reset_end_round_wins()
    finally:
        cfg.tier_weights = old
        gs.in_bonus, gs.bonus_tier = False, None
        del gs.refill


def test_wild_lit_bias(gs, cfg):
    """wild_lit_bias = 1: a Wild on an unlit cell moves to a lit basic cell of its column (Bonus only)."""
    old = cfg.wild_lit_bias
    try:
        cfg.wild_lit_bias = 1.0
        gs.in_bonus, gs.bonus_tier = True, "bonus"
        gs.board = [[gs.make_symbol("L1") for _ in range(5)] for _ in range(6)]
        gs.board[1][4] = gs.make_symbol("W")
        gs.lit = {(1, 2)}
        gs.steer_weapons_to_lit()
        assert gs.board[1][2].name == "W" and gs.board[1][4].name == "L1"
    finally:
        cfg.wild_lit_bias = old
        gs.in_bonus, gs.bonus_tier = False, None


def test_lit_wild_lines_only(gs, cfg):
    """lit_wild_lines_only: a winning line without a Wild lights nothing; a line with a Wild lights as before."""
    old = (cfg.lit_rule, cfg.lit_wild_lines_only)
    try:
        cfg.lit_rule, cfg.lit_wild_lines_only = "lines", True
        gs.spawn_stage(1)
        gs.skin_cells = set()
        gs.refill = lambda: []
        set_board(gs, board_with_top("H2 H2 H2 H2 L1 L2"))
        gs.lit = set()
        gs.step_connect()
        assert gs.lit == set()
        set_board(gs, board_with_top("H2 H2 W H2 L1 L2"))
        gs.step_connect()
        assert {(0, 0), (1, 0), (2, 0), (3, 0)} <= gs.lit
        # a display Wild counts by default, not with "real"
        for mode, lights in ((True, True), ("real", False)):
            cfg.lit_wild_lines_only = mode
            set_board(gs, board_with_top("H2 H2 H2 H2 L1 L2"))
            gs.skin_cells = {(2, 0)}
            gs.lit = set()
            gs.step_connect()
            assert bool(gs.lit) == lights
        gs.skin_cells = set()
    finally:
        cfg.lit_rule, cfg.lit_wild_lines_only = old
        del gs.refill


def test_weapon_lit_bias(gs, cfg):
    """weapon_lit_bias = 1: a weapon on an unlit cell moves to a lit basic cell of its own column."""
    old = cfg.weapon_lit_bias
    try:
        cfg.weapon_lit_bias = 1.0
        gs.in_bonus, gs.bonus_tier = True, "bonus"
        gs.board = [[gs.make_symbol("L1") for _ in range(5)] for _ in range(6)]
        gs.board[2][0] = gs.make_symbol("BM")
        gs.lit = {(2, 3), (4, 0)}
        gs.steer_weapons_to_lit()
        assert gs.board[2][3].name == "BM" and gs.board[2][0].name == "L1"
        gs.board[2][3], gs.board[2][0] = gs.make_symbol("L1"), gs.make_symbol("SW")
        gs.lit = {(4, 0)}  # nothing lit in column 2 -> stays
        gs.steer_weapons_to_lit()
        assert gs.board[2][0].name == "SW"
        cfg.weapon_lit_bias = 0
        gs.lit = {(2, 3)}
        gs.steer_weapons_to_lit()
        assert gs.board[2][0].name == "SW"
    finally:
        cfg.weapon_lit_bias = old
        gs.in_bonus, gs.bonus_tier = False, None


def test_chest_rules_2026_10_29(gs, cfg):
    """Designer 2026-10-29: only diamond chests are sure to hold a coin, and only that coin keeps the tier floor
    ("sure_only"); a chest power is always one with nothing in reserve, otherwise the gift is a coin."""
    old = (cfg.chest_sure_coin_tiers, cfg.chest_coin_min, cfg.chest_power_new_only, cfg.chest_upgrade_chance,
           cfg.chest_gift_power_chance)
    try:
        cfg.chest_sure_coin_tiers, cfg.chest_coin_min, cfg.chest_power_new_only = ["kimcuong"], "sure_only", True
        cfg.chest_upgrade_chance = 0.0
        cfg.chest_gift_power_chance = {"dong": 1.0, "bac": 1.0, "vang": 1.0, "kimcuong": 1.0}
        gs.in_bonus, gs.bonus_tier, gs.stage = True, "super", 3
        random.seed(8)
        for tier in ("vang", "kimcuong"):
            gs.reserve = {p: 0 for p in cfg.power_names}
            gs.book.events.clear()
            gs.open_chest({"id": "boss1", "chest": tier, "chest_opened": False})
            gifts = gs.book.events[-1]["gifts"]
            coins = [g for g in gifts if g["kind"] == "coin"]
            if tier == "vang":
                assert not coins  # gold may be all powers now
            else:
                assert len(coins) == 1 and coins[0]["value"] >= cfg.coin_tiers["kimcuong"][0]
            powers = [g["power"] for g in gifts if g["kind"] == "power"]
            assert len(powers) == len(set(powers))  # never a power already in reserve
            gs.win_manager.reset_end_round_wins()
        gs.reserve = {p: 1 for p in cfg.power_names}  # every power stored -> coins only
        gs.book.events.clear()
        gs.open_chest({"id": "boss1", "chest": "bac", "chest_opened": False})
        gifts = gs.book.events[-1]["gifts"]
        assert gifts and all(g["kind"] == "coin" for g in gifts)
        assert all(g["value"] >= gs.current_min_coin() for g in gifts)
        gs.win_manager.reset_end_round_wins()
    finally:
        (cfg.chest_sure_coin_tiers, cfg.chest_coin_min, cfg.chest_power_new_only, cfg.chest_upgrade_chance,
         cfg.chest_gift_power_chance) = old
        gs.in_bonus, gs.bonus_tier = False, None
        gs.wincap_triggered = False


def test_chest_upgrade_tier_weights(gs, cfg):
    old = (cfg.chest_upgrade_chance, cfg.chest_upgrade_tier_weights)
    try:
        cfg.chest_upgrade_chance, cfg.chest_upgrade_tier_weights = 1.0, {"bac": 1, "vang": 0, "kimcuong": 0}
        random.seed(9)
        for _ in range(50):
            gs.book.events.clear()
            gs.open_chest({"id": "boss1", "chest": "dong", "chest_opened": False})
            assert gs.book.events[-1]["upgradedTo"] == "bac"
            gs.win_manager.reset_end_round_wins()
            gs.wincap_triggered = False
    finally:
        cfg.chest_upgrade_chance, cfg.chest_upgrade_tier_weights = old


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

def test_wild_skins_only_on_opening_board(gs, cfg):
    """Designer 2026-10-25: display-only Wilds appear at the start of a spin only, never after a refill."""
    old = cfg.wild_skin_chance
    try:
        cfg.wild_skin_chance = 1.0
        seen = 0
        for i in range(15):
            random.seed(800 + i)
            gs.betmode, gs.criteria = "buy3", "freegame"
            gs.reset_book()
            gs.run_bonus("bonus", {(0, 1), (2, 2), (4, 3)})
            ev = gs.book.events
            for k, e in enumerate(ev):
                if e["type"] == "wildSkin":
                    seen += 1
                    assert ev[k - 1]["type"] == "reveal"  # right after the opening board, never after "refill"
        assert seen > 0
    finally:
        cfg.wild_skin_chance = old


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


# ---- Unified rules 1-7 ("LUAT HOP NHAT", designer 2026-11-02) ----------------------------------------------
def test_v4_hp_explicit_values(gs, cfg):
    """Rule 3: a stage HP spec with more than 2 values is the exact list (stage 5: 90/95/100/110/120)."""
    old = cfg.stage_hp_range
    try:
        cfg.stage_hp_range = {**old, 0: (10, 20), 5: [90, 95, 100, 110, 120]}
        random.seed(3)
        seen0, seen5 = set(), set()
        for _ in range(300):
            seen0.add(gs._roll_hp(cfg.stage_hp_range[0]))
            seen5.add(gs._roll_hp(cfg.stage_hp_range[5]))
        assert seen0 == {10, 15, 20} and seen5 == {90, 95, 100, 110, 120}
    finally:
        cfg.stage_hp_range = old


def test_v4_chest_sets_and_open(gs, cfg):
    """Rule 3: fixed chest set per stage (Heroic 3 red); one bag of the chest's own kind; at most one upgrade
    (never from red); power and chest multi come independently with the bag; multi capped per chest."""
    old = (cfg.chest_rule, cfg.chest_open_upgrade_chance, cfg.chest_gift_power_chance, cfg.chest_gift_multi_chance,
           cfg.tumble_multi)
    try:
        cfg.chest_rule, cfg.tumble_multi = "v4", True
        random.seed(5)
        for stage, want in cfg.stage_chest_sets.items():
            if stage == "heroic":
                continue
            gs.spawn_stage(stage)
            got = sorted(b["chest"] for b in gs.bosses)
            assert got == sorted(want[:len(got)]) if stage != ENDLESS else got[0] in want
        gs.heroic = True
        gs.spawn_stage(5)
        assert [b["chest"] for b in gs.bosses] == ["do"] * 3
        gs.heroic = False
        # several upgrades in one open (designer 2026-11-02): green can reach red
        cfg.chest_open_upgrade_chance = {"dong": 1.0, "bac": 1.0, "vang": 1.0}
        gs.in_bonus, gs.bonus_tier, gs.stage = True, "bonus", 1
        gs.reserve = {p: 0 for p in cfg.power_names}
        gs.open_chest({"id": "boss1", "chest": "dong", "chest_opened": False})
        assert [e for e in gs.book.events if e["type"] == "chestOpened"][-1]["upgradedTo"] == "do"
        cfg.chest_open_upgrade_max = 1
        gs.open_chest({"id": "boss1", "chest": "dong", "chest_opened": False})
        assert [e for e in gs.book.events if e["type"] == "chestOpened"][-1]["upgradedTo"] == "bac"
        cfg.chest_open_upgrade_max = None
        bands = {"dong": (1, 4), "bac": (5, 15), "vang": (20, 50), "do": (100, 25000)}
        cfg.chest_open_upgrade_chance = {"dong": 0.5, "bac": 0.5, "vang": 0.5}
        cfg.chest_gift_power_chance = {"dong": 1.0, "bac": 1.0, "vang": 1.0, "do": 1.0}
        cfg.chest_gift_multi_chance = {"dong": 1.0, "bac": 1.0, "vang": 1.0, "do": 1.0}
        gs.in_bonus, gs.bonus_tier, gs.stage = True, "bonus", 1
        order = cfg.chest_order_v4
        for tier in order:
            for _ in range(150):
                gs.tumble_boss, gs.tumble_base = [], 0.0
                gs.reserve = {p: 0 for p in cfg.power_names}
                gs.book.events.clear()
                gs.open_chest({"id": "boss1", "chest": tier, "chest_opened": False})
                ev = gs.book.events[-1]
                end = tier if ev["upgradedTo"] is None else ev["upgradedTo"]
                assert order.index(end) >= order.index(tier)
                assert tier != "do" or ev["upgradedTo"] is None
                bags = [g for g in ev["gifts"] if g["kind"] == "bag"]
                assert len(bags) == 1 and bands[end][0] <= bags[0]["value"] <= bands[end][1]
                assert bags[0]["bag"] == cfg.chest_tier_bag_names[end]
                assert {g["kind"] for g in ev["gifts"]} == {"bag", "power", "multi"}
                assert all(m <= cfg.chest_multi_cap[end] for m in gs.tumble_boss)
                assert gs.tumble_base == bags[0]["value"]  # the bag waits for the Global
    finally:
        (cfg.chest_rule, cfg.chest_open_upgrade_chance, cfg.chest_gift_power_chance, cfg.chest_gift_multi_chance,
         cfg.tumble_multi) = old
        gs.in_bonus, gs.bonus_tier, gs.heroic = False, None, False
        gs.tumble_boss, gs.tumble_base = [], 0.0


def test_v4_global_accumulates_additively(gs, cfg):
    """Rule 5: Global = sum(Wild) x product(chest multis) of this spin + what earlier spins of the scope added."""
    old = (cfg.tumble_multi, cfg.tumble_combine, dict(cfg.tier_weights))
    try:
        cfg.tumble_multi, cfg.tumble_combine = True, "add"
        cfg.tier_weights = {**old[2], "epic": {**old[2].get("epic", {}), "tumble_reset_scope": "bonus"}}
        gs.in_bonus, gs.bonus_tier = True, "epic"
        gs.reset_tumble("bonus")
        gs.begin_spin()
        gs.tumble_wild, gs.tumble_boss, gs.tumble_base = 3, [2], 1.0
        gs.settle_tumble()  # spin 1: 3 x 2 = 6
        assert gs.tumble_acc == 6 and gs.win_manager.spin_win == 6
        gs.win_manager.reset_end_round_wins()
        gs.begin_spin()
        assert gs.tumble_wild == 0 and gs.tumble_boss == [] and gs.tumble_acc == 6
        gs.tumble_wild, gs.tumble_base = 4, 1.0
        gs.settle_tumble()  # spin 2: 6 + 4 = 10
        assert gs.win_manager.spin_win == 10 and gs.tumble_acc == 10
        gs.win_manager.reset_end_round_wins()
        gs.begin_spin()
        gs.tumble_base = 1.0
        gs.settle_tumble()  # spin 3: nothing new, Global 10 stays
        assert gs.win_manager.spin_win == 10 and gs.tumble_acc == 10
        gs.reset_tumble("bonus")
        assert gs.tumble_acc == 0
    finally:
        cfg.tumble_multi, cfg.tumble_combine, cfg.tier_weights = old
        gs.in_bonus, gs.bonus_tier = False, None
        gs.win_manager.reset_end_round_wins()
        gs.tumble_wild, gs.tumble_boss, gs.tumble_base, gs.tumble_acc = 0, [], 0.0, 0


def test_v4_shuffle_power(gs, cfg):
    """Rule 3: Shuffle keeps Wild / weapons / Scatter in place, permutes the basic symbols and puts 1-3 multis
    (2-10x) on basic cells; the multis add up on a line."""
    gs.spawn_stage(1)
    gs.begin_spin()
    rows = ["W L1 H1 AR L2 H2", "L3 H3 L4 H4 L1 SC", "H5 L2 H1 L3 H2 L4", "L1 L2 L3 L4 H1 H2", "H3 H4 H5 L1 L2 L3"]
    set_board(gs, rows)
    fixed = {(c, r): gs.board[c][r].name for c, r in gs.all_cells() if not gs.is_basic(gs.board[c][r])}
    before = sorted(gs.board[c][r].name for c, r in gs.all_cells() if gs.is_basic(gs.board[c][r]))
    random.seed(8)
    gs.power_shuffle()
    assert {x: gs.board[x[0]][x[1]].name for x in fixed} == fixed
    assert sorted(gs.board[c][r].name for c, r in gs.all_cells() if gs.is_basic(gs.board[c][r])) == before
    mult_cells = [(c, r) for c, r in gs.all_cells() if gs.enhance[c][r]]
    assert 1 <= len(mult_cells) <= 3 and all(gs.is_basic(gs.board[c][r]) for c, r in mult_cells)
    assert all(gs.enhance[c][r] in cfg.shuffle_mult_weights for c, r in mult_cells)
    # fires after the weapons, from reserve
    gs.reserve = {p: 0 for p in cfg.power_names}
    gs.reserve["shuffle"] = 1
    gs.bosses = []  # no bosses: nothing to damage
    gs.resolve_actions()
    assert gs.reserve["shuffle"] == 0
    gs.reserve = {p: 0 for p in cfg.power_names}


def test_v4_lit_only_connected_wild_cells(gs, cfg):
    """Rule 4: lit_wild_lines_only = "cells": only the connected Wild cells light up, not their whole line."""
    old = (cfg.lit_rule, cfg.lit_wild_lines_only)
    try:
        cfg.lit_rule, cfg.lit_wild_lines_only = "lines", "cells"
        gs.spawn_stage(1)
        gs.begin_spin()
        gs.lit = set()
        gs.refill = lambda: []
        set_board(gs, board_with_top("H2 W H2 H2 L1 L2"))
        gs.step_connect()
        assert gs.lit == {(1, 0)}
    finally:
        cfg.lit_rule, cfg.lit_wild_lines_only = old
        del gs.refill


def test_v4_coin_excluded_values(gs, cfg):
    old = cfg.coin_excluded_values
    try:
        cfg.coin_excluded_values = [6]
        random.seed(1)
        assert all(gs.draw_coin(5, table={5: 1, 6: 100, 8: 1}) != 6 for _ in range(200))
    finally:
        cfg.coin_excluded_values = old


def test_heroic_at_least_five_wilds(gs, cfg):
    """Rule 6: every Heroic spin starts with >= 5 Wilds (all x2+)."""
    assert cfg.heroic_min_wild_or_weapon >= 5
    assert set(cfg.tier_weights["heroic"]["guarantee_symbol_weights"]) == {"W"}
    assert min(cfg.tier_weights["heroic"]["wild_mult_weights"]) >= 2


def test_stage_hp_weights(gs, cfg):
    """Designer 2026-11-02: HP odds per stage over the rule's own values; values outside the range never come up."""
    old = cfg.stage_hp_weights
    try:
        cfg.stage_hp_weights = {1: {20: 3, 25: 1, 99: 50}}
        random.seed(2)
        got = [gs._roll_hp((20, 35), 1) for _ in range(4000)]
        assert set(got) == {20, 25} and 0.7 < got.count(20) / len(got) < 0.8
        assert set(gs._roll_hp((35, 50), 2) for _ in range(300)) == {35, 40, 45, 50}  # stage without a table: uniform
    finally:
        cfg.stage_hp_weights = old


def test_tumble_band_tables(gs, cfg):
    """Trial 2026-11-02: Wild / chest multi odds follow the spin's tumble win (small / mid / big band)."""
    old = (cfg.tumble_band_bounds, cfg.tumble_band_tables)
    try:
        cfg.tumble_band_bounds = [2, 10]
        cfg.tumble_band_tables = {"wild_multi_weights": [{5: 1}, None, {2: 1}]}
        gs.tumble_base = 0.0
        assert gs.tumble_band() == 0 and gs.band_table("wild_multi_weights") == {5: 1}
        gs.tumble_base = 5.0
        assert gs.tumble_band() == 1 and gs.band_table("wild_multi_weights") == gs.weights("wild_multi_weights")
        gs.tumble_base = 10.0
        assert gs.tumble_band() == 2 and gs.band_table("wild_multi_weights") == {2: 1}
        assert gs.band_table("chest_multi_weights") == gs.weights("chest_multi_weights")
    finally:
        cfg.tumble_band_bounds, cfg.tumble_band_tables = old
        gs.tumble_base = 0.0


def test_destroy_weight_by_alive(gs, cfg):
    """Trial 2026-11-03: Destroy is likelier the more bosses are alive."""
    old = (cfg.destroy_weight_by_alive, cfg.power_pick_weights)
    try:
        cfg.power_pick_weights = {"destroy": 1, "upgrade": 1}
        cfg.destroy_weight_by_alive = {3: 3, 1: 0}
        gs.reserve = {p: 0 for p in cfg.power_names}
        gs.spawn_stage(1)
        random.seed(6)
        picks = [gs.pick_power() for _ in range(4000)]
        assert 0.7 < picks.count("destroy") / len(picks) < 0.8  # 3 alive: 3:1
        gs.bosses[0]["alive"] = gs.bosses[1]["alive"] = False
        assert all(gs.pick_power() == "upgrade" for _ in range(200))  # 1 alive: never Destroy
    finally:
        cfg.destroy_weight_by_alive, cfg.power_pick_weights = old
        gs.reserve = {p: 0 for p in cfg.power_names}


def test_guarantee_line(gs, cfg):
    """Dead-spin guard "line" (2026-11-03): a board that connects nothing gets a sure 3-symbol line."""
    gs.spawn_stage(1)
    gs.begin_spin()
    set_board(gs, FILLER)
    assert not gs.evaluate_lines()
    random.seed(3)
    gs.guarantee_line()
    assert gs.evaluate_lines()


# ---- Complete unified document (designer 2026-11-03) ------------------------------------------------------------
def test_doc_power_order_after_weapons(gs, cfg):
    """Section 8: reserved powers fire only after lines and weapons, in the order Upgrade, Transform, Replace, Shuffle."""
    old = cfg.action_order
    try:
        cfg.action_order = "doc"
        gs.spawn_stage(1)
        gs.begin_spin()
        set_board(gs, FILLER)
        gs.reserve = {p: 0 for p in cfg.power_names}
        for p in ("shuffle", "upgrade", "transform"):
            gs.reserve[p] = 1
        gs.book.events.clear()
        random.seed(2)
        gs.resolve_actions()
        fired = [e["power"] for e in gs.book.events if e["type"] == "powerActivated"]
        assert fired[:3] == ["upgrade", "transform", "shuffle"]
        assert all(gs.reserve[p] == 0 for p in ("shuffle", "upgrade", "transform"))
    finally:
        cfg.action_order = old
        gs.reserve = {p: 0 for p in cfg.power_names}


def test_doc_shuffle(gs, cfg):
    """Doc Shuffle: every non-connected cell (Scatter stays) moves and gets a multiplier; a line appears if possible."""
    old = cfg.shuffle_rule
    try:
        cfg.shuffle_rule = "doc"
        gs.spawn_stage(1)
        gs.begin_spin()
        rows = ["H1 L2 H1 L4 SC L2", "L3 L1 H1 L2 L3 L4", "L2 L1 L4 L3 L2 L1", "L4 L3 L2 L1 L4 L3", "L1 L2 L3 L4 L1 L2"]
        set_board(gs, rows)
        assert not gs.evaluate_lines()
        random.seed(5)
        gs.power_shuffle()
        assert gs.board[4][0].name == "SC"
        assert gs.evaluate_lines()  # a line could be made, so it was
        n_mult = sum(1 for c, r in gs.all_cells() if gs.enhance[c][r] > 0)
        assert n_mult == 29  # every cell but the Scatter
    finally:
        cfg.shuffle_rule = old


def test_transform_may_hit_weapons(gs, cfg):
    old = cfg.transform_skips_weapons
    try:
        cfg.transform_skips_weapons = False
        gs.spawn_stage(1)
        gs.begin_spin()
        rows = ["AR AR AR AR AR AR"] * 5
        set_board(gs, rows)
        gs.power_transform()
        assert any(gs.is_wild(gs.board[c][r]) for c, r in gs.all_cells())
    finally:
        cfg.transform_skips_weapons = old


def test_super_global_if2x(gs, cfg):
    """Super: the accumulated Global joins only a spin with its own >= 2x; otherwise x1 and the accumulation stays."""
    old = (cfg.tumble_multi, cfg.tumble_combine, dict(cfg.tier_weights))
    try:
        cfg.tumble_multi, cfg.tumble_combine = True, "add"
        cfg.tier_weights = {**old[2], "super": {**old[2].get("super", {}), "tumble_reset_scope": "bonus",
                                                "tumble_acc_rule": "if2x"}}
        gs.in_bonus, gs.bonus_tier = True, "super"
        gs.reset_tumble("bonus")
        gs.begin_spin(); gs.tumble_wild, gs.tumble_base = 3, 1.0; gs.settle_tumble()   # 3x, acc 3
        assert gs.win_manager.spin_win == 3 and gs.tumble_acc == 3
        gs.win_manager.reset_end_round_wins()
        gs.begin_spin(); gs.tumble_base = 1.0; gs.settle_tumble()                     # no multi: x1, acc stays 3
        assert gs.win_manager.spin_win == 1 and gs.tumble_acc == 3
        gs.win_manager.reset_end_round_wins()
        gs.begin_spin(); gs.tumble_wild, gs.tumble_base = 2, 1.0; gs.settle_tumble()   # 2 + 3 = 5, acc 5
        assert gs.win_manager.spin_win == 5 and gs.tumble_acc == 5
    finally:
        cfg.tumble_multi, cfg.tumble_combine, cfg.tier_weights = old
        gs.in_bonus, gs.bonus_tier = False, None
        gs.win_manager.reset_end_round_wins()
        gs.tumble_wild, gs.tumble_boss, gs.tumble_base, gs.tumble_acc = 0, [], 0.0, 0


def test_legendary_bonus(gs, cfg):
    """Document section 9: 6 Scatters -> Legendary: 10 spins from stage 5, >= 5 multi Wilds each spin, all lit."""
    old = (dict(cfg.scatter_to_tier), cfg.max_scatters_on_board, dict(cfg.bonus_min_multi_wilds), list(cfg.full_lit_tiers))
    try:
        cfg.scatter_to_tier = {**old[0], 6: "legendary"}
        cfg.max_scatters_on_board = 6
        cfg.bonus_min_multi_wilds = {"legendary": 5}
        cfg.full_lit_tiers = ["epic", "legendary"]
        gs.reset_book()
        random.seed(9)
        starts = []
        orig = gs.play_one_spin
        def spy(reel, **kw):
            starts.append(kw.get("min_multi_wilds"))
            orig(reel, **kw)
        gs.play_one_spin = spy
        gs.run_bonus("legendary")
        ev = gs.book.events
        assert next(e for e in ev if e["type"] == "bonusStart")["stage"] == 5
        assert next(e for e in ev if e["type"] == "bonusStart")["freeSpins"] == 10
        assert starts and all(s == 5 for s in starts)
        reveals = [e for e in ev if e["type"] == "reveal"]
        def multi_wilds(board):
            return sum(1 for col in board for s in col if s.get("name") == "W" and s.get("value", 0) >= 2)
        assert all(multi_wilds(e["board"]) >= 5 for e in reveals)
    finally:
        cfg.scatter_to_tier, cfg.max_scatters_on_board, cfg.bonus_min_multi_wilds, cfg.full_lit_tiers = old
        del gs.play_one_spin
        gs.reset_book()


def test_doc_shuffle_keeps_lines_made_by_earlier_powers(gs, cfg):
    """Powers fire back to back with no payout in between: a line made by an earlier power (here Transform) is kept
    in place by Shuffle and only counts as the baseline - Shuffle must add a line or lengthen one on top of it."""
    old = (cfg.shuffle_rule, cfg.action_order)
    try:
        cfg.shuffle_rule, cfg.action_order = "doc", "doc"
        gs.spawn_stage(1)
        gs.begin_spin()
        set_board(gs, FILLER)
        for c in range(3):  # as if Transform just made a 3-Wild line on line 1
            gs.board[c][0] = gs.make_symbol("W")
        before = gs.evaluate_lines()
        kept = {(p["reel"], p["row"]) for w in before for p in w["positions"]}
        assert kept
        syms = {x: gs.board[x[0]][x[1]] for x in kept}
        base = gs._win_signature()
        random.seed(4)
        gs.power_shuffle()
        assert all(gs.board[c][r] is syms[(c, r)] for c, r in kept)  # connected cells did not move
        assert all(gs.enhance[c][r] == 0 for c, r in kept)            # and got no Shuffle Multiplier
        assert gs._win_signature() > base                             # more / longer lines than before
    finally:
        cfg.shuffle_rule, cfg.action_order = old


def test_arrow_table_damage(gs, cfg):
    """Designer 2026-11-04: Arrow damage 10-35 in steps of 5, likelier high for a boss with more (max and remaining) HP."""
    old = cfg.arrow_rule
    try:
        cfg.arrow_rule = "table"
        random.seed(1)
        weak = {"hp": 5, "hp_max": 20}
        strong = {"hp": 120, "hp_max": 120}
        dw = [gs.arrow_damage(weak) for _ in range(3000)]
        ds = [gs.arrow_damage(strong) for _ in range(3000)]
        assert set(dw) <= {10, 15, 20, 25, 30, 35} and set(ds) <= {10, 15, 20, 25, 30, 35}
        assert sum(ds) / len(ds) > 27 and sum(dw) / len(dw) < 18
    finally:
        cfg.arrow_rule = old


def test_bonus_min_win_reject_mode():
    """bonus_min_total_win_mode "reject": an Epic under the floor is flagged for a re-run, nothing is topped up."""
    from gamestate import GameState
    from game_config import GameConfig
    cfg = GameConfig()
    gs = GameState(cfg)
    gs.reset_book()
    gs.bonus_min_total_win_mode_saved = cfg.bonus_min_total_win_mode
    try:
        cfg.bonus_min_total_win_mode = "reject"
        gs.win_manager.freegame_wins = 100.0
        gs.bonus_min_win_topup("epic")
        assert gs.bonus_below_floor
        assert gs.win_manager.freegame_wins == 100.0
        gs.reset_book()
        assert not gs.bonus_below_floor
        cfg.bonus_min_total_win_mode = "topup"
        gs.win_manager.freegame_wins = 100.0
        gs.bonus_min_win_topup("epic")
        assert not gs.bonus_below_floor
    finally:
        cfg.bonus_min_total_win_mode = gs.bonus_min_total_win_mode_saved


def test_bonus_min_win_reroll_limit():
    """bonus_min_total_win_rerolls: after the allowed re-runs the floor is topped up instead."""
    from gamestate import GameState
    from game_config import GameConfig
    cfg = GameConfig()
    gs = GameState(cfg)
    saved = (cfg.bonus_min_total_win_mode, cfg.bonus_min_total_win_rerolls)
    try:
        cfg.bonus_min_total_win_mode, cfg.bonus_min_total_win_rerolls = "reject", 1
        gs.reset_book()
        gs.floor_rerolls = 0
        gs.win_manager.freegame_wins = 100.0
        gs.bonus_min_win_topup("epic")
        assert gs.bonus_below_floor and gs.floor_rerolls == 1
        gs.reset_book()
        gs.win_manager.freegame_wins = 100.0
        gs.bonus_min_win_topup("epic")
        assert not gs.bonus_below_floor  # second time: topped up
    finally:
        cfg.bonus_min_total_win_mode, cfg.bonus_min_total_win_rerolls = saved

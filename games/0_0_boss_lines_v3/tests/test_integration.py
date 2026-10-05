"""Whole-round invariants across every bet mode (small N, fast)."""
import pytest

from src.wins.win_manager import WinManager

N = 25


def rounds(gs, cfg, mode, crit, n=N):
    gs.betmode = mode
    gs.criteria = crit
    gs.win_manager = WinManager(cfg.basegame_type, cfg.freegame_type, cfg.wincap)
    for i in range(n):
        gs.run_spin(i)
        yield gs


CASES = [("base", "basegame"), ("base", "0"), ("base", "freegame"), ("ante", "basegame"),
         ("feature", "basegame"), ("buy3", "freegame"), ("buy4", "freegame")]


@pytest.mark.parametrize("mode,crit", CASES)
def test_round_invariants(gs, cfg, mode, crit):
    for g in rounds(gs, cfg, mode, crit):
        ev = g.book.events
        assert 0 <= g.final_win <= cfg.wincap
        assert all(g.board[c][r] is not None for c in range(6) for r in range(5))
        sc = [sum(g.is_scatter(g.board[c][r]) for r in range(5)) for c in range(6)]
        assert sum(sc) <= 5 and max(sc) <= 1
        if crit == "0":
            assert g.final_win == 0
        if crit == "freegame":
            assert any(e["type"] == "bonusStart" for e in ev)
        if crit == "basegame" and mode in ("base", "ante"):
            assert not any(e["type"] == "bonusStart" for e in ev)
        in_bonus = False
        for e in ev:
            if e["type"] == "bonusStart":
                in_bonus = True
            if e["type"] == "chestOpened" and not in_bonus:
                assert all(gift["kind"] == "coin" for gift in e["gifts"])
            if e["type"] == "bossDamage":
                assert e["hp"] >= 0


def test_heroic_never_shows_scatter_or_endless(gs, cfg):
    seen = 0
    for g in rounds(gs, cfg, "feature", "basegame", 60):
        if not g.heroic:
            continue
        seen += 1
        for e in g.book.events:
            if e["type"] == "reveal":
                assert all(s["name"] != "SC" for col in e["board"] for s in col)
            if e["type"] == "bossState":
                assert e["stage"] in (5,)
    assert seen > 0


def test_bonus_stage_progression_and_endless_hp(gs, cfg):
    for g in rounds(gs, cfg, "buy4", "freegame", 40):
        stages, endless_hp = [], []
        for e in g.book.events:
            if e["type"] == "freeSpinStart":
                stages.append(6 if e["stage"] == "endless" else e["stage"])
            if e["type"] == "bossState" and e["stage"] == "endless":
                endless_hp.append(e["bosses"][0]["hpMax"])
        assert stages == sorted(stages)
        assert endless_hp == sorted(endless_hp)
        assert stages[0] >= cfg.bonus_tiers["super"]["start_stage"]

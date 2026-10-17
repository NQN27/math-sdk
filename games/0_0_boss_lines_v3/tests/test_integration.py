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
         ("feature", "basegame"), ("buy3", "freegame"), ("buy4", "freegame"),
         ("random_bonus", "freegame")]


@pytest.mark.parametrize("mode,crit", CASES)
def test_round_invariants(gs, cfg, mode, crit):
    for g in rounds(gs, cfg, mode, crit):
        ev = g.book.events
        assert 0 <= g.final_win <= cfg.wincap
        had_treasure = any(e["type"] == "treasureStart" for e in ev)
        # empty cells only after a Treasure (activated Star/Clover cells stay empty, N10)
        assert had_treasure or all(g.board[c][r] is not None for c in range(6) for r in range(5))
        sc = [sum(g.is_scatter(g.board[c][r]) for r in range(5) if g.board[c][r] is not None) for c in range(6)]
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
        if stages:  # an Epic can hit Maxwin in its opening Treasure, before spin 1
            assert stages[0] >= cfg.bonus_tiers["super"]["start_stage"]


def _segments(events):
    """Split a book's events into (context, spin_events) per spin."""
    ctx, cur, out = {"tier": None, "feature": None}, None, []
    for e in events:
        t = e["type"]
        if t == "bonusStart":
            ctx = {"tier": e["tier"], "feature": None}
        elif t == "featureSpin":
            ctx = {"tier": None, "feature": e["feature"]}
        if t == "reveal":
            cur = {"ctx": dict(ctx), "events": []}
            out.append(cur)
        if t == "epicOpeningTreasure" and cur is not None:
            cur["ctx"]["opening"] = True
        if cur is not None:
            cur["events"].append(e)
    return out


def _wild_weapon_count(reveal, cfg, weapons_only=False):
    names = [s["name"] for col in reveal["board"] for s in col[1:-1]]  # strip padding rows
    return sum((n == "W" and not weapons_only) or n in cfg.weapon_symbols for n in names)


@pytest.fixture
def tame(cfg):
    """Same rules, much smaller payouts, so Bonus rounds finish without
    hitting the 25,000x cap and the bookkeeping checks actually run."""
    patches = {
        "coin_value_weights": {0.2: 30, 0.5: 26, 1: 22, 2: 16, 3: 12, 4: 10, 5: 1, 20: 0.5, 100: 0.2},
        "treasure_kind_weights": {"coin": 90, "magnet": 2, "clover": 3, "scatter": 2},
        "global_factor_weights": {2: 1},
        "clover_factor_weights": {2: 1},
        "enhance_factor_weights": {2: 1},
        "wild_mult_weights": {2: 1},
        "stage_min_coin": {s: 0.2 for s in cfg.stage_min_coin},
        "coin_tiers": {k: [0.2] for k in cfg.coin_tiers},
    }
    saved = {k: dict(getattr(cfg, k)) for k in patches}
    for k, v in patches.items():
        getattr(cfg, k).clear()
        getattr(cfg, k).update(v)
    yield cfg
    for k, v in saved.items():
        getattr(cfg, k).clear()
        getattr(cfg, k).update(v)


@pytest.mark.parametrize("mode", ["buy3", "buy4", "random_bonus", "feature"])
def test_mode_guarantees_and_bookkeeping(gs, tame, mode):
    cfg = tame
    checked = 0
    crit = "basegame" if mode == "feature" else "freegame"
    epic_spins = 0
    for g in rounds(gs, cfg, mode, crit, 40):
        ev = g.book.events
        capped = any(e["type"] == "wincap" for e in ev)
        for seg in _segments(ev):
            reveal = seg["events"][0]
            tier, feat = seg["ctx"]["tier"], seg["ctx"]["feature"]
            if tier in ("super", "epic") and not seg["ctx"].get("opening", False):
                assert _wild_weapon_count(reveal, cfg, weapons_only=True) >= cfg.bonus_min_weapons[tier]
            if feat == "heroic" and tier is None:
                assert _wild_weapon_count(reveal, cfg) >= cfg.heroic_min_wild_or_weapon
            opening = seg["ctx"].get("opening", False)
            if tier == "epic" and not opening:
                epic_spins += 1
            # Hold and Spin was removed from every mode (designer 2026-10-07)
            assert not any(e["type"].startswith("holdSpin") for e in seg["events"])
            end = [e for e in seg["events"] if e["type"] == "spinEnd"]
            treasure = any(e["type"] == "treasureStart" for e in seg["events"])
            if end and not capped and feat != "treasureHunt" and not opening:
                assert treasure == end[0]["stageCleared"]
        # every killed boss opens its chest exactly once (unless the cap ended the round)
        if not capped:
            kills = sum(e["type"] == "bossDefeated" for e in ev)
            chests = sum(e["type"] == "chestOpened" for e in ev)
            assert kills == chests
        # spins played = initial + Scatters collected + Treasure Scatters + chest extra spins
        starts = [e for e in ev if e["type"] == "bonusStart"]
        if starts and not capped:
            checked += 1
            if starts[0]["tier"] == "epic":
                assert any(e["type"] == "epicOpeningTreasure" for e in ev)
            played = sum(e["type"] == "freeSpinStart" for e in ev)
            added = (sum(e["added"] for e in ev if e["type"] == "scatterCollected")
                     + sum(e.get("addedSpins", 0) for e in ev if e["type"] == "treasureSymbols")
                     + sum(e.get("extraSpin", 0) for e in ev if e["type"] == "chestOpened"))
            assert played == starts[0]["freeSpins"] + added
    if mode == "buy4":
        assert epic_spins > 0
    if mode in ("buy3", "buy4", "random_bonus"):
        assert checked >= 20, f"only {checked} uncapped Bonus rounds were checked"


def test_treasure_cells_skip_scatter(gs):
    from conftest import set_board
    set_board(gs, ["SC L1 L2 L3 L4 L1"] + ["L1 L2 L3 L4 L1 L2"] * 4)
    gs.lit = {(0, 0), (1, 0)}
    gs.bonus_tier = None
    assert gs.treasure_cells() == {(1, 0)}


@pytest.mark.parametrize("reset", [False, True])
def test_lit_reset_each_spin_trial(gs, cfg, reset):
    """Q23 trial flag: with the tier listed, every Bonus spin after the first starts
    with no lit cells; without it lit cells only grow during a Bonus (Q23)."""
    old = cfg.lit_reset_each_spin_tiers
    cfg.lit_reset_each_spin_tiers = ("bonus",) if reset else ()
    seen = []
    orig = gs.play_one_spin

    def spy(*a, **k):
        if gs.in_bonus:
            seen.append((gs.bonus_tier, set(gs.lit)))
        return orig(*a, **k)
    gs.play_one_spin = spy
    try:
        checked = 0
        for g in rounds(gs, cfg, "buy3", "freegame", 30):
            spins = [lit for tier, lit in seen if tier == "bonus"]
            seen.clear()
            for prev_end, lit in zip(spins, spins[1:]):
                if reset:
                    assert lit == set()
                else:
                    assert prev_end <= lit
                checked += 1
        assert checked > 20
    finally:
        cfg.lit_reset_each_spin_tiers = old
        gs.play_one_spin = orig


@pytest.mark.parametrize("mode,crit,key", [("buy3", "freegame", "bonus_tier"), ("buy4", "freegame", "bonus_tier"),
                                            ("feature", "basegame", "feature")])
def test_optimizer_force_records(gs, cfg, mode, crit, key):
    """Designer 2026-10-12: every Bonus book carries {"bonus_tier": t} and every Feature book
    {"feature": heroic|treasure_hunt}, so the optimizer can fix each tier's mean exactly."""
    gs.recorded_events = {}
    n = 0
    for g in rounds(gs, cfg, mode, crit, 30):
        n += 1
    tagged = {}
    for desc, rec in gs.recorded_events.items():
        d = dict(desc)
        if key in d:
            for b in rec["bookIds"]:
                tagged.setdefault(b, []).append(d[key])
    assert len(tagged) == n and all(len(v) == 1 for v in tagged.values())
    if key == "bonus_tier":
        allowed = {cfg.scatter_to_tier[s] for s in cfg.tier_mix[mode]}
        assert {v[0] for v in tagged.values()} <= allowed


def test_wild_coin_min_and_table(gs, cfg):
    """Designer 2026-10-14 (Normal Bonus trial): Wild coin events can have a minimum value and
    their own coin table; defaults (0, None) keep drawing from the Treasure coin table."""
    old = (cfg.wild_coin_min_value, cfg.wild_coin_value_weights, dict(cfg.tier_weights))
    try:
        cfg.tier_weights = {"bonus": {"wild_coin_min_value": 2.0, "wild_coin_value_weights": {1: 50, 2: 30, 5: 20}}}
        cfg.wild_coin_min_value, cfg.wild_coin_value_weights = 0.0, None
        vals = []
        for g in rounds(gs, cfg, "buy3", "freegame", 40):
            tier = None  # only Normal Bonus free spins (not the trigger spin, not Super/Epic)
            for e in g.book.events:
                if e["type"] == "bonusStart":
                    tier = e["tier"]
                elif e["type"] == "wildEvent" and e["event"] == "coin" and tier == "bonus" and e["value"] < cfg.wincap:
                    vals.append(e["value"])
        assert vals and all(v in (2, 5) for v in vals)
    finally:
        cfg.wild_coin_min_value, cfg.wild_coin_value_weights, cfg.tier_weights = old

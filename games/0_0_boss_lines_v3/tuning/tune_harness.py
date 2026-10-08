"""Per-tier Bonus tuning harness (Boss Lines v3).

usage: python _scratch/tune_harness.py TIER N [overrides.json] [tag]
  TIER       bonus | super | epic | feature_heroic | feature_treasure | base
  overrides  JSON {config_attr: value} applied (dicts are REPLACED) in every worker

Writes _scratch/results/<tag>_<tier>_<timestamp>.csv (one payout per session)
and a .json summary: mean/median/percentiles, Max Win rate, payout split by
source, stage reached, spins per session.
"""
import json
import os
import random
import statistics
import sys
import time
import zlib
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
SDK = os.path.dirname(os.path.dirname(GAME))
# worker processes (designer 2026-10-08: keep the machine usable; override with TUNE_PROCS)
PROCS = int(os.environ.get("TUNE_PROCS", "2"))


def _setup(overrides):
    for p in (SDK, GAME):
        if p not in sys.path:
            sys.path.insert(0, p)
    from gamestate import GameState
    from game_config import GameConfig
    from src.wins.win_manager import WinManager
    cfg = GameConfig()
    reel_specs = overrides.pop("_reel_specs", None) if isinstance(overrides, dict) else None
    if reel_specs:  # rebuild reels in memory with modified gen_reels specs
        import gen_reels
        for name, spec in reel_specs.items():
            full = {**gen_reels.REEL_SPECS[name], **spec}
            cfg.reels[name] = [gen_reels.build_column(name, c, full) for c in range(6)]
    def numkeys(base, table):  # JSON keys are strings; match the base table's key types (recursively)
        if not (isinstance(base, dict) and isinstance(table, dict)):
            return table
        if base and all(isinstance(x, (int, float)) for x in base):
            ints = all(isinstance(x, int) for x in base)
            table = {(int(float(k)) if ints and float(k).is_integer() else float(k)): w for k, w in table.items()}
        sub = next(iter(base.values()), None)
        return {k: numkeys(base.get(k, sub), v) for k, v in table.items()}
    if "tier_weights" in overrides:
        overrides["tier_weights"] = {
            tier: {name: numkeys(getattr(cfg, name), table) for name, table in tables.items()}
            for tier, tables in overrides["tier_weights"].items()}
    for k, v in overrides.items():
        cur = getattr(cfg, k)
        if isinstance(cur, dict) and isinstance(v, dict):
            v = {(float(kk) if isinstance(next(iter(cur), None), (int, float)) and not isinstance(kk, (int, float))
                  else kk): vv for kk, vv in v.items()}
            v = {(int(kk) if isinstance(kk, float) and kk.is_integer() and all(isinstance(x, int) for x in cur)
                  else kk): vv for kk, vv in v.items()}
        setattr(cfg, k, v)
    gs = GameState(cfg)
    gs.win_manager = WinManager(cfg.basegame_type, cfg.freegame_type, cfg.wincap)
    return gs, cfg


def _one(gs, cfg, tier, i):
    random.seed(zlib.crc32(tier.encode()) % 99991 * 1_000_003 + i)  # stable across processes
    if tier == "base":
        gs.betmode, gs.criteria = "base", "basegame"
        gs.reset_book()
        gs.run_base_spin(gs.get_current_distribution_conditions())
        return
    gs.betmode, gs.criteria = "buy3", "freegame"
    gs.reset_book()
    if tier.startswith("feature"):
        gs.betmode, gs.criteria = "feature", "basegame"
        cfg.feature_heroic_chance = 1.0 if tier == "feature_heroic" else 0.0
        gs.run_feature_spin(gs.get_current_distribution_conditions())
        return
    n = {"bonus": 3, "super": 4, "epic": 5}[tier]
    cols = random.sample(range(6), n)
    trigger = {(c, random.randrange(5)) for c in cols}
    gs.run_bonus(tier, trigger)


def _diag_new():
    return {"conn_hist": {}, "conn_zero": {}, "spins": 0, "zero_spins": 0, "zero_streak_hist": {},
            "stage_clears_hist": {}, "treasure_kinds": {}, "clover_factor": {}, "golden_factor": {},
            "global_factor": {}, "treasure_paid": [], "topups": 0, "topup_paid": 0.0}


def _bump(d, k, v=1):
    d[str(k)] = d.get(str(k), 0) + v


def _diag_session(diag, ev):
    """Per-spin connection counts, dead spins, stage clears, Treasure symbol mix."""
    conn, clears, streak, worst = 0, 0, 0, 0
    for e in ev:
        t = e["type"]
        if t == "destroy" and e.get("cause") == "connect":
            conn += 1
        elif t == "spinEnd":
            diag["spins"] += 1
            _bump(diag["conn_hist"], conn)
            zero = e["spinWin"] == 0
            if zero:
                diag["zero_spins"] += 1
                _bump(diag["conn_zero"], conn)
                streak += 1
                worst = max(worst, streak)
            else:
                streak = 0
            clears += bool(e["stageCleared"])
            conn = 0
        elif t == "treasureSymbols":
            for c in e["cells"]:
                _bump(diag["treasure_kinds"], c["kind"])
                if c["kind"] in ("clover", "golden", "global"):
                    _bump(diag[c["kind"] + "_factor"], c["value"])
        elif t == "treasureEnd":
            diag["treasure_paid"].append(e["paid"])
        elif t == "bonusMinWin":
            diag["topups"] += 1
            diag["topup_paid"] += e["topUp"]
    _bump(diag["stage_clears_hist"], clears)
    _bump(diag["zero_streak_hist"], worst)


def worker(args):
    tier, start, n, overrides = args
    overrides = json.loads(json.dumps(overrides))
    gs, cfg = _setup(overrides)
    out = []
    diag = _diag_new()
    for i in range(start, start + n):
        _one(gs, cfg, tier, i)
        ev = gs.book.events
        src = {"lines": 0.0, "wildcoin": 0.0, "chest": 0.0, "treasure": 0.0}
        stage, spins, treasures = None, 0, 0
        for e in ev:
            t = e["type"]
            if t == "lineWins":
                src["lines"] += e["total"]
            elif t == "wildEvent" and e["event"] == "coin":
                src["wildcoin"] += e["paid"]
            elif t == "chestOpened":
                src["chest"] += sum(g.get("paid", 0) for g in e["gifts"])
            elif t == "treasureStart":
                treasures += 1
            elif t == "freeSpinStart":
                spins += 1
                stage = e["stage"]
        # Treasure = everything not paid by lines / Wild coins / chests (covers
        # a Treasure that ends early on Maxwin, whose payout has no treasureEnd)
        src["treasure"] = max(0.0, gs.win_manager.running_bet_win - src["lines"] - src["wildcoin"] - src["chest"])
        out.append({"win": gs.win_manager.running_bet_win, "maxwin": gs.wincap_triggered,
                    "src": src, "stage": stage, "spins": spins, "treasures": treasures})
        _diag_session(diag, ev)
    return out, diag


def _diag_merge(parts):
    tot = _diag_new()
    for d in parts:
        for k, v in d.items():
            if isinstance(v, dict):
                for kk, vv in v.items():
                    tot[k][kk] = tot[k].get(kk, 0) + vv
            elif isinstance(v, list):
                tot[k].extend(v)
            else:
                tot[k] += v
    tp = tot.pop("treasure_paid")
    tot["treasure_count"] = len(tp)
    tot["treasure_paid_mean"] = sum(tp) / len(tp) if tp else 0.0
    for k in ("conn_hist", "conn_zero", "zero_streak_hist", "stage_clears_hist", "clover_factor",
              "golden_factor", "global_factor"):
        tot[k] = dict(sorted(tot[k].items(), key=lambda kv: float(kv[0])))
    return tot


def main():
    tier, n = sys.argv[1], int(sys.argv[2])
    overrides = json.load(open(sys.argv[3])) if len(sys.argv) > 3 and sys.argv[3] != "-" else {}
    tag = sys.argv[4] if len(sys.argv) > 4 else "run"
    procs = PROCS
    chunk = n // procs
    t0 = time.time()
    with Pool(procs) as pool:
        parts = pool.map(worker, [(tier, k * chunk, chunk, overrides) for k in range(procs)])
    rows = [r for p, _ in parts for r in p]
    diag = _diag_merge([d for _, d in parts])
    wins = sorted(r["win"] for r in rows)
    N = len(wins)

    def pct(p):
        return wins[min(N - 1, int(N * p / 100))]

    src = {k: sum(r["src"][k] for r in rows) / N for k in rows[0]["src"]}
    stages = {}
    for r in rows:
        stages[str(r["stage"])] = stages.get(str(r["stage"]), 0) + 1
    summary = {
        "tier": tier, "n": N, "tag": tag, "overrides": overrides,
        "mean": sum(wins) / N, "median": statistics.median(wins),
        "p": {p: pct(p) for p in (10, 25, 50, 75, 90, 95, 99, 99.9)},
        "maxwin_rate": sum(r["maxwin"] for r in rows) / N,
        "maxwin_count": sum(r["maxwin"] for r in rows),
        "source_mean": src,
        "last_stage_pct": {k: round(100 * v / N, 2) for k, v in sorted(stages.items())},
        "spins_mean": statistics.mean(r["spins"] for r in rows),
        "treasures_mean": statistics.mean(r["treasures"] for r in rows),
        "seconds": round(time.time() - t0, 1),
        "diag": diag,
    }
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    base = os.path.join(HERE, "results", f"{tag}_{tier}_{stamp}")
    with open(base + ".csv", "w") as f:
        f.write("\n".join(f"{w:.2f}" for w in (r["win"] for r in rows)))
    json.dump(summary, open(base + ".json", "w"), indent=1)
    mw = summary["maxwin_count"]
    print(f"[{tag}] {tier} n={N} mean={summary['mean']:.2f} median={summary['median']:.2f} "
          f"p90={summary['p'][90]:.1f} p99={summary['p'][99]:.1f} "
          f"MaxWin={mw}/{N} (1 in {N / mw:.0f})" if mw else
          f"[{tag}] {tier} n={N} mean={summary['mean']:.2f} median={summary['median']:.2f} "
          f"p90={summary['p'][90]:.1f} p99={summary['p'][99]:.1f} MaxWin=0/{N}")
    print("   source:", {k: round(v, 2) for k, v in src.items()},
          "| spins", round(summary["spins_mean"], 2), "| treasures", round(summary["treasures_mean"], 2),
          "| last stage %", summary["last_stage_pct"], f"| {summary['seconds']}s")
    print("   saved", base + ".json")


if __name__ == "__main__":
    main()

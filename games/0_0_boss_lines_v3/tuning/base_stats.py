"""Base / Ante natural stats (no forced Bonus; a triggered Bonus is NOT played).

usage: python tuning/base_stats.py MODE N overrides.json TAG     (MODE: base | ante)
Reports per spin: mean base-game win (x base bet), hit rate, zero rate, Treasure rate,
stage-0 clear rate, natural 3/4/5-Scatter trigger rates, Max Win count.
Saves tuning/results/TAG_MODE_<time>.csv (base win per spin) and .json.
"""
import json
import os
import statistics
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tune_harness as H  # noqa: E402


def worker(args):
    mode, start, n, overrides = args
    gs, cfg = H._setup(json.loads(json.dumps(overrides)))
    import random
    out = []
    for i in range(start, start + n):
        random.seed(7_919 * (mode == "ante") + i)
        gs.betmode, gs.criteria = mode, "basegame"
        gs.reset_book()
        gs.run_base_spin(gs.get_current_distribution_conditions())
        ev = gs.book.events
        tier, nsc = gs.scatter_tier()
        src = {"lines": 0.0, "wildcoin": 0.0, "chest": 0.0}
        for e in ev:
            if e["type"] == "lineWins":
                src["lines"] += e["total"]
            elif e["type"] == "wildEvent" and e["event"] == "coin":
                src["wildcoin"] += e["paid"]
            elif e["type"] == "chestOpened":
                src["chest"] += sum(g.get("paid", 0) for g in e["gifts"])
        src["treasure"] = max(0.0, gs.win_manager.running_bet_win - sum(src.values()))
        out.append({"win": gs.win_manager.running_bet_win, "sc": nsc, "tier": tier, "src": src,
                    "treasure": any(e["type"] == "treasureStart" for e in ev),
                    "cleared": any(e["type"] == "spinEnd" and e["stageCleared"] for e in ev),
                    "maxwin": gs.wincap_triggered})
    return out


def main():
    mode, n = sys.argv[1], int(sys.argv[2])
    ov = json.load(open(sys.argv[3])) if len(sys.argv) > 3 and sys.argv[3] != "-" else {}
    tag = sys.argv[4] if len(sys.argv) > 4 else "base"
    procs, chunk = 8, n // 8
    t0 = time.time()
    with Pool(procs) as pool:
        rows = [r for p in pool.map(worker, [(mode, k * chunk, chunk, ov) for k in range(procs)]) for r in p]
    N = len(rows)
    w = sorted(r["win"] for r in rows)
    trig = {t: sum(r["tier"] == t for r in rows) / N for t in ("bonus", "super", "epic")}
    any_trig = sum(trig.values())
    s = {
        "mode": mode, "n": N, "tag": tag, "overrides": ov,
        "mean_base_win": sum(w) / N, "median": statistics.median(w),
        "mean_base_win_no_trigger": sum(r["win"] for r in rows if r["tier"] is None) / max(1, sum(r["tier"] is None for r in rows)),
        "hit_rate": sum(x > 0 for x in w) / N, "sd": statistics.pstdev(w),
        "p": {p: w[min(N - 1, int(N * p / 100))] for p in (50, 90, 99, 99.9, 99.99)},
        "treasure_rate": sum(r["treasure"] for r in rows) / N,
        "stage0_clear_rate": sum(r["cleared"] for r in rows) / N,
        "trigger_rate": trig, "trigger_any": any_trig,
        "trigger_1_in": (1 / any_trig) if any_trig else None,
        "tier_mix_of_triggers": {t: (v / any_trig if any_trig else 0) for t, v in trig.items()},
        "maxwin_count": sum(r["maxwin"] for r in rows),
        "source_mean": {k: sum(r["src"][k] for r in rows) / N for k in rows[0]["src"]},
        "seconds": round(time.time() - t0, 1),
    }
    os.makedirs(os.path.join(H.HERE, "results"), exist_ok=True)
    base = os.path.join(H.HERE, "results", f"{tag}_{mode}_{time.strftime('%Y%m%d_%H%M%S')}")
    with open(base + ".csv", "w") as f:
        f.write("\n".join(f"{r['win']:.2f}" for r in rows))
    json.dump(s, open(base + ".json", "w"), indent=1)
    print(f"[{tag}] {mode} n={N} base mean={s['mean_base_win']:.4f} (no-trigger spins {s['mean_base_win_no_trigger']:.4f}) "
          f"median={s['median']:.2f} sd={s['sd']:.2f} hit={100 * s['hit_rate']:.1f}% "
          f"treasure={100 * s['treasure_rate']:.2f}% MaxWin={s['maxwin_count']}/{N}")
    print(f"   triggers 1 in {s['trigger_1_in'] and round(s['trigger_1_in'], 1)} | tier mix "
          + str({k: round(100 * v, 2) for k, v in s['tier_mix_of_triggers'].items()})
          + f" | p99={s['p'][99]:.1f} p99.9={s['p'][99.9]:.1f} p99.99={s['p'][99.99]:.1f} | {s['seconds']}s")
    print("   source", {k: round(v, 4) for k, v in s["source_mean"].items()})
    print("   saved", base + ".json")


if __name__ == "__main__":
    main()

"""Where does a Bonus tier's payout come from, by stage and source?

usage: python _scratch/stage_split.py TIER N overrides.json tag
Payout is attributed to the stage of the current free spin ("opening" = before
the first free spin, i.e. Epic's opening Treasure). A Treasure that stops on
Maxwin has no treasureEnd; its remainder is attributed to the last stage seen.
Saves _scratch/results/<tag>_split_<tier>_<stamp>.json
"""
import json
import os
import sys
import time
from collections import defaultdict
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tune_harness as H  # noqa: E402


def worker(args):
    tier, start, n, overrides = args
    gs, cfg = H._setup(json.loads(json.dumps(overrides)))
    pay = defaultdict(float)       # (stage, source) -> total
    reach = defaultdict(int)       # stage -> sessions that played it
    spins = defaultdict(int)       # stage -> spins played
    capped = 0
    for i in range(start, start + n):
        H._one(gs, cfg, tier, i)
        stage, seen, acc = "opening", {"opening"}, 0.0
        for e in gs.book.events:
            t = e["type"]
            if t == "freeSpinStart":
                stage = str(e["stage"])
                spins[stage] += 1
                seen.add(stage)
            elif t == "lineWins":
                pay[(stage, "lines")] += e["total"]; acc += e["total"]
            elif t == "wildEvent" and e["event"] == "coin":
                pay[(stage, "wildcoin")] += e["paid"]; acc += e["paid"]
            elif t == "chestOpened":
                v = sum(g.get("paid", 0) for g in e["gifts"])
                pay[(stage, "chest")] += v; acc += v
            elif t == "treasureEnd":
                pay[(stage, "treasure")] += e["paid"]; acc += e["paid"]
        rest = gs.win_manager.running_bet_win - acc
        if rest > 1e-6:
            pay[(stage, "treasure_capped")] += rest
        capped += gs.wincap_triggered
        for s in seen:
            reach[s] += 1
    return dict(pay), dict(reach), dict(spins), capped


def main():
    tier, n = sys.argv[1], int(sys.argv[2])
    ov = json.load(open(sys.argv[3]))
    tag = sys.argv[4] if len(sys.argv) > 4 else "split"
    procs, chunk = 8, n // 8
    with Pool(procs) as pool:
        parts = pool.map(worker, [(tier, k * chunk, chunk, ov) for k in range(procs)])
    N = chunk * procs
    pay, reach, spins, capped = defaultdict(float), defaultdict(int), defaultdict(int), 0
    for p, r, s, c in parts:
        for k, v in p.items():
            pay[k] += v
        for k, v in r.items():
            reach[k] += v
        for k, v in s.items():
            spins[k] += v
        capped += c
    order = ["opening", "1", "2", "3", "4", "5", "endless"]
    srcs = ["lines", "wildcoin", "chest", "treasure", "treasure_capped"]
    rows = {}
    total = sum(pay.values()) / N
    print(f"{tier} n={N} mean={total:.1f} MaxWin={capped}/{N}")
    print(f"{'stage':8s} {'reach%':>7s} {'spins':>6s} " + " ".join(f"{s:>10s}" for s in srcs) + f" {'total':>9s} {'share':>6s}")
    for st in order:
        if st not in reach:
            continue
        vals = {s: pay.get((st, s), 0) / N for s in srcs}
        t = sum(vals.values())
        rows[st] = {"reach_pct": 100 * reach[st] / N, "spins_per_session": spins.get(st, 0) / N, **vals, "total": t}
        print(f"{st:8s} {100 * reach[st] / N:7.1f} {spins.get(st, 0) / N:6.2f} "
              + " ".join(f"{vals[s]:10.1f}" for s in srcs) + f" {t:9.1f} {100 * t / total:5.1f}%")
    os.makedirs(os.path.join(H.HERE, "results"), exist_ok=True)
    out = os.path.join(H.HERE, "results", f"{tag}_split_{tier}_{time.strftime('%Y%m%d_%H%M%S')}.json")
    json.dump({"tier": tier, "n": N, "mean": total, "maxwin": capped, "rows": rows, "overrides": ov}, open(out, "w"), indent=1)
    print("saved", out)


if __name__ == "__main__":
    main()

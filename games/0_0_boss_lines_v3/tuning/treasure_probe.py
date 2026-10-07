"""One tier's Treasures: cells, paid, Global at end, kinds, rounds. usage: python tuning/treasure_probe.py TIER N overrides.json"""
import json, os, statistics as S, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tune_harness as H
if __name__ == "__main__":
    tier, n = sys.argv[1], int(sys.argv[2])
    gs, cfg = H._setup(json.load(open(sys.argv[3])))
    rows = []
    for i in range(n):
        H._one(gs, cfg, tier, i)
        cur = None
        for e in gs.book.events:
            if e["type"] == "treasureStart":
                cur = {"cells": len(e["cells"]), "rounds": 0, "kinds": {}, "coin_sum": 0.0}
            elif e["type"] == "treasureSymbols" and cur:
                cur["rounds"] += 1
                for c in e["cells"]:
                    cur["kinds"][c["kind"]] = cur["kinds"].get(c["kind"], 0) + 1
                    if c["kind"] == "coin": cur["coin_sum"] += c["value"]
            elif e["type"] == "treasureEnd" and cur:
                cur.update(paid=e["paid"], total=e["total"], g=e["globalMult"]); rows.append(cur); cur = None
    paid = sorted(r["paid"] for r in rows)
    k = len(rows)
    print(f"{tier}: {k} Treasures, paid mean {sum(paid)/k:.1f} median {S.median(paid):.1f} p25 {paid[k//4]:.1f} p75 {paid[3*k//4]:.1f} p90 {paid[9*k//10]:.1f}")
    print(f"  cells mean {S.mean(r['cells'] for r in rows):.1f} median {S.median(r['cells'] for r in rows)}; rounds mean {S.mean(r['rounds'] for r in rows):.2f}; Global at end mean {S.mean(r['g'] for r in rows):.2f}")
    print(f"  coin face sum (first draws) median {S.median(r['coin_sum'] for r in rows):.1f}; total before Global median {S.median(r['total'] for r in rows):.1f}")
    for lo, hi in ((0, 25), (25, 60), (60, 90), (90, 100)):
        sel = sorted(rows, key=lambda r: r["paid"])[k*lo//100:k*hi//100]
        kinds = {}
        for r in sel:
            for kk, v in r["kinds"].items(): kinds[kk] = kinds.get(kk, 0) + v / len(sel)
        print(f"  p{lo}-{hi}: paid {S.mean(r['paid'] for r in sel):.1f} cells {S.mean(r['cells'] for r in sel):.1f} g {S.mean(r['g'] for r in sel):.2f} coinface {S.mean(r['coin_sum'] for r in sel):.1f} kinds/Treasure {{{', '.join(f'{a}: {b:.2f}' for a, b in sorted(kinds.items()))}}}")

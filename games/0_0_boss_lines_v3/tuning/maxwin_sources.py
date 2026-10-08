"""Where do Max Wins (and big wins) come from?

usage: python tuning/maxwin_sources.py TIER N overrides.json TAG [big_threshold]
For every session that hits 25,000x (and every session >= big_threshold, default 5000x):
  * direct coin: a 25,000x coin appeared (Treasure symbol, chest gift or Wild coin)
  * otherwise the source of the payment that crossed the cap / most of the win:
    lines, Wild coin, chest, Treasure (split by whether Golden/Clover/Global multiplied it)
Saves tuning/results/TAG_maxwinsrc_TIER_<time>.json
"""
import json
import os
import sys
import time
from collections import Counter
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tune_harness as H  # noqa: E402


def classify(ev, total, cap):
    coin = any(
        (e["type"] == "treasureSymbols" and any(c["kind"] == "coin" and c["value"] >= cap for c in e["cells"]))
        or (e["type"] == "chestOpened" and any(g.get("value", 0) >= cap for g in e["gifts"]))
        or (e["type"] == "wildEvent" and e.get("value", 0) >= cap)
        for e in ev)
    if coin:
        return "xu 25.000x"
    src = Counter()
    treasure_mod = Counter()
    mods = set()
    for e in ev:
        t = e["type"]
        if t == "treasureStart":
            mods = set()
        elif t in ("treasureClover", "treasureGoldenClover", "treasureStar", "treasureMagnet"):
            mods.add({"treasureClover": "Clover", "treasureGoldenClover": "Golden", "treasureStar": "Star",
                      "treasureMagnet": "Nam châm"}[t])
        elif t == "treasureSymbols" and e.get("globalMult", 1) > 1:
            mods.add("Global")
        elif t == "lineWins":
            src["dòng"] += sum(w["win"] for w in e["wins"])
        elif t == "wildEvent" and e["event"] == "coin":
            src["xu Wild"] += e["paid"]
        elif t == "chestOpened":
            src["rương"] += sum(g.get("paid", 0) for g in e["gifts"])
        elif t in ("treasureEnd", "treasureMaxwin"):
            v = e.get("paid", e.get("value", 0))
            src["Treasure"] += v
            for m in mods or {"chỉ xu"}:
                treasure_mod[m] += v
    acc = sum(src.values())
    if total - acc > 1:  # Treasure stopped by the cap has no treasureEnd
        src["Treasure"] += total - acc
        for m in mods or {"chỉ xu"}:
            treasure_mod[m] += total - acc
    main = src.most_common(1)[0][0] if src else "?"
    if main == "Treasure" and treasure_mod:
        main = "Treasure (" + "+".join(sorted(k for k, v in treasure_mod.items() if v >= 0.25 * src["Treasure"])) + ")"
    share = max(src.values()) / max(1e-9, sum(src.values())) if src else 0
    return main if share >= 0.5 else "cộng dồn nhiều nguồn"


def worker(args):
    tier, start, n, ov, big = args
    gs, cfg = H._setup(json.loads(json.dumps(ov)))
    out = []
    for i in range(start, start + n):
        H._one(gs, cfg, tier, i)
        w = gs.win_manager.running_bet_win
        if w >= big:
            out.append({"win": w, "maxwin": gs.wincap_triggered, "src": classify(gs.book.events, w, cfg.wincap)})
    return out


def main():
    tier, n, ov, tag = sys.argv[1], int(sys.argv[2]), json.load(open(sys.argv[3])), sys.argv[4]
    big = float(sys.argv[5]) if len(sys.argv) > 5 else 5000.0
    p = H.PROCS
    chunk = n // p
    t0 = time.time()
    with Pool(p) as pool:
        rows = [r for part in pool.map(worker, [(tier, k * chunk, chunk, ov, big) for k in range(p)]) for r in part]
    N = chunk * p
    mw = [r for r in rows if r["maxwin"]]
    bg = [r for r in rows if not r["maxwin"]]
    res = {"tier": tier, "n": N, "big_threshold": big, "maxwin": len(mw), "big_not_max": len(bg),
           "maxwin_sources": Counter(r["src"] for r in mw), "big_sources": Counter(r["src"] for r in bg),
           "seconds": round(time.time() - t0)}
    os.makedirs(os.path.join(H.HERE, "results"), exist_ok=True)
    out = os.path.join(H.HERE, "results", f"{tag}_maxwinsrc_{tier}_{time.strftime('%Y%m%d_%H%M%S')}.json")
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()

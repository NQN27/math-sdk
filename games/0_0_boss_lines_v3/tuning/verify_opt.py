"""usage: python tuning/verify_opt.py  - RTP and per-tier/feature means of the optimized lookups in library/publish_files"""
import csv, json, os
GAME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(GAME, "library")
COST = {"base": 1, "ante": 3, "feature": 500, "buy3": 100, "buy4": 300, "random_bonus": 400}
for mode, cost in COST.items():
    f = os.path.join(LIB, "publish_files", f"lookUpTable_{mode}_0.csv")
    if not os.path.exists(f):
        print(mode, "no optimized lookup"); continue
    rows = {int(r[0]): (float(r[1]), float(r[2]) / 100) for r in csv.reader(open(f))}
    W = sum(w for w, _ in rows.values())
    rtp = sum(w * p for w, p in rows.values()) / W / cost
    zero = sum(w for w, p in rows.values() if p == 0) / W
    mw = sum(w for w, p in rows.values() if p >= 25000) / W
    out = [f"{mode:13s} RTP {100 * rtp:.4f}%  0x {100 * zero:.2f}%  MaxWin 1 in {1 / mw:,.0f}" if mw else f"{mode:13s} RTP {100 * rtp:.4f}%  0x {100 * zero:.2f}%"]
    forces = json.load(open(os.path.join(LIB, "forces", f"force_record_{mode}.json")))
    for r in forces:
        s = r["search"]
        if len(s) == 1 and s[0]["name"] in ("bonus_tier", "feature", "maxwin_tier", "maxwin_feature"):
            ids = [i for i in r["bookIds"] if i in rows]
            w = sum(rows[i][0] for i in ids)
            if not w:
                continue
            mean = sum(rows[i][0] * rows[i][1] for i in ids) / w
            out.append(f"   {s[0]['name']}={s[0]['value']}: share {100 * w / W:.4f}% (1 in {W / w:,.1f}), mean {mean:,.2f}")
    print("\n".join(out))

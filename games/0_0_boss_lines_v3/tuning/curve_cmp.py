"""usage: python tuning/curve_cmp.py TAG [TAG...]  - Bonus percentiles vs designer curve"""
import glob, json, sys
curve = {float(a): float(b) for a, b in (l.strip().split(",") for l in open("tuning/targets/bonus_curve_2026-10-09.csv") if l[0].isdigit())}
P = (1, 5, 10, 25, 40, 50, 60, 75, 80, 85, 90, 95, 98, 99, 99.5, 99.9)
print(f"{'tag':6s} {'mean':>6s} {'clr':>5s} {'lines':>5s} " + " ".join(f"{'p'+format(p,'g'):>6s}" for p in P) + "  fit(5..99.5)")
print(f"{'target':6s} {88.88:6.1f} {'':5s} {'':5s} " + " ".join(f"{curve[p]:6.1f}" for p in P))
for tag in sys.argv[1:]:
    f = sorted(glob.glob(f"tuning/results/{tag}_bonus_2*.csv"))[-1]
    w = sorted(float(x) for x in open(f).read().split()); n = len(w)
    j = json.load(open(f[:-4] + ".json"))
    q = lambda p: w[min(n - 1, int(n * p / 100))]
    ok = sum(abs(q(p) / v - 1) <= 0.15 for p, v in curve.items() if 5 <= p <= 99.5)
    tot = sum(1 for p in curve if 5 <= p <= 99.5)
    clr = sum(int(k) * v for k, v in j["diag"]["stage_clears_hist"].items()) / n
    src = j["source_mean"]; ln = src.get("lines", 0)
    print(f"{tag:6s} {sum(w)/n:6.1f} {clr:5.2f} {ln:5.1f} " + " ".join(f"{q(p):6.1f}" for p in P) + f"  {ok}/{tot}")

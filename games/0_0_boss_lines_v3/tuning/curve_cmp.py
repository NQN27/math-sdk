"""usage: python tuning/curve_cmp.py [--tier bonus|super|epic] [--dir DIR] TAG [TAG...]
Tier percentiles vs the designer curve (Google Sheet 2026-10-14), one row per tag, plus the
percentiles outside +-15% (p5..p99.5) and the Max Win count."""
import glob, json, sys

args = sys.argv[1:]
tier, rdir = "bonus", "tuning/results"
while args and args[0].startswith("--"):
    if args[0] == "--tier":
        tier = args[1]
    elif args[0] == "--dir":
        rdir = args[1]
    args = args[2:]
MEAN = {"bonus": 91.0, "super": 245.0, "epic": 2045.0}[tier]
curve = {float(a): float(b) for a, b in (l.strip().split(",") for l in open(f"tuning/targets/{tier}_curve_2026-10-14.csv") if l[0].isdigit())}
P = [p for p in (1, 5, 10, 25, 40, 50, 60, 75, 80, 85, 90, 95, 98, 99, 99.5, 99.9) if p in curve]
print(f"{'tag':8s} {'mean':>7s} {'clr':>5s} {'MW':>4s} " + " ".join(f"{'p'+format(p,'g'):>7s}" for p in P) + "  fit")
print(f"{'target':8s} {MEAN:7.1f} {'':5s} {'':4s} " + " ".join(f"{curve[p]:7.1f}" for p in P))
bads = []
for tag in args:
    f = sorted(glob.glob(f"{rdir}/{tag}_{tier}_2*.csv"))[-1]
    w = sorted(float(x) for x in open(f).read().split()); n = len(w)
    j = json.load(open(f[:-4] + ".json"))
    q = lambda p: w[min(n - 1, int(n * p / 100))]
    chk = [(p, v) for p, v in curve.items() if 5 <= p <= 99.5]
    bad = [f"p{p:g}:{q(p) / v - 1:+.0%}" for p, v in chk if abs(q(p) / v - 1) > 0.15]
    clr = sum(int(k) * v for k, v in j["diag"]["stage_clears_hist"].items()) / n
    print(f"{tag:8s} {sum(w) / n:7.1f} {clr:5.2f} {j['maxwin_count']:4d} " + " ".join(f"{q(p):7.1f}" for p in P)
          + f"  {len(chk) - len(bad)}/{len(chk)}")
    bads.append(f"{tag} off: " + " ".join(bad))
print("\n".join(bads))

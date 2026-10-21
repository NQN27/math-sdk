"""RTP of N random sessions (N = 5/20/100/1000) if the payout distribution matched the designer's curve exactly.

usage: python tuning/sample_rtp_curve.py [--reps 1000]
Each curve row (percentile p_k, value v_k) is a bucket (p_{k-1}, p_k] paying v_k; the last bucket (to p100) is
the Max Win. Price = target mean / 0.967, the same convention as sample_rtp_lookup.py, so the two tables compare.
"""
import bisect
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CURVES = {"bonus": ("bonus", 91.0), "super": ("super", 245.0), "epic": ("epic", 2045.0),
          "heroic": ("heroic", 403.0), "treasure_hunt": ("treasure_hunt", 564.0)}
SAMPLE_N = (5, 20, 100, 1000)
REPS = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 1000

rng = random.Random(20261021)
print(f"RTP of N random sessions drawn from the designer curve, median of {REPS} repeats (p10, p90, p99)")
for name, (f, mean) in CURVES.items():
    rows = [tuple(map(float, l.strip().split(","))) for l in open(os.path.join(HERE, "targets", f"{f}_curve_2026-10-14.csv"))
            if l[0].isdigit()]
    cum = [p / 100 for p, _ in rows]
    vals = [v for _, v in rows]
    curve_mean = sum((p - q) / 100 * v for (p, v), q in zip(rows, [0.0] + [p for p, _ in rows[:-1]]))
    draw = lambda: vals[min(len(vals) - 1, bisect.bisect_left(cum, rng.random()))]
    price = mean / 0.967
    out = []
    for n in SAMPLE_N:
        v = sorted(sum(draw() for _ in range(n)) / (n * price) for _ in range(REPS))
        out.append(f"N={n}: {100 * v[REPS // 2]:6.1f}% (p10 {100 * v[REPS // 10]:5.1f}, p90 {100 * v[9 * REPS // 10]:6.1f}, "
                   f"p99 {100 * v[99 * REPS // 100]:6.1f})")
    print(f"{name:14s} (curve mean {curve_mean:7.1f}, target {mean:g}) " + "  ".join(out))

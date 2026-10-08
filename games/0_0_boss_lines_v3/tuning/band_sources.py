"""Where the money comes from inside each percentile band of one tier.

usage: python tuning/band_sources.py TIER N overrides.json
Prints, for sessions in p0-5, p5-25, p25-60, p60-75, p75-90, p90-99, p99-100:
mean total and mean lines / wild coin / chest / Treasure, stage clears, spins.
"""
import json
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tune_harness as H  # noqa: E402

BANDS = [(0, 5), (5, 25), (25, 60), (60, 75), (75, 90), (90, 99), (99, 100)]


def main():
    tier, n = sys.argv[1], int(sys.argv[2])
    ov = json.load(open(sys.argv[3]))
    chunk = n // H.PROCS
    with Pool(H.PROCS) as pool:
        parts = pool.map(H.worker, [(tier, k * chunk, chunk, ov) for k in range(H.PROCS)])
    rows = sorted((r for p, _ in parts for r in p), key=lambda r: r["win"])
    N = len(rows)
    print(f"{tier} n={N} mean={sum(r['win'] for r in rows) / N:.1f}")
    print(f"{'band':9s} {'win':>8s} {'lines':>8s} {'wildcoin':>8s} {'chest':>8s} {'treasure':>8s} {'clears':>6s} {'spins':>6s}")
    for lo, hi in BANDS:
        sel = rows[int(N * lo / 100):int(N * hi / 100)]
        if not sel:
            continue
        k = len(sel)

        def avg(f):
            return sum(f(r) for r in sel) / k
        print(f"p{lo:>2d}-{hi:<3d}  {avg(lambda r: r['win']):8.1f} {avg(lambda r: r['src']['lines']):8.1f} "
              f"{avg(lambda r: r['src']['wildcoin']):8.1f} {avg(lambda r: r['src']['chest']):8.1f} "
              f"{avg(lambda r: r['src']['treasure']):8.1f} {avg(lambda r: r['treasures']):6.2f} {avg(lambda r: r['spins']):6.2f}")


if __name__ == "__main__":
    main()

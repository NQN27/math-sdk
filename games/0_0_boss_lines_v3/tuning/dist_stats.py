"""Distribution stats from tune_harness CSVs (one payout per session).

usage: python tuning/dist_stats.py TAG [TIER ...]
  reads the newest tuning/results/<TAG>_<tier>_*.csv for each tier (default bonus super epic)
Prints mean, median, sd, var, CV, standard error of the mean, percentiles and the
share of sessions per band of the tier's mean target, plus the source split /
stage reach / Max Win count from the matching .json summary.
"""
import glob
import json
import os
import statistics as S
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGETS = {"bonus": 88.9, "super": 240.0, "epic": 1492.5}


def main():
    tag = sys.argv[1]
    tiers = sys.argv[2:] or ["bonus", "super", "epic"]
    for tier in tiers:
        files = sorted(glob.glob(os.path.join(HERE, "results", f"{tag}_{tier}_*.csv")))
        if not files:
            print(f"{tier}: no CSV for tag {tag}")
            continue
        f = files[-1]
        w = sorted(float(x) for x in open(f).read().split())
        n = len(w)
        m = sum(w) / n
        sd = S.pstdev(w)

        def pct(p):
            return w[min(n - 1, int(n * p / 100))]

        tgt = TARGETS.get(tier)
        print(f"{tier}: {os.path.basename(f)} n={n} mean={m:.2f} median={S.median(w):.2f} sd={sd:.1f} "
              f"var={sd * sd:.0f} cv={sd / m:.2f} se_mean={sd / n ** .5:.1f}")
        print("  percentiles", {p: round(pct(p), 1) for p in (1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9)},
              "min", w[0], "max", w[-1])
        if tgt:
            edges = [0, .5 * tgt, tgt, 2 * tgt, 5 * tgt, 10 * tgt, 25000.01]
            bands = [round(100 * sum(lo <= x < hi for x in w) / n, 2) for lo, hi in zip(edges, edges[1:])]
            print(f"  % sessions in [<0.5, 0.5-1, 1-2, 2-5, 5-10, >10] x target {tgt}: {bands}")
        js = f[:-4] + ".json"
        if os.path.exists(js):
            j = json.load(open(js))
            print("  source", {k: round(v, 1) for k, v in j["source_mean"].items()},
                  "| spins", round(j["spins_mean"], 2), "| treasures", round(j["treasures_mean"], 2),
                  "| last stage %", j["last_stage_pct"], "| MaxWin", j["maxwin_count"])


if __name__ == "__main__":
    main()

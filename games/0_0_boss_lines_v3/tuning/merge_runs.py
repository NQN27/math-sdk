"""Merge chunked harness runs (same tier, different TUNE_START) into one result.

usage: python tuning/merge_runs.py TIER OUT_TAG IN_TAG [IN_TAG ...]
Uses the newest tuning/results/<IN_TAG>_<TIER>_*.csv/.json of each input tag and writes
tuning/results/<OUT_TAG>_<TIER>_<time>.csv/.json in the same format as tune_harness.py.
"""
import glob
import json
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def newest(tag, tier):
    f = sorted(glob.glob(os.path.join(HERE, "results", f"{tag}_{tier}_2*.csv")))[-1]
    return f, json.load(open(f[:-4] + ".json"))


def merge_diag(ds):
    out = {}
    tc = sum(d.get("treasure_count", 0) for d in ds)
    for d in ds:
        for k, v in d.items():
            if k in ("treasure_paid_mean", "treasure_count"):
                continue
            if isinstance(v, dict):
                o = out.setdefault(k, {})
                for kk, vv in v.items():
                    o[kk] = o.get(kk, 0) + vv
            elif isinstance(v, (int, float)):
                out[k] = out.get(k, 0) + v
    out["treasure_count"] = tc
    out["treasure_paid_mean"] = sum(d.get("treasure_paid_mean", 0) * d.get("treasure_count", 0) for d in ds) / tc if tc else 0.0
    return out


def main():
    tier, out_tag, tags = sys.argv[1], sys.argv[2], sys.argv[3:]
    wins, js = [], []
    for tag in tags:
        f, j = newest(tag, tier)
        wins += [float(x) for x in open(f).read().split()]
        js.append(j)
    starts = sorted((j.get("start", 0), j["n"]) for j in js)
    for (s1, n1), (s2, _) in zip(starts, starts[1:]):
        assert s1 + n1 <= s2, f"overlapping seed ranges {starts}"
    N = len(wins)
    w = sorted(wins)
    src = {k: sum(j["source_mean"][k] * j["n"] for j in js) / N for k in js[0]["source_mean"]}
    summary = {
        "tier": tier, "n": N, "tag": out_tag, "merged_from": tags, "starts": starts, "overrides": js[0]["overrides"],
        "mean": sum(w) / N, "median": statistics.median(w),
        "p": {p: w[min(N - 1, int(N * p / 100))] for p in (10, 25, 50, 75, 90, 95, 99, 99.9)},
        "maxwin_count": sum(j["maxwin_count"] for j in js), "source_mean": src,
        "spins_mean": sum(j["spins_mean"] * j["n"] for j in js) / N,
        "treasures_mean": sum(j["treasures_mean"] * j["n"] for j in js) / N,
        "seconds": sum(j["seconds"] for j in js), "diag": merge_diag([j["diag"] for j in js]),
    }
    summary["maxwin_rate"] = summary["maxwin_count"] / N
    base = os.path.join(HERE, "results", f"{out_tag}_{tier}_{time.strftime('%Y%m%d_%H%M%S')}")
    open(base + ".csv", "w").write("\n".join(f"{x:.2f}" for x in wins))
    json.dump(summary, open(base + ".json", "w"), indent=1)
    print(f"[{out_tag}] {tier} n={N} mean={summary['mean']:.2f} MaxWin={summary['maxwin_count']}/{N} saved {base}.json")


if __name__ == "__main__":
    main()

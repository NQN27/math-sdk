"""RTP of N random rounds (N = 5/20/100/1000), 100 repeats, median and p10/p90 - read straight from the optimized
lookups in library/publish_files (the shipped weights), per bet mode and per Bonus tier.

usage: python tuning/sample_rtp_lookup.py [--reps 100]
Tier price = tier mean target / 0.967 (same convention as spec_check.py); mode price = mode cost.
"""
import bisect
import csv
import itertools
import json
import os
import random
import sys

GAME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(GAME, "library")
COST = {"base": 1, "ante": 3, "feature": 500, "buy3": 100, "buy4": 300, "random_bonus": 400}
TIER_MEAN = {"bonus": 91.0, "super": 245.0, "epic": 2045.0}
FEATURE_MEAN = {"heroic": 403.0, "treasure_hunt": 564.0}
SAMPLE_N = (5, 20, 100, 1000)
REPS = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 100


def sampler(pairs):
    """pairs [(weight, pay)] -> draw(rng) by weight"""
    cum = list(itertools.accumulate(w for w, _ in pairs))
    pays = [p for _, p in pairs]
    return lambda rng: pays[bisect.bisect_right(cum, rng.random() * cum[-1])]


def line(name, draw, price, rng):
    out = []
    for n in SAMPLE_N:
        v = sorted(sum(draw(rng) for _ in range(n)) / (n * price) for _ in range(REPS))
        out.append(f"N={n}: {100 * v[REPS // 2]:6.1f}% (p10 {100 * v[REPS // 10]:5.1f}, p90 {100 * v[9 * REPS // 10]:6.1f})")
    print(f"{name:24s} " + "  ".join(out))


rng = random.Random(20261019)
print(f"RTP of N random rounds, median of {REPS} repeats (p10, p90)")
for mode, cost in COST.items():
    rows = {int(r[0]): (int(r[1]), int(r[2]) / 100) for r in csv.reader(open(os.path.join(LIB, "publish_files", f"lookUpTable_{mode}_0.csv")))}
    line(f"{mode}", sampler(list(rows.values())), cost, rng)
    forces = json.load(open(os.path.join(LIB, "forces", f"force_record_{mode}.json")))
    for r in forces:
        s = r["search"]
        # (Feature's own bonus_tier books also carry the Treasure hunt spin's pay, so only its feature split is shown)
        if len(s) == 1 and ((s[0]["name"] == "bonus_tier" and mode in ("buy3", "buy4", "random_bonus"))
                            or (s[0]["name"] == "feature" and mode == "feature")):
            key = s[0]["value"]
            m = TIER_MEAN.get(key) or FEATURE_MEAN.get(key)
            pairs = [rows[i] for i in r["bookIds"] if i in rows and rows[i][0] > 0]
            if len(pairs) >= 20:
                line(f"  {mode}:{key}", sampler(pairs), m / 0.967, rng)

import random
import sys

N_ROWS = 307
OUT = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\reels\UP_Reels.csv"

# Baseline = the ORIGINAL, already-validated UP_Reels.csv density (measured
# ~1061x avg). "Direction" = a modest enrichment target (more H/W/Power,
# less L). We blend continuously between them with a single scalar t in
# [0,1] (t=0 -> baseline, t=1 -> full direction) since integer weight nudges
# turned out too coarse - the average payout is extremely sensitive/non-
# linear near this density (whole-board-explode + cascade + Both-Ways
# compounding), so we need fine-grained control to bisect onto a target.
BASELINE_OTHER = {
    "L1": 74, "L2": 60, "L3": 61, "L4": 47, "L5": 40,
    "H1": 7, "H2": 5, "H3": 2, "H4": 2,
    "W": 4, "PWM": 1, "PGM": 0,
    "PXW": 0, "PXP": 0, "PBS": 0, "PMY": 0, "PAL": 0,
    "EL": 2, "BO": 2,
}
DIRECTION_OTHER = {
    "L1": 40, "L2": 34, "L3": 33, "L4": 25, "L5": 20,
    "H1": 16, "H2": 12, "H3": 8, "H4": 6,
    "W": 12, "PWM": 4, "PGM": 4,
    "PXW": 2, "PXP": 2, "PBS": 2, "PMY": 2, "PAL": 2,
    "EL": 4, "BO": 4,
}
BASELINE_COL0 = {
    "L1": 76, "L2": 61, "L3": 62, "L4": 48, "L5": 40,
    "H1": 7, "H2": 5, "H3": 2, "H4": 2,
    "EL": 2, "BO": 2,
}
DIRECTION_COL0 = {
    "L1": 46, "L2": 39, "L3": 38, "L4": 29, "L5": 23,
    "H1": 18, "H2": 14, "H3": 9, "H4": 7,
    "EL": 4, "BO": 4,
}


def blend(baseline, direction, t):
    keys = sorted(set(baseline) | set(direction))
    out = {}
    for k in keys:
        b = baseline.get(k, 0)
        d = direction.get(k, 0)
        out[k] = (1 - t) * b + t * d
    return out


def build_column(weights, n, rng):
    names = list(weights.keys())
    wts = list(weights.values())
    return rng.choices(names, weights=wts, k=n)


def main(t, seed=1):
    rng = random.Random(seed)
    w_col0 = blend(BASELINE_COL0, DIRECTION_COL0, t)
    w_other = blend(BASELINE_OTHER, DIRECTION_OTHER, t)
    cols = [build_column(w_col0, N_ROWS, rng)]
    for _ in range(4):
        cols.append(build_column(w_other, N_ROWS, rng))
    with open(OUT, "w", newline="") as f:
        for r in range(N_ROWS):
            f.write(",".join(cols[c][r] for c in range(5)) + "\n")
    print(f"wrote {OUT} at t={t}")


if __name__ == "__main__":
    t = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    main(t, seed)

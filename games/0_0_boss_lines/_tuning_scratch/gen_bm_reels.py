import random
import sys

N_ROWS = 307
OUT = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\reels\BM_Reels.csv"

# Baseline = current validated BM_Reels.csv density (measured ~78.34x avg,
# target 80.13x, unchanged from old spec). This reel has NO power symbols
# and is NOT fat-tailed (zero wincap hits at n=20000, SE=2.72) unlike
# Super_BM/UP_Reels, so a mild L->H/W shift should move the mean close to
# linearly with t. Small nudge only (~+2.3% needed).
BASELINE_OTHER = {
    "L1": 65, "L2": 52, "L3": 53, "L4": 41, "L5": 34,
    "H1": 22, "H2": 17, "H3": 8, "H4": 7,
    "W": 2, "BO": 3, "EL": 3,
}
# WRONG DIRECTION FOUND: shifting L->H density diluted cluster formation and
# LOWERED the average (78.34 -> 43.75 at t=0.5) despite H paying more per
# hit - this is a cluster/ways-pay mechanic, so concentration matters more
# than per-symbol paytable value. New direction: keep L/H ratios ~fixed,
# only add wild (W) density (wilds boost every cluster regardless of type),
# taken proportionally from all symbols.
DIRECTION_OTHER = {
    "L1": 61, "L2": 49, "L3": 50, "L4": 38, "L5": 32,
    "H1": 21, "H2": 16, "H3": 7, "H4": 7,
    "W": 10, "BO": 3, "EL": 3,
}
BASELINE_COL0 = {
    "L1": 65, "L2": 52, "L3": 54, "L4": 42, "L5": 35,
    "H1": 22, "H2": 17, "H3": 7, "H4": 7,
    "BO": 3, "EL": 3,
}
DIRECTION_COL0 = {
    "L1": 61, "L2": 49, "L3": 51, "L4": 39, "L5": 33,
    "H1": 21, "H2": 16, "H3": 7, "H4": 7,
    "W": 6, "BO": 3, "EL": 3,
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

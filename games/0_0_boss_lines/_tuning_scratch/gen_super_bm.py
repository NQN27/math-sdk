import random
import sys

N_ROWS = 307
OUT = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\reels\Super_BM.csv"

# Baseline = current validated Super_BM.csv density (measured ~250.91x avg,
# target was 250.00x). New target is 240.77x (~4% lower) - blend toward a
# mild "less rich" direction (more L, less H/W/Power), same continuous-blend
# approach as UP_Reels.csv given how sensitive this mechanic is to density.
BASELINE_OTHER = {
    "L1": 62, "L2": 50, "L3": 52, "L4": 40, "L5": 32,
    "H1": 22, "H2": 17, "H3": 7, "H4": 7,
    "W": 9, "PWM": 1.4, "PGM": 0.4, "PXW": 0.4, "PXP": 0.2,
    "PBS": 0.2, "PMY": 0.2, "PAL": 0.2,
    "EL": 3, "BO": 3,
}
DIRECTION_OTHER = {
    "L1": 72, "L2": 58, "L3": 60, "L4": 46, "L5": 37,
    "H1": 17, "H2": 13, "H3": 5, "H4": 5,
    "W": 6, "PWM": 1, "PGM": 0.3, "PXW": 0.3, "PXP": 0.15,
    "PBS": 0.15, "PMY": 0.15, "PAL": 0.15,
    "EL": 3, "BO": 3,
}
BASELINE_COL0 = {
    "L1": 65, "L2": 53, "L3": 54, "L4": 42, "L5": 35,
    "H1": 22, "H2": 16, "H3": 7, "H4": 7,
    "EL": 3, "BO": 3,
}
DIRECTION_COL0 = {
    "L1": 75, "L2": 61, "L3": 62, "L4": 48, "L5": 40,
    "H1": 17, "H2": 12, "H3": 5, "H4": 5,
    "EL": 3, "BO": 3,
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

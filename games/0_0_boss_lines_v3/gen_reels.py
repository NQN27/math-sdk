"""Reel strip generator for Boss Lines v3 (6 columns x 5 rows).

Structure follows Proposal_2026-10-06.docx; every DENSITY below is a
placeholder until tuning.

  * Six independent columns, one RNG stream per (file, column).
  * Symbols: L1-L4, H1-H5, W, SC, weapons AR (arrow) / BM (bomb) /
    SW (sword) / LT (lightning).
  * Each Bonus stage reel leaves out the low symbols that stage removes
    (stage 2 no L1, stage 3 no L1-L2, ..., stage 5 and Endless no L at all).
  * Specials (SC and weapons) are PLACED with circular spacing so a 5-row
    window never shows two in one column (Scatter: max 1 per column).
  * The Heroic reel has no Scatter (Heroic spin never shows Scatter).

Run from this folder:  python gen_reels.py   (reproducible: fixed seeds)
"""
import os
import random
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REELS_DIR = os.path.join(HERE, "reels")
N_COLS = 6
N_ROWS_STRIP = 300

LOWS = ["L1", "L2", "L3", "L4"]
SHAPE = {"L1": 60, "L2": 52, "L3": 46, "L4": 40, "H1": 22, "H2": 17, "H3": 12, "H4": 8, "H5": 5}
WEAPON_MIX = {"AR": 35, "BM": 25, "SW": 25, "LT": 15}

# (wild %, scatter %, weapon %) per reel. Placeholders.
# Bonus reels: 1 Scatter per column (0.34%). At 1% (3 per column) a Bonus
# spin collected ~1.38 extra spins on average (every refilled cell can draw a
# Scatter), so the Bonus never ran out of spins - see README.
REEL_SPECS = {
    "BR0": dict(removed=0, wild=5.0, sc=1.4, weapon=1.5),
    "ANTE": dict(removed=0, wild=5.0, sc=3.0, weapon=1.5),
    "HERO": dict(removed=4, wild=8.0, sc=0.0, weapon=3.0),  # Heroic fights stage 5 -> no L
    "BON_S1": dict(removed=0, wild=6.0, sc=0.34, weapon=2.0),
    "BON_S2": dict(removed=1, wild=5.5, sc=0.34, weapon=2.0),
    "BON_S3": dict(removed=2, wild=5.0, sc=0.34, weapon=2.0),
    "BON_S4": dict(removed=3, wild=4.5, sc=0.34, weapon=2.0),
    "BON_S5": dict(removed=4, wild=4.0, sc=0.34, weapon=2.0),
    "BON_E": dict(removed=4, wild=4.0, sc=0.34, weapon=2.5),
}


def seed_for(name, col):
    return zlib.crc32(f"v3:{name}:{col}".encode()) & 0xFFFFFFFF


def place_specials(n, counts, rng, gap=5):
    items = [s for s, k in counts.items() for _ in range(k)]
    rng.shuffle(items)
    placed = {}
    for sym in items:
        for _ in range(500):
            row = rng.randrange(n)
            if all(min((row - r2) % n, (r2 - row) % n) >= gap for r2 in placed):
                placed[row] = sym
                break
        else:
            raise RuntimeError(f"cannot place {sym} in {n} rows with gap {gap}")
    return placed


def build_column(name, col, spec):
    rng = random.Random(seed_for(name, col))
    n = N_ROWS_STRIP
    counts = {}
    if spec["sc"] > 0:
        counts["SC"] = max(1, round(spec["sc"] / 100 * n))
    total_w = round(spec["weapon"] / 100 * n)
    ratio = sum(WEAPON_MIX.values())
    for sym, r in WEAPON_MIX.items():
        k = round(total_w * r / ratio)
        if k:
            counts[sym] = k
    placed = place_specials(n, counts, rng)
    shape = {k: v for k, v in SHAPE.items() if k not in LOWS[: spec["removed"]]}
    n_fill = n - len(placed)
    n_wild = min(n_fill, round(spec["wild"] / 100 * n))
    filler = ["W"] * n_wild + rng.choices(list(shape), weights=list(shape.values()), k=n_fill - n_wild)
    rng.shuffle(filler)
    it = iter(filler)
    return [placed[r] if r in placed else next(it) for r in range(n)]


def main():
    os.makedirs(REELS_DIR, exist_ok=True)
    for name, spec in REEL_SPECS.items():
        cols = [build_column(name, c, spec) for c in range(N_COLS)]
        with open(os.path.join(REELS_DIR, f"{name}.csv"), "w", newline="") as f:
            for r in range(N_ROWS_STRIP):
                f.write(",".join(cols[c][r] for c in range(N_COLS)) + "\n")
    print("wrote", ", ".join(REEL_SPECS), "to", REELS_DIR)


if __name__ == "__main__":
    main()

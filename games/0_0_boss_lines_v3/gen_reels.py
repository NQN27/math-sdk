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
# Section 7: columns 4-6 carry slightly more Arrows (boss 3 / boss 2's right
# half), so every boss is about equally likely to be the last one killed.
ARROW_BOOST_COLS = {3: 1.4, 4: 1.4, 5: 1.4}

# (wild %, scatter %, weapon %) per reel. Placeholders.
# Bonus reels: 1 Scatter per column (0.34%). At 1% (3 per column) a Bonus
# spin collected ~1.38 extra spins on average (every refilled cell can draw a
# Scatter), so the Bonus never ran out of spins - see README.
REEL_SPECS = {  # accepted 2026-11-11: Normal LH8 (BON_S*), Super SP17 (SUPX_*), Epic EP34 (EPX_*); older f17 reels kept
    "BR0": dict(removed=0, wild=2.0, sc=0.9, weapon=0.6, shape={'L1': 50, 'L2': 48, 'L3': 46, 'L4': 44, 'H1': 22, 'H2': 17, 'H3': 12, 'H4': 8, 'H5': 5}),
    "ANTE": dict(removed=0, wild=2.0, sc=2.0, weapon=0.6, shape={'L1': 50, 'L2': 48, 'L3': 46, 'L4': 44, 'H1': 22, 'H2': 17, 'H3': 12, 'H4': 8, 'H5': 5}),
    "HERO": dict(removed=4, wild=1.5, sc=0.0, weapon=0.0),
    "BON_S1": dict(removed=0, wild=1.7, sc=0.34, weapon=1.9, shape={'L1': 40, 'L2': 40, 'L3': 40, 'L4': 40, 'H1': 24, 'H2': 23, 'H3': 21, 'H4': 19, 'H5': 16}, arrow_boost={'3': 1.5, '4': 1.5, '5': 1.5}, weapon_adjust={'0': {'BM': -1, 'SW': -1}, '1': {'BM': -1, 'SW': -1}, '2': {'BM': -1, 'SW': -1}, '3': {'BM': -1}, '4': {'BM': -1}, '5': {'BM': -1}}),
    "BON_S2": dict(removed=1, wild=1.8, sc=0.34, weapon=3.3, arrow_boost={'3': 1.5, '4': 1.5, '5': 1.5}, weapon_adjust={'0': {'LT': -1}, '1': {'LT': -1}, '2': {'LT': -1}, '3': {'LT': -1}, '4': {'LT': -1}, '5': {'LT': -1}}),
    "BON_S3": dict(removed=2, wild=1.0, sc=0.34, weapon=4.0, arrow_boost={'3': 1.5, '4': 1.5, '5': 1.5}),
    "BON_S4": dict(removed=3, wild=0.4, sc=0.34, weapon=4.3, arrow_boost={'3': 1.5, '4': 1.5, '5': 1.5}),
    "BON_S5": dict(removed=4, wild=0.4, sc=0.34, weapon=4.3, arrow_boost={'3': 1.5, '4': 1.5, '5': 1.5}),
    "BON_E": dict(removed=4, wild=0.8, sc=0.34, weapon=0.0),
    "SUP_S2": dict(removed=1, wild=1.8, sc=0.34, weapon=0.1),
    "SUP_S3": dict(removed=2, wild=1.2, sc=0.34, weapon=0.05),
    "SUP_S4": dict(removed=3, wild=0.3, sc=0.34, weapon=0.0),
    "SUP_S5": dict(removed=4, wild=0.3, sc=0.34, weapon=0.0),
    "SUP_E": dict(removed=4, wild=0.3, sc=0.34, weapon=0.0),
    "EPI_S3": dict(removed=2, wild=2.0, sc=0.34, weapon=0.0, shape={'L1': 30, 'L2': 30, 'L3': 30, 'L4': 30, 'H1': 28, 'H2': 26, 'H3': 24, 'H4': 22, 'H5': 20}),
    "EPI_S4": dict(removed=3, wild=1.6, sc=0.34, weapon=0.0, shape={'L1': 30, 'L2': 30, 'L3': 30, 'L4': 30, 'H1': 28, 'H2': 26, 'H3': 24, 'H4': 22, 'H5': 20}),
    "EPI_S5": dict(removed=4, wild=1.6, sc=0.34, weapon=0.0, shape={'L1': 30, 'L2': 30, 'L3': 30, 'L4': 30, 'H1': 28, 'H2': 26, 'H3': 24, 'H4': 22, 'H5': 20}),
    "EPI_E": dict(removed=4, wild=1.6, sc=0.34, weapon=0.0, shape={'L1': 30, 'L2': 30, 'L3': 30, 'L4': 30, 'H1': 28, 'H2': 26, 'H3': 24, 'H4': 22, 'H5': 20}),
    "SUPX_S1": dict(removed=0, wild=1.7, sc=0.34, weapon=2.4, shape={'L1': 40, 'L2': 40, 'L3': 40, 'L4': 40, 'H1': 24, 'H2': 23, 'H3': 21, 'H4': 19, 'H5': 16}, arrow_boost={'3': 1.5, '4': 1.5, '5': 1.5}, weapon_adjust={'0': {'BM': -1}, '1': {'BM': -1}, '2': {'BM': -1}, '3': {'BM': -1}, '4': {'BM': -1}, '5': {'BM': -1}}),
    "SUPX_S2": dict(removed=1, wild=1.8, sc=0.34, weapon=3.4, arrow_boost={'3': 1.5, '4': 1.5, '5': 1.5}),
    "SUPX_S3": dict(removed=2, wild=1.0, sc=0.34, weapon=4.0, arrow_boost={'3': 1.5, '4': 1.5, '5': 1.5}),
    "SUPX_S4": dict(removed=3, wild=0.4, sc=0.34, weapon=4.3, arrow_boost={'3': 1.5, '4': 1.5, '5': 1.5}),
    "SUPX_S5": dict(removed=4, wild=0.4, sc=0.34, weapon=4.3, arrow_boost={'3': 1.5, '4': 1.5, '5': 1.5}),
    "SUPX_E": dict(removed=4, wild=0.4, sc=0.34, weapon=2.0, arrow_boost={'3': 1.5, '4': 1.5, '5': 1.5}),
    "EPX_S1": dict(removed=0, wild=1.7, sc=0.45, weapon=2.4, shape={'L1': 40, 'L2': 40, 'L3': 40, 'L4': 40, 'H1': 24, 'H2': 23, 'H3': 21, 'H4': 19, 'H5': 16}, arrow_boost={'3': 1.5, '4': 1.5, '5': 1.5}),
    "EPX_S2": dict(removed=1, wild=1.7, sc=0.45, weapon=4.0, arrow_boost={'3': 1.5, '4': 1.5, '5': 1.5}),
    "EPX_S3": dict(removed=2, wild=1.2, sc=0.45, weapon=2.2, arrow_boost={'3': 1.5, '4': 1.5, '5': 1.5}),
    "EPX_S4": dict(removed=3, wild=0.4, sc=0.45, weapon=2.2, arrow_boost={'3': 1.5, '4': 1.5, '5': 1.5}),
    "EPX_S5": dict(removed=4, wild=0.4, sc=0.45, weapon=2.2, arrow_boost={'3': 1.5, '4': 1.5, '5': 1.5}),
    "EPX_E": dict(removed=4, wild=0.4, sc=0.45, weapon=2.2, arrow_boost={'3': 1.5, '4': 1.5, '5': 1.5}),
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
    mix = dict(WEAPON_MIX)
    boost = {int(k): v for k, v in spec.get("arrow_boost", ARROW_BOOST_COLS).items()}  # per reel (tuning, 2026-11-02)
    mix["AR"] *= boost.get(col, 1.0)
    ratio = sum(mix.values())
    for sym, r in mix.items():
        k = round(total_w * r / ratio)
        if k:
            counts[sym] = k
    for sym, dk in spec.get("weapon_adjust", {}).get(str(col), {}).items():  # exact +/- per column (tuning, 2026-11-03)
        counts[sym] = max(0, counts.get(sym, 0) + dk)
    placed = place_specials(n, counts, rng)
    # optional per-reel symbol shape (tuning); default SHAPE
    shape = {k: v for k, v in spec.get("shape", SHAPE).items() if k not in LOWS[: spec["removed"]]}
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

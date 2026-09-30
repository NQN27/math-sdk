"""Reel strip generator for Boss Lines v2 (6 columns x 5 rows).

Design rules (DESIGN_CHANGES_v2.md; all NUMBERS are placeholders until the
tuning phase - this file fixes the STRUCTURE):

  * Six independent columns, each with its own RNG stream (the mechanical
    conversion had column 6 == column 4, which correlated stops).
  * Symbols: L1-L4, H1-H5, W, Powers (PWM wild multi, PUP upgrade, PXW extra
    wild, PCN power coin; PMX maxwin on WCAP only), SC (base reels only),
    EL/GS/GL (Bonus reels only).
  * Wild is allowed in EVERY column; Power symbols only in columns 2-5
    (index 1-4), never the first/last column.
  * Specials (SC/Power/EL/gun) are PLACED, not drawn: they keep a minimum
    spacing inside a column (circular) so a 5-row window never shows two of
    them, and Scatter keeps >= 8 rows from another Scatter (the engine's
    "max 1 Scatter per column" guarantee). L/H/W filler is random by weight.
  * Bonus stage reels keep the whole L1-L4 set on every stage (a stage-
    cleared low symbol is removed at run time by enforce_removed_symbols),
    only the wild-like density tapers per stage.

Run from the game folder:  python gen_reels.py
Seeds are fixed per file name, so output is reproducible.
"""
import os
import random
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REELS_DIR = os.path.join(HERE, "reels")
N_COLS = 6
INNER = range(1, N_COLS - 1)  # columns allowed to hold Power symbols

# ---- L/H shapes (relative weights of the ordinary paying symbols) ---------
SHAPES = {
    # standard: mostly low pay, H5 rarest
    "std": {"L1": 60, "L2": 52, "L3": 50, "L4": 42, "H1": 20, "H2": 15, "H3": 10, "H4": 7, "H5": 4},
    # ante / feature: richer highs
    "rich": {"L1": 42, "L2": 38, "L3": 38, "L4": 32, "H1": 26, "H2": 20, "H3": 14, "H4": 10, "H5": 6},
    # wincap fence: high-heavy
    "cap": {"L1": 8, "L2": 8, "L3": 10, "L4": 10, "H1": 22, "H2": 26, "H3": 22, "H4": 14, "H5": 12},
    # Mega Bonus: lows dominate (its wins come from power/coin stacking)
    "mega": {"L1": 74, "L2": 60, "L3": 58, "L4": 46, "H1": 8, "H2": 6, "H3": 3, "H4": 2, "H5": 2},
}

# ---- Power mix (relative, sums used as ratios) ------------------------------
POWER_MIX = {"PWM": 40, "PUP": 25, "PXW": 20, "PCN": 15}

# ---- Wild-like taper per Bonus tier/stage (total W+Power % of a column) -----
STAGE_WILD_PCT = {
    "normal": {1: 23.0, 2: 16.0, 3: 10.0, 4: 4.0, 5: 2.0},
    "super": {2: 18.0, 3: 13.0, 4: 10.0, 5: 8.5},
    "hidden": {3: 4.0, 4: 3.5, 5: 3.0},
}
# share of the wild-like weight that is Power in the inner columns (overall
# share over all 6 columns; inner columns are scaled up to compensate).
POWER_FRAC = {"normal": 0.15, "super": 0.35, "hidden": 0.55}
TIER_PREFIX = {"normal": "BM_Reels", "super": "Super_BM", "hidden": "UP_Reels"}
TIER_SHAPE = {"normal": "std", "super": "std", "hidden": "mega"}
# Bonus-only collectibles, % of rows per column
BONUS_SPECIALS = {"EL": 0.9, "GS": 0.7, "GL": 0.5}


def seed_for(name, col):
    return zlib.crc32(f"{name}:{col}".encode()) & 0xFFFFFFFF


def place_specials(n, counts, rng, gap=4, sc_gap=8):
    """Return {row: symbol} placing each special with circular spacing."""
    items = [s for s, k in counts.items() for _ in range(k)]
    rng.shuffle(items)
    placed = {}
    for sym in items:
        for _ in range(400):
            row = rng.randrange(n)
            ok = True
            for r2, s2 in placed.items():
                d = min((row - r2) % n, (r2 - row) % n)
                need = sc_gap if (sym == "SC" and s2 == "SC") else gap
                if d < need:
                    ok = False
                    break
            if ok:
                placed[row] = sym
                break
        else:
            raise RuntimeError(f"could not place {sym} with spacing in {n} rows")
    return placed


def build_column(name, col, n, shape, wild_pct, power_pct, extra_pct):
    """wild_pct = TOTAL W+Power % of this column; power_pct part of it is
    Power symbols (0 outside inner columns); extra_pct = {sym: % of rows}
    for SC/EL/GS/GL etc."""
    rng = random.Random(seed_for(name, col))
    counts = {}
    for sym, pct in extra_pct.items():
        if pct > 0:
            counts[sym] = max(1, round(pct / 100.0 * n))
    if power_pct > 0:
        total_p = max(1, round(power_pct / 100.0 * n))
        ratio_sum = sum(POWER_MIX.values())
        raw = {sym: total_p * r / ratio_sum for sym, r in POWER_MIX.items()}
        alloc = {sym: int(v) for sym, v in raw.items()}
        for sym in sorted(raw, key=lambda k: raw[k] - alloc[k], reverse=True)[: total_p - sum(alloc.values())]:
            alloc[sym] += 1
        counts.update({sym: k for sym, k in alloc.items() if k})
    placed = place_specials(n, counts, rng)
    n_fill = n - len(placed)
    w_count = max(0, round((wild_pct - power_pct) / 100.0 * n))
    nonwild = list(shape.items())
    names = [k for k, _ in nonwild]
    weights = [v for _, v in nonwild]
    filler = ["W"] * min(w_count, n_fill)
    filler += rng.choices(names, weights=weights, k=n_fill - len(filler))
    rng.shuffle(filler)
    it = iter(filler)
    return [placed[r] if r in placed else next(it) for r in range(n)]


def write_reel(fname, n, shape, wild_pct, power_frac, extra_pct, extra_by_col=None):
    """Write reels/<fname>. `wild_pct` is the per-column W+Power %, applied
    to every column; Power only lives in inner columns, scaled up by 6/4 so
    the overall Power share over the six columns equals power_frac*wild."""
    cols = []
    inner_scale = N_COLS / len(INNER)
    for c in range(N_COLS):
        p = min(wild_pct * power_frac * inner_scale, wild_pct * 0.9) if c in INNER else 0.0
        extra = dict(extra_pct)
        if extra_by_col:
            extra.update(extra_by_col.get(c, {}))
        cols.append(build_column(fname, c, n, shape, wild_pct, p, extra))
    path = os.path.join(REELS_DIR, fname)
    with open(path, "w", newline="") as f:
        for r in range(n):
            f.write(",".join(cols[c][r] for c in range(N_COLS)) + "\n")


def main():
    os.makedirs(REELS_DIR, exist_ok=True)
    N = 307
    # --- base game / ante / feature spins / wincap / freegame fallback -------
    write_reel("BR0.csv", N, SHAPES["std"], 6.5, 0.30, {"SC": 1.3})
    write_reel("Ante_BR0.csv", N, SHAPES["rich"], 9.5, 0.30, {"SC": 1.3})
    write_reel("PWR0.csv", N, SHAPES["std"], 9.0, 0.45, {})  # feature spin: Power-dense, no scatter
    write_reel("WCAP.csv", 169, SHAPES["cap"], 26.0, 0.10, {"PMX": 0.0},
               extra_by_col={c: {"PMX": 1.2} for c in INNER})
    write_reel("FR0.csv", N, SHAPES["std"], 6.0, 0.20, dict(BONUS_SPECIALS))
    # --- Bonus stage reels ---------------------------------------------------
    for tier, stages in STAGE_WILD_PCT.items():
        for stage, pct in stages.items():
            write_reel(f"{TIER_PREFIX[tier]}_S{stage}.csv", N, SHAPES[TIER_SHAPE[tier]], pct,
                       POWER_FRAC[tier], dict(BONUS_SPECIALS))
    # --- aliases still referenced by game_config's reels dict -----------------
    import shutil
    for alias, src in (("BM_Reels.csv", "BM_Reels_S1.csv"), ("Super_BM.csv", "Super_BM_S2.csv"),
                       ("UP_Reels.csv", "UP_Reels_S3.csv"), ("FR1.csv", "FR0.csv"), ("FR2.csv", "FR0.csv")):
        shutil.copyfile(os.path.join(REELS_DIR, src), os.path.join(REELS_DIR, alias))
    print("wrote reels to", REELS_DIR)


if __name__ == "__main__":
    main()

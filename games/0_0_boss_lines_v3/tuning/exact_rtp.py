"""Make each optimized lookup's RTP exactly 96.7% (designer: no RTP error on submit).

usage: python tuning/exact_rtp.py OVERRIDES.json [mode ...]
The optimizer converges to within ~0.005% of the target. This changes the integer weights of two books
(one 0x / lowest-pay book and one heavy book) so the RTP is exactly 967/1000, with relative weight changes
around 1e-5 and no rescaling of the table. Then rewrites the configs (hashes) for the new lookups.
"""
import csv
import json
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
SDK = os.path.dirname(os.path.dirname(GAME))
for p in (SDK, GAME, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)
COST = {"base": 1, "ante": 3, "feature": 500, "buy3": 100, "buy4": 300, "random_bonus": 400}
TARGET = Fraction(967, 1000)


def _egcd(a, b):
    if b == 0:
        return a, 1, 0
    g, x, y = _egcd(b, a % b)
    return g, y, x - (a // b) * y


def fix(mode):
    """Integer weights, exact RTP: change the weights of two books A, B (A = the heaviest 0x book, or the
    heaviest lowest-paying book) so that 10 * sum(w*pay_cents) == 967 * cost * 100 * sum(w) / 100 exactly,
    i.e. da*(10*pa - 967c) + db*(10*pb - 967c) == 967c*W - 10*S  (a linear Diophantine equation)."""
    f = os.path.join(GAME, "library", "publish_files", f"lookUpTable_{mode}_0.csv")
    rows = [[int(a), int(b), int(c)] for a, b, c in csv.reader(open(f))]
    c = COST[mode]
    S = sum(w * p for _, w, p in rows)  # pay in cents of the base bet
    W = sum(w for _, w, _ in rows)
    R = 967 * c * W - 10 * S  # (pay in cents: RTP = S / (W*c*100) -> 10*S == 967*c*W)
    if R == 0:
        print(f"{mode}: already exact"); return
    by_w = sorted(rows, key=lambda r: (r[2], -r[1]))  # lowest pay first, heaviest first
    A = by_w[0]
    alpha = 10 * A[2] - 967 * c
    best = None
    for B in sorted(rows, key=lambda r: -r[1])[:2000]:  # heavy books: small relative changes
        if B is A:
            continue
        beta = 10 * B[2] - 967 * c
        g, x, y = _egcd(alpha, beta)
        if R % g:
            continue
        da, db = x * (R // g), y * (R // g)
        # move along the solution line to the smallest |da| + |db|
        sa, sb = beta // g, -alpha // g
        t = round(-(da * sa + db * sb) / (sa * sa + sb * sb))
        da, db = da + t * sa, db + t * sb
        if A[1] + da > 0 and B[1] + db > 0:
            cost_ = abs(da) / A[1] + abs(db) / B[1]
            if best is None or cost_ < best[0]:
                best = (cost_, B, da, db)
    if best is None:
        raise SystemExit(f"{mode}: no exact integer solution found")
    _, B, da, db = best
    A[1] += da
    B[1] += db
    S2, W2 = sum(w * p for _, w, p in rows), sum(w for _, w, _ in rows)
    assert Fraction(S2, W2 * c * 100) == TARGET
    with open(f, "w", newline="") as fh:
        csv.writer(fh).writerows(rows)
    print(f"{mode}: RTP {float(Fraction(S, W * c * 100)) * 100:.6f}% -> exactly 96.7% "
          f"(book {A[0]} pay {A[2] / 100:g}x weight {da:+d}; book {B[0]} pay {B[2] / 100:g}x weight {db:+d})")


if __name__ == "__main__":
    overrides = json.load(open(sys.argv[1]))
    modes = sys.argv[2:] or list(COST)
    for m in modes:
        fix(m)
    os.chdir(SDK)
    import tune_harness
    gamestate, config = tune_harness._setup(overrides)
    from game_optimization import OptimizationSetup
    from src.write_data.write_configs import generate_configs
    OptimizationSetup(config)
    generate_configs(gamestate)

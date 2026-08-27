import sys
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import pure_production_full_measure as ppfm

# Quick scan across (hp_pool, damage_mult) candidates on the REAL current
# mechanic (Wild-col0 fix + counter-attack grace + deadspin routing, no
# chain-break patch) to re-locate mean~80.13x now that the mechanic changed.
# n kept modest for a first scan; best candidate(s) get a confirm run after.

CANDIDATES = [
    ("hp50_100_dmg100_baseline", [50, 50, 50, 100, 100], 1.0),
    ("hp100flat_dmg100", [100, 100, 100, 100, 100], 1.0),
    ("hp150flat_dmg100", [150, 150, 150, 150, 150], 1.0),
    ("hp100_150_dmg085", [100, 100, 100, 150, 150], 0.85),
    ("hp150_200_dmg080", [150, 150, 150, 200, 200], 0.80),
    ("hp200flat_dmg070", [200, 200, 200, 200, 200], 0.70),
]

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    results = []
    for i, (tag, hp, dmg) in enumerate(CANDIDATES):
        r = ppfm.measure(n, 991000 + i, tag, hp_choices=hp, damage_mult=dmg)
        results.append(r)
    print("\n=== SUMMARY ===")
    for r in results:
        print(f"{r['tag']:>28}: mean={r['mean']:.2f}x median={r['median']:.2f}x ratio={r['ratio']:.1f}%")

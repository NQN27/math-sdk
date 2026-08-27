import sys
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import pure_production_full_measure as ppfm

# Round 2: preserve the ORIGINAL pool's taper shape (50,50,50,100,100 = 1:2
# early:late ratio) and scale it up, instead of flattening to equal HP across
# reels - round 1 showed flattening blows the median/mean ratio way past the
# 40-50% target band (up to 106%), since it over-compresses the stage-reach
# distribution the reward table was shaped around.

CANDIDATES = [
    ("scale1.5x_dmg100", [75, 75, 75, 150, 150], 1.0),
    ("scale2.0x_dmg100", [100, 100, 100, 200, 200], 1.0),
    ("scale2.5x_dmg100", [125, 125, 125, 250, 250], 1.0),
    ("scale2.0x_dmg090", [100, 100, 100, 200, 200], 0.90),
    ("scale1.75x_dmg100", [88, 88, 88, 175, 175], 1.0),
]

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    results = []
    for i, (tag, hp, dmg) in enumerate(CANDIDATES):
        r = ppfm.measure(n, 992000 + i, tag, hp_choices=hp, damage_mult=dmg)
        results.append(r)
    print("\n=== SUMMARY ===")
    for r in results:
        print(f"{r['tag']:>28}: mean={r['mean']:.2f}x median={r['median']:.2f}x ratio={r['ratio']:.1f}%")

import sys
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch")
import normal_hp200_deadspinrate_test as t

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    HP200 = [200, 200, 200, 200, 200]
    for none_pct in (10, 25):
        for p_dead in (0.65, 0.72, 0.80, 0.88):
            t.measure(n, 960000, f"hp200_none{none_pct}_pdead{int(p_dead*100)}", HP200, none_pct, p_dead)

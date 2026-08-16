import sys, random, statistics, warnings, csv
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager
import normal_3param_matrix_test as m

OUT_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch"

gamestate_mod.GameState.run_bonus_session = m.patched_run_bonus_session


def patched_run_one_bonus_spin_counted(self, both_ways):
    self._diag_spin_count = getattr(self, "_diag_spin_count", 0) + 1
    return m.patched_run_one_bonus_spin(self, both_ways)


gamestate_mod.GameState.run_one_bonus_spin = patched_run_one_bonus_spin_counted


def measure(n, seed_offset, tag, hp_choices, none_pct, damage_mult, save_csv=True):
    m._CB_MODE = "sweep4"
    rest = (100 - none_pct) / 3
    m._SWEEP4_WEIGHTS = [rest, rest, rest, none_pct]

    config = game_config_mod.GameConfig()
    config.bonus_safety_cap_spins = 150
    config.bonus_player_hp_choices = dict(config.bonus_player_hp_choices)
    config.bonus_player_hp_choices["normal"] = hp_choices
    if damage_mult != 1.0:
        config.symbol_damage_range = {
            name: (lo * damage_mult, hi * damage_mult)
            for name, (lo, hi) in config.symbol_damage_range.items()
        }
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals = []
    spins = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs._diag_spin_count = 0
            gs.run_bonus_session("normal")
            totals.append(gs.win_manager.running_bet_win)
            spins.append(gs._diag_spin_count)

    if save_csv:
        with open(f"{OUT_DIR}\\{tag}_n{n}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["payout_multiplier", "spin_count"])
            for t, s in zip(totals, spins):
                w.writerow([t, s])

    mean = sum(totals) / n
    median = statistics.median(totals)
    stdev = statistics.pstdev(totals)
    ratio = median / mean * 100 if mean > 0 else 0
    zero = 100 * sum(1 for t in totals if t == 0) / n
    sorted_t = sorted(totals)

    def pct(p):
        return sorted_t[min(n - 1, int(p * n))]

    mean_spins = sum(spins) / n
    median_spins = statistics.median(spins)
    max_spins = max(spins)
    le2 = 100 * sum(1 for s in spins if s <= 2) / n
    le3 = 100 * sum(1 for s in spins if s <= 3) / n

    print(f"\n=== {tag} (n={n}) hp={hp_choices[0]}.. none={none_pct}% dmg={damage_mult:.2f} ===")
    print(
        f"mean={mean:.2f}x median={median:.2f}x ratio={ratio:.1f}% CV={stdev/mean:.2f} zero={zero:.2f}%"
    )
    print(
        "percentiles: "
        f"p10={pct(0.10):.1f}x p25={pct(0.25):.1f}x p50={pct(0.50):.1f}x "
        f"p75={pct(0.75):.1f}x p90={pct(0.90):.1f}x p95={pct(0.95):.1f}x "
        f"p99={pct(0.99):.1f}x p99.9={pct(0.999):.1f}x max={sorted_t[-1]:.1f}x"
    )
    print(
        f"spins: mean={mean_spins:.2f} median={median_spins} max={max_spins} "
        f"spins<=2={le2:.2f}% spins<=3={le3:.2f}%"
    )

    # payout bucket histogram
    buckets = [(0, 0), (0, 5), (5, 20), (20, 50), (50, 100), (100, 200),
               (200, 500), (500, 1000), (1000, 10 ** 9)]
    print("payout buckets:")
    for lo, hi in buckets:
        if lo == 0 and hi == 0:
            cnt = sum(1 for t in totals if t == 0)
            label = "==0"
        else:
            cnt = sum(1 for t in totals if lo < t <= hi) if lo != 0 else sum(1 for t in totals if 0 < t <= hi)
            label = f"({lo},{hi}]"
        print(f"  {label:>14}: {100*cnt/n:5.2f}%")

    return dict(tag=tag, mean=mean, median=median, ratio=ratio, cv=stdev / mean,
                zero=zero, mean_spins=mean_spins, median_spins=median_spins,
                max_spins=max_spins)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50000

    measure(n, 970000, "confirm50k_hp75_dmg130_baseline", [75, 75, 100, 100, 100], 10, 1.30)
    measure(n, 970001, "confirm50k_hp200_none40_dmg45", [200, 200, 200, 200, 200], 40, 0.45)
    measure(n, 970002, "confirm50k_hp200_none25_dmg55", [200, 200, 200, 200, 200], 25, 0.55)

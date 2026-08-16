import sys, random, csv, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

OUT_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch"


def measure(n, seed_offset, tag, hp_choices=None, save_csv=False):
    config = game_config_mod.GameConfig()
    config.bonus_safety_cap_spins = 150
    if hp_choices is not None:
        config.bonus_player_hp_choices = dict(config.bonus_player_hp_choices)
        config.bonus_player_hp_choices["normal"] = hp_choices
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals = []
    stage6_totals = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session("normal")
            payout = gs.win_manager.running_bet_win
            totals.append(payout)
            if gs.stage >= 6:
                stage6_totals.append(payout)

    if save_csv:
        with open(f"{OUT_DIR}\\{tag}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["payout_multiplier"])
            for t in totals:
                w.writerow([t])

    mean = sum(totals) / n
    median = statistics.median(totals)
    stdev = statistics.pstdev(totals)
    se = stdev / (n ** 0.5)
    ratio = median / mean * 100 if mean > 0 else 0
    s6_avg = sum(stage6_totals) / len(stage6_totals) if stage6_totals else 0
    under5 = sum(1 for t in totals if t < 5) / n * 100
    zero = sum(1 for t in totals if t == 0) / n * 100
    print(
        f"[{tag}] (n={n}): mean={mean:.2f}x (+/-{1.96*se:.2f}) median={median:.2f}x "
        f"ratio={ratio:.1f}% CV={stdev/mean:.2f} stage6plus_avg={s6_avg:.1f}x (n={len(stage6_totals)}) "
        f"under5x={under5:.2f}% zero={zero:.2f}%"
    )
    return mean, median


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    measure(n, 555111, "normal_hp_current", hp_choices=[50, 50, 50, 100, 100], save_csv=True)
    measure(n, 555222, "normal_hp_75_75_100_100_100", hp_choices=[75, 75, 100, 100, 100], save_csv=True)

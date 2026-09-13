import sys, os, random, statistics

REPO = r"D:\Stake Engine\math-sdk"
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "games", "0_0_boss_lines"))
os.chdir(REPO)

from gamestate import GameState
from game_config import GameConfig
from src.wins.win_manager import WinManager

TARGET = {1: 38.30, 2: 32.70, 3: 16.45, 4: 7.40, 5: 3.60, 6: 5.0}


def measure(n, seed_offset, boss_hp_mult, init_hp, bonus_hp, tag):
    config = GameConfig()
    config.use_flat_damage["normal"] = True
    config.flat_damage_boss_hp_mult["normal"] = boss_hp_mult
    config.flat_damage_player_hp_initial_mult["normal"] = init_hp / 200.0
    config.flat_damage_player_hp_bonus_mult["normal"] = bonus_hp / 50.0

    gs = GameState(config)
    mode_max_win = config.bet_modes[0].get_wincap()
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, mode_max_win)
    gs.betmode = "base"

    stage_death_counts = {}
    totals, spin_counts = [], []
    for i in range(n):
        gs.sim = i
        gs.criteria = "freegame"
        random.seed(seed_offset * 1000003 + i + 1)
        gs.reset_book()
        gs.run_bonus_session("normal")
        totals.append(gs.win_manager.running_bet_win)
        spin_counts.append(gs.bonus_spin_count)
        stage_death_counts[gs.stage] = stage_death_counts.get(gs.stage, 0) + 1

    mean = sum(totals) / n
    median = statistics.median(totals)
    mean_spins = sum(spin_counts) / n
    death_pct = {s: 100 * stage_death_counts.get(s, 0) / n for s in range(1, 7)}
    err = sum(abs(death_pct[s] - TARGET[s]) for s in range(1, 7))
    death_str = ", ".join(f"s{s}={death_pct[s]:.1f}(t{TARGET[s]})" for s in range(1, 7))
    print(f"{tag:24s} -> mean={mean:8.2f}x median={median:7.2f}x spins/sess={mean_spins:6.2f} "
          f"err={err:6.1f}  {death_str}", flush=True)
    return mean, median, death_pct, err


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    # baseline: flat 0.113 everywhere, current (10,3) player HP
    measure(n, 850000, 0.113, 10, 3, "flat-0.113")
    measure(n, 850000, {1: 0.07, 2: 0.113, 3: 0.113, 4: 0.113, 5: 0.113, 6: 0.113}, 10, 3, "s1=0.07")
    measure(n, 850000, {1: 0.05, 2: 0.113, 3: 0.113, 4: 0.113, 5: 0.113, 6: 0.113}, 10, 3, "s1=0.05")
    measure(n, 850000, {1: 0.04, 2: 0.10, 3: 0.113, 4: 0.113, 5: 0.113, 6: 0.113}, 10, 3, "s1=.04,s2=.10")
    measure(n, 850000, {1: 0.03, 2: 0.09, 3: 0.113, 4: 0.113, 5: 0.113, 6: 0.113}, 10, 3, "s1=.03,s2=.09")

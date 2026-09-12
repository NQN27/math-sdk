import sys, os, random, statistics

REPO = r"D:\Stake Engine\math-sdk"
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "games", "0_0_boss_lines"))
os.chdir(REPO)

from gamestate import GameState
from game_config import GameConfig
from src.wins.win_manager import WinManager


def measure(n, seed_offset, boss_hp_mult, player_initial_mult, player_bonus_mult, tag):
    config = GameConfig()
    config.use_flat_damage["normal"] = True
    config.flat_damage_boss_hp_mult["normal"] = boss_hp_mult
    config.flat_damage_player_hp_initial_mult["normal"] = player_initial_mult
    config.flat_damage_player_hp_bonus_mult["normal"] = player_bonus_mult

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
    death_str = ", ".join(f"s{s}={100*c/n:.1f}%" for s, c in sorted(stage_death_counts.items()))
    print(f"{tag:12s} init={player_initial_mult:.4f} -> mean={mean:8.2f}x median={median:7.2f}x "
          f"spins/sess={mean_spins:6.2f}  {death_str}", flush=True)
    return mean, median, mean_spins


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    boss_hp = 0.113
    for pm in [0.046, 0.048, 0.050, 0.052, 0.054, 0.056, 0.058]:
        measure(n, 700000, boss_hp, pm, pm, f"pm={pm}")

import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager
import normal_3param_matrix_test as m

# User confirmed: boss counter-attack is unconditional per spin (not just
# dead spins) - game_bonus.py:405-407. So a REAL HP raise (not a cosmetic
# filler trick) is the honest way to fund more real spins per session.
# Already measured the extremes: HP75 -> mean_spins~3.9-4.05 (loved
# economy), HP200 -> mean_spins=6.41 but median pins ~95x (too high).
# Untested: the middle ground. Sweep HP in a moderate range, keep the
# sweep4 CB pool + a damage multiplier chosen to try to hold mean near the
# loved ~80x, and report BOTH spin count and payout shape together so the
# real tradeoff (more spins vs rising median) is visible, not assumed.

gamestate_mod.GameState.run_bonus_session = m.patched_run_bonus_session


def patched_run_one_bonus_spin_counted(self, both_ways):
    self._diag_spin_count = getattr(self, "_diag_spin_count", 0) + 1
    return m.patched_run_one_bonus_spin(self, both_ways)


gamestate_mod.GameState.run_one_bonus_spin = patched_run_one_bonus_spin_counted


def measure(n, seed_offset, tag, hp_choices, damage_mult):
    m._CB_MODE = "sweep4"
    m._SWEEP4_WEIGHTS = [35, 30, 25, 10]

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

    mean = sum(totals) / n
    median = statistics.median(totals)
    stdev = statistics.pstdev(totals)
    ratio = median / mean * 100 if mean > 0 else 0
    zero = 100 * sum(1 for t in totals if t == 0) / n
    mean_spins = sum(spins) / n
    median_spins = statistics.median(spins)
    le2 = 100 * sum(1 for s in spins if s <= 2) / n
    print(
        f"[{tag}] hp={hp_choices[0]}.. dmg={damage_mult:.2f} (n={n}): "
        f"mean={mean:.2f}x median={median:.2f}x ratio={ratio:.1f}% CV={stdev/mean:.2f} "
        f"zero={zero:.2f}% | mean_spins={mean_spins:.2f} median_spins={median_spins} spins<=2={le2:.2f}%"
    )


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000

    CASES = [
        ("hp75_dmg130_baseline", [75, 75, 100, 100, 100], 1.30),
        ("hp90_dmg125", [90, 90, 110, 110, 110], 1.25),
        ("hp100_dmg120", [100, 100, 120, 120, 120], 1.20),
        ("hp115_dmg115", [115, 115, 130, 130, 130], 1.15),
        ("hp125_dmg110", [125, 125, 140, 140, 140], 1.10),
        ("hp150_dmg100", [150, 150, 160, 160, 160], 1.00),
    ]
    seed = 920000
    for tag, hp, dmg in CASES:
        measure(n, seed, tag, hp, dmg)
        seed += 1

import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager
import normal_3param_matrix_test as m

# Directly measure mean/median/max SPIN COUNT (not just payout) for the
# leading candidates, instead of assuming it carries over from an earlier,
# differently-configured spin-length measurement.

gamestate_mod.GameState.run_bonus_session = m.patched_run_bonus_session


def patched_run_one_bonus_spin_counted(self, both_ways):
    self._diag_spin_count = getattr(self, "_diag_spin_count", 0) + 1
    return m.patched_run_one_bonus_spin(self, both_ways)


gamestate_mod.GameState.run_one_bonus_spin = patched_run_one_bonus_spin_counted


def measure(n, seed_offset, tag, hp_choices, none_pct, damage_mult):
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

    mean = sum(totals) / n
    median = statistics.median(totals)
    stdev = statistics.pstdev(totals)
    ratio = median / mean * 100 if mean > 0 else 0
    zero = 100 * sum(1 for t in totals if t == 0) / n
    mean_spins = sum(spins) / n
    median_spins = statistics.median(spins)
    max_spins = max(spins)
    le2 = 100 * sum(1 for s in spins if s <= 2) / n
    print(
        f"[{tag}] hp={hp_choices[0]}.. none={none_pct}% dmg={damage_mult:.2f} (n={n}): "
        f"mean={mean:.2f}x median={median:.2f}x ratio={ratio:.1f}% CV={stdev/mean:.2f} zero={zero:.2f}% | "
        f"spins: mean={mean_spins:.2f} median={median_spins} max={max_spins} spins<=2={le2:.2f}%"
    )


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000

    # Baseline for comparison
    measure(n, 950000, "hp75_dmg130_baseline", [75, 75, 100, 100, 100], 10, 1.30)
    # Leading HP200+damage-reduction candidate found so far
    measure(n, 950001, "hp200_none40_dmg45", [200, 200, 200, 200, 200], 40, 0.45)
    measure(n, 950002, "hp200_none25_dmg55", [200, 200, 200, 200, 200], 25, 0.55)

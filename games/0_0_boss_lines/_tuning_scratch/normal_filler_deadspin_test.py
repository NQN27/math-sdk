import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager
import normal_3param_matrix_test as m

# User's clarified design intent: filler dead-spins are FREE - they must
# not touch real connect probability, must not cost HP, and must not
# change total payout. Given that, they cannot affect the payout
# distribution by construction (zero-value, zero-cost events added on top
# of the real game loop can't move a sum). This script proves that
# empirically rather than just by argument: reruns the loved
# hp75+dmg30% candidate with the real CB/HP/damage machinery untouched,
# records each session's REAL spin count and payout, then adds filler
# spins in plain Python (no game-state interaction at all) at several
# candidate rates and confirms payout stats are unchanged while
# mean_spins rises.

gamestate_mod.GameState.run_one_bonus_spin = m.patched_run_one_bonus_spin
gamestate_mod.GameState.run_bonus_session = m.patched_run_bonus_session


def patched_run_one_bonus_spin_counted(self, both_ways):
    self._diag_spin_count = getattr(self, "_diag_spin_count", 0) + 1
    return m.patched_run_one_bonus_spin(self, both_ways)


gamestate_mod.GameState.run_one_bonus_spin = patched_run_one_bonus_spin_counted


def measure_with_fillers(n, seed_offset, tag, hp_choices, damage_mult, fill_rate):
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

    filler_rng = random.Random(seed_offset * 777 + 1)
    totals = []
    real_spins = []
    padded_spins = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs._diag_spin_count = 0
            gs.run_bonus_session("normal")
            rs = gs._diag_spin_count
            totals.append(gs.win_manager.running_bet_win)
            real_spins.append(rs)
            # Free filler: for each real spin taken, independently add one
            # extra "filler" dead spin with probability fill_rate. Uses a
            # SEPARATE rng stream so it never perturbs the real game's
            # random.seed()-driven draws (reels/CB/HP) at all.
            fillers = sum(1 for _ in range(rs) if filler_rng.random() < fill_rate)
            padded_spins.append(rs + fillers)

    mean = sum(totals) / n
    median = statistics.median(totals)
    stdev = statistics.pstdev(totals)
    ratio = median / mean * 100 if mean > 0 else 0
    zero = 100 * sum(1 for t in totals if t == 0) / n
    mean_real = sum(real_spins) / n
    mean_padded = sum(padded_spins) / n
    print(
        f"[{tag}] fill_rate={fill_rate:.2f} (n={n}): mean={mean:.2f}x median={median:.2f}x "
        f"ratio={ratio:.1f}% CV={stdev/mean:.2f} zero={zero:.2f}% | "
        f"real_spins={mean_real:.2f} -> padded_spins={mean_padded:.2f}"
    )


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    HP = [75, 75, 100, 100, 100]
    DMG = 1.30
    for fr in (0.0, 0.3, 0.5, 0.8, 1.0, 1.5):
        measure_with_fillers(n, 910000, f"hp75_dmg130_filler", HP, DMG, fr)

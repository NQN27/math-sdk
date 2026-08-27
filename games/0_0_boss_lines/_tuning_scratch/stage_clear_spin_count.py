"""Does the inverted HP schedule (stage1 tankier than stage2) actually show
up as an observable gameplay problem - i.e. does stage 1 take MORE internal
bonus spins to clear than stage 2, backwards from the expected "gets harder
as you progress" intuition? Real, unmodified game_config.py, counts internal
spins between stage entry and stage clear via run_one_bonus_spin call count."""
import json
import statistics
import sys
import warnings
import random
from collections import defaultdict

sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_bonus as game_bonus_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

spins_per_stage = defaultdict(list)

_orig_run_one_spin = game_bonus_mod.GameBonus.run_one_bonus_spin


def patched_run_one_spin(self, both_ways):
    stage_before = getattr(self, "stage", None)
    self._stage_spin_counter = getattr(self, "_stage_spin_counter", 0) + 1
    _orig_run_one_spin(self, both_ways)
    stage_after = getattr(self, "stage", None)
    if stage_after != stage_before or getattr(self, "boss_system_active", True) is False:
        spins_per_stage[stage_before].append(self._stage_spin_counter)
        self._stage_spin_counter = 0


game_bonus_mod.GameBonus.run_one_bonus_spin = patched_run_one_spin


def measure(n, seed_offset):
    config = game_config_mod.GameConfig()
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs._stage_spin_counter = 0
            gs.run_bonus_session("normal")

    result = {}
    for stage in sorted(spins_per_stage):
        vals = spins_per_stage[stage]
        result[stage] = {
            "count": len(vals),
            "mean_spins_to_clear_or_die": round(sum(vals) / len(vals), 2),
            "median_spins": statistics.median(vals),
        }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 997001
    measure(n, seed)

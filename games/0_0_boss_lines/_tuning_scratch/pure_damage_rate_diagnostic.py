import sys, random
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Measure real per-spin total damage output at stage 1 with artificially
# huge boss HP (so no boss ever dies / no stage clear interrupts), to
# compare directly against the JS reimplementation's own measured ~165/spin
# average at the same stage - isolates whether the gap is in damage
# modeling (explode radius, wild rule, win frequency) vs something else
# (session-loop/end-condition logic).

config = game_config_mod.GameConfig()
gs = gamestate_mod.GameState(config)
gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
gs.betmode = "base"

N = 2000
total_dmg = 0.0
per_boss = {"boss1": 0.0, "boss2": 0.0, "boss3": 0.0}
win_counts = []

_orig_deal = gs.deal_damage_to_boss.__func__


def spy_deal(self, col, damage):
    nonlocal_total["dmg"] += damage
    boss_id = self.route_boss_for_column(col)
    if self.boss_alive.get(boss_id, False):
        per_boss[boss_id] += damage
    return _orig_deal(self, col, damage)


nonlocal_total = {"dmg": 0.0}
gamestate_mod.GameState.deal_damage_to_boss = spy_deal

_orig_evaluate = gamestate_mod.GameState.evaluate_and_explode
pass_counter = {"passes": 0, "cells": 0, "wins": 0}


def spy_evaluate(self, both_ways=False):
    result = _orig_evaluate(self, both_ways=both_ways)
    pass_counter["passes"] += 1
    pass_counter["cells"] += len(getattr(self, "pass_exploded_positions", []))
    pass_counter["wins"] += len(self.win_data.get("wins", []))
    return result


gamestate_mod.GameState.evaluate_and_explode = spy_evaluate

total_passes = 0
total_cells = 0
total_wins = 0

for i in range(N):
    gs.sim = i
    gs.criteria = "freegame"
    random.seed(555000 + i)
    gs.reset_book()
    gs.in_bonus = True
    gs.bonus_tier = "normal"
    gs.gametype = config.freegame_type
    gs.reset_boss_battle(start_stage=1)
    gs.reset_power_system()
    # inflate boss HP so nothing dies mid-measurement
    gs.boss_hp = {b: 1e9 for b in config.boss_ids}
    gs.boss_hp_max = dict(gs.boss_hp)
    nonlocal_total["dmg"] = 0.0
    pass_counter["passes"] = 0
    pass_counter["cells"] = 0
    pass_counter["wins"] = 0
    gs.booster_pending_for_next_spin = False
    gs.booster_multiplier_current_spin = 1.0
    gs.run_one_bonus_spin(both_ways=False)
    total_dmg += nonlocal_total["dmg"]
    win_counts.append(gs.win_data.get("totalWin", 0))
    total_passes += pass_counter["passes"]
    total_cells += pass_counter["cells"]
    total_wins += pass_counter["wins"]

print(f"N={N}")
print(f"avg total damage per spin (stage1, dmgMult=1, infinite boss HP): {total_dmg/N:.2f}")
print(f"avg damage per boss per spin: {{ {', '.join(f'{k}: {v/N:.2f}' for k,v in per_boss.items())} }}")
print(f"avg line-win cash total per spin (sanity): {sum(win_counts)/N:.3f}")
print(f"avg resolve-loop passes per spin: {total_passes/N:.2f}")
print(f"avg exploding cells per spin (summed across passes): {total_cells/N:.2f}")
print(f"avg winning-line count per spin (summed across passes): {total_wins/N:.2f}")


"""Diagnostic: is Super's stage-2 HP collapse explained purely by the shared
boss_stage_table's Dam values, or is something Power-specific amplifying
player HP loss beyond what the plain boss counterattack numbers predict?

Measures actual mean player-HP-lost-per-spin at stage 2 for Super's real
session (real reels, real Power density) via a hook on player_hp changes,
and separately reports stage 2's raw boss_stage_table Dam values for
reference (zero-override harness - real game_config.py).
"""
import sys
import random
import statistics

sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

config = game_config_mod.GameConfig()
print("Stage 2 boss_stage_table (dam, hp):", config.boss_stage_table[2])
print("Super HP pool choices:", config.bonus_player_hp_choices["super"])
print("Super start stage:", config.bonus_start_stage["super"])

gs = gamestate_mod.GameState(config)
gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
gs.betmode = "base"

per_spin_hp_loss = []
per_spin_stage = []

N = 2000
for i in range(N):
    gs.sim = i
    gs.criteria = "freegame"
    random.seed(970001 * 1000003 + i + 1)
    gs.reset_book()
    gs.run_bonus_session("super")
    # walk the book's events to find playerHpState transitions
    prev_hp = None
    spins_seen = 0
    for e in gs.book.events:
        if e.get("type") == "playerHpState":
            hp = e["playerHp"]
            if prev_hp is not None:
                loss = prev_hp - hp
                if loss > 0:
                    per_spin_hp_loss.append(loss)
            prev_hp = hp
            spins_seen += 1

print(f"\nn={N} sessions, {len(per_spin_hp_loss)} HP-loss events recorded")
if per_spin_hp_loss:
    print(f"mean HP loss per counterattack event: {statistics.mean(per_spin_hp_loss):.2f}")
    print(f"median: {statistics.median(per_spin_hp_loss):.2f}")
    print(f"max: {max(per_spin_hp_loss):.2f}")
    print(f"min: {min(per_spin_hp_loss):.2f}")

# reference: raw sum of stage-2 boss Dam values (if all 3 counterattack same spin)
stage2 = config.boss_stage_table[2]
total_dam = sum(v[0] for v in stage2.values())
print(f"\nreference: stage-2 boss_stage_table raw Dam sum (all 3 bosses, base before +/-25% variance): {total_dam}")
print(f"reference: stage-2 boss_stage_table individual Dam values: {[v[0] for v in stage2.values()]}")

"""New angle on the still-open ~8% Python-vs-JS clear-time residual
(see STAGE2_CLEARTIME_INVESTIGATION_FINDINGS.md): the prior investigation
confirmed mean/stdev/deciles 5th-80th match almost exactly between engines,
but first-passage time to a fixed HP threshold is disproportionately
sensitive to the RIGHT TAIL of the per-spin damage distribution (rare big
spins), which was never explicitly checked past the 80th percentile. If
Python's tail is thinner (fewer huge-damage outlier spins) than JS's, that
alone would make Python take MORE spins on average to reach the same HP
total even with an identical mean - explaining the gap without needing any
new low-order statistical mismatch.

Boss1 made immortal (huge HP) at stage 1, matching the prior investigation's
own isolation methodology. Booster cycling replicated manually via
game_bonus.py's own 2-line cycle (the exact fix documented for root cause #1
in the prior investigation) - WITHOUT this fix the harness silently
disables the Booster and is not a valid comparison.
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
gs = gamestate_mod.GameState(config)
gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
gs.betmode = "base"

N = int(sys.argv[1]) if len(sys.argv) > 1 else 60000
seed_base = int(sys.argv[2]) if len(sys.argv) > 2 else 777000

per_spin_boss1_damage = []

nonlocal_total = {"dmg": 0.0}
_orig_deal = gamestate_mod.GameState.deal_damage_to_boss


def spy_deal(self, col, damage):
    boss_id = self.route_boss_for_column(col)
    if boss_id == "boss1" and self.boss_alive.get(boss_id, False):
        nonlocal_total["dmg"] += damage
    return _orig_deal(self, col, damage)


gamestate_mod.GameState.deal_damage_to_boss = spy_deal

gs.booster_pending_for_next_spin = False
gs.booster_multiplier_current_spin = 1.0

for i in range(N):
    gs.sim = i
    gs.criteria = "freegame"
    random.seed(seed_base + i)
    gs.reset_book()
    gs.in_bonus = True
    gs.bonus_tier = "normal"
    gs.gametype = config.freegame_type
    gs.reset_boss_battle(start_stage=1)
    gs.reset_power_system()
    gs.boss_hp = {b: 1e9 for b in config.boss_ids}
    gs.boss_hp_max = dict(gs.boss_hp)

    # replicate game_bonus.py's own booster-cycle step (lines 355-358) -
    # the exact fix for root cause #1 in the prior investigation. Carries
    # booster_pending_for_next_spin across iterations (it's set inside
    # run_one_bonus_spin when a BO symbol explodes), same as the real
    # run_bonus_session outer loop would.
    gs.booster_multiplier_current_spin = (
        config.booster_damage_multiplier if gs.booster_pending_for_next_spin else 1.0
    )
    gs.booster_pending_for_next_spin = False

    nonlocal_total["dmg"] = 0.0
    gs.run_one_bonus_spin(both_ways=False)
    per_spin_boss1_damage.append(nonlocal_total["dmg"])

vals = sorted(per_spin_boss1_damage)
n = len(vals)
mean = sum(vals) / n
stdev = statistics.pstdev(vals)
skew = sum((v - mean) ** 3 for v in vals) / n / (stdev ** 3) if stdev > 0 else 0
kurt = sum((v - mean) ** 4 for v in vals) / n / (stdev ** 4) - 3 if stdev > 0 else 0


def pct(p):
    return vals[min(n - 1, int(p * n))]


print(f"PYTHON n={n}  mean={mean:.3f}  stdev={stdev:.3f}  skew={skew:.4f}  excess_kurtosis={kurt:.4f}")
for p in [0.50, 0.70, 0.80, 0.85, 0.90, 0.95, 0.97, 0.99, 0.995, 0.999]:
    print(f"  p{p*100:>5.1f} = {pct(p):>10.2f}")
print(f"  max = {vals[-1]:.2f}")

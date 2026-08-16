import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager
import normal_3param_matrix_test as m

# The JS demo assumed real stage-clears must be happening often enough to
# explain HP200's much longer mean_spins (8.26 vs 3.88 at HP75) via the
# +50/+50 HP stage-clear grant compounding. Verify against the REAL engine
# instead of guessing at a simplified damage model: track final stage
# reached and whether stage 6 was ever fully cleared, per session.

gamestate_mod.GameState.run_bonus_session = m.patched_run_bonus_session


def patched_run_one_bonus_spin_counted(self, both_ways):
    self._diag_spin_count = getattr(self, "_diag_spin_count", 0) + 1
    # BUG (found 2026-08-17): checking self.stage only once per spin, here,
    # misses mid-spin stage advances - clear_stage() can advance self.stage
    # multiple times WITHIN a single spin's cascade if enough damage lands
    # in one pass to clear back-to-back stages, so a session that clears
    # stage 6 in the same spin it cleared stage 5 got recorded as reaching
    # only stage 5. Wrap clear_stage itself instead, so every actual
    # transition is caught regardless of how many happen in one spin.
    self._diag_max_stage = max(getattr(self, "_diag_max_stage", 1), self.stage)
    return m.patched_run_one_bonus_spin(self, both_ways)


_original_clear_stage = gamestate_mod.GameState.clear_stage


def patched_clear_stage(self, stage):
    self._diag_max_stage = max(getattr(self, "_diag_max_stage", 1), stage)
    result = _original_clear_stage(self, stage)
    self._diag_max_stage = max(getattr(self, "_diag_max_stage", 1), getattr(self, "stage", stage))
    return result


gamestate_mod.GameState.clear_stage = patched_clear_stage


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

    spins = []
    max_stages = []
    end_reasons = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs._diag_spin_count = 0
            gs._diag_max_stage = 1
            gs.run_bonus_session("normal")
            spins.append(gs._diag_spin_count)
            max_stages.append(gs._diag_max_stage)
            end_reasons.append(getattr(gs, "bonus_end_reason", "?"))

    mean_spins = sum(spins) / n
    median_spins = statistics.median(spins)
    stage_dist = {s: 100 * sum(1 for x in max_stages if x == s) / n for s in range(1, 7)}
    reason_dist = {}
    for r in end_reasons:
        reason_dist[r] = reason_dist.get(r, 0) + 1
    reason_pct = {k: 100 * v / n for k, v in reason_dist.items()}
    print(f"\n=== {tag} (n={n}) hp={hp_choices[0]}.. none={none_pct}% dmg={damage_mult:.2f} ===")
    print(f"mean_spins={mean_spins:.2f} median_spins={median_spins}")
    print("max stage reached distribution: " + ", ".join(f"stage{s}={stage_dist[s]:.2f}%" for s in range(1, 7)))
    print("end reasons: " + ", ".join(f"{k}={v:.2f}%" for k, v in sorted(reason_pct.items())))


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    measure(n, 980000, "hp75_dmg130_baseline", [75, 75, 100, 100, 100], 10, 1.30)
    measure(n, 980001, "hp200_none40_dmg45", [200, 200, 200, 200, 200], 40, 0.45)

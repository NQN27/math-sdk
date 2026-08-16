import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Pure production ground truth, NO chain-break monkeypatch, NO run_one_bonus_spin
# override - uses the real, unmodified GameBonus.run_bonus_session /
# run_one_bonus_spin exactly as game_bonus.py ships them. Only instrumentation:
# a spin counter and a clear_stage wrapper to track max stage reached (purely
# observational, does not change behavior). This is the apples-to-apples
# target for the new slot-UI JS reimplementation (boss_lines_slot_shell.html),
# which also implements the pure real mechanic with no chain-break concept.

_original_run_one_bonus_spin = gamestate_mod.GameState.run_one_bonus_spin


def patched_run_one_bonus_spin_counted(self, both_ways):
    self._diag_spin_count = getattr(self, "_diag_spin_count", 0) + 1
    return _original_run_one_bonus_spin(self, both_ways)


gamestate_mod.GameState.run_one_bonus_spin = patched_run_one_bonus_spin_counted

_original_clear_stage = gamestate_mod.GameState.clear_stage


def patched_clear_stage(self, stage):
    self._diag_max_stage = max(getattr(self, "_diag_max_stage", 1), stage)
    result = _original_clear_stage(self, stage)
    self._diag_max_stage = max(getattr(self, "_diag_max_stage", 1), getattr(self, "stage", stage))
    return result


gamestate_mod.GameState.clear_stage = patched_clear_stage


def measure(n, seed_offset, tag, hp_choices, damage_mult):
    config = game_config_mod.GameConfig()
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
    print(f"\n=== {tag} (n={n}) hp={hp_choices} dmg={damage_mult:.2f} [PURE PRODUCTION, no chain-break] ===")
    print(f"mean_spins={mean_spins:.2f} median_spins={median_spins} max_spins={max(spins)}")
    print(f"spins<=2: {100*sum(1 for x in spins if x<=2)/n:.2f}%")
    print("max stage reached distribution: " + ", ".join(f"stage{s}={stage_dist[s]:.2f}%" for s in range(1, 7)))
    print("end reasons: " + ", ".join(f"{k}={v:.2f}%" for k, v in sorted(reason_pct.items())))


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    measure(n, 770000, "production_default", [50, 50, 50, 100, 100], 1.0)
    measure(n, 770001, "candidate_hp200_dmg45", [200, 200, 200, 200, 200], 0.45)

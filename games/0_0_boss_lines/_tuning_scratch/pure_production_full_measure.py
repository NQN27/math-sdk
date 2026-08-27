import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Pure production ground truth (no chain-break patch, no HP/damage overrides
# unless explicitly requested) - full payout + spin-count + stage-reach
# picture for the CURRENT on-disk config, exactly as it ships (Wild-col0 fix,
# counter-attack grace, deadspin routing all included since they're in
# game_executables.py/game_bonus.py/game_config.py directly, not patches).

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


def measure(n, seed_offset, tag, hp_choices=None, damage_mult=1.0):
    config = game_config_mod.GameConfig()
    if hp_choices is not None:
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

    spins, max_stages, end_reasons, totals = [], [], [], []
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
            totals.append(gs.win_manager.running_bet_win)

    mean = sum(totals) / n
    median = statistics.median(totals)
    stdev = statistics.pstdev(totals)
    ratio = median / mean * 100 if mean > 0 else 0
    zero = 100 * sum(1 for t in totals if t == 0) / n
    sorted_t = sorted(totals)

    def pct(p):
        return sorted_t[min(n - 1, int(p * n))]

    mean_spins = sum(spins) / n
    median_spins = statistics.median(spins)
    stage_dist = {s: 100 * sum(1 for x in max_stages if x == s) / n for s in range(1, 7)}
    reason_dist = {}
    for r in end_reasons:
        reason_dist[r] = reason_dist.get(r, 0) + 1
    reason_pct = {k: 100 * v / n for k, v in reason_dist.items()}

    print(f"\n=== {tag} (n={n}) hp={hp_choices} dmg={damage_mult:.2f} [PURE PRODUCTION] ===")
    print(f"mean={mean:.2f}x median={median:.2f}x ratio={ratio:.1f}% CV={stdev/mean:.2f} zero={zero:.2f}%")
    print(f"percentiles: p50={pct(.5):.1f}x p75={pct(.75):.1f}x p90={pct(.9):.1f}x "
          f"p95={pct(.95):.1f}x p99={pct(.99):.1f}x max={sorted_t[-1]:.1f}x")
    print(f"spins: mean={mean_spins:.2f} median={median_spins} max={max(spins)} "
          f"spins<=2={100*sum(1 for x in spins if x<=2)/n:.2f}%")
    print("max stage reached: " + ", ".join(f"s{s}={stage_dist[s]:.2f}%" for s in range(1, 7)))
    print("end reasons: " + ", ".join(f"{k}={v:.2f}%" for k, v in sorted(reason_pct.items())))
    return dict(tag=tag, mean=mean, median=median, ratio=ratio)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    measure(n, 880000, "current_production_default")

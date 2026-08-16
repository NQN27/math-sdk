import sys, random, statistics, warnings, json
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

OUT_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch"

# Comprehensive per-(tier, stage) breakdown of: dead-spin rate (chain==1,
# i.e. that internal spin's initial reveal had zero wins and never
# cascaded) and the chain-length distribution/average AMONG spins that DID
# connect (chain>1) - needed before choosing chain-break parameters for any
# stage/tier, per the user's request to ground the design in real
# measurement rather than guessed curves.

_original_evaluate = gamestate_mod.GameState.evaluate_and_explode
_original_run_one_bonus_spin = gamestate_mod.GameState.run_one_bonus_spin


def _patched_evaluate(self, *a, **kw):
    self._diag_pass_count = getattr(self, "_diag_pass_count", 0) + 1
    return _original_evaluate(self, *a, **kw)


def _patched_run_one_bonus_spin(self, both_ways):
    self._diag_pass_count = 0
    stage_at_start = self.stage
    result = _original_run_one_bonus_spin(self, both_ways)
    if not hasattr(self, "_diag_stage_chain_log"):
        self._diag_stage_chain_log = []
    self._diag_stage_chain_log.append((stage_at_start, self._diag_pass_count))
    return result


gamestate_mod.GameState.evaluate_and_explode = _patched_evaluate
gamestate_mod.GameState.run_one_bonus_spin = _patched_run_one_bonus_spin


def measure_tier(tier, n, seed_offset):
    config = game_config_mod.GameConfig()
    config.bonus_safety_cap_spins = 250
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    # stage -> list of chain lengths (every internal spin logged at that stage)
    by_stage = {s: [] for s in range(1, 7)}

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs._diag_stage_chain_log = []
            gs.run_bonus_session(tier)
            for stage_at_start, chain_len in gs._diag_stage_chain_log:
                if 1 <= stage_at_start <= 6:
                    by_stage[stage_at_start].append(chain_len)

    print(f"\n=== {tier} (n={n} sessions) ===")
    summary = {}
    for stage in range(1, 7):
        chains = by_stage[stage]
        if not chains:
            print(f"  stage {stage}: no spins observed")
            continue
        total = len(chains)
        dead = sum(1 for c in chains if c == 1)
        connected = [c for c in chains if c > 1]
        dead_rate = 100 * dead / total
        conn_mean = statistics.mean(connected) if connected else 0
        conn_median = statistics.median(connected) if connected else 0
        conn_p90 = sorted(connected)[int(0.9 * len(connected))] if connected else 0
        conn_max = max(connected) if connected else 0
        print(
            f"  stage {stage}: n_spins={total} dead_rate={dead_rate:.2f}% "
            f"| when connected (n={len(connected)}): mean_chain={conn_mean:.2f} "
            f"median_chain={conn_median} p90_chain={conn_p90} max_chain={conn_max}"
        )
        summary[stage] = {
            "n_spins": total, "dead_rate_pct": round(dead_rate, 2),
            "n_connected": len(connected), "conn_mean_chain": round(conn_mean, 2),
            "conn_median_chain": conn_median, "conn_p90_chain": conn_p90, "conn_max_chain": conn_max,
        }
    return summary


if __name__ == "__main__":
    n_normal = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    n_super = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    n_hidden = int(sys.argv[3]) if len(sys.argv) > 3 else 8000

    all_summary = {}
    all_summary["normal"] = measure_tier("normal", n_normal, 55001)
    all_summary["super"] = measure_tier("super", n_super, 55002)
    all_summary["hidden"] = measure_tier("hidden", n_hidden, 55003)

    with open(f"{OUT_DIR}\\all_tier_stage_chain_summary.json", "w") as f:
        json.dump(all_summary, f, indent=2)
    print(f"\nSaved summary JSON to {OUT_DIR}\\all_tier_stage_chain_summary.json")

import sys, random, warnings, statistics
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# HYPOTHESIS TEST (2026-08-18): bonus_player_hp_choices["normal"] is consumed
# via random.choice() in game_bonus.py:326 - it's a WEIGHTED starting-HP draw,
# not a per-stage schedule. [50,50,50,100,100] = 60% start HP=50, 40% start
# HP=100. Earlier sweeps (pure_production_sweep2.py) scaled BOTH values up
# together (e.g. [100,100,100,200,200]) which preserved the 60/40 weighting
# but pushed stage-6 reach from ~22% up to 58% as HP rose - suspected cause
# of the ratio blowout (44%->115%), since stage 6 has an exclusive top-tier
# reward pool calibrated for ~22% reach. This script instead raises ONLY the
# low draw (fixes "instant death" 60% segment) leaving the high draw (100)
# and the 60/40 split untouched, to see if spins<=2% improves without
# dragging extra sessions into the stage-6 pool. Also reports payout split
# by whether the session reached stage 6, to directly test the hypothesis.
# PURE PRODUCTION: no chain-break monkeypatch, uses real run_bonus_session /
# run_one_bonus_spin / clear_stage unmodified except observational counters.

_orig_run_one_spin = gamestate_mod.GameState.run_one_bonus_spin
_orig_clear_stage = gamestate_mod.GameState.clear_stage

_state = {"spins": 0, "max_stage": 1}


def hooked_run_one_spin(self, *a, **k):
    _state["spins"] += 1
    return _orig_run_one_spin(self, *a, **k)


def hooked_clear_stage(self, *a, **k):
    result = _orig_clear_stage(self, *a, **k)
    _state["max_stage"] = max(_state["max_stage"], getattr(self, "stage", 1))
    return result


gamestate_mod.GameState.run_one_bonus_spin = hooked_run_one_spin
gamestate_mod.GameState.clear_stage = hooked_clear_stage


def measure(n, seed_offset, tag, hp_choices, dmg_mult=1.0):
    config = game_config_mod.GameConfig()
    config.bonus_player_hp_choices["normal"] = hp_choices
    if dmg_mult != 1.0:
        # symbol_damage_range is a single dict keyed by symbol name, shared
        # across all three tiers (normal/super/hidden) - there is no
        # per-tier key. Scratch-only global rescale is fine for measurement
        # (fresh GameConfig() each call); a production change would need a
        # different mechanism to avoid touching super/hidden.
        config.symbol_damage_range = {
            name: (lo * dmg_mult, hi * dmg_mult)
            for name, (lo, hi) in config.symbol_damage_range.items()
        }

    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals, spins_list, max_stages, s6_reach = [], [], [], []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            _state["spins"] = 0
            _state["max_stage"] = 1
            gs.run_bonus_session("normal")
            totals.append(gs.win_manager.running_bet_win)
            spins_list.append(_state["spins"])
            max_stages.append(_state["max_stage"])
            s6_reach.append(_state["max_stage"] >= 6)

    mean = sum(totals) / n
    median = statistics.median(totals)
    ratio = median / mean * 100 if mean > 0 else 0
    zero = 100 * sum(1 for t in totals if t == 0) / n
    spins_le2 = 100 * sum(1 for s in spins_list if s <= 2) / n
    mean_spins = sum(spins_list) / n

    s6_totals = [t for t, r in zip(totals, s6_reach) if r]
    non_s6_totals = [t for t, r in zip(totals, s6_reach) if not r]
    s6_pct = 100 * len(s6_totals) / n

    print(f"\n=== {tag} (n={n}) hp={hp_choices} dmg={dmg_mult:.2f} [PURE PRODUCTION] ===")
    print(f"mean={mean:.2f}x median={median:.2f}x ratio={ratio:.1f}% zero={zero:.2f}%")
    print(f"spins: mean={mean_spins:.2f} spins<=2={spins_le2:.2f}%")
    print(f"stage6 reach={s6_pct:.2f}% | s6-subset mean={sum(s6_totals)/len(s6_totals):.2f}x median={statistics.median(s6_totals):.2f}x"
          f" | non-s6 mean={sum(non_s6_totals)/len(non_s6_totals):.2f}x median={statistics.median(non_s6_totals):.2f}x")
    return dict(tag=tag, mean=mean, median=median, ratio=ratio, spins_le2=spins_le2, s6_pct=s6_pct, mean_spins=mean_spins)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    CANDIDATES = [
        ("baseline_current_prod", [50, 50, 50, 100, 100], 1.0),
        ("lowhp55", [55, 55, 55, 100, 100], 1.0),
        ("lowhp60", [60, 60, 60, 100, 100], 1.0),
        ("lowhp65", [65, 65, 65, 100, 100], 1.0),
        ("lowhp70", [70, 70, 70, 100, 100], 1.0),
        ("lowhp65_dmg095", [65, 65, 65, 100, 100], 0.95),
        ("lowhp70_dmg090", [70, 70, 70, 100, 100], 0.90),
    ]
    results = []
    for i, (tag, hp, dmg) in enumerate(CANDIDATES):
        results.append(measure(n, 999500 + i, tag, hp, dmg))

    print("\n=== SUMMARY ===")
    for r in results:
        print(f"{r['tag']:>22}: mean={r['mean']:.2f}x median={r['median']:.2f}x ratio={r['ratio']:.1f}%"
              f" spins<=2={r['spins_le2']:.2f}% s6reach={r['s6_pct']:.2f}% mean_spins={r['mean_spins']:.2f}")

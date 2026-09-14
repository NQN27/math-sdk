import sys, random, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# 3-way payout split for Normal Bonus: line-pay vs regular (non-chest)
# reward-drop vs chest-exclusive reward-drop, plus stage-death% and
# spins/session - one report covering everything asked for in one pass.

_orig_award_win = gamestate_mod.GameState.award_win
_orig_roll_reward_drop = gamestate_mod.GameState.roll_reward_drop
_tag = {"kind": None}
_totals = {"line": 0.0, "regular": 0.0, "chest": 0.0}


def tagged_roll_reward_drop(self, is_last_of_stage, stage):
    is_chest = stage == self.config.max_stage and is_last_of_stage
    _tag["kind"] = "chest" if is_chest else "regular"
    return _orig_roll_reward_drop(self, is_last_of_stage, stage)


gamestate_mod.GameState.roll_reward_drop = tagged_roll_reward_drop


def tagged_award_win(self, amount):
    result = _orig_award_win(self, amount)
    if _tag["kind"] is not None:
        _totals[_tag["kind"]] += amount
        _tag["kind"] = None
    else:
        _totals["line"] += amount
    return result


gamestate_mod.GameState.award_win = tagged_award_win


def measure(n, seed_offset, use_flat, tag):
    config = game_config_mod.GameConfig()
    if use_flat:
        config.use_flat_damage["normal"] = True
    gs = gamestate_mod.GameState(config)
    mode_max_win = config.bet_modes[0].get_wincap()
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, mode_max_win)
    gs.betmode = "base"

    line_totals, regular_totals, chest_totals, session_totals = [], [], [], []
    stage_death = {}
    spin_counts = []
    maxwin_count = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            _totals["line"] = 0.0
            _totals["regular"] = 0.0
            _totals["chest"] = 0.0
            _tag["kind"] = None
            gs.run_bonus_session("normal")
            raw = gs.win_manager.running_bet_win
            if raw >= mode_max_win:
                maxwin_count += 1
            line_totals.append(_totals["line"])
            regular_totals.append(_totals["regular"])
            chest_totals.append(_totals["chest"])
            session_totals.append(raw)
            stage_death[gs.stage] = stage_death.get(gs.stage, 0) + 1
            spin_counts.append(gs.bonus_spin_count)

    mean_line = sum(line_totals) / n
    mean_regular = sum(regular_totals) / n
    mean_chest = sum(chest_totals) / n
    mean_total = sum(session_totals) / n
    median_total = statistics.median(session_totals)
    mean_spins = sum(spin_counts) / n
    chest_hit_rate = sum(1 for c in chest_totals if c > 0) / n

    print(f"\n=== {tag} (n={n}) ===")
    print(f"maxwin hits: {maxwin_count}")
    print(f"line-pay:        {mean_line:.2f}x  ({100*mean_line/mean_total:.1f}% of total)")
    print(f"regular reward:  {mean_regular:.2f}x  ({100*mean_regular/mean_total:.1f}% of total)")
    print(f"chest reward:    {mean_chest:.2f}x  ({100*mean_chest/mean_total:.1f}% of total)  "
          f"(chest reached in {100*chest_hit_rate:.2f}% of sessions)")
    print(f"session total: mean={mean_total:.2f}x median={median_total:.2f}x "
          f"ratio={100*median_total/mean_total:.1f}%")
    print(f"avg spins/session={mean_spins:.2f}")
    print("stage-end %:", {k: round(100*v/n, 2) for k, v in sorted(stage_death.items())})


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    which = sys.argv[2] if len(sys.argv) > 2 else "both"
    if which in ("default", "both"):
        measure(n, 993000, False, "PRODUCTION (cascade, use_flat_damage=False)")
    if which in ("flat", "both"):
        measure(n, 993000, True, "FLAT-DAMAGE (current tuned config)")

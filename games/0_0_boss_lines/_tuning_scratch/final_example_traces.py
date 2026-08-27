import sys, random, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import final_combined_candidate as fc
from src.wins.win_manager import WinManager

# Concrete spin-by-spin traces for the NEW final combined candidate, same
# style as find_2spin_death_example.py earlier this session - find a
# typical early death, a mid-attrition death, and a stage6 clear, and
# narrate what actually happened.

_orig_run_one_spin = fc.gamestate_mod.GameState.run_one_bonus_spin
_log = []


def hooked_run_one_spin(self, both_ways):
    hp_before = self.player_hp
    stage_before = self.stage
    grace_before = getattr(self, "boss_counterattack_grace", False)
    alive_before = dict(self.boss_alive)
    dam_before = dict(self.boss_dam)
    win_before = self.win_manager.running_bet_win
    result = _orig_run_one_spin(self, both_ways)
    win_after = self.win_manager.running_bet_win
    _log.append(dict(
        stage_before=stage_before, hp_before=hp_before, hp_after=self.player_hp,
        grace_active=grace_before, alive_before=alive_before, dam_before=dam_before,
        spin_win=win_after - win_before, stage_after=self.stage,
    ))
    return result


fc.gamestate_mod.GameState.run_one_bonus_spin = hooked_run_one_spin


def find_example(max_tries, seed_offset, want_max_stage=None, want_spin_range=None, label=""):
    config = fc.build_config(1.0, 45.0)
    gs = fc.gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(max_tries):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            _log.clear()
            fc._state["max_stage"] = 1
            fc._state["pass_count"] = 0
            fc._state["chain_block_pending"] = False
            fc._state["general_chance"] = 0.0
            fc._state["chain_break_threshold"] = 2
            fc._state["chain_break_step"] = 0.30
            gs.run_bonus_session("normal")
            spin_count = len(_log)
            ms = fc._state["max_stage"]
            if want_max_stage is not None and ms != want_max_stage:
                continue
            if want_spin_range is not None and not (want_spin_range[0] <= spin_count <= want_spin_range[1]):
                continue

            print(f"\n=== {label}: sim={i}, {spin_count} internal spin(s), max_stage={ms}, "
                  f"total payout={gs.win_manager.running_bet_win:.2f}x, end_reason={getattr(gs,'bonus_end_reason','?')} ===")
            for idx, row in enumerate(_log, 1):
                alive_bosses = [b for b, a in row["alive_before"].items() if a]
                dam_this_spin = sum(row["dam_before"][b] for b in alive_bosses)
                stage_note = f"{row['stage_before']}"
                if row["stage_after"] != row["stage_before"]:
                    stage_note += f" -> {row['stage_after']} (cleared)"
                grace_note = " [GRACE - no counter-attack]" if row["grace_active"] else ""
                print(f"  spin{idx:>2}: stage {stage_note:>12} | HP {row['hp_before']:>8.1f} | "
                      f"dam this spin: {dam_this_spin:>7.1f}{grace_note} | win: {row['spin_win']:>8.2f}x")
            return
    print(f"\n[{label}] No matching example found in {max_tries} tries.")


if __name__ == "__main__":
    max_tries = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    find_example(max_tries, 970000, want_spin_range=(1, 3), label="Early death (1-3 spins)")
    find_example(max_tries, 970001, want_spin_range=(6, 10), label="Mid-attrition death (6-10 spins)")
    find_example(max_tries, 970002, want_max_stage=6, label="Reaches stage 6")

import sys, random, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Find and narrate a REAL example (current, unmodified production config,
# hp=[50,50,50,100,100]) of a session that ends within <=2 internal spins,
# so the designer can see exactly what happened spin-by-spin: starting HP
# draw, stage, per-boss Dam roll, whether counter-attack grace applied,
# connect/no-connect, and the resulting HP after each spin.

_orig_run_one_spin = gamestate_mod.GameState.run_one_bonus_spin

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
        stage_before=stage_before,
        hp_before=hp_before,
        hp_after=self.player_hp,
        grace_active=grace_before,
        alive_before=alive_before,
        dam_before=dam_before,
        spin_win=win_after - win_before,
        stage_after=self.stage,
    ))
    return result


gamestate_mod.GameState.run_one_bonus_spin = hooked_run_one_spin


def main(max_tries, seed_offset):
    config = game_config_mod.GameConfig()
    gs = gamestate_mod.GameState(config)
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
            hp_drawn = None
            gs.run_bonus_session("normal")
            spin_count = len(_log)
            if spin_count <= 2:
                print(f"\n=== Found example: sim={i}, {spin_count} internal spin(s), "
                      f"total payout={gs.win_manager.running_bet_win:.2f}x ===")
                for idx, row in enumerate(_log, 1):
                    alive_bosses = [b for b, a in row["alive_before"].items() if a]
                    dam_this_spin = sum(row["dam_before"][b] for b in alive_bosses)
                    print(f"\n-- Spin {idx} --")
                    print(f"  Stage: {row['stage_before']}"
                          + (f" -> {row['stage_after']} (cleared this spin)" if row["stage_after"] != row["stage_before"] else ""))
                    print(f"  Player HP before spin: {row['hp_before']:.1f}")
                    print(f"  Bosses alive: {alive_bosses}, per-boss Dam this spin: "
                          + ", ".join(f"{b}={row['dam_before'][b]:.1f}" for b in alive_bosses))
                    print(f"  Counter-attack grace active (skips damage)? {row['grace_active']}")
                    print(f"  Line-pay win this spin: {row['spin_win']:.2f}x")
                    if row["grace_active"]:
                        print(f"  -> Counter-attack SKIPPED (grace spin). HP after: {row['hp_after']:.1f}")
                    else:
                        print(f"  -> Counter-attack damage dealt: {dam_this_spin:.1f} "
                              f"(sum of alive bosses' Dam, already includes +/-25% variance roll)")
                        print(f"  -> Player HP after: {row['hp_after']:.1f}")
                print(f"\nSession ended: player_hp={gs.player_hp:.2f}, "
                      f"reason={getattr(gs, 'bonus_end_reason', '?')}")
                return
    print("No <=2-spin example found in the given number of tries - try a larger max_tries or different seed_offset.")


if __name__ == "__main__":
    max_tries = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    seed_offset = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    main(max_tries, seed_offset)

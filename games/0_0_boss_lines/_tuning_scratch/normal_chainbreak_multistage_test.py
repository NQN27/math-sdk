import sys, random, csv, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
import game_bonus as game_bonus_mod
from src.wins.win_manager import WinManager

OUT_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch"

# Per-stage-calibrated chain-break design, grounded in
# all_tier_stage_chain_diagnostic.py's n=10000 measurement of Normal's
# actual connected-chain-length distribution per stage:
#   stage: median / p90 (connected chains only)
#   2: 4 / 9      3: 4 / 10      4: 4 / 9      5: 4 / 11      6: 5 / 10
# Finding: medians/p90s cluster tightly (~4-5 / ~9-11) across ALL stages for
# Normal - unlike Hidden, where chain scale grows hugely by stage. So a
# "per-stage-calibrated" threshold converges to roughly the SAME absolute
# pass range for every Normal stage; the user's "gentler for stage 2-4"
# request is implemented via a lower slope/cap for those stages, not a
# later start point.
#
# Shape: p_stop(passes) = 0 for passes <= START, else
#        min(CAP, K * (GROWTH**(passes-START) - 1))
STAGE_GROUPS = {
    # stage 2-4: gentler (lower cap, shallower growth)
    2: dict(start=6, k=0.01, growth=1.4, cap=0.35),
    3: dict(start=6, k=0.01, growth=1.4, cap=0.35),
    4: dict(start=6, k=0.01, growth=1.4, cap=0.35),
    # stage 5-6: steeper (matches the earlier user-approved curve)
    5: dict(start=5, k=0.005, growth=1.6, cap=0.7),
    6: dict(start=5, k=0.005, growth=1.6, cap=0.7),
}


def p_stop(stage, passes):
    cfg = STAGE_GROUPS.get(stage)
    if cfg is None:
        return 0.0
    if passes <= cfg["start"]:
        return 0.0
    return min(cfg["cap"], cfg["k"] * (cfg["growth"] ** (passes - cfg["start"]) - 1))


def patched_run_one_bonus_spin(self, both_ways):
    self.win_manager.reset_spin_win()
    self.pass_exploded_positions = []
    self.create_board_reelstrips()
    self.enforce_removed_symbols()
    self.evaluate_and_explode(both_ways=both_ways)
    self.emit_tumble_win_events()
    self.emit_pass_extra_events()

    passes = 1
    forced_breaks = 0
    forced_breaks_by_stage = {}
    while not self.wincap_triggered and passes < self.config.max_resolve_passes:
        has_win = self.win_data["totalWin"] > 0
        has_fifo = bool(self.power_queue)
        if has_win and self.bonus_tier == "normal":
            p = p_stop(self.stage, passes)
            if p > 0 and random.random() < p:
                forced_breaks += 1
                forced_breaks_by_stage[self.stage] = forced_breaks_by_stage.get(self.stage, 0) + 1
                break
        if has_win or has_fifo:
            self.tumble_game_board()
            self.activate_next_power()
            self.evaluate_and_explode(both_ways=both_ways)
            self.emit_tumble_win_events()
            self.emit_pass_extra_events()
            passes += 1
            continue
        if self._board_has_elixir_or_booster():
            self._activate_elixir_booster()
            self.tumble_game_board()
            self.evaluate_and_explode(both_ways=both_ways)
            self.emit_tumble_win_events()
            self.emit_pass_extra_events()
            passes += 1
            continue
        break
    if passes >= self.config.max_resolve_passes:
        if self.power_queue:
            self.power_queue = []

    self._diag_forced_breaks = getattr(self, "_diag_forced_breaks", 0) + forced_breaks
    for st, cnt in forced_breaks_by_stage.items():
        self._diag_forced_breaks_by_stage = getattr(self, "_diag_forced_breaks_by_stage", {})
        self._diag_forced_breaks_by_stage[st] = self._diag_forced_breaks_by_stage.get(st, 0) + cnt
    self.set_end_tumble_event()
    self.win_manager.update_gametype_wins(self.gametype)


def measure(n, seed_offset, tag, use_chainbreak, save_csv=False):
    if use_chainbreak:
        gamestate_mod.GameState.run_one_bonus_spin = patched_run_one_bonus_spin
    else:
        gamestate_mod.GameState.run_one_bonus_spin = game_bonus_mod.GameBonus.run_one_bonus_spin

    config = game_config_mod.GameConfig()
    config.bonus_safety_cap_spins = 150
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals = []
    stage6_totals = []
    total_forced_breaks = 0
    breaks_by_stage_total = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs._diag_forced_breaks = 0
            gs._diag_forced_breaks_by_stage = {}
            gs.run_bonus_session("normal")
            payout = gs.win_manager.running_bet_win
            totals.append(payout)
            total_forced_breaks += gs._diag_forced_breaks
            for st, cnt in gs._diag_forced_breaks_by_stage.items():
                breaks_by_stage_total[st] = breaks_by_stage_total.get(st, 0) + cnt
            if gs.stage >= 6:
                stage6_totals.append(payout)

    if save_csv:
        with open(f"{OUT_DIR}\\{tag}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["payout_multiplier"])
            for t in totals:
                w.writerow([t])

    mean = sum(totals) / n
    median = statistics.median(totals)
    stdev = statistics.pstdev(totals)
    se = stdev / (n ** 0.5)
    ratio = median / mean * 100 if mean > 0 else 0
    s6_avg = sum(stage6_totals) / len(stage6_totals) if stage6_totals else 0
    print(
        f"[{tag}] (n={n}): mean={mean:.2f}x (+/-{1.96*se:.2f}) median={median:.2f}x "
        f"ratio={ratio:.1f}% CV={stdev/mean:.2f} stage6plus_avg={s6_avg:.1f}x (n={len(stage6_totals)}) "
        f"total_forced_breaks={total_forced_breaks} by_stage={breaks_by_stage_total}"
    )
    return mean, median


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    measure(n, 444555, "normal_chainbreak_ms_baseline", use_chainbreak=False, save_csv=True)
    measure(n, 444666, "normal_chainbreak_multistage", use_chainbreak=True, save_csv=True)

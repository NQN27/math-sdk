import sys, random, csv, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
import game_bonus as game_bonus_mod
from src.wins.win_manager import WinManager

OUT_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch"

# Test harness for the user's "chain-break" idea: after a cascade already
# has a connection (has_win==True, which would normally trigger another
# tumble), roll an increasing, uncapped-shape probability of forcibly
# ending the cascade instead - scoped to Normal-tier stage 5-6 only (per
# user's explicit direction: "tăng dần, không cap, chỉ áp dụng stage 5-6").
# Implemented here as a monkeypatch of run_one_bonus_spin (exact copy of
# the original with ONE inserted check) so this can be tested WITHOUT
# touching the production game_bonus.py until the design is validated.

CHAIN_BREAK_RATE = 0.05  # p_stop(passes) = min(1.0, RATE * passes), linear, no artificial cap

# Exponential variant (per user's refined request: "expo cham roi to dan" -
# slow start, then grows fast): p_stop(passes) = min(CAP, K*(GROWTH**passes - 1))
EXP_K = 0.002
EXP_GROWTH = 1.4
EXP_CAP = 0.7
USE_EXP = False


def p_stop_linear(passes):
    return min(1.0, CHAIN_BREAK_RATE * passes)


def p_stop_exp(passes):
    return min(EXP_CAP, EXP_K * (EXP_GROWTH ** passes - 1))


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
    while not self.wincap_triggered and passes < self.config.max_resolve_passes:
        has_win = self.win_data["totalWin"] > 0
        has_fifo = bool(self.power_queue)
        if has_win:
            if self.bonus_tier == "normal" and self.stage in (5, 6):
                p_stop = p_stop_exp(passes) if USE_EXP else p_stop_linear(passes)
                if random.random() < p_stop:
                    forced_breaks += 1
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
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs._diag_forced_breaks = 0
            gs.run_bonus_session("normal")
            payout = gs.win_manager.running_bet_win
            totals.append(payout)
            total_forced_breaks += gs._diag_forced_breaks
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
    buckets = [(0, 5, "0-5"), (5, 15, "5-15"), (15, 50, "15-50"), (50, 100, "50-100"),
               (100, 250, "100-250"), (250, 1000, "250-1000"), (1000, 1e12, ">1000")]
    bucket_str = " ".join(
        f"{lbl}:{100*sum(1 for t in totals if lo<=t<hi)/n:.1f}%" for lo, hi, lbl in buckets
    )
    print(
        f"[{tag}] (n={n}): mean={mean:.2f}x (+/-{1.96*se:.2f}) median={median:.2f}x "
        f"ratio={ratio:.1f}% CV={stdev/mean:.2f} stage6plus_avg={s6_avg:.1f}x (n={len(stage6_totals)}) "
        f"total_forced_breaks={total_forced_breaks}\n"
        f"    buckets: {bucket_str}"
    )
    return mean, median


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    mode = sys.argv[2] if len(sys.argv) > 2 else "linear"
    if mode == "exp":
        USE_EXP = True
        if len(sys.argv) > 3:
            EXP_K = float(sys.argv[3])
        if len(sys.argv) > 4:
            EXP_GROWTH = float(sys.argv[4])
        if len(sys.argv) > 5:
            EXP_CAP = float(sys.argv[5])
        preview = {p: round(p_stop_exp(p), 4) for p in (1, 3, 5, 8, 10, 12, 15, 18, 20, 25, 30)}
        print(f"p_stop_exp preview (K={EXP_K}, GROWTH={EXP_GROWTH}, CAP={EXP_CAP}): {preview}")
        tag = f"normal_chainbreak_exp_k{EXP_K}_g{EXP_GROWTH}_cap{EXP_CAP}"
    else:
        if len(sys.argv) > 3:
            CHAIN_BREAK_RATE = float(sys.argv[3])
        tag = f"normal_chainbreak_rate{CHAIN_BREAK_RATE}"

    measure(n, 333444, "normal_chainbreak_baseline", use_chainbreak=False, save_csv=True)
    measure(n, 333555, tag, use_chainbreak=True, save_csv=True)

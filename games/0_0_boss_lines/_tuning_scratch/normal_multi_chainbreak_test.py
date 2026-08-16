import sys, random, csv, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
import game_bonus as game_bonus_mod
from src.wins.win_manager import WinManager

OUT_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch"

# User's idea: instead of ONE fixed chain-break severity for every session,
# draw a severity PER BONUS SESSION (same pattern as bonus_player_hp_choices
# - one random.choice at session start, held for the whole session) from a
# weighted pool of curves ranging from "standard" cut down to "barely
# touches anything". Rationale: most sessions get controlled mean/CV, but
# the LIGHTEST-tier sessions occasionally let a monster chain through
# uncut - reintroducing some of the right-tail excitement chain-break
# otherwise removes uniformly from every session, without giving that back
# to ALL sessions (which would undo the mean-control benefit entirely).
CURVE_STANDARD = {  # = STAGE_GROUPS_LOOSE from the single-curve tests
    2: dict(start=7, k=0.008, growth=1.35, cap=0.2),
    3: dict(start=7, k=0.008, growth=1.35, cap=0.2),
    4: dict(start=7, k=0.008, growth=1.35, cap=0.2),
    5: dict(start=7, k=0.004, growth=1.5, cap=0.5),
    6: dict(start=7, k=0.004, growth=1.5, cap=0.5),
}
CURVE_LIGHTER = {  # = STAGE_GROUPS_ULTRALIGHT
    2: dict(start=9, k=0.005, growth=1.3, cap=0.15),
    3: dict(start=9, k=0.005, growth=1.3, cap=0.15),
    4: dict(start=9, k=0.005, growth=1.3, cap=0.15),
    5: dict(start=9, k=0.003, growth=1.4, cap=0.35),
    6: dict(start=9, k=0.003, growth=1.4, cap=0.35),
}
CURVE_LIGHTEST = {  # barely touches anything - very late start, tiny cap
    2: dict(start=14, k=0.003, growth=1.2, cap=0.08),
    3: dict(start=14, k=0.003, growth=1.2, cap=0.08),
    4: dict(start=14, k=0.003, growth=1.2, cap=0.08),
    5: dict(start=14, k=0.002, growth=1.25, cap=0.15),
    6: dict(start=14, k=0.002, growth=1.25, cap=0.15),
}

# (weight, curve) pairs - weights don't need to sum to 1, random.choices
# normalizes. "make % for it like HP" -> tune these percentages directly.
CURVE_POOL = [
    (0.50, CURVE_STANDARD),
    (0.30, CURVE_LIGHTER),
    (0.20, CURVE_LIGHTEST),
]
_CURVE_CHOICES = [c for _, c in CURVE_POOL]
_CURVE_WEIGHTS = [w for w, _ in CURVE_POOL]


def p_stop(curve, stage, passes):
    cfg = curve.get(stage)
    if cfg is None:
        return 0.0
    if passes <= cfg["start"]:
        return 0.0
    return min(cfg["cap"], cfg["k"] * (cfg["growth"] ** (passes - cfg["start"]) - 1))


_original_run_bonus_session = gamestate_mod.GameState.run_bonus_session


def patched_run_bonus_session(self, tier):
    # Draw ONE curve for this whole session (same pattern as
    # bonus_player_hp_choices), held across every internal spin within it -
    # not a per-spin re-roll.
    self._diag_active_curve = random.choices(_CURVE_CHOICES, weights=_CURVE_WEIGHTS, k=1)[0]
    self._diag_curve_label = CURVE_POOL[_CURVE_CHOICES.index(self._diag_active_curve)]
    return _original_run_bonus_session(self, tier)


def patched_run_one_bonus_spin(self, both_ways):
    self.win_manager.reset_spin_win()
    self.pass_exploded_positions = []
    self.create_board_reelstrips()
    self.enforce_removed_symbols()
    self.evaluate_and_explode(both_ways=both_ways)
    self.emit_tumble_win_events()
    self.emit_pass_extra_events()

    curve = getattr(self, "_diag_active_curve", CURVE_STANDARD)
    passes = 1
    forced_breaks = 0
    while not self.wincap_triggered and passes < self.config.max_resolve_passes:
        has_win = self.win_data["totalWin"] > 0
        has_fifo = bool(self.power_queue)
        if has_win and self.bonus_tier == "normal":
            p = p_stop(curve, self.stage, passes)
            if p > 0 and random.random() < p:
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


def measure(n, seed_offset, tag, hp_choices=None, save_csv=False):
    gamestate_mod.GameState.run_one_bonus_spin = patched_run_one_bonus_spin
    gamestate_mod.GameState.run_bonus_session = patched_run_bonus_session

    config = game_config_mod.GameConfig()
    config.bonus_safety_cap_spins = 150
    if hp_choices is not None:
        config.bonus_player_hp_choices = dict(config.bonus_player_hp_choices)
        config.bonus_player_hp_choices["normal"] = hp_choices
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    totals = []
    stage6_totals = []
    total_forced_breaks = 0
    curve_usage = {0: 0, 1: 0, 2: 0}
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
            curve_idx = _CURVE_CHOICES.index(gs._diag_active_curve)
            curve_usage[curve_idx] += 1
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
    s6_reach = 100 * len(stage6_totals) / n
    under5 = 100 * sum(1 for t in totals if t < 5) / n
    zero = 100 * sum(1 for t in totals if t == 0) / n
    top1 = sorted(totals)[int(0.99 * n)]
    print(
        f"[{tag}] (n={n}): mean={mean:.2f}x (+/-{1.96*se:.2f}) median={median:.2f}x "
        f"ratio={ratio:.1f}% CV={stdev/mean:.2f} stage6_reach={s6_reach:.1f}% "
        f"under5x={under5:.2f}% zero={zero:.2f}% top1pct_threshold={top1:.1f}x "
        f"total_forced_breaks={total_forced_breaks} curve_usage(std/lighter/lightest)={curve_usage}"
    )
    return mean, median


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000

    # 1) Multi-version chain-break alone, HP unchanged - isolate its shape
    #    vs the single-curve results (loose alone: mean=49.68x CV=1.04).
    measure(n, 700060, "multichainbreak_alone", hp_choices=[50, 50, 50, 100, 100], save_csv=True)

    # 2) Multi-version chain-break + HP75 - compare against the single-curve
    #    "best so far" (loose+HP75: mean=59.18x median=39.80x CV=0.88 zero=0.81%).
    measure(n, 700061, "multichainbreak_hp75", hp_choices=[75, 75, 100, 100, 100], save_csv=True)

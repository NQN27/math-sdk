import sys, random, csv, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
import game_bonus as game_bonus_mod
from src.wins.win_manager import WinManager

OUT_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch"

# Full 3-parameter matrix: chain-break MODE x HP pool x damage multiplier.
# Per user's standing note ("a skill is not to config only 1 parameter i
# will destroy whole thing") - every row here nudges all 3 levers together
# rather than maxing one out. CB axis has 2 modes:
#   - "loose": single fixed curve (STAGE_GROUPS_LOOSE from the earlier
#     single-curve tests - steep vs loose barely differed, so one
#     representative fixed curve stands in for that whole family).
#   - "multi": the 50/30/20 weighted per-session severity draw (the one
#     real, if modest, improvement found so far: same mean, higher CV than
#     any single fixed curve).

CURVE_LOOSE = {
    2: dict(start=7, k=0.008, growth=1.35, cap=0.2),
    3: dict(start=7, k=0.008, growth=1.35, cap=0.2),
    4: dict(start=7, k=0.008, growth=1.35, cap=0.2),
    5: dict(start=7, k=0.004, growth=1.5, cap=0.5),
    6: dict(start=7, k=0.004, growth=1.5, cap=0.5),
}
CURVE_LIGHTER = {
    2: dict(start=9, k=0.005, growth=1.3, cap=0.15),
    3: dict(start=9, k=0.005, growth=1.3, cap=0.15),
    4: dict(start=9, k=0.005, growth=1.3, cap=0.15),
    5: dict(start=9, k=0.003, growth=1.4, cap=0.35),
    6: dict(start=9, k=0.003, growth=1.4, cap=0.35),
}
CURVE_LIGHTEST = {
    2: dict(start=14, k=0.003, growth=1.2, cap=0.08),
    3: dict(start=14, k=0.003, growth=1.2, cap=0.08),
    4: dict(start=14, k=0.003, growth=1.2, cap=0.08),
    5: dict(start=14, k=0.002, growth=1.25, cap=0.15),
    6: dict(start=14, k=0.002, growth=1.25, cap=0.15),
}
MULTI_POOL = [(0.50, CURVE_LOOSE), (0.30, CURVE_LIGHTER), (0.20, CURVE_LIGHTEST)]
_MULTI_CHOICES = [c for _, c in MULTI_POOL]
_MULTI_WEIGHTS = [w for w, _ in MULTI_POOL]

# User: ratio=92.6% on multi+HP125+dmg20% (the best in-band candidate) is
# "too flat" - loosen the population-level severity by re-splitting the
# same 3 curves' weights 30-30-200 (raw weights, random.choices normalizes
# -> ~11.5%/11.5%/76.9%) instead of 50-30-20 -> most sessions now draw the
# CURVE_LIGHTEST tier (barely touches anything, start pass 14/cap 0.08-0.15)
# so more of the tail survives uncut, aiming to pull ratio/ CV back toward
# more skew without giving up the zero-payout fix (which comes from HP, not
# CB severity).
MULTI_POOL_V2 = [(30, CURVE_LOOSE), (30, CURVE_LIGHTER), (200, CURVE_LIGHTEST)]
_MULTI_V2_CHOICES = [c for _, c in MULTI_POOL_V2]
_MULTI_V2_WEIGHTS = [w for w, _ in MULTI_POOL_V2]


def p_stop(curve, stage, passes):
    cfg = curve.get(stage)
    if cfg is None:
        return 0.0
    if passes <= cfg["start"]:
        return 0.0
    return min(cfg["cap"], cfg["k"] * (cfg["growth"] ** (passes - cfg["start"]) - 1))


_original_run_bonus_session = gamestate_mod.GameState.run_bonus_session
_CB_MODE = "loose"  # set per-measure() call: "loose" or "multi"


_SWEEP_CHOICES = [CURVE_LOOSE, CURVE_LIGHTER, CURVE_LIGHTEST]
_SWEEP_WEIGHTS = [50, 30, 20]  # mutated per measure() call when cb_mode == "sweep"

# User: max=764.4x "quite small", wants median pulled toward 40-50x so max
# can grow. Empty dict -> p_stop's curve.get(stage) is None for every stage
# -> returns 0.0 always -> a literal "chain-break OFF" tier (not just
# "barely touches", truly uncapped), to let a small % of rare sessions run
# unbounded and pull max/p99 up without moving median much (rare by
# construction). Paired with a 4th weight slot on the SAME sweep_choices
# list, mode "sweep4".
CURVE_NONE = {}
_SWEEP4_CHOICES = [CURVE_LOOSE, CURVE_LIGHTER, CURVE_LIGHTEST, CURVE_NONE]
_SWEEP4_WEIGHTS = [30, 30, 30, 10]  # mutated per measure() call when cb_mode == "sweep4"


def patched_run_bonus_session(self, tier):
    if _CB_MODE == "multi":
        self._diag_active_curve = random.choices(_MULTI_CHOICES, weights=_MULTI_WEIGHTS, k=1)[0]
    elif _CB_MODE == "multiv2":
        self._diag_active_curve = random.choices(_MULTI_V2_CHOICES, weights=_MULTI_V2_WEIGHTS, k=1)[0]
    elif _CB_MODE == "sweep":
        self._diag_active_curve = random.choices(_SWEEP_CHOICES, weights=_SWEEP_WEIGHTS, k=1)[0]
    elif _CB_MODE == "sweep4":
        self._diag_active_curve = random.choices(_SWEEP4_CHOICES, weights=_SWEEP4_WEIGHTS, k=1)[0]
    else:
        self._diag_active_curve = CURVE_LOOSE
    return _original_run_bonus_session(self, tier)


def patched_run_one_bonus_spin(self, both_ways):
    self.win_manager.reset_spin_win()
    self.pass_exploded_positions = []
    self.create_board_reelstrips()
    self.enforce_removed_symbols()
    self.evaluate_and_explode(both_ways=both_ways)
    self.emit_tumble_win_events()
    self.emit_pass_extra_events()

    curve = getattr(self, "_diag_active_curve", CURVE_LOOSE)
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


def measure(n, seed_offset, tag, cb_mode, hp_choices, damage_mult, save_csv=False):
    global _CB_MODE
    _CB_MODE = cb_mode
    gamestate_mod.GameState.run_one_bonus_spin = patched_run_one_bonus_spin
    gamestate_mod.GameState.run_bonus_session = patched_run_bonus_session

    config = game_config_mod.GameConfig()
    config.bonus_safety_cap_spins = 150
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

    totals = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs._diag_forced_breaks = 0
            gs.run_bonus_session("normal")
            totals.append(gs.win_manager.running_bet_win)

    if save_csv:
        with open(f"{OUT_DIR}\\{tag}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["payout_multiplier"])
            for t in totals:
                w.writerow([t])

    mean = sum(totals) / n
    median = statistics.median(totals)
    stdev = statistics.pstdev(totals)
    ratio = median / mean * 100 if mean > 0 else 0
    under5 = 100 * sum(1 for t in totals if t < 5) / n
    zero = 100 * sum(1 for t in totals if t == 0) / n
    sorted_t = sorted(totals)
    p90 = sorted_t[int(0.90 * n)]
    p99 = sorted_t[int(0.99 * n)]
    mx = sorted_t[-1]
    print(
        f"[{tag}] cb={cb_mode} hp={hp_choices[0]}.. dmg={damage_mult:.2f} (n={n}): "
        f"mean={mean:.2f}x median={median:.2f}x ratio={ratio:.1f}% CV={stdev/mean:.2f} "
        f"under5x={under5:.2f}% zero={zero:.2f}% p90={p90:.1f}x p99={p99:.1f}x max={mx:.1f}x"
    )
    return dict(tag=tag, cb=cb_mode, hp=hp_choices, dmg=damage_mult, mean=mean,
                median=median, ratio=ratio, cv=stdev/mean, under5=under5, zero=zero,
                p90=p90, p99=p99, max=mx)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000

    # Wider sweep per user's ask: instead of one-off weight triples, sweep
    # the "lightest" tier's share smoothly (10/25/40/60/75/90%), splitting
    # the remainder evenly between standard/lighter each time - clean
    # 1-parameter view of how ratio/CV/mean/zero move as more sessions draw
    # the barely-touches-anything tier. Fixed on HP125+dmg20% (the best
    # in-band candidate found so far: mean=82.52x ratio=92.6% CV=0.78
    # zero=0.31% at the original 50/30/20 split) so this isolates the
    # weight-split's effect alone.
    LIGHTEST_PCTS = [10, 25, 40, 60, 75, 90]
    seed = 820000
    for lp in LIGHTEST_PCTS:
        rest = (100 - lp) / 2
        _SWEEP_WEIGHTS = [rest, rest, lp]
        tag = f"sweep_lightest{lp}_hp125_dmg120"
        measure(n, seed, tag, "sweep", [125, 125, 125, 125, 125], 1.20, save_csv=True)
        seed += 1

import sys, random, csv, statistics, warnings
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
import game_bonus as game_bonus_mod
from src.wins.win_manager import WinManager

OUT_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines\_tuning_scratch"

# Combined test: per-stage-calibrated chain-break (caps excessive long
# chains, esp. stage5-6) + a more generous HP pool (reduces dead-spin rate
# at the cost of more survival -> more mean, in isolation) - user's idea:
# these two levers may partially OFFSET each other (chain-break pulls mean
# down, HP-raise pushes it up), potentially letting HP go much higher
# (~200) than the earlier isolated test ([75,75,100,100,100], +21% mean)
# without blowing the budget as much, once chain-break is also active.
STAGE_GROUPS = {
    2: dict(start=6, k=0.01, growth=1.4, cap=0.35),
    3: dict(start=6, k=0.01, growth=1.4, cap=0.35),
    4: dict(start=6, k=0.01, growth=1.4, cap=0.35),
    5: dict(start=5, k=0.005, growth=1.6, cap=0.7),
    6: dict(start=5, k=0.005, growth=1.6, cap=0.7),
}

# "Loosened" variant per user's balance request: later start + lower cap,
# so chain-break only trims the truly extreme tail rather than a big chunk
# of the stage5-6 population - keeps more upside/excitement than the
# original curves above.
STAGE_GROUPS_LOOSE = {
    2: dict(start=7, k=0.008, growth=1.35, cap=0.2),
    3: dict(start=7, k=0.008, growth=1.35, cap=0.2),
    4: dict(start=7, k=0.008, growth=1.35, cap=0.2),
    5: dict(start=7, k=0.004, growth=1.5, cap=0.5),
    6: dict(start=7, k=0.004, growth=1.5, cap=0.5),
}
ACTIVE_STAGE_GROUPS = STAGE_GROUPS_LOOSE


# Flat-rate variant: no exponential ramp, just a constant probability once
# passes exceed `start` - a genuinely different SHAPE (not just a looser
# exponential), included per the "be creative, don't get stuck on one curve
# family" request. Tags each stage's config with mode="flat"/rate instead
# of k/growth/cap.
STAGE_GROUPS_ULTRALIGHT = {
    2: dict(start=9, k=0.005, growth=1.3, cap=0.15),
    3: dict(start=9, k=0.005, growth=1.3, cap=0.15),
    4: dict(start=9, k=0.005, growth=1.3, cap=0.15),
    5: dict(start=9, k=0.003, growth=1.4, cap=0.35),
    6: dict(start=9, k=0.003, growth=1.4, cap=0.35),
}

STAGE_GROUPS_FLAT = {
    2: dict(mode="flat", start=8, rate=0.10),
    3: dict(mode="flat", start=8, rate=0.10),
    4: dict(mode="flat", start=8, rate=0.10),
    5: dict(mode="flat", start=8, rate=0.15),
    6: dict(mode="flat", start=8, rate=0.15),
}


def p_stop(stage, passes):
    cfg = ACTIVE_STAGE_GROUPS.get(stage)
    if cfg is None:
        return 0.0
    if passes <= cfg["start"]:
        return 0.0
    if cfg.get("mode") == "flat":
        return cfg["rate"]
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
    while not self.wincap_triggered and passes < self.config.max_resolve_passes:
        has_win = self.win_data["totalWin"] > 0
        has_fifo = bool(self.power_queue)
        if has_win and self.bonus_tier == "normal":
            p = p_stop(self.stage, passes)
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


def measure(n, seed_offset, tag, use_chainbreak, hp_choices=None, damage_mult=None,
            curve=None, save_csv=False):
    if use_chainbreak:
        gamestate_mod.GameState.run_one_bonus_spin = patched_run_one_bonus_spin
    else:
        gamestate_mod.GameState.run_one_bonus_spin = game_bonus_mod.GameBonus.run_one_bonus_spin

    if curve is not None:
        global ACTIVE_STAGE_GROUPS
        ACTIVE_STAGE_GROUPS = curve

    config = game_config_mod.GameConfig()
    config.bonus_safety_cap_spins = 150
    if hp_choices is not None:
        config.bonus_player_hp_choices = dict(config.bonus_player_hp_choices)
        config.bonus_player_hp_choices["normal"] = hp_choices
    if damage_mult is not None:
        # measure() only ever runs tier="normal" sessions (see the loop
        # below), so scaling this dict here has no effect on Super/Hidden -
        # equivalent to a "Normal-only" damage bump for this test's purposes
        # without needing a runtime tier-gated monkeypatch.
        config.symbol_damage_range = {
            name: (lo * damage_mult, hi * damage_mult)
            for name, (lo, hi) in config.symbol_damage_range.items()
        }
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
    s6_reach = 100 * len(stage6_totals) / n
    under5 = 100 * sum(1 for t in totals if t < 5) / n
    zero = 100 * sum(1 for t in totals if t == 0) / n
    print(
        f"[{tag}] (n={n}): mean={mean:.2f}x (+/-{1.96*se:.2f}) median={median:.2f}x "
        f"ratio={ratio:.1f}% CV={stdev/mean:.2f} stage6_reach={s6_reach:.1f}% "
        f"under5x={under5:.2f}% zero={zero:.2f}% total_forced_breaks={total_forced_breaks}"
    )
    return mean, median


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15000

    # User picked HP75 + loose CB + damage+10% (mean=63.22x median=44.10x
    # ratio=69.8% CV=0.84 zero=0.74%) as the preferred direction and asked
    # to push harder on it specifically. Damage bump was shown to be a
    # clean mean-multiplier that doesn't disturb HP's zero-payout fix and
    # barely touches CV/shape (damage15/25-alone kept CV~2.2-2.3, near
    # baseline's 2.35) - so sweep damage% up on top of the SAME HP75+loose
    # CB base to walk mean toward the 85x target without re-touching HP or
    # chain-break (both already tuned/settled for this combo).
    ACTIVE_STAGE_GROUPS = STAGE_GROUPS_LOOSE
    # User: don't push damage alone (it was climbing ratio toward/past 100%
    # by 150-165% - same flattening failure mode as pushing HP too far
    # alone) - split the mean-raising duty across BOTH HP and damage, each
    # moved less far, to try to reach 80-85x mean with a better-preserved
    # CV/ratio than loading it all onto one axis.
    GRID = [
        ("hp125_dmg113", [125, 125, 125, 125, 125], 1.13),
        ("hp125_dmg115", [125, 125, 125, 125, 125], 1.15),
        ("hp140_dmg110", [140, 140, 140, 140, 140], 1.10),
    ]
    for i, (tag, hp, dm) in enumerate(GRID):
        measure(n, 700090 + i, f"grid_{tag}", use_chainbreak=True,
                hp_choices=hp, damage_mult=dm, curve=STAGE_GROUPS_LOOSE, save_csv=True)

    # 3) Flat-rate chain-break (new curve family) + HP75, vs the exponential
    #    curve's already-measured HP75 result (twoinone_loose_hp75: mean=
    #    59.18x median=39.80x CV=0.88 zero=0.81%).
    measure(n, 700042, "creative_flatcb_hp75", use_chainbreak=True,
            hp_choices=[75, 75, 100, 100, 100], curve=STAGE_GROUPS_FLAT, save_csv=True)

    # 4) Damage +15% (Normal only), NO chain-break, NO HP change - isolated
    #    effect of the offense-side lever on its own.
    measure(n, 700043, "creative_damage15_alone", use_chainbreak=False,
            hp_choices=[50, 50, 50, 100, 100], damage_mult=1.15, save_csv=True)

    # 5) Damage +15% + loose chain-break, HP unchanged - does damage recover
    #    mean that chain-break took, without touching HP/dead-spin at all?
    measure(n, 700044, "creative_damage15_loosecb", use_chainbreak=True,
            hp_choices=[50, 50, 50, 100, 100], damage_mult=1.15,
            curve=STAGE_GROUPS_LOOSE, save_csv=True)

    # 6) Triple stack: modest HP75 + loose chain-break + damage +10% - the
    #    "everything a little" combo.
    measure(n, 700045, "creative_triple_hp75_loosecb_dmg10", use_chainbreak=True,
            hp_choices=[75, 75, 100, 100, 100], damage_mult=1.10,
            curve=STAGE_GROUPS_LOOSE, save_csv=True)

    # 7) Damage +25% alone (bigger bump) - see if damage alone can hit the
    #    zero<1% target without touching HP or chain-break at all.
    measure(n, 700046, "creative_damage25_alone", use_chainbreak=False,
            hp_choices=[50, 50, 50, 100, 100], damage_mult=1.25, save_csv=True)

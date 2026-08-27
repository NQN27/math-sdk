"""Custom book events for the boss/stage system, the whole-board explode
rule, and (Phase 2) the Power system - none of these have a reusable
equivalent in src/events/events.py."""

BOARD_EXPLODE = "boardExplode"
BOSS_STATE = "bossState"
BOSS_DEFEATED = "bossDefeated"
STAGE_CLEAR = "stageClear"
REWARD_DROP = "rewardDrop"
POWER_CONNECTED = "powerConnected"
POWER_ACTIVATED = "powerActivated"
POWER_STATE = "powerState"

# --- Phase 3: Scatter/Bonus --------------------------------------------------
SCATTER_TALLY = "scatterTally"
BONUS_TRIGGER = "bonusTrigger"
BONUS_SPIN_START = "bonusSpinStart"
BONUS_COUNTERATTACK = "bonusCounterattack"
BONUS_END = "bonusEnd"
PLAYER_HP_STATE = "playerHpState"
ELIXIR_ACTIVATED = "elixirActivated"
BOOSTER_ACTIVATED = "boosterActivated"


def board_explode_event(gamestate, positions):
    """All board positions marked to explode this resolve pass - a superset
    of the winning lines' own positions (every same-type symbol anywhere on
    the board, not just the copies inside a winning line - see
    game_calculations.evaluate_and_explode)."""
    include_padding_index = gamestate.config.include_padding
    out_positions = []
    for pos in positions:
        row = pos["row"] + 1 if include_padding_index else pos["row"]
        out_positions.append({"reel": pos["reel"], "row": row})
    event = {
        "index": len(gamestate.book.events),
        "type": BOARD_EXPLODE,
        "positions": out_positions,
    }
    gamestate.book.add_event(event)


def boss_state_event(gamestate):
    """Current stage + all 3 bosses' HP/max-HP/alive state, for HP-bar UI."""
    event = {
        "index": len(gamestate.book.events),
        "type": BOSS_STATE,
        "stage": gamestate.stage,
        "bossSystemActive": gamestate.boss_system_active,
        "bossHp": {b: round(gamestate.boss_hp[b], 2) for b in gamestate.config.boss_ids},
        "bossMaxHp": {b: gamestate.boss_hp_max[b] for b in gamestate.config.boss_ids},
        "bossDam": {b: gamestate.boss_dam[b] for b in gamestate.config.boss_ids},
        "bossAlive": {b: gamestate.boss_alive[b] for b in gamestate.config.boss_ids},
    }
    gamestate.book.add_event(event)


def boss_defeated_event(gamestate, boss_id, is_last_of_stage, reward_tier, reward_amount):
    """A single boss reached 0 HP and an instant reward-drop was rolled/paid."""
    event = {
        "index": len(gamestate.book.events),
        "type": BOSS_DEFEATED,
        "stage": gamestate.stage,
        "bossId": boss_id,
        "isLastOfStage": is_last_of_stage,
        "rewardTier": reward_tier,
        "rewardAmount": round(reward_amount, 2),
    }
    gamestate.book.add_event(event)


def stage_clear_event(gamestate, stage_cleared, removed_symbol, pruned_tiers, next_stage):
    """All 3 bosses of `stage_cleared` are defeated: the stage effect
    (symbol removal + reward-tier pruning) is applied and the fight advances
    to `next_stage` (or the boss system goes dormant if there is none)."""
    event = {
        "index": len(gamestate.book.events),
        "type": STAGE_CLEAR,
        "stageCleared": stage_cleared,
        "removedSymbol": removed_symbol,
        "prunedTiers": list(pruned_tiers),
        "nextStage": next_stage,
    }
    gamestate.book.add_event(event)


# --- Power system (Phase 2) -------------------------------------------------


def _padded_row(gamestate, row):
    return row + 1 if gamestate.config.include_padding else row


def power_connected_event(gamestate, power_type, reel, row):
    """A Power symbol was connected via a winning payline this resolve pass.
    Emitted for every connection - immediate-group types (wild_multi/
    global_multi/maxwin) alongside their own power_activated_event (they
    activate the same pass they connect); FIFO-group types are emitted here
    when collected, then again via power_activated_event whenever they're
    later popped and activated (possibly a different pass)."""
    event = {
        "index": len(gamestate.book.events),
        "type": POWER_CONNECTED,
        "powerType": power_type,
        "position": {"reel": reel, "row": _padded_row(gamestate, row)},
    }
    gamestate.book.add_event(event)


def power_activated_event(gamestate, power_type, details):
    """A Power effect actually executed (immediate-group: same pass it
    connected; FIFO-group: whenever popped from the queue, one at a time).
    `details` is effect-specific - see game_calculations.evaluate_and_explode
    (wild_multi/global_multi) and game_executables.py's power_* handlers
    (maxwin/extra_wild/extra_power/big_symbol/mystery/alter)."""
    event = {
        "index": len(gamestate.book.events),
        "type": POWER_ACTIVATED,
        "powerType": power_type,
        "details": details,
    }
    gamestate.book.add_event(event)


def power_state_event(gamestate):
    """Current Global Multi total/effective value and FIFO queue snapshot,
    for UI display - emitted once per resolve pass alongside boss_state_event
    (see game_executables.emit_pass_extra_events)."""
    event = {
        "index": len(gamestate.book.events),
        "type": POWER_STATE,
        "globalMultiTotal": gamestate.global_multi_total,
        "effectiveGlobalMult": gamestate.effective_global_mult(),
        "powerQueue": list(gamestate.power_queue),
    }
    gamestate.book.add_event(event)


# --- Phase 3: Scatter / Bonus / Player HP / Elixir / Booster -----------------


def scatter_tally_event(gamestate, scatter_columns):
    """Running Scatter tally (by column, finalized once the base spin's
    cascade reaches static state) - emitted once, right after the base
    spin's resolve loop ends (see gamestate.run_spin)."""
    event = {
        "index": len(gamestate.book.events),
        "type": SCATTER_TALLY,
        "scatterColumns": sorted(scatter_columns),
        "count": len(scatter_columns),
    }
    gamestate.book.add_event(event)


def bonus_trigger_event(gamestate, tier, player_hp, player_hp_max, start_stage):
    """A Bonus session is starting: tier/granted Player HP/starting stage."""
    event = {
        "index": len(gamestate.book.events),
        "type": BONUS_TRIGGER,
        "tier": tier,
        "playerHp": player_hp,
        "playerHpMax": player_hp_max,
        "startStage": start_stage,
        "bothWays": gamestate.config.bonus_both_ways[tier],
    }
    gamestate.book.add_event(event)


def bonus_spin_start_event(gamestate, spin_index):
    """One internal spin within an active Bonus session is starting."""
    event = {
        "index": len(gamestate.book.events),
        "type": BONUS_SPIN_START,
        "spinIndex": spin_index,
    }
    gamestate.book.add_event(event)


def bonus_counterattack_event(gamestate, total_damage, player_hp_after):
    """All currently-alive bosses counterattacked at the end of a Bonus
    spin's resolve loop, dealing their summed Dam to Player HP."""
    event = {
        "index": len(gamestate.book.events),
        "type": BONUS_COUNTERATTACK,
        "totalDamage": round(total_damage, 2),
        "playerHpAfter": round(player_hp_after, 2),
    }
    gamestate.book.add_event(event)


def bonus_end_event(gamestate, tier, spins_taken, player_hp_final, end_reason):
    """Bonus session over - `end_reason` in {"hp_depleted", "wincap",
    "safety_cap", "stage_cleared"} (see game_bonus.run_bonus_session -
    stage 6 is an endless tail for tiers in config.stage6_endless_tiers;
    currently all 3 tiers are enabled, but "stage_cleared" remains a
    possible end_reason for any tier a future config change excludes from
    the endless tail - it ends the session the first time stage 6 clears,
    same as the original pre-endless behavior)."""
    event = {
        "index": len(gamestate.book.events),
        "type": BONUS_END,
        "tier": tier,
        "spinsTaken": spins_taken,
        "playerHpFinal": round(player_hp_final, 2),
        "endReason": end_reason,
    }
    gamestate.book.add_event(event)


def player_hp_state_event(gamestate):
    """Current Player HP/max snapshot - emitted whenever it changes
    (grant/Elixir heal/stage-clear bonus/counterattack)."""
    event = {
        "index": len(gamestate.book.events),
        "type": PLAYER_HP_STATE,
        "playerHp": round(gamestate.player_hp, 2),
        "playerHpMax": gamestate.player_hp_max,
    }
    gamestate.book.add_event(event)


def elixir_activated_event(gamestate, position, healed, player_hp_after):
    """One Elixir instance activated: healed Player HP by `healed` (already
    %-of-current, rounded to the nearest 10, capped at max)."""
    event = {
        "index": len(gamestate.book.events),
        "type": ELIXIR_ACTIVATED,
        "position": {"reel": position[0], "row": _padded_row(gamestate, position[1])},
        "healed": healed,
        "playerHpAfter": round(player_hp_after, 2),
    }
    gamestate.book.add_event(event)


def booster_activated_event(gamestate, positions):
    """1+ Booster instances activated together this pass: sets (does not
    stack) the boss-damage-multiplier flag for the NEXT bonus spin.
    booster_damage_multiplier is tier-scoped (2026-08-28) - only ever
    called from within an active Bonus session, so gamestate.bonus_tier is
    always set here."""
    event = {
        "index": len(gamestate.book.events),
        "type": BOOSTER_ACTIVATED,
        "positions": [{"reel": r, "row": _padded_row(gamestate, ro)} for r, ro in positions],
        "damageMultiplierNextSpin": gamestate.config.booster_damage_multiplier[gamestate.bonus_tier],
    }
    gamestate.book.add_event(event)

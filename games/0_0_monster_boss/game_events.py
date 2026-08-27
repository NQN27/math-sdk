APPLY_TUMBLE_MULTIPLIER = "applyMultiplierToTumble"
BOSS_DAMAGE = "bossDamage"
BOSS_BONUS = "bossBonus"


def boss_damage_event(gamestate, boss_hp, boss_max_hp, bosses_defeated):
    """Pass current boss HP pools after a tumble, so the frontend can animate HP
    bars for the 3 bosses. Shared by both the base-game boss battle
    (apply_boss_damage) and the free-spin boss wave (apply_freegame_boss_damage) -
    callers pass in whichever HP pool/max-HP/defeated-flag is relevant to their
    context, since the two run independent boss battles with different scales."""
    event = {
        "index": len(gamestate.book.events),
        "type": BOSS_DAMAGE,
        "bossHp": {str(boss_id): hp for boss_id, hp in boss_hp.items()},
        "bossMaxHp": boss_max_hp,
        "bossesDefeated": bosses_defeated,
    }
    gamestate.book.add_event(event)


def boss_bonus_event(gamestate, amount):
    """Pass the instant bonus amount awarded when all 3 bosses are defeated,
    so the frontend can show a 'BOSS DEFEATED +Nx' style callout."""
    event = {
        "index": len(gamestate.book.events),
        "type": BOSS_BONUS,
        "amount": amount,
    }
    gamestate.book.add_event(event)

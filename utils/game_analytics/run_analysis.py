"""Print .xlsx format summary document.
Args:
    - game-id, must match folder_name in src/games/<game-id>
    - Define search keys as listed in force_record_<mode>.json file. Partial keys in the force-file are matched to search keys

"""

from typing import List, Dict
from utils.game_analytics.retrieve_game_information import GameInformation
from utils.game_analytics.print_all_results import PrintJSON, PrintXLSX


def create_stat_sheet(game: str, custom_keys: List[Dict] = None, modes_to_analyse: List[str] = None):
    """Function executed from run file.

    `modes_to_analyse`: optional explicit subset of bet-mode names to
    analyse (default None preserves the original behaviour - GameInformation
    falls back to EVERY bet mode currently in game_config.py's bet_modes).
    Added for games/0_0_boss_lines's "Phase 4 v2" round: that game defines 6
    bet modes but this round only resimulates 4 of them
    (base/ante/buy3/buy4) - the other 2 (ultimatepower/godmode) are
    deliberately untouched this round, and their OWN existing library files
    were separately found to be internally stale (force_record_*.json
    references bookIds from an earlier ~100k-scale run, while
    lookUpTable_*_0.csv on disk is from a later, smaller re-run that never
    got paired with a matching force_record - a pre-existing inconsistency,
    unrelated to this round's changes) - passing an explicit subset here lets
    a game's own run.py skip analysing a mode without needing to touch that
    mode's files at all."""
    game_obj = GameInformation(game, custom_keys=custom_keys, modes_to_analyse=modes_to_analyse)
    PrintJSON(game_obj)
    PrintXLSX(game_obj)

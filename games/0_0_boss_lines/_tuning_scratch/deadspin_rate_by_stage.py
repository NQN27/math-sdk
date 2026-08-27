"""Does the EFFECTIVE deadspin/chain-block success rate vary by stage, even
though the config constants (chain_block_threshold/step,
bonus_grace_deadspin_chance) are flat scalars? Each stage uses a different
reel strip and has progressively more symbols removed (stage_clear removes
L1-L5 cumulatively), so _route_column_force_deadspin's valid-position search
could plausibly succeed/fail at very different rates by stage. Instruments
both grace-deadspin (create_board_reelstrips) and chain-block
(_maybe_apply_chain_block) by monkeypatching them to record, per stage:
  - how many times each mechanic's roll actually triggers an attempt
  - how many of those attempts SUCCEED (find a valid position) vs fall back
Real, unmodified game_config.py (chain_block_step=0.30, the shipped value) -
this is pure measurement, no config changes."""
import json
import sys
import warnings
import random
from collections import defaultdict

sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
import game_executables as game_executables_mod
from src.wins.win_manager import WinManager

stats = defaultdict(lambda: {
    "grace_attempts": 0, "grace_successes": 0,
    "chain_attempts": 0, "chain_successes": 0,
})

_orig_route = game_executables_mod.GameExecutables._route_column_force_deadspin
_orig_create_board = game_executables_mod.GameExecutables.create_board_reelstrips
_orig_maybe_chain = game_executables_mod.GameExecutables._maybe_apply_chain_block


def patched_create_board(self):
    was_grace_pending = getattr(self, "grace_deadspin_pending", False)
    stage = getattr(self, "stage", None)
    if getattr(self, "in_bonus", False) and was_grace_pending:
        self._grace_track = {"att": 0, "succ": 0}
    _orig_create_board(self)
    if getattr(self, "in_bonus", False) and was_grace_pending and stage is not None:
        gt = getattr(self, "_grace_track", None)
        if gt:
            stats[stage]["grace_attempts"] += gt["att"]
            stats[stage]["grace_successes"] += gt["succ"]


def patched_route_tracking(self, col):
    before = getattr(self, "_deadspin_route_fallback_count", 0)
    _orig_route(self, col)
    after = getattr(self, "_deadspin_route_fallback_count", 0)
    succeeded = (after == before)
    gt = getattr(self, "_grace_track", None)
    if gt is not None:
        gt["att"] += 1
        if succeeded:
            gt["succ"] += 1
    ct = getattr(self, "_chain_track", None)
    if ct is not None:
        ct["att"] += 1
        if succeeded:
            ct["succ"] += 1
    return succeeded


def patched_maybe_chain(self):
    stage = getattr(self, "stage", None)
    self._chain_track = {"att": 0, "succ": 0}
    _orig_maybe_chain(self)
    ct = self._chain_track
    if stage is not None and ct["att"] > 0:
        stats[stage]["chain_attempts"] += ct["att"]
        stats[stage]["chain_successes"] += ct["succ"]
    self._chain_track = None


game_executables_mod.GameExecutables._route_column_force_deadspin = patched_route_tracking
game_executables_mod.GameExecutables.create_board_reelstrips = patched_create_board
game_executables_mod.GameExecutables._maybe_apply_chain_block = patched_maybe_chain


def measure(n, seed_offset):
    config = game_config_mod.GameConfig()
    gs = gamestate_mod.GameState(config)
    gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
    gs.betmode = "base"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            gs.sim = i
            gs.criteria = "freegame"
            random.seed(seed_offset * 1000003 + i + 1)
            gs.reset_book()
            gs.run_bonus_session("normal")

    result = {}
    for stage in sorted(stats):
        s = stats[stage]
        result[stage] = {
            "grace_attempts": s["grace_attempts"],
            "grace_success_rate": round(100 * s["grace_successes"] / s["grace_attempts"], 2) if s["grace_attempts"] else None,
            "chain_attempts": s["chain_attempts"],
            "chain_success_rate": round(100 * s["chain_successes"] / s["chain_attempts"], 2) if s["chain_attempts"] else None,
        }
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 996001
    measure(n, seed)

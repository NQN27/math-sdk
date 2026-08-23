"""Lightweight, sims-only book regeneration (NOT the full run.py - no
optimization/analysis/format-checks, which would take much longer and
rewrite RTP-calibrated lookup tables we don't need touched just for a visual
sanity check). Real, unmodified game_config.py/gamestate.py - writes real
books_buy3.jsonl.zst reflecting the currently-shipped accepted bundle
(HP=200/boss table/SEG1-7/chain-block, commit cda6d50). buy3 guarantees a
bonus trigger every spin (~92% resolving to Normal tier per prior analysis),
so a small n here yields plenty of real Normal Bonus book examples. library/
is entirely gitignored (confirmed via `git check-ignore`), so this is fully
safe/reversible - just overwrites local, untracked simulation output."""
import sys

sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")

from gamestate import GameState
from game_config import GameConfig
from src.state.run_sims import create_books

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    mode = sys.argv[2] if len(sys.argv) > 2 else "buy3"

    config = GameConfig()
    gamestate = GameState(config)

    create_books(
        gamestate,
        config,
        {mode: n},
        batch_size=max(100, n // 2),
        threads=1,
        compress=True,
        profiling=False,
    )
    print(f"DONE: generated {n} sims for mode={mode}")

"""Converts real math-sdk generated books into the TS story-data format
web-sdk's Storybook apps expect.

Reveal boards are stripped down to the 5 VISIBLE rows per reel (padding
removed) - Boss Lines' own frontend (apps/boss-lines/src/game/
stateGame.svelte.ts) is wired to `createReelForSpinning`, the SAME
reel-animation component `apps/lines` uses (confirmed directly: both files
import createReelForSpinning, not createReelForCascading) - and apps/lines'
own committed fixtures (src/stories/data/base_books.ts) show 5-row reveal
boards, confirming that's this component family's real convention, not a
one-off. `createReelForCascading` (used by apps/scatter/cluster/ways, whose
fixtures ARE 7-row padded) is a DIFFERENT component Boss Lines does not use,
despite Boss Lines' gameplay also having tumble/cascade mechanics - it was
scaffolded from the `lines` app template, so its frontend reel plumbing
follows lines' convention, not scatter's. Do not "fix" this back to padded
without first re-pointing stateGame.svelte.ts at createReelForCascading (a
much bigger change, unverified) - see readme.txt's Phase 4 section / the
2026-08-25 investigation for the full reasoning.

Every OTHER event type (winInfo/boardExplode/tumbleBoard/etc, which report
row in the padded 1-5 range per game_events.py's _padded_row helper) is
passed through unchanged - the frontend's bookEventHandlerMap.ts already
subtracts 1 from those before indexing into the unpadded board array.

Usage:
  python convert_books_for_webfe.py <mode> <out_books.ts> <out_events.ts> [limit]
"""
import json
import os
import sys

import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.dirname(HERE)


def strip_padding_from_reveal(board):
    return [reel[1:-1] for reel in board]


def load_books(zst_path, limit=None):
    dctx = zstandard.ZstdDecompressor()
    with open(zst_path, "rb") as f:
        data = dctx.decompress(f.read(), max_output_size=2_000_000_000)
    lines = data.decode().splitlines()
    books = []
    for line in lines:
        b = json.loads(line)
        for e in b["events"]:
            if e["type"] == "reveal":
                e["board"] = strip_padding_from_reveal(e["board"])
        books.append(b)
    if limit:
        books = pick_representative(books, limit)
    return books


def pick_representative(books, limit):
    """Keep the fixture small but interesting: prefer a spread of outcomes
    (bonus-triggering, winning, and losing books) over the first N in file
    order, which are overwhelmingly small base-game losses."""
    is_bonus = {b["id"]: any(e["type"] == "bonusTrigger" for e in b["events"]) for b in books}
    bonus = [b for b in books if is_bonus[b["id"]]]
    wins = [b for b in books if not is_bonus[b["id"]] and b["payoutMultiplier"] > 0]
    zeros = [b for b in books if not is_bonus[b["id"]] and b["payoutMultiplier"] == 0]

    bonus.sort(key=lambda b: -b["payoutMultiplier"])
    wins.sort(key=lambda b: -b["payoutMultiplier"])

    quota_bonus = min(len(bonus), max(1, limit // 2))
    quota_wins = min(len(wins), max(1, limit // 3))
    quota_zeros = max(0, limit - quota_bonus - quota_wins)

    picked = bonus[:quota_bonus] + wins[:quota_wins] + zeros[:quota_zeros]
    return picked[:limit]


def to_ts(payload):
    # json.dumps gives valid JS object-literal syntax (double-quoted keys are
    # valid JS/TS), so this is a straight, lossless serialization - no data
    # is rewritten by hand.
    return f"export default {json.dumps(payload, indent=1)};\n"


def make_events_fixture(books):
    """One representative real example per distinct event type seen, for the
    single-event Storybook fixtures (base_events.ts/bonus_events.ts)."""
    seen = {}
    for b in books:
        for e in b["events"]:
            if e["type"] not in seen:
                seen[e["type"]] = e
    return seen


if __name__ == "__main__":
    mode = sys.argv[1]
    out_books = sys.argv[2]
    out_events = sys.argv[3]
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else None

    zst_path = os.path.join(GAME_DIR, "library", "publish_files", f"books_{mode}.jsonl.zst")
    all_books = load_books(zst_path)
    print(f"loaded {len(all_books)} books from {zst_path}")

    events_fixture = make_events_fixture(all_books)
    books = pick_representative(all_books, limit) if limit else all_books

    with open(out_books, "w", encoding="utf-8") as f:
        f.write(to_ts(books))
    print(f"wrote {out_books} with {len(books)} books")

    with open(out_events, "w", encoding="utf-8") as f:
        f.write(to_ts(events_fixture))
    print(
        f"wrote {out_events} with {len(events_fixture)} distinct event types: "
        f"{sorted(events_fixture)}"
    )

"""Converts real math-sdk generated books into the TS story-data format
web-sdk's Storybook apps expect.

This is a STRAIGHT PASS-THROUGH: no board or position data is altered at all.
That was verified against the framework's own cascading-reel implementation
(packages/utils-slots/src/createReelForCascading.svelte.ts) and against the
officially-tracked apps/scatter fixtures, which Boss Lines' frontend is built
on. Cascading reels keep the reveal event's FULL padded board (7 rows per reel
for a 5-row game) and map array index i to visible row i-1, so:

  * reveal boards must keep their padding rows, and
  * the PADDED row indices (1..5) that game_events.py emits on every
    `position` are already the correct array indices.

apps/scatter's own committed fixtures show the same 7-row boards and 1..5 row
values, confirming this is the framework's convention rather than a quirk of
this game. (Non-cascading, `lines`-style spinning reels use unpadded 5-row
boards instead - do not copy this script's behaviour to such a game without
re-checking.)

Usage:
  python convert_books_for_webfe.py <mode> <out_books.ts> <out_events.ts> [limit]
"""
import json
import os
import sys

import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.dirname(HERE)


def load_books(zst_path, limit=None):
    dctx = zstandard.ZstdDecompressor()
    with open(zst_path, "rb") as f:
        data = dctx.decompress(f.read(), max_output_size=2_000_000_000)
    lines = data.decode().splitlines()
    books = []
    for line in lines:
        books.append(json.loads(line))
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

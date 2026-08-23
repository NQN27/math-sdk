"""Converts real math-sdk generated books into the TS story-data format
web-sdk's Storybook apps expect, confirmed against the framework's own
packages/utils-slots/src/createEnhanceBoardSpin.ts and the officially-tracked
example apps (apps/lines, apps/ways, etc): reveal events keep ONLY the 5
visible rows per reel (no padding rows) plus their own paddingPositions field
(= the raw reel index, unchanged) - visual pre-fill during spin animation is
synthesized client-side from config.paddingReels, not embedded per-event.
Every other event type is passed through completely unchanged - this script
does not alter any game-outcome data, only strips the 2 padding entries per
reel from "reveal" events.
"""
import json
import sys
import zstandard

GAME_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines"


def strip_padding_from_reveal(board):
    return [reel[1:-1] for reel in board]


def load_books(zst_path, limit=None):
    dctx = zstandard.ZstdDecompressor()
    with open(zst_path, "rb") as f:
        data = dctx.decompress(f.read(), max_output_size=1_000_000_000)
    lines = data.decode().splitlines()
    if limit:
        lines = lines[:limit]
    books = []
    for line in lines:
        b = json.loads(line)
        for e in b["events"]:
            if e["type"] == "reveal":
                e["board"] = strip_padding_from_reveal(e["board"])
        books.append(b)
    return books


def to_ts(books, var_name):
    # json.dumps gives valid JS object-literal syntax (double-quoted keys are
    # valid JS/TS), so this is a straight, lossless serialization - no data
    # is rewritten by hand.
    body = json.dumps(books, indent=1)
    return f"export default {body};\n"


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
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    out_books = sys.argv[3]
    out_events = sys.argv[4]
    var_name = sys.argv[5] if len(sys.argv) > 5 else "books"

    zst_path = f"{GAME_DIR}\\library\\publish_files\\books_{mode}.jsonl.zst"
    books = load_books(zst_path, limit)
    print(f"loaded {len(books)} books from {zst_path}")

    with open(out_books, "w", encoding="utf-8") as f:
        f.write(to_ts(books, var_name))
    print(f"wrote {out_books}")

    events_fixture = make_events_fixture(books)
    with open(out_events, "w", encoding="utf-8") as f:
        f.write(to_ts(events_fixture, "events"))
    print(f"wrote {out_events} with {len(events_fixture)} distinct event types: {sorted(events_fixture.keys())}")

"""Cross-check: does each real generated book's own top-level payout field
match what you'd independently compute by replaying its own event stream
(summing win events / reading the final setTotalWin+finalWin)? This is a
pure data-consistency check on already-generated books.jsonl.zst - no
simulation is re-run, so any mismatch found here is either a bug in how
game_events.py emits these fields, or in how the book-level summary field is
written (game_state.py / book writing code), not a frontend issue.
"""
import json
import sys
import zstandard

GAME_DIR = r"D:\Stake Engine\math-sdk\games\0_0_boss_lines"


def load_books(zst_path, limit=None):
    dctx = zstandard.ZstdDecompressor()
    with open(zst_path, "rb") as f:
        data = dctx.decompress(f.read(), max_output_size=1_000_000_000)
    lines = data.decode().splitlines()
    if limit:
        lines = lines[:limit]
    return [json.loads(line) for line in lines]


def check_mode(mode, limit=2000):
    zst_path = f"{GAME_DIR}\\library\\publish_files\\books_{mode}.jsonl.zst"
    books = load_books(zst_path, limit)
    print(f"\n=== mode={mode}  n={len(books)} ===")

    top_level_keys = set()
    for b in books[:5]:
        top_level_keys.update(b.keys())
    print(f"top-level book keys (sample): {sorted(top_level_keys)}")

    mismatches_vs_finalwin = []
    mismatches_vs_settotalwin = []
    finalwin_vs_settotalwin_mismatches = []
    no_finalwin = 0
    no_settotalwin = 0

    for b in books:
        book_payout = b.get("payoutMultiplier")
        events = b["events"]
        final_win_events = [e for e in events if e["type"] == "finalWin"]
        set_total_win_events = [e for e in events if e["type"] == "setTotalWin"]

        final_win_amt = final_win_events[-1]["amount"] if final_win_events else None
        set_total_win_amt = set_total_win_events[-1]["amount"] if set_total_win_events else None

        if final_win_amt is None:
            no_finalwin += 1
        if set_total_win_amt is None:
            no_settotalwin += 1

        if final_win_amt is not None and book_payout is not None and abs(final_win_amt - book_payout) > 0.01:
            mismatches_vs_finalwin.append((b.get("id"), book_payout, final_win_amt))
        if set_total_win_amt is not None and book_payout is not None and abs(set_total_win_amt - book_payout) > 0.01:
            mismatches_vs_settotalwin.append((b.get("id"), book_payout, set_total_win_amt))
        if final_win_amt is not None and set_total_win_amt is not None and abs(final_win_amt - set_total_win_amt) > 0.01:
            finalwin_vs_settotalwin_mismatches.append((b.get("id"), set_total_win_amt, final_win_amt))

    print(f"books with NO finalWin event: {no_finalwin}/{len(books)}")
    print(f"books with NO setTotalWin event: {no_settotalwin}/{len(books)}")
    print(f"book.payoutMultiplier != last finalWin.amount: {len(mismatches_vs_finalwin)}/{len(books)}")
    for row in mismatches_vs_finalwin[:5]:
        print(f"    id={row[0]} payoutMultiplier={row[1]} finalWin.amount={row[2]}")
    print(f"book.payoutMultiplier != last setTotalWin.amount: {len(mismatches_vs_settotalwin)}/{len(books)}")
    for row in mismatches_vs_settotalwin[:5]:
        print(f"    id={row[0]} payoutMultiplier={row[1]} setTotalWin.amount={row[2]}")
    print(f"last finalWin.amount != last setTotalWin.amount: {len(finalwin_vs_settotalwin_mismatches)}/{len(books)}")
    for row in finalwin_vs_settotalwin_mismatches[:5]:
        print(f"    id={row[0]} setTotalWin.amount={row[1]} finalWin.amount={row[2]}")


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    for mode in ["base", "buy3"]:
        try:
            check_mode(mode, limit)
        except FileNotFoundError as e:
            print(f"mode={mode}: SKIPPED, file not found: {e}")

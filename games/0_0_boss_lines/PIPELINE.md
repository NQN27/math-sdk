# Boss Lines — Full Test Pipeline (math-sdk + web-sdk)

Step-by-step to go from a fresh clone of both repos to a running,
verified, backend-matched frontend. Written 2026-08-26 for testing on a
new machine (no GPU, 30GB RAM) - see the "No GPU" note in step 6.

Read `TOWORK.md` first for known open issues that aren't bugs in this
pipeline itself.

## 0. What you need

- Two repos, cloned side by side (paths below assume this):
  - `math-sdk` — this repo. Branch `backup_plan`. Personal fork:
    `https://github.com/NQN27/Stake_game.git`
  - `web-sdk` — the frontend. Branch `main`. Personal fork (private):
    `https://github.com/NQN27/web-sdk.git`
- Python 3.10+ , Node.js + pnpm.

```
git clone -b backup_plan https://github.com/NQN27/Stake_game.git math-sdk
git clone -b main https://github.com/NQN27/web-sdk.git web-sdk
```

## 1. Install dependencies

```
cd math-sdk
pip install -r requirements.txt

cd ../web-sdk
pnpm install
```

## 2. Confirm the backend library is present (or regenerate it)

The generated books/configs already live in git
(`games/0_0_boss_lines/library/publish_files/`,
`games/0_0_boss_lines/library/configs/`) — you do NOT need to re-run the
full simulation to test. Just confirm they're there:

```
ls games/0_0_boss_lines/library/publish_files/
# expect: books_base.jsonl.zst, books_ante.jsonl.zst, books_buy3.jsonl.zst,
#         books_buy4.jsonl.zst, books_godmode.jsonl.zst, books_ultimatepower.jsonl.zst
ls games/0_0_boss_lines/library/configs/
# expect: config_fe_0_0_boss_lines.json (among others)
```

Only re-run the full pipeline if you're deliberately re-tuning the math
(this takes a while - 20k sims x 6 bet modes + optimization):

```
cd games/0_0_boss_lines
python run.py
```

## 3. Regenerate the frontend config + story data from the CURRENT backend

This is the step that keeps math-sdk and web-sdk paired — always run this
after ANY change to `game_config.py` or after regenerating books, even if
you didn't touch the frontend at all.

```
cd math-sdk/games/0_0_boss_lines/_tuning_scratch

python gen_webfe_config.py "../../../../web-sdk/apps/boss-lines/src/game/config.ts"

python convert_books_for_webfe.py base "../../../../web-sdk/apps/boss-lines/src/stories/data/base_books.ts" "../../../../web-sdk/apps/boss-lines/src/stories/data/base_events.ts" 200

python convert_books_for_webfe.py buy3 "../../../../web-sdk/apps/boss-lines/src/stories/data/bonus_books.ts" "../../../../web-sdk/apps/boss-lines/src/stories/data/bonus_events.ts" 150
```

Adjust the relative paths above if your two repos aren't cloned as
siblings in the same parent folder.

**Do not** edit `config.ts` or `*_books.ts`/`*_events.ts` by hand — they're
generated. If something looks wrong in them, the fix belongs in
`game_config.py`/the book data or in the two Python scripts above, not in
the `.ts` files directly.

## 4. Type-check the frontend

```
cd web-sdk/apps/boss-lines
NODE_OPTIONS="--max-old-space-size=6144" npx tsc --noEmit
```

Expect a handful of PRE-EXISTING errors unrelated to Boss Lines (missing
placeholder art files under `static/assets/**`, some `node_modules`/SvelteKit
type-resolution quirks, one known pre-existing `paddingBoard` readonly-array
type error — see `TOWORK.md`). Anything else new is worth investigating
before moving on.

## 5. Start the dev server

```
cd web-sdk/apps/boss-lines
pnpm run storybook
```

Opens on `http://localhost:6001`. The FIRST request after starting is slow
(can be 1-2 minutes — it's bundling the large story-data files for the
first time), subsequent ones are fast. Don't assume it's broken if the
first page load takes a while.

Two stories matter for manual testing:
- `http://localhost:6001/?path=/story/mode-base-book--random` (single spin)
- `http://localhost:6001/?path=/story/mode-bonus-book--random` (full boss
  battle session)

Click the green **"Action"** button to play a random real book. Both demos
show a yellow warning banner at the bottom of the screen: the sample is
curated for variety, NOT statistically random — never use it to eyeball
mean/RTP (see step 7 for that).

## 6. No-GPU note

Without a GPU, the browser falls back to software-rendered WebGL/canvas.
This is SLOWER but should be MORE stable, not less — the intermittent
crash we hit repeatedly on this dev machine ("GPU stall due to
ReadPixels", WebGPU/spine driver crashes during the win-celebration
animation) is a *virtualized-GPU* problem specific to this sandbox. A
real machine with no GPU at all sidesteps that failure mode entirely, at
the cost of rendering speed. If it's slow, that's expected; if it hangs
or throws real JS errors (not just slow rendering), that's a real bug —
check the browser console.

## 7. Verify math/frontend consistency (optional, no browser needed)

```
cd math-sdk/games/0_0_boss_lines/_tuning_scratch
python verify_book_payout_consistency.py 2000
```

Confirms every book's own `payoutMultiplier` field matches its
`finalWin`/`setTotalWin` events exactly — i.e. the data sent to the
frontend is faithful to what the backend actually computed. Expect
"0/2000" mismatches on every line.

For real mean/median/variance/per-stage numbers (NOT from the frontend
demo sample):

```
python normal_bonus_full_stats.py 12000
```

## 8. If something's actually broken (not just slow)

- **"Missing bookEventHandler" console error**: a real book event type has
  no handler in `bookEventHandlerMap.ts`/`typesBookEvent.ts` — this HAS
  happened before (`updateTumbleWin`, `wincap`) when new/rarer event types
  showed up after regenerating story data. Add the type + a handler,
  don't ignore it.
- **Stuck at "Running..." forever with no error**: something is awaiting a
  broadcast that never resolves. This exact class of bug has hit this app
  three separate times (row-index off-by-one, a shared-reference
  animation-complete signal, a frame-visibility-gated animation-complete
  signal) — see `readme.txt`'s Phase 4 section for the full history before
  assuming it's a new mechanism.
- **Boss HUD (Stage/HP/Boss 1-2-3) invisible but nothing else is wrong**:
  check viewport height — this was a real, now-fixed bug where the HUD sat
  too high above the board and got clipped on any window under ~900px
  tall.

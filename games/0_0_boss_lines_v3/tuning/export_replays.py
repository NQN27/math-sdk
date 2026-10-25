"""Export real simulated sessions for the replay viewer (single process).

usage: python tuning/export_replays.py overrides.json OUT.json [per_tier_pool]
Simulates a pool of sessions per tier (Bonus / Super / Epic / Heroic / Treasure hunt), picks ~12 spread
over the payout distribution (plus the biggest and any Max Win), then re-runs
those exact sessions (seeds are deterministic) and saves their events.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tune_harness as H  # noqa: E402

PICK_PCT = [2, 10, 25, 40, 50, 60, 75, 85, 92, 97, 99.5]
POOL = {"bonus": 400, "super": 300, "epic": 150, "feature_heroic": 400, "feature_treasure": 300}
TARGET = {"bonus": 91.0, "super": 245.0, "epic": 2045.0, "feature_heroic": 403.0, "feature_treasure": 564.0}


def main():
    ov_path, out = sys.argv[1], sys.argv[2]
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    ov = json.load(open(ov_path))
    gs, cfg = H._setup(json.loads(json.dumps(ov)))
    # Replay-only "lit" events: the cells each destroy actually lit (lit_rule makes this impossible
    # to rebuild from the other events). No RNG is used, so sessions stay identical.
    from game_events import emit, pos
    real_destroy = type(gs).destroy_cells
    def destroy_cells(self, cells, lit_cells=()):
        before = set(self.lit)
        real_destroy(self, cells, lit_cells)
        new = [c for c in self.lit if c not in before]
        if new:
            emit(self, "lit", cells=[pos(self, c, r) for c, r in sorted(new)])
    type(gs).destroy_cells = destroy_cells
    sessions = []
    for tier, n in POOL.items():
        n = int(n * scale)
        wins = []
        for i in range(n):
            H._one(gs, cfg, tier, i)
            wins.append((gs.win_manager.running_bet_win, i, gs.wincap_triggered))
        ranked = sorted(wins)
        picks = {}
        for p in PICK_PCT:
            k = min(n - 1, int(n * p / 100))
            picks[ranked[k][1]] = p
        picks[ranked[-1][1]] = 100
        for w, i, mw in ranked:
            if mw and len([x for x in picks.values() if x == "maxwin"]) < 1:
                picks[i] = "maxwin"
        rank_of = {i: r for r, (_, i, _) in enumerate(ranked)}
        for i, label in sorted(picks.items(), key=lambda kv: rank_of[kv[0]]):
            H._one(gs, cfg, tier, i)
            ev = [{k: v for k, v in e.items() if k != "index"} for e in gs.book.events]
            sessions.append({
                "tier": tier, "seed": i, "win": round(gs.win_manager.running_bet_win, 2),
                "maxwin": gs.wincap_triggered, "pct": round(100 * rank_of[i] / max(1, n - 1), 1),
                "events": ev,
            })
        print(tier, "pool", n, "picked", len(picks), "median", ranked[n // 2][0])
    meta = {"overrides": os.path.basename(ov_path), "targets": TARGET, "pool": {k: int(v * scale) for k, v in POOL.items()},
            "boss_zones": cfg.boss_zones, "wincap": cfg.wincap, "litEvents": True}
    json.dump({"meta": meta, "sessions": sessions}, open(out, "w"), separators=(",", ":"))
    print("wrote", out, os.path.getsize(out) // 1024, "KB,", len(sessions), "sessions")


if __name__ == "__main__":
    main()

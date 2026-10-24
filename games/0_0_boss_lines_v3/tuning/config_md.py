"""Readable Markdown sheet of a tuning candidate's effective config (overrides applied on top of game_config.py).

usage: python tuning/config_md.py OVERRIDES.json OUT.md [RESULTS.txt]
Weight tables are shown as shares (% of the table), values per Bonus tier / Feature side by side; the exact raw
numbers stay in the overrides JSON. RESULTS.txt (verify_opt + sample_rtp output) is appended if given.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tune_harness as H  # noqa: E402

TIERS = ["bonus", "super", "epic", "heroic", "treasure_hunt"]
TNAME = {"bonus": "Normal", "super": "Super", "epic": "Epic", "heroic": "Heroic", "treasure_hunt": "Treasure hunt"}
SKIP = {"_reel_specs", "tier_weights"}


def num(x):
    if isinstance(x, float):
        return f"{x:.6g}"
    return str(x)


def shares(table):
    """{value: weight} -> 'value pct%' list (weights as % of the table)."""
    tot = sum(v for v in table.values() if isinstance(v, (int, float))) or 1
    out = []
    for k, v in table.items():
        p = 100 * v / tot
        if p == 0:
            continue
        ps = f"{p:.3g}%" if p >= 0.01 else f"{p:.2g}%"
        out.append(f"{num(k)}: {ps}")
    return " · ".join(out) or "–"


def show(name, v):
    if isinstance(v, dict) and v and all(isinstance(x, dict) for x in v.values()):
        return "<br>".join(f"**{k}**: {show(name, x)}" for k, x in v.items())
    if isinstance(v, dict) and name.endswith("_weights") and all(isinstance(x, (int, float)) for x in v.values()):
        return shares(v)
    if isinstance(v, dict):
        return ", ".join(f"{num(k)}: {show(name, x)}" for k, x in v.items()) or "{}"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(show(name, x) for x in v) + "]"
    return num(v)


def main():
    ov_path, out = sys.argv[1], sys.argv[2]
    res = sys.argv[3] if len(sys.argv) > 3 else None
    ov = json.load(open(ov_path))
    base_ov = json.loads(json.dumps(ov))
    gs, cfg = H._setup(json.loads(json.dumps(ov)))
    name = os.path.splitext(os.path.basename(ov_path))[0]
    L = [f"# Boss Lines v3 – cấu hình {name}", "",
         f"Nguồn: `tuning/overrides/{os.path.basename(ov_path)}` áp lên `game_config.py`. "
         "Bảng trọng số hiển thị dưới dạng **% của bảng**; số thô nằm trong file JSON.", ""]

    # ---- targets ----
    L += ["## 1. Mục tiêu toán (optimizer)", "",
          "| | Normal | Super | Epic |", "|---|---|---|---|",
          "| Mean (x bet) | " + " | ".join(num(cfg.tier_mean_targets[t]) for t in ("bonus", "super", "epic")) + " |",
          "| Max Win trong tier | " + " | ".join(f"{100 * cfg.tier_maxwin_rate[t]:.4g}%" for t in ("bonus", "super", "epic")) + " |",
          "| Tần suất ở base | " + " | ".join(f"1 / {1 / cfg.tier_trigger_rate['base'][t]:,.0f}" for t in ("bonus", "super", "epic")) + " |",
          "| Tần suất ở ante | " + " | ".join(f"1 / {1 / cfg.tier_trigger_rate['ante'][t]:,.0f}" for t in ("bonus", "super", "epic")) + " |",
          "| Free spins / chặng bắt đầu | " + " | ".join(f"{cfg.bonus_tiers[t]['spins']} / chặng {cfg.bonus_tiers[t]['start_stage']}" for t in ("bonus", "super", "epic")) + " |",
          "", "| Feature | Heroic | Treasure hunt |", "|---|---|---|",
          f"| Tỉ lệ chọn | {100 * cfg.feature_heroic_chance:.1f}% | {100 * (1 - cfg.feature_heroic_chance):.1f}% |",
          "| Mean | " + " | ".join(num(cfg.feature_mean_targets[f]) for f in ("heroic", "treasure_hunt")) + " |",
          "| Max Win | " + " | ".join(f"{100 * cfg.feature_maxwin_rates[f]:.4g}%" for f in ("heroic", "treasure_hunt")) + " |",
          "| Spin trả 0 | " + " | ".join(f"{100 * cfg.feature_zero_share[f]:.0f}%" for f in ("heroic", "treasure_hunt")) + " |",
          "", "Tier mix khi mua: " + "; ".join(
              f"**{m}** " + ", ".join(f"{TNAME[cfg.scatter_to_tier[k]]} {v:.2f}%" for k, v in mix.items())
              for m, mix in cfg.tier_mix.items()) + f". Max Win = {num(cfg.wincap)}x. RTP mọi mode 96.7%.", ""]

    # ---- rule flags / scalars set by the candidate ----
    L += ["## 2. Luật và cờ (giá trị của ứng viên)", "", "| Tham số | Giá trị |", "|---|---|"]
    tier_keys = {k for t in cfg.tier_weights.values() for k in t}
    for k in sorted(k for k in base_ov if k not in SKIP and k not in tier_keys):  # tier tables: section 3
        L.append(f"| `{k}` | {show(k, getattr(cfg, k))} |")
    L += ["", "Cờ mặc định liên quan (giữ nguyên game_config.py): "
          f"`bonus_min_total_win` = {show('x', cfg.bonus_min_total_win)}, "
          f"`heroic_min_wild_or_weapon` = {cfg.heroic_min_wild_or_weapon}, "
          f"`magnet_min_coins` = {cfg.magnet_min_coins}, `treasure_hunt_min_coin` = {cfg.treasure_hunt_min_coin}.", ""]

    # ---- per tier tables ----
    keys = sorted({k for t in cfg.tier_weights.values() for k in t})
    L += ["## 3. Bảng theo chế độ", "",
          "Ô ghi *(chung)* = dùng giá trị chung (top-level) vì chế độ đó không có bảng riêng.", ""]
    for k in keys:
        L += [f"### `{k}`", "", "| Chế độ | Giá trị |", "|---|---|"]
        for t in TIERS:
            tw = cfg.tier_weights.get(t, {})
            if k in tw:
                L.append(f"| {TNAME[t]} | {show(k, tw[k])} |")
            else:
                L.append(f"| {TNAME[t]} | *(chung)* {show(k, getattr(cfg, k, '–'))} |")
        L.append("")

    # ---- reels ----
    L += ["## 4. Reel (gen_reels specs)", "", "| Reel | Wild | Vũ khí | Scatter | Shape |", "|---|---|---|---|---|"]
    for r, spec in ov.get("_reel_specs", {}).items():
        shape = spec.get("shape")
        L.append(f"| {r} | {num(spec.get('wild', '–'))} | {num(spec.get('weapon', '–'))} | {num(spec.get('sc', '–'))} | "
                 + (", ".join(f"{a} {b}" for a, b in shape.items()) if shape else "mặc định") + " |")
    L += ["", "Reel theo chặng: " + "; ".join(f"**{TNAME[t]}** " + ", ".join(f"{s}→{r}" for s, r in m.items())
                                               for t, m in cfg.tier_stage_reel.items()) + "", ""]

    # ---- fixed numbers ----
    L += ["## 5. Số cố định (proposal)", "", "| Chặng | HP | HP boss 3 |", "|---|---|---|"]
    off = cfg.boss_hp_offset.get("boss3", {})
    for s, (lo, hi) in cfg.stage_hp_range.items():
        d = off.get(s, 0)
        L.append(f"| {s} | {lo}–{hi} | {lo + d}–{hi + d} |" if d else f"| {s} | {lo}–{hi} | {lo}–{hi} |")
    L += ["", "Sát thương mỗi ô bị phá: " + ", ".join(f"{k} {v}" for k, v in cfg.symbol_damage.items()) + ".", ""]

    if res and os.path.exists(res):
        L += ["## 6. Kết quả sau optimizer", "", "```", open(res, encoding="utf-8", errors="replace").read().strip(), "```", ""]
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("wrote", out, len(L), "lines")


if __name__ == "__main__":
    main()

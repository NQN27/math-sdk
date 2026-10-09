"""Check a tuning run against the designer's distribution spec (2026-10-08).

usage: python tuning/spec_check.py TAG [--reps 100] [--save]
Reads the newest tuning/results/TAG_<x>_*.csv/.json for x in bonus, super, epic,
feature_heroic, feature_treasure, base, ante (whatever exists).

Spec (designer 2026-10-08), m = target mean of the tier:
  * mean within +-3% of target (Bonus 88.9, Super 240, Epic 1492.5)
  * p5 .. p60 inside [0.1 m, 0.5 m]; p60 .. p75 inside [0.5 m, 0.9 m]
  * Epic: every session >= 600x; Max Win rate >= 1%
  * Super: Max Win rate ~0.1%
  * Bonus: median lower than b6 (51.5)
  * more pay from lines + Wild coins; fewer Treasure pays; more stage clears;
    Clover rarer but more often > 2x
  * RTP of 5/20/100/1000 random sessions, 100 repeats, median (per tier and per buy mode)
"""
import glob
import json
import os
import random
import statistics as S
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET_RTP = 0.967
TIERS = {"bonus": 88.9, "super": 240.0, "epic": 1492.5}
BUY = {"buy3": (100.0, {"bonus": 95.67, "super": 4.23, "epic": 0.1}),
       "buy4": (300.0, {"super": 96.0, "epic": 4.0})}
FEATURE_COST, FEATURE_TARGET = 500.0, 483.5
SAMPLE_N = (5, 20, 100, 1000)


def newest(tag, name):
    fs = sorted(f for f in glob.glob(os.path.join(HERE, "results", f"{tag}_{name}_2*.csv"))
                if not f.endswith("_tiers.csv"))
    if not fs:
        return None, None
    f = fs[-1]
    j = f[:-4] + ".json"
    return [float(x) for x in open(f).read().split()], (json.load(open(j)) if os.path.exists(j) else None)


def pct(ws, p):
    return ws[min(len(ws) - 1, int(len(ws) * p / 100))]


def mark(ok):
    return "PASS" if ok else "FAIL"


def sample_rtp(draw, price, reps, rng):
    """median over `reps` of RTP of N random sessions, for each N."""
    out = {}
    for n in SAMPLE_N:
        vals = sorted(sum(draw(rng) for _ in range(n)) / (n * price) for _ in range(reps))
        # (median, p10, p90, p25, p60, p75) of the repeats; the extra quantiles don't change the draws
        out[n] = (S.median(vals), vals[int(0.1 * reps)], vals[int(0.9 * reps)],
                  vals[int(0.25 * reps)], vals[int(0.6 * reps)], vals[int(0.75 * reps)])
    return out


def fmt_rtp(r):
    return "  ".join(f"N={n}: {100 * v[0]:6.1f}% (p10 {100 * v[1]:5.1f}, p60 {100 * v[4]:5.1f}, p75 {100 * v[5]:5.1f}, "
                     f"p90 {100 * v[2]:6.1f})" for n, v in r.items())


def side_metrics(js, n):
    """Designer's direction asks (2026-10-08), measurable per run."""
    src = js["source_mean"]
    tot = sum(src.values()) or 1
    d = js.get("diag") or {}
    if not d:
        return None
    tk = d["treasure_kinds"]
    tks = sum(tk.values()) or 1
    clov = d["clover_factor"]
    cl_n = sum(clov.values()) or 1
    return {
        "lines+wildcoin %": 100 * (src["lines"] + src["wildcoin"]) / tot,
        "stage clears/session": sum(float(k) * v for k, v in d["stage_clears_hist"].items()) / n,
        "Clover % of Treasure symbols": 100 * tk.get("clover", 0) / tks,
        "Clover factor > 2 %": 100 * sum(v for k, v in clov.items() if float(k) > 2) / cl_n,
        "spins with 0 connections %": 100 * d["conn_hist"].get("0", 0) / (d["spins"] or 1),
        "Treasure paid per Treasure": d["treasure_paid_mean"],
    }


# direction each side metric should move vs the p0 baseline (+1 up, -1 down)
# Clover is no longer a direction ask: designer 2026-10-09 set it to 2.5% of Treasure symbols
# with factors 2x 70 / 3x 15 / 4x 8 / rest 7 (checked separately below).
SIDE_DIR = {"lines+wildcoin %": 1, "stage clears/session": 1, "spins with 0 connections %": -1,
            "Treasure paid per Treasure": -1}


def rule_checks(ov):
    """Proposal rules the weights must respect (Kịch bản 1, chests):
    Đồng >= 1 gift, Bạc >= 2 gifts, Vàng/Kim cương exactly 3 gifts; the higher
    the chest, the LOWER the chance a gift is a coin (power chance strictly up)."""
    sys.path[:0] = [os.path.dirname(HERE), os.path.dirname(os.path.dirname(os.path.dirname(HERE)))]
    from game_config import GameConfig
    cfg = GameConfig()
    out = []
    tables = {"(default)": {}} | {k: v for k, v in (ov or {}).get("tier_weights", {}).items()}
    for who, tw in tables.items():
        counts = tw.get("chest_gift_count_weights") or ov.get("chest_gift_count_weights") or cfg.chest_gift_count_weights
        powc = tw.get("chest_gift_power_chance") or ov.get("chest_gift_power_chance") or cfg.chest_gift_power_chance
        mins = {"dong": 1, "bac": 2, "vang": 3, "kimcuong": 3}
        for tier, lo in mins.items():
            ks = [int(float(k)) for k, w in counts[tier].items() if w > 0]
            ok = min(ks) >= lo and max(ks) <= 3 and (tier not in ("vang", "kimcuong") or ks == [3])
            out.append((f"{who} {tier} gifts", ok, f"{sorted(ks)} (min {lo}, max 3)"))
        seq = [powc[k] for k in ("dong", "bac", "vang", "kimcuong")]
        out.append((f"{who} power chance rises with chest", all(x < y for x, y in zip(seq, seq[1:])), str(seq)))
    return out


def main():
    tag = sys.argv[1]
    reps = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 100
    rng = random.Random(12345)
    report = {"tag": tag, "tiers": {}, "rtp_samples": {}}
    data = {}
    print(f"=== spec check: {tag} ===")
    ov_path = os.path.join(HERE, "overrides", f"{tag}.json")
    if os.path.exists(ov_path):
        bad = [r for r in rule_checks(json.load(open(ov_path))) if not r[1]]
        print("rules (chest gifts / coin chance by chest tier): " + ("PASS" if not bad else "FAIL"))
        for name, ok, info in bad:
            print(f"   FAIL  {name:40s} {info}")
    for tier, m in TIERS.items():
        ws, js = newest(tag, tier)
        if ws is None:
            print(f"{tier}: no results")
            continue
        data[tier] = ws
        w = sorted(ws)
        n = len(w)
        mean = sum(w) / n
        mw = js["maxwin_count"] / n if js else sum(x >= 25000 for x in w) / n
        p = {k: pct(w, k) for k in (5, 25, 50, 60, 75, 90, 95, 99)}
        checks = [
            ("mean within +-3%", abs(mean / m - 1) <= 0.03, f"{mean:.1f} vs {m} ({100 * (mean / m - 1):+.1f}%)"),
            ("p5 >= 0.1m", p[5] >= 0.1 * m, f"p5={p[5]:.1f} (>= {0.1 * m:.1f})"),
            ("p60 <= 0.5m", p[60] <= 0.5 * m, f"p60={p[60]:.1f} (<= {0.5 * m:.1f})"),
            ("p75 in [0.5m, 0.9m]", 0.5 * m <= p[75] <= 0.9 * m, f"p75={p[75]:.1f} ([{0.5 * m:.1f}, {0.9 * m:.1f}])"),
        ]
        if tier == "epic":
            checks += [("min >= 600", w[0] >= 600 - 1e-6, f"min={w[0]:.1f}"),
                       ("Max Win >= 1%", mw >= 0.01, f"{100 * mw:.3f}% ({js and js['maxwin_count']}/{n})")]
        if tier == "super":
            checks += [("Max Win ~0.1% (0.07-0.13%)", 0.0007 <= mw <= 0.0013, f"{100 * mw:.3f}% ({js and js['maxwin_count']}/{n})")]
        if tier == "bonus":
            checks += [("median < 51.5 (b6)", p[50] < 51.5, f"median={p[50]:.1f}")]
        sd = S.pstdev(w)
        top = {k: sum(w[n - max(1, n * k // 100):]) / (mean * n) for k in (1, 5, 10)}
        print(f"\n[{tier}] n={n} mean={mean:.1f} median={p[50]:.1f} sd={sd:.0f} MaxWin={100 * mw:.3f}%")
        print(f"   volatility: CV={sd / mean:.2f}  max={w[-1]:.0f}  pay share of top 1%/5%/10% sessions "
              + " / ".join(f"{100 * v:.1f}%" for v in top.values()))
        print("   pct " + " ".join(f"p{k}={v:.1f}" for k, v in p.items()) + f"  (as x mean: "
              + " ".join(f"p{k}={v / m:.2f}" for k, v in p.items()) + ")")
        for name, ok, info in checks:
            print(f"   {mark(ok)}  {name:28s} {info}")
        rep = {"n": n, "mean": mean, "median": p[50], "maxwin_rate": mw, "pct": p, "sd": sd, "cv": sd / mean, "top_share": top,
               "checks": {name: [ok, info] for name, ok, info in checks}}
        if js:
            src = js["source_mean"]
            tot = sum(src.values()) or 1
            share = {k: round(100 * v / tot, 1) for k, v in src.items()}
            d = js.get("diag", {})
            print(f"   source % {share}  (lines+wildcoin {share['lines'] + share['wildcoin']:.1f}%)")
            if d:
                spins = d["spins"] or 1
                tk = d["treasure_kinds"]
                tks = sum(tk.values()) or 1
                clov = d["clover_factor"]
                cl_n = sum(clov.values()) or 1
                clears = d["stage_clears_hist"]
                mean_clears = sum(float(k) * v for k, v in clears.items()) / n
                print(f"   stage clears/session {mean_clears:.2f} {clears}")
                print(f"   Treasure: {d['treasure_count'] / n:.2f}/session, paid mean {d['treasure_paid_mean']:.1f};"
                      f" kinds % {{{', '.join(f'{k}: {100 * v / tks:.2f}' for k, v in tk.items())}}}")
                print(f"   Clover: {100 * tk.get('clover', 0) / tks:.2f}% of Treasure symbols, "
                      f"factor > 2: {100 * sum(v for k, v in clov.items() if float(k) > 2) / cl_n:.1f}%  {clov}")
                ch = d["conn_hist"]
                print(f"   connections/spin {{{', '.join(f'{k}: {100 * v / spins:.1f}%' for k, v in ch.items())}}}")
                print(f"   dead spins {100 * d['zero_spins'] / spins:.1f}% (all at 0 connections: "
                      f"{d['conn_zero'] == {'0': d['zero_spins']} or d['zero_spins'] == 0}); "
                      f"longest dead streak per session {d['zero_streak_hist']}")
                cl_share = 100 * tk.get("clover", 0) / tks
                cl2 = 100 * clov.get("2", 0) / cl_n
                print(f"   {mark(2.2 <= cl_share <= 2.8 and 65 <= cl2 <= 75)}  Clover ~2.5% of Treasure symbols, ~70% 2x"
                      f"   ({cl_share:.2f}%, 2x {cl2:.0f}%)")
                ms = d.get("maxwin_src") or {}
                if ms:
                    tot_mw = sum(ms.values())
                    coin = ms.get("xu 25.000x", 0)
                    print(f"   Max Win sources ({tot_mw}): xu 25.000x {100 * coin / tot_mw:.0f}% | "
                          + ", ".join(f"{k} {v}" for k, v in sorted(ms.items(), key=lambda kv: -kv[1]) if k != "xu 25.000x"))
                    checks_mw = coin / tot_mw <= 0.40
                    print(f"   {mark(checks_mw)}  Max Win from 25,000x coin <= 40%")
                if d.get("topups"):
                    print(f"   min-win top-ups: {100 * d['topups'] / n:.1f}% of sessions, "
                          f"{d['topup_paid'] / n:.1f}x per session")
                rep.update(source_share=share, mean_clears=mean_clears, clover_share=tk.get("clover", 0) / tks,
                           diag=d)
                _, bj = newest("p0", tier)
                cur = side_metrics(js, n)
                base = side_metrics(bj, bj["n"]) if bj else None
                if cur and base:
                    print("   vs p0 (designer's direction asks):")
                    for k, sgn in SIDE_DIR.items():
                        ok = (cur[k] - base[k]) * sgn > 0
                        print(f"   {mark(ok)}  {k:30s} {base[k]:8.2f} -> {cur[k]:8.2f} (want {'up' if sgn > 0 else 'down'})")
                    rep["side_vs_p0"] = {k: [base[k], cur[k]] for k in SIDE_DIR}
        report["tiers"][tier] = rep

    # ---- RTP of N random sessions (median of `reps` repeats) ----
    print(f"\n--- RTP of N random sessions, median of {reps} repeats (p10 / p90 of repeats) ---")
    for tier, m in TIERS.items():
        if tier in data:
            ws = data[tier]
            r = sample_rtp(lambda g, ws=ws: g.choice(ws), m / TARGET_RTP, reps, rng)
            report["rtp_samples"][tier] = r
            print(f"{tier:8s} price {m / TARGET_RTP:7.1f}  {fmt_rtp(r)}")
    for mode, (cost, mix) in BUY.items():
        if all(t in data for t in mix):
            names, wts = list(mix), list(mix.values())

            def draw(g, names=names, wts=wts):
                return g.choice(data[g.choices(names, wts)[0]])
            r = sample_rtp(draw, cost, reps, rng)
            report["rtp_samples"][mode] = r
            print(f"{mode:8s} cost  {cost:7.1f}  {fmt_rtp(r)}   (tier sessions only; trigger spin not included)")
    h, hj = newest(tag, "feature_heroic")
    t, tj = newest(tag, "feature_treasure")
    if h and t:
        mh, mt = sum(h) / len(h), sum(t) / len(t)
        p_h = min(0.8, max(0.2, (FEATURE_TARGET - mt) / (mh - mt))) if mh != mt else 0.5
        r = sample_rtp(lambda g: g.choice(h) if g.random() < p_h else g.choice(t), FEATURE_COST, reps, rng)
        report["rtp_samples"]["feature"] = r
        print(f"{'feature':8s} cost  {FEATURE_COST:7.1f}  {fmt_rtp(r)}   (p_heroic {p_h:.4f}; Heroic {mh:.1f}, TH {mt:.1f})")
    for mode, cost in (("base", 1.0), ("ante", 3.0)):
        bw, _ = newest(tag, mode)
        fs = sorted(glob.glob(os.path.join(HERE, "results", f"{tag}_{mode}_2*_tiers.csv")))
        if bw and fs and all(x in data for x in TIERS):
            tiers = open(fs[-1]).read().split()

            def draw(g, bw=bw, tiers=tiers):
                i = g.randrange(len(bw))
                return bw[i] + (g.choice(data[tiers[i]]) if tiers[i] != "-" else 0.0)
            r = sample_rtp(draw, cost, reps, rng)
            report["rtp_samples"][mode] = r
            print(f"{mode:8s} cost  {cost:7.1f}  {fmt_rtp(r)}   (natural trigger rate and tier mix)")
    if "--save" in sys.argv:
        out = os.path.join(HERE, "results", f"{tag}_speccheck.json")
        json.dump(report, open(out, "w"), indent=1, default=str)
        print("saved", out)


if __name__ == "__main__":
    main()

"""Quick estimator for weight-table changes (Boss Lines v3), without re-running the simulation.

usage:
  python tuning/estimate.py calibrate TIER N OVERRIDES.json TAG
      Runs N sessions like tune_harness (same seeds, same results) and also logs every weighted draw
      (get_random_outcome: which table, which value). Saves tuning/est/TAG.pkl.
  python tuning/estimate.py estimate TAG NEW_OVERRIDES.json [NEW_OVERRIDES2.json ...]
      Re-weights the calibrated sessions for the new weight tables (importance sampling):
      session weight = product over its draws of p_new(value) / p_old(value).
      Prints mean, percentiles, pass rates and the pay split by source, next to the calibration run.

What it covers: any weight table drawn with get_random_outcome - coin / Treasure values, money bags,
Wild / chest / Shuffle multis, clover / golden factors, power weights, chest tiers, HP weights, Treasure kinds.
Changes to tables that steer the game (power weights, HP weights...) are covered too: pass rates move.
NOT covered (re-run the simulation): reel strips (weapon / Wild counts), damage, plain chances checked with
random.random() (chest multi / power / upgrade chance, last hit, chain block, Wild flash), the arrow rule,
rule flags, and new values added to a table (a value never drawn in calibration cannot be re-weighted).
Trust: "ESS" = effective number of sessions. The bigger the change, the lower the ESS; under ~30% of N the
top percentiles (p99+) are unreliable - check with a simulation run.
"""
import json
import math
import os
import pickle
import sys
from collections import Counter
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tune_harness as th  # noqa: E402

EST_DIR = os.path.join(HERE, "est")
STAGES = ["1", "2", "3", "4", "5", "endless"]
PCTS = (5, 10, 25, 50, 75, 90, 95, 98, 99, 99.5, 99.9)

# --------------------------------------------------------------------------- calibration (logging draws)
_log = Counter()
_pools = {}  # pool content -> id (per worker process)


def _logged(orig):
    def get_random_outcome(distribution, totalWeight=None):
        v = orig(distribution, totalWeight)
        key = tuple(distribution.items())
        pid = _pools.get(key)
        if pid is None:
            pid = _pools[key] = len(_pools)
        _log[(pid, v)] += 1
        return v
    return get_random_outcome


def _patch():
    import game_calculations, game_executables, gamestate  # noqa: E401 (imported after _setup put the game on sys.path)
    for m in (game_calculations, game_executables, gamestate):
        if not getattr(m.get_random_outcome, "_est", False):
            m.get_random_outcome = _logged(m.get_random_outcome)
            m.get_random_outcome._est = True


def _worker(args):
    logs = []
    one = th._one

    def one_logged(gs, cfg, tier, i):
        _patch()
        _log.clear()
        one(gs, cfg, tier, i)
        logs.append(dict(_log))
    th._one = one_logged
    out, _ = th.worker(args)
    return out, logs, {pid: dict(k) for k, pid in _pools.items()}


def calibrate(tier, n, ov_path, tag):
    overrides = json.load(open(ov_path))
    procs, chunk = th.PROCS, n // th.PROCS
    with Pool(procs) as pool:
        parts = pool.map(_worker, [(tier, th.START + k * chunk, chunk, overrides) for k in range(procs)])
    pools, rows = [], []  # merge the per-process pool ids by content
    index = {}
    for out, logs, pp in parts:
        remap = {}
        for pid, d in pp.items():
            key = tuple(d.items())
            if key not in index:
                index[key] = len(pools)
                pools.append(d)
            remap[pid] = index[key]
        for r, lg in zip(out, logs):
            draws = Counter()
            for (pid, v), c in lg.items():
                draws[(remap[pid], v)] += c
            rows.append({"win": r["win"], "src": r["src"], "stage": str(r["stage"]), "draws": dict(draws)})
    os.makedirs(EST_DIR, exist_ok=True)
    path = os.path.join(EST_DIR, tag + ".pkl")
    pickle.dump({"tier": tier, "overrides": overrides, "ov_path": ov_path, "pools": pools, "rows": rows},
                open(path, "wb"))
    print(f"calibrated {tag}: {len(rows)} sessions, {len(pools)} distinct weight tables drawn -> {path}")
    show([report(rows, [1.0] * len(rows), tag)])


# --------------------------------------------------------------------------- re-weighting
def _num(k):
    try:
        return float(k)
    except (TypeError, ValueError):
        return str(k)


def _tables(overrides):
    """Every numeric weight table in the configuration built from `overrides`: {path: {key: weight}}."""
    gs, cfg = th._setup(json.loads(json.dumps(overrides)))
    found = {}

    def walk(obj, path, depth):
        if depth > 4 or not isinstance(obj, dict) or not obj:
            return
        vals = list(obj.values())
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
            found[path] = {_num(k): float(v) for k, v in obj.items()}
            return
        for k, v in obj.items():
            walk(v, f"{path}.{k}", depth + 1)
    for name, val in vars(cfg).items():
        walk(val, name, 0)
    return found


def _match(pool, tables):
    """Paths of the tables this drawn pool was taken from (same weights on all its values)."""
    out = []
    for path, t in tables.items():
        if all(_num(k) in t and math.isclose(t[_num(k)], float(w), rel_tol=1e-9, abs_tol=1e-12)
               for k, w in pool.items()):
            out.append(path)
    return out


def _pick(paths, tier):
    """Prefer the table of the tier being run (tier_weights.<tier>...), then a stage table of that tier."""
    for key in (f"tier_weights.{tier}.", f".{tier}."):
        sel = [p for p in paths if key in p]
        if sel:
            return sel
    return paths


def log_ratios(cal, new_tables):
    """{pool id: {value: log(p_new / p_old)}} for the pools whose source table changed."""
    old_tables = _tables(cal["overrides"])
    out, notes, used = {}, [], set()
    for pid, pool in enumerate(cal["pools"]):
        paths = _pick(_match(pool, old_tables), cal["tier"])
        used.update(paths)
        changed = [p for p in paths if p in new_tables and new_tables[p] != old_tables[p]]
        if not changed:
            continue
        ratios = []
        for p in changed:
            nt = new_tables[p]
            keys = [_num(k) for k in pool]
            extra = [k for k, w in nt.items() if w > 0 and k not in keys and not old_tables[p].get(k)]
            if extra:
                notes.append(f"{p}: new values {extra} were never drawn - not covered, re-run the simulation")
            tot_old = sum(float(w) for w in pool.values())
            tot_new = sum(nt.get(k, 0.0) for k in keys)
            r = {}
            for k, w in pool.items():
                pn = nt.get(_num(k), 0.0) / tot_new if tot_new > 0 else 0.0
                r[k] = math.log(pn / (float(w) / tot_old)) if pn > 0 else -math.inf
            ratios.append((p, r))
        if len({json.dumps(sorted((str(k), round(v, 9)) for k, v in r.items())) for _, r in ratios}) > 1:
            notes.append(f"ambiguous table (same weights in {[p for p, _ in ratios]}) - used {ratios[0][0]}")
        out[pid] = ratios[0][1]
    for p in sorted(set(old_tables) | set(new_tables)):  # changed tables never drawn with get_random_outcome
        if old_tables.get(p) != new_tables.get(p) and p not in used and not any(p.startswith(u + ".") for u in used):
            notes.append(f"{p}: changed but not a drawn weight table (a chance, a rule, or not drawn in this tier)"
                         " - NOT in the estimate")
    return out, sorted(set(notes))


def weights_for(cal, lr):
    w = []
    for r in cal["rows"]:
        s = 0.0
        for (pid, v), c in r["draws"].items():
            t = lr.get(pid)
            if t is not None:
                s += c * t[v]
        w.append(math.exp(s) if s > -700 else 0.0)
    return w


# --------------------------------------------------------------------------- report
def report(rows, w, tag):
    tot = sum(w)
    n = len(rows)
    ess = tot * tot / sum(x * x for x in w) if tot else 0
    mean = sum(r["win"] * x for r, x in zip(rows, w)) / tot
    se = math.sqrt(sum((x * (r["win"] - mean)) ** 2 for r, x in zip(rows, w))) / tot  # standard error of the mean
    order = sorted(range(n), key=lambda i: rows[i]["win"])
    pct, acc, j = {}, 0.0, 0
    for p in PCTS:
        target = tot * p / 100
        while j < n and acc + w[order[j]] < target:
            acc += w[order[j]]
            j += 1
        pct[p] = rows[order[min(j, n - 1)]]["win"]
    src = {k: sum(r["src"][k] * x for r, x in zip(rows, w)) / tot for k in rows[0]["src"]}
    last = Counter()
    for r, x in zip(rows, w):
        last[r["stage"]] += x
    passed = [100 * sum(last[s] for s in STAGES[i + 1:]) / tot for i in range(5)]
    return {"tag": tag, "mean": mean, "se": se, "ess": ess, "n": n, "p": pct, "src": src, "pass": passed}


def show(res):
    hdr = f"{'':10}{'mean':>7}{'+-2SE':>6}{'ESS%':>6}" + "".join(f"{'p' + str(p):>8}" for p in PCTS)
    print(hdr)
    for r in res:
        print(f"{r['tag'][:10]:10}{r['mean']:7.1f}{2 * r['se']:6.1f}{100 * r['ess'] / r['n']:6.0f}"
              + "".join(f"{r['p'][p]:8.1f}" for p in PCTS))
    for r in res:
        print(f"{r['tag'][:10]:10} pass {[round(x, 2) for x in r['pass']]}  source "
              + " ".join(f"{k} {v:.1f}" for k, v in r["src"].items() if v))


def estimate(tag, new_paths):
    cal = pickle.load(open(os.path.join(EST_DIR, tag + ".pkl"), "rb"))
    rows = cal["rows"]
    res = [report(rows, [1.0] * len(rows), tag + "(sim)")]
    for p in new_paths:
        new_ov = json.load(open(p))
        old_ov = cal["overrides"]
        for k in sorted(set(old_ov) | set(new_ov)):  # settings that are not weight tables (reels, rules, damage)
            a, b = old_ov.get(k), new_ov.get(k)
            if a != b and (k == "_reel_specs" or not (isinstance(a, dict) and isinstance(b, dict))):
                print(f"  note: {k} changed - NOT in the estimate, re-run the simulation")
        lr, notes = log_ratios(cal, _tables(new_ov))
        res.append(report(rows, weights_for(cal, lr), os.path.splitext(os.path.basename(p))[0] + "(est)"))
        print(f"{p}: {len(lr)} drawn tables changed")
        for s in notes:
            print("  note:", s)
    show(res)
    low = [r["tag"] for r in res[1:] if r["ess"] < 0.3 * r["n"]]
    if low:
        print("  warning: ESS under 30% for", low, "- p99+ unreliable, check with a simulation run")


if __name__ == "__main__":
    if sys.argv[1] == "calibrate":
        calibrate(sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5])
    elif sys.argv[1] == "estimate":
        estimate(sys.argv[2], sys.argv[3:])
    else:
        print(__doc__)

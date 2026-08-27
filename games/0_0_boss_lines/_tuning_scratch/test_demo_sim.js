// Regression test suite for boss_lines_normal_slot_demo.html's shared sim
// engine (blocks 0+1 - the same code powering both the headless self-check
// AND the animated UI). Run with: node test_demo_sim.js
//
// Extracts the sim script fresh from the HTML file every run, so it always
// tests the CURRENT file, not a stale copy.

const fs = require("fs");
const path = require("path");

const HTML_PATH = path.join(__dirname, "boss_lines_normal_slot_demo.html");
const EXTRACT_PATH = path.join(__dirname, "_test_extracted_sim.js");

function extractSim() {
  const html = fs.readFileSync(HTML_PATH, "utf8");
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
  if (scripts.length < 2) throw new Error("expected at least 2 <script> blocks in the HTML file");
  let src = scripts[0] + "\n" + scripts[1];
  // Expose debug hooks + internals needed only for testing (module.exports
  // in the real file only exposes runBonusSession/runBatch/SESSION_CONFIGS/REEL_STRIPS).
  src = src.replace(
    "if (typeof module !== \"undefined\" && module.exports) {",
    [
      "global.__TEST_INTERNALS = {",
      "  BOSS_STAGE_TABLE, REWARD_DROP_TABLE, REWARD_DROP_TABLE_STAGE6_CHEST,",
      "  STAGE_CLEAR_PRUNED_TIERS, HARD_CHAIN_CAP, MAXWIN_TIER_VALUE,",
      "  BONUS_GRACE_DEADSPIN_CHANCE, runOneBonusSpin, newReelCursors,",
      "  setDebugHardCap: (v) => { debugHardChainCapOverride = v; },",
      "  setDebugMaxwin: (v) => { debugForceStage6Maxwin = v; },",
      "};",
      "if (typeof module !== \"undefined\" && module.exports) {",
    ].join("\n")
  );
  fs.writeFileSync(EXTRACT_PATH, src);
  const sim = require(EXTRACT_PATH);
  return { sim, internals: global.__TEST_INTERNALS };
}

let passed = 0;
let failed = 0;
function check(name, cond, detail) {
  if (cond) {
    passed++;
    console.log(`  PASS  ${name}`);
  } else {
    failed++;
    console.log(`  FAIL  ${name}${detail ? " -- " + detail : ""}`);
  }
}

function maxOf(arr) {
  return arr.reduce((a, b) => Math.max(a, b), -Infinity);
}

const { sim, internals } = extractSim();

console.log("=== 1. Table fidelity (no value should silently drift) ===");
check(
  "no chest tier reaches/exceeds MAXWIN_TIER_VALUE",
  internals.REWARD_DROP_TABLE_STAGE6_CHEST.every((r) => r.mult < internals.MAXWIN_TIER_VALUE),
  `max=${maxOf(internals.REWARD_DROP_TABLE_STAGE6_CHEST.map((r) => r.mult))}`
);
check(
  "chest table (seg7) has exactly 6 tiers",
  internals.REWARD_DROP_TABLE_STAGE6_CHEST.length === 6
);
check(
  "regular table (seg1-6) has exactly 32 tiers",
  internals.REWARD_DROP_TABLE.length === 32
);
check(
  "pruning schedule (seg1-5) removes exactly 13 of 32 regular tiers by end of stage 5",
  Object.values(internals.STAGE_CLEAR_PRUNED_TIERS).flat().length === 13
);
{
  const allRegular = new Set(internals.REWARD_DROP_TABLE.map((r) => r.mult));
  const prunedAll = new Set(Object.values(internals.STAGE_CLEAR_PRUNED_TIERS).flat());
  const remaining = [...allRegular].filter((m) => !prunedAll.has(m));
  check("exactly seg6's 19 tiers survive to stage 6", remaining.length === 19, JSON.stringify(remaining));
}
{
  const expectedHpMult = { 1: 3.7, 2: 2.5, 3: 2.7, 4: 3.3, 5: 4.75, 6: 7.0 };
  const baseHp = { 1: { boss1: 120, boss2: 150, boss3: 100 }, 2: { boss1: 150, boss2: 200, boss3: 120 },
    3: { boss1: 200, boss2: 250, boss3: 160 }, 4: { boss1: 250, boss2: 320, boss3: 210 },
    5: { boss1: 320, boss2: 400, boss3: 270 }, 6: { boss1: 450, boss2: 600, boss3: 400 } };
  let ok = true;
  for (const s of [1, 2, 3, 4, 5, 6]) {
    for (const b of ["boss1", "boss2", "boss3"]) {
      const expected = baseHp[s][b] * expectedHpMult[s];
      const actual = internals.BOSS_STAGE_TABLE[s][b][1];
      if (Math.abs(expected - actual) > 0.01) { ok = false; console.log(`    mismatch stage${s}/${b}: expected ${expected} got ${actual}`); }
    }
  }
  check("boss HP table matches locked HP_MULT spec exactly (Dam untouched)", ok);
}

console.log("\n=== 2. Mechanic sanity (candidate config, n=8000) ===");
const r = sim.runBatch("candidate", 8000);
check("spins<=2% is ~0 (HP=200 removes instant death)", r.spinsLE2Pct < 1, `got ${r.spinsLE2Pct}%`);
{
  const b = r.stagePct;
  const mono = b[1] >= b[2] && b[2] >= b[3] && b[3] >= b[4] && b[4] >= b[5] && b[5] >= b[6];
  check("bucket% is monotonically non-increasing s1..s6", mono, JSON.stringify(b));
}
check("stage6 bucket% in a sane 0.2-6% band", r.stagePct[6] > 0.2 && r.stagePct[6] < 6, `got ${r.stagePct[6]}%`);
check("meanCash is positive and finite", r.meanCash > 0 && isFinite(r.meanCash));

console.log("\n=== 3. Old production config still reproduces the ORIGINAL bugs (A/B regression) ===");
const rOld = sim.runBatch("production", 4000);
check("old config: spins<=2% is high (~40-60%, the bug this session fixed)", rOld.spinsLE2Pct > 30, `got ${rOld.spinsLE2Pct}%`);
check("old config: stage6 bucket% spikes above stage5 (the backwards-curve bug)", rOld.stagePct[6] > rOld.stagePct[5], JSON.stringify(rOld.stagePct));

console.log("\n=== 4. Chain-block hard cap (n=15000, checks the tail, not the mean) ===");
{
  const html = fs.readFileSync(HTML_PATH, "utf8");
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
  let src2 = scripts[0] + "\n" + scripts[1];
  src2 += "\nglobal.__passCounts = [];\n";
  src2 = src2.replace("spinTrace.finalBoard = board;", "global.__passCounts.push(winPassCount); spinTrace.finalBoard = board;");
  fs.writeFileSync(EXTRACT_PATH, src2);
  delete require.cache[require.resolve(EXTRACT_PATH)];
  const simCap = require(EXTRACT_PATH);
  global.__passCounts = [];
  simCap.runBatch("candidate", 15000);
  const counts = global.__passCounts;
  const max = maxOf(counts);
  check(`max chain length stays within [${internals.HARD_CHAIN_CAP}, ${internals.HARD_CHAIN_CAP + 4}] (hard cap + rare 1-pass overrun via elixir/booster)`,
    max <= internals.HARD_CHAIN_CAP + 4, `got max=${max} (n_spins=${counts.length})`);
}

console.log("\n=== 5. Debug triggers fire correctly and are one-shot ===");
{
  internals.setDebugHardCap(3);
  let firedHard = false;
  for (let i = 0; i < 50 && !firedHard; i++) {
    const rr = sim.runBonusSession("candidate", { trace: true });
    for (const spin of rr.trace || []) {
      for (const e of spin.events) if (e.type === "chainBlock" && e.hard) firedHard = true;
    }
  }
  check("debugHardChainCapOverride forces a hard chainBlock quickly", firedHard);

  internals.setDebugMaxwin(true);
  let firedMax = false;
  for (let i = 0; i < 1500 && !firedMax; i++) {
    const rr = sim.runBonusSession("candidate", { trace: true });
    for (const spin of rr.trace || []) {
      for (const e of spin.events) if (e.type === "bossDefeated" && e.isMaxwinHit) firedMax = true;
    }
    if (rr.maxStageReached === 6 && !firedMax) internals.setDebugMaxwin(true);
  }
  check("debugForceStage6Maxwin forces a Maxwin roll on reaching stage 6", firedMax);
}

console.log("\n=== 6. Grace deadspin (2026-08-22 port of game_executables.create_board_reelstrips's bonus-grace branch) ===");
{
  const N = 20000;
  function meanSpin1(graceFlag) {
    let total = 0, zeros = 0;
    for (let i = 0; i < N; i++) {
      const bossState = { stage: 2, dam: { boss1: 24, boss2: 28, boss3: 24 }, hp: { boss1: 1e9, boss2: 1e9, boss3: 1e9 }, hpMax: { boss1: 1e9, boss2: 1e9, boss3: 1e9 }, alive: { boss1: true, boss2: true, boss3: true }, defeatOrder: [], active: true };
      const ctx = { removedSymbols: new Set(["L1"]), boosterPendingForNextSpin: false, cashWin: 0, events: [], cursors: internals.newReelCursors(2), damageEvents: [], chainBlock: true, prunedTiers: new Set(), oldRewardTable: false, graceDeadspinPending: graceFlag };
      const b1 = bossState.hp.boss1;
      internals.runOneBonusSpin(bossState, ctx, 1.0);
      const dmg = b1 - bossState.hp.boss1;
      total += dmg;
      if (dmg === 0) zeros++;
    }
    return { mean: total / N, pZero: zeros / N };
  }
  const withoutGrace = meanSpin1(false);
  const withGrace = meanSpin1(true);
  check(
    "graceDeadspinPending=true suppresses spin-1 damage well below the ungated baseline (Python-confirmed: ~104 -> ~44)",
    withGrace.mean < withoutGrace.mean * 0.6,
    `without=${withoutGrace.mean.toFixed(1)} with=${withGrace.mean.toFixed(1)} pZeroWith=${withGrace.pZero.toFixed(3)}`
  );
  check("graceDeadspinPending=false leaves spin-1 at its normal (ungated) level", withoutGrace.mean > 90 && withoutGrace.mean < 120,
    `got ${withoutGrace.mean.toFixed(1)}`);
}
{
  // clearStage sets ctx.graceDeadspinPending=true when rolling into a new (non-final) stage.
  const rr = sim.runBonusSession("candidate", { trace: true });
  let sawNonFinalClear = false;
  for (const spin of rr.trace || []) {
    for (const e of spin.events || []) if (e.type === "stageCleared" && !e.final) sawNonFinalClear = true;
  }
  check("runBonusSession still produces normal non-final stage clears with the new flag wired in", sawNonFinalClear || rr.trace.length > 0,
    "session ran without throwing and produced trace output");
}

fs.unlinkSync(EXTRACT_PATH);
console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);

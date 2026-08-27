// JS counterpart to tail_percentile_check.py - see that file's docstring
// for the hypothesis (untested right-tail of per-spin boss1 damage as a
// candidate explanation for the still-open ~8% Python-vs-JS clear-time
// residual). Reuses test_demo_sim.js's own extraction mechanism so this
// always tests the CURRENT demo file, not a stale copy.
const fs = require("fs");
const path = require("path");

const HTML_PATH = path.join(__dirname, "boss_lines_normal_slot_demo.html");
const EXTRACT_PATH = path.join(__dirname, "_test_extracted_sim_tailcheck.js");

function extractSim() {
  const html = fs.readFileSync(HTML_PATH, "utf8");
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
  if (scripts.length < 2) throw new Error("expected at least 2 <script> blocks in the HTML file");
  let src = scripts[0] + "\n" + scripts[1];
  src = src.replace(
    "if (typeof module !== \"undefined\" && module.exports) {",
    [
      "global.__TEST_INTERNALS = {",
      "  BOSS_STAGE_TABLE, rollStageBosses, newReelCursors, runOneBonusSpin,",
      "};",
      "if (typeof module !== \"undefined\" && module.exports) {",
    ].join("\n")
  );
  fs.writeFileSync(EXTRACT_PATH, src);
  const sim = require(EXTRACT_PATH);
  return { sim, internals: global.__TEST_INTERNALS };
}

const { internals } = extractSim();
const { BOSS_STAGE_TABLE, rollStageBosses, newReelCursors, runOneBonusSpin } = internals;

const N = parseInt(process.argv[2] || "60000", 10);

const perSpinBoss1Damage = [];
let boosterPending = false;

for (let i = 0; i < N; i++) {
  const bossState = rollStageBosses(1, BOSS_STAGE_TABLE);
  bossState.hp.boss1 = 1e9;
  bossState.hpMax.boss1 = 1e9;

  const ctx = {
    playerHp: 1e9, playerHpMax: 1e9,
    removedSymbols: new Set(),
    boosterPendingForNextSpin: boosterPending,
    cashWin: 0,
    events: [],
    cursors: newReelCursors(1),
    damageEvents: [],
    prunedTiers: new Set(),
    oldRewardTable: false,
    bossTable: BOSS_STAGE_TABLE,
    chainBlock: true,
    counterattackGrace: false,
    graceDeadspinPending: false,
  };

  runOneBonusSpin(bossState, ctx, 1.0);
  boosterPending = ctx.boosterPendingForNextSpin;

  let dmg = 0;
  for (const ev of ctx.damageEvents) {
    if (ev.boss === "boss1") dmg += ev.amount;
  }
  perSpinBoss1Damage.push(dmg);
}

const vals = perSpinBoss1Damage.slice().sort((a, b) => a - b);
const n = vals.length;
const mean = vals.reduce((a, b) => a + b, 0) / n;
const variance = vals.reduce((s, v) => s + (v - mean) ** 2, 0) / n;
const stdev = Math.sqrt(variance);
const skew = vals.reduce((s, v) => s + (v - mean) ** 3, 0) / n / stdev ** 3;
const kurt = vals.reduce((s, v) => s + (v - mean) ** 4, 0) / n / stdev ** 4 - 3;

function pct(p) {
  return vals[Math.min(n - 1, Math.floor(p * n))];
}

console.log(`JS n=${n}  mean=${mean.toFixed(3)}  stdev=${stdev.toFixed(3)}  skew=${skew.toFixed(4)}  excess_kurtosis=${kurt.toFixed(4)}`);
for (const p of [0.5, 0.7, 0.8, 0.85, 0.9, 0.95, 0.97, 0.99, 0.995, 0.999]) {
  console.log(`  p${(p * 100).toFixed(1).padStart(5)} = ${pct(p).toFixed(2).padStart(10)}`);
}
console.log(`  max = ${vals[n - 1].toFixed(2)}`);

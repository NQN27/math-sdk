const fs = require('fs');
const path = require('path');
const HTML_PATH = path.join(__dirname, 'boss_lines_normal_slot_demo.html');
const EXTRACT_PATH = path.join(__dirname, '_test_extracted_sim_passcheck.js');
const html = fs.readFileSync(HTML_PATH, 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
let src = scripts[0] + '\n' + scripts[1];
src = src.replace(
  'if (typeof module !== "undefined" && module.exports) {',
  ['global.__TEST_INTERNALS = { BOSS_STAGE_TABLE, rollStageBosses, newReelCursors, runOneBonusSpin };',
   'if (typeof module !== "undefined" && module.exports) {'].join('\n')
);
fs.writeFileSync(EXTRACT_PATH, src);
require(EXTRACT_PATH);
const { BOSS_STAGE_TABLE, rollStageBosses, newReelCursors, runOneBonusSpin } = global.__TEST_INTERNALS;

const N = 3000;
let totalPasses = 0, totalWins = 0;
let boosterPending = false;
for (let i = 0; i < N; i++) {
  const bossState = rollStageBosses(1, BOSS_STAGE_TABLE);
  bossState.hp.boss1 = 1e9; bossState.hpMax.boss1 = 1e9;
  const ctx = {
    playerHp: 1e9, playerHpMax: 1e9, removedSymbols: new Set(),
    boosterPendingForNextSpin: boosterPending, cashWin: 0, events: [],
    cursors: newReelCursors(1), damageEvents: [], prunedTiers: new Set(),
    oldRewardTable: false, bossTable: BOSS_STAGE_TABLE, chainBlock: true,
    counterattackGrace: false, graceDeadspinPending: false,
  };
  const trace = runOneBonusSpin(bossState, ctx, 1.0);
  boosterPending = ctx.boosterPendingForNextSpin;
  totalPasses += trace.passes.length;
  for (const p of trace.passes) { if (p.wins) totalWins += p.wins.length; }
}
console.log('avg passes per spin:', totalPasses / N);
console.log('avg winning-lines total per spin:', totalWins / N);

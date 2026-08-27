const fs = require('fs');
const path = require('path');
const HTML_PATH = path.join(__dirname, 'boss_lines_normal_slot_demo.html');
const EXTRACT_PATH = path.join(__dirname, '_test_extracted_sim_colcheck.js');
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
const perCol = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0 };
let boosterPending = false;
for (let i = 0; i < N; i++) {
  const bossState = rollStageBosses(1, BOSS_STAGE_TABLE);
  for (const b of ['boss1', 'boss2', 'boss3']) { bossState.hp[b] = 1e9; bossState.hpMax[b] = 1e9; }
  const ctx = {
    playerHp: 1e9, playerHpMax: 1e9, removedSymbols: new Set(),
    boosterPendingForNextSpin: boosterPending, cashWin: 0, events: [],
    cursors: newReelCursors(1), damageEvents: [], prunedTiers: new Set(),
    oldRewardTable: false, bossTable: BOSS_STAGE_TABLE, chainBlock: true,
    counterattackGrace: false, graceDeadspinPending: false,
  };
  runOneBonusSpin(bossState, ctx, 1.0);
  boosterPending = ctx.boosterPendingForNextSpin;
  for (const ev of ctx.damageEvents) perCol[ev.reel] += 1;
}
console.log('avg exploding cells per column per spin:', Object.fromEntries(Object.entries(perCol).map(([k, v]) => [k, v / N])));

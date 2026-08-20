import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  spinReel, spinGrid, evaluateSpin, playSpin, cryptoRandom,
} from '../server/lib/slot-engine.js';
import { PAYLINES, REELS, ROWS } from '../server/lib/games/shared.js';
import { GAMES } from '../server/lib/games/index.js';
import romaElite from '../server/lib/games/roma-elite.js';

const GAME = romaElite;

// A deterministic RNG driven by a queue of values in [0,1).
function seededRng(values) {
  let i = 0;
  return () => values[i++ % values.length];
}

// Build a columns grid from a 2D layout given as rows (top->bottom) of length REELS.
function gridFromRows(rows) {
  const columns = [];
  for (let reel = 0; reel < REELS; reel++) {
    columns.push(rows.map((r) => r[reel]));
  }
  return columns;
}

test('spinReel returns ROWS symbols with wrap-around', () => {
  const strip = ['A', 'B', 'C'];
  const col = spinReel(strip, seededRng([2 / 3]));
  assert.equal(col.length, ROWS);
  assert.deepEqual(col, ['C', 'A', 'B', 'C']);
});

test('spinGrid produces REELS columns of ROWS rows', () => {
  const grid = spinGrid(GAME, cryptoRandom);
  assert.equal(grid.length, REELS);
  for (const col of grid) assert.equal(col.length, ROWS);
});

test('a full top-row line of EMPEROR pays the 5-of-a-kind value', () => {
  const rows = [
    ['EMPEROR', 'EMPEROR', 'EMPEROR', 'EMPEROR', 'EMPEROR'],
    ['COIN', 'AMPHORA', 'COIN', 'AMPHORA', 'COIN'],
    ['AMPHORA', 'COIN', 'AMPHORA', 'COIN', 'AMPHORA'],
    ['COIN', 'AMPHORA', 'COIN', 'AMPHORA', 'COIN'],
  ];
  const columns = gridFromRows(rows);
  const bet = PAYLINES.length; // lineBet = 1
  const res = evaluateSpin(GAME, columns, bet);
  const topLine = res.lineWins.find((w) => w.line === 1);
  assert.ok(topLine, 'top line should win');
  assert.equal(topLine.symbol, 'EMPEROR');
  assert.equal(topLine.count, 5);
  assert.equal(topLine.amount, GAME.paytable.EMPEROR[5]);
});

test('wild substitutes to complete a line', () => {
  const rows = [
    ['EAGLE', 'WILD', 'EAGLE', 'COIN', 'COIN'],
    ['COIN', 'AMPHORA', 'COIN', 'AMPHORA', 'COIN'],
    ['AMPHORA', 'COIN', 'AMPHORA', 'COIN', 'AMPHORA'],
    ['COIN', 'AMPHORA', 'COIN', 'AMPHORA', 'COIN'],
  ];
  const columns = gridFromRows(rows);
  const res = evaluateSpin(GAME, columns, PAYLINES.length);
  const topLine = res.lineWins.find((w) => w.line === 1);
  assert.ok(topLine);
  assert.equal(topLine.symbol, 'EAGLE');
  assert.equal(topLine.count, 3);
  assert.equal(topLine.amount, GAME.paytable.EAGLE[3]);
});

test('runs shorter than 3 do not pay', () => {
  const rows = [
    ['EMPEROR', 'EMPEROR', 'COIN', 'AMPHORA', 'SHIELD'],
    ['COIN', 'AMPHORA', 'SHIELD', 'COIN', 'AMPHORA'],
    ['AMPHORA', 'SHIELD', 'COIN', 'AMPHORA', 'SHIELD'],
    ['SHIELD', 'COIN', 'AMPHORA', 'SHIELD', 'COIN'],
  ];
  const columns = gridFromRows(rows);
  const res = evaluateSpin(GAME, columns, PAYLINES.length);
  assert.equal(res.lineWins.find((w) => w.line === 1), undefined);
});

test('3 scatters award a scatter pay and free spins', () => {
  const rows = [
    ['SCATTER', 'COIN', 'SCATTER', 'COIN', 'SCATTER'],
    ['COIN', 'AMPHORA', 'COIN', 'AMPHORA', 'COIN'],
    ['AMPHORA', 'COIN', 'AMPHORA', 'COIN', 'AMPHORA'],
    ['COIN', 'AMPHORA', 'COIN', 'AMPHORA', 'COIN'],
  ];
  const columns = gridFromRows(rows);
  const res = evaluateSpin(GAME, columns, 200);
  assert.equal(res.scatter.count, 3);
  assert.ok(res.scatter.freeSpinsAwarded > 0);
  assert.ok(res.scatter.win > 0);
});

test('free-spin multiplier is applied to line wins but not scatter pays', () => {
  const rows = [
    ['CHARIOT', 'CHARIOT', 'CHARIOT', 'COIN', 'COIN'],
    ['COIN', 'AMPHORA', 'COIN', 'AMPHORA', 'COIN'],
    ['AMPHORA', 'COIN', 'AMPHORA', 'COIN', 'AMPHORA'],
    ['COIN', 'AMPHORA', 'COIN', 'AMPHORA', 'COIN'],
  ];
  const columns = gridFromRows(rows);
  const bet = PAYLINES.length;
  const normal = evaluateSpin(GAME, columns, bet, { isFreeSpin: false });
  const free = evaluateSpin(GAME, columns, bet, { isFreeSpin: true });
  const nWin = normal.lineWins.find((w) => w.line === 1).amount;
  const fWin = free.lineWins.find((w) => w.line === 1).amount;
  assert.equal(fWin, nWin * GAME.freeSpinMultiplier);
});

test('empty grid produces zero total win', () => {
  const rows = [
    ['COIN', 'AMPHORA', 'SHIELD', 'LAUREL', 'CHARIOT'],
    ['COIN', 'AMPHORA', 'SHIELD', 'LAUREL', 'CHARIOT'],
    ['COIN', 'AMPHORA', 'SHIELD', 'LAUREL', 'CHARIOT'],
    ['COIN', 'AMPHORA', 'SHIELD', 'LAUREL', 'CHARIOT'],
  ];
  const columns = gridFromRows(rows);
  const res = evaluateSpin(GAME, columns, 200);
  assert.equal(res.totalWin, 0);
});

test('statistical sanity: RTP over many spins is within a social-game band', () => {
  const bet = 200;
  const spins = 20000;
  let staked = 0;
  let returned = 0;
  for (let i = 0; i < spins; i++) {
    staked += bet;
    returned += playSpin(GAME, bet).totalWin;
  }
  const rtp = returned / staked;
  assert.ok(rtp > 0.3 && rtp < 1.5, `RTP out of expected band: ${rtp.toFixed(3)}`);
});

test('every payline is a valid path within the grid', () => {
  assert.equal(PAYLINES.length, 40);
  for (const line of PAYLINES) {
    assert.equal(line.length, REELS);
    for (const row of line) assert.ok(row >= 0 && row < ROWS);
  }
});

test('every game defines all 12 symbols with paytable entries for paying symbols', () => {
  for (const game of Object.values(GAMES)) {
    const ids = Object.keys(game.symbols);
    assert.equal(ids.length, 12, `${game.id} should have 12 symbols`);
    assert.ok(game.symbols.WILD, `${game.id} needs a WILD`);
    assert.ok(game.symbols.SCATTER, `${game.id} needs a SCATTER`);
    assert.equal(game.reelStrips.length, REELS);
    for (const id of ids) {
      if (id === 'SCATTER') continue;
      assert.ok(game.paytable[id], `${game.id}:${id} needs a paytable row`);
      assert.ok(game.paytable[id][3] && game.paytable[id][5]);
    }
  }
});

// Roma Elite — server-authoritative slot engine.
// Pure functions: given a game config, an RNG and a bet, produce a fully-evaluated
// spin result. The engine is the single source of truth for outcomes; the client
// only animates what the server decides.

import crypto from 'node:crypto';
import { REELS, ROWS, PAYLINES } from './games/shared.js';

// Cryptographically-strong float in [0, 1). Injectable for deterministic tests.
export function cryptoRandom() {
  const buf = crypto.randomBytes(6); // 48 bits of entropy
  let n = 0;
  for (let i = 0; i < 6; i++) n = n * 256 + buf[i];
  return n / 2 ** 48;
}

// Spin a single reel: choose a random stop on its strip and read ROWS symbols
// downward with wrap-around. Returns an array of length ROWS (top -> bottom).
export function spinReel(stripArr, rng) {
  const stop = Math.floor(rng() * stripArr.length) % stripArr.length;
  const col = [];
  for (let r = 0; r < ROWS; r++) col.push(stripArr[(stop + r) % stripArr.length]);
  return col;
}

// Produce the full grid as columns[reel][row].
export function spinGrid(game, rng = cryptoRandom) {
  const columns = [];
  for (let reel = 0; reel < REELS; reel++) {
    columns.push(spinReel(game.reelStrips[reel], rng));
  }
  return columns;
}

function symbolAt(columns, reel, row) {
  return columns[reel][row];
}

// Evaluate one payline left-to-right. WILD substitutes for any paying symbol.
// A win requires a run of >= 3 identical (or wild) symbols starting on reel 0.
function evaluateLine(columns, line, paytable) {
  const first = symbolAt(columns, 0, line[0]);
  if (first === 'SCATTER') return null;

  // Resolve the base paying symbol. A line starting on WILD pays for the first
  // non-wild symbol it meets; a pure-wild run pays as WILD.
  let base = first;
  if (base === 'WILD') {
    for (let reel = 1; reel < REELS; reel++) {
      const s = symbolAt(columns, reel, line[reel]);
      if (s !== 'WILD' && s !== 'SCATTER') { base = s; break; }
    }
  }

  const positions = [];
  let count = 0;
  for (let reel = 0; reel < REELS; reel++) {
    const s = symbolAt(columns, reel, line[reel]);
    if (s === base || s === 'WILD') {
      count++;
      positions.push([reel, line[reel]]);
    } else break;
  }

  if (count < 3) return null;
  const table = paytable[base];
  if (!table || !table[count]) return null;
  return { symbol: base, count, positions: positions.slice(0, count) };
}

function evaluateScatters(columns) {
  const positions = [];
  for (let reel = 0; reel < REELS; reel++) {
    for (let row = 0; row < ROWS; row++) {
      if (columns[reel][row] === 'SCATTER') positions.push([reel, row]);
    }
  }
  return { count: positions.length, positions };
}

// Fully evaluate a spin for a given game.
// bet = total stake for the spin; lineBet = bet / number of paylines.
// isFreeSpin applies the game's free-spin multiplier to line wins (not scatter).
export function evaluateSpin(game, columns, bet, { isFreeSpin = false } = {}) {
  const lineBet = bet / PAYLINES.length;
  const lineWins = [];
  let lineTotal = 0;

  for (let i = 0; i < PAYLINES.length; i++) {
    const res = evaluateLine(columns, PAYLINES[i], game.paytable);
    if (!res) continue;
    const base = game.paytable[res.symbol][res.count] * lineBet;
    const amount = Math.round(base * (isFreeSpin ? game.freeSpinMultiplier : 1));
    lineTotal += amount;
    lineWins.push({
      line: i + 1, symbol: res.symbol, count: res.count,
      positions: res.positions, amount,
    });
  }

  const scatters = evaluateScatters(columns);
  let scatterWin = 0;
  let freeSpinsAwarded = 0;
  if (scatters.count >= 3) {
    const capped = Math.min(scatters.count, 5);
    scatterWin = Math.round((game.scatterPay[capped] || 0) * bet);
    freeSpinsAwarded = game.scatterFreeSpins[capped] || 0;
  }

  return {
    columns,
    bet,
    lineBet,
    isFreeSpin,
    lineWins,
    scatter: {
      count: scatters.count,
      positions: scatters.positions,
      win: scatterWin,
      freeSpinsAwarded,
    },
    totalWin: lineTotal + scatterWin,
  };
}

// Convenience: spin + evaluate in one call.
export function playSpin(game, bet, opts = {}, rng = cryptoRandom) {
  const columns = spinGrid(game, rng);
  return evaluateSpin(game, columns, bet, opts);
}

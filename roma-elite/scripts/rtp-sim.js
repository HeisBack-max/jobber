// Full-experience RTP simulator: plays base spins and resolves free-spin rounds
// (including re-triggers) so the number reflects what a player actually receives.
import { playSpin } from '../server/lib/slot-engine.js';
import { getGame } from '../server/lib/games/index.js';

const gameId = process.argv[2] || 'roma-elite';
const bet = Number(process.argv[3] || 200);
const n = Number(process.argv[4] || 300000);
const game = getGame(gameId);

let staked = 0;
let returned = 0;
let hits = 0;
let baseTriggers = 0;
let bigWins = 0;

for (let i = 0; i < n; i++) {
  staked += bet;
  const r = playSpin(game, bet);
  returned += r.totalWin;
  if (r.totalWin > 0) hits++;
  if (r.totalWin >= bet * 20) bigWins++;

  let pending = r.scatter.freeSpinsAwarded;
  if (pending > 0) baseTriggers++;
  let guard = 0;
  while (pending > 0 && guard < 5000) {
    pending--;
    guard++;
    const fs = playSpin(game, bet, { isFreeSpin: true });
    returned += fs.totalWin;
    if (fs.scatter.freeSpinsAwarded > 0) pending += fs.scatter.freeSpinsAwarded;
  }
}

console.log(`game=${game.id} bet=${bet} spins=${n}`);
console.log('Full RTP:          ', (returned / staked * 100).toFixed(1) + '%');
console.log('Base hit freq:     ', (hits / n * 100).toFixed(1) + '%');
console.log('Free-spin trigger: ', (baseTriggers / n * 100).toFixed(2) + '%  (1 in ' + Math.round(n / Math.max(baseTriggers, 1)) + ')');
console.log('Big win >=20x:     ', (bigWins / n * 100).toFixed(2) + '%');

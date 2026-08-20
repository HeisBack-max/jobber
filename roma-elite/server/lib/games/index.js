// Game registry. Add a theme by dropping a config module here.
import romaElite from './roma-elite.js';
import phnomPenh from './phnom-penh.js';

export const GAMES = {
  [romaElite.id]: romaElite,
  [phnomPenh.id]: phnomPenh,
};

export const DEFAULT_GAME = romaElite.id;

export function getGame(id) {
  return GAMES[id] || GAMES[DEFAULT_GAME];
}

// A trimmed, client-safe view of a game (no reel strips — those stay server-side
// so outcomes can't be predicted from the payload).
export function publicGameConfig(game) {
  return {
    id: game.id,
    theme: game.theme,
    symbols: game.symbols,
    paytable: game.paytable,
    scatterPay: game.scatterPay,
    scatterFreeSpins: game.scatterFreeSpins,
    freeSpinMultiplier: game.freeSpinMultiplier,
    betTiers: game.betTiers,
    defaultBet: game.defaultBet,
  };
}

export function gameList() {
  return Object.values(GAMES).map((g) => ({
    id: g.id, name: g.theme.name, tagline: g.theme.tagline, palette: g.theme.palette,
  }));
}

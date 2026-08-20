// Shared slot geometry used by every Roma Elite game theme.
// The reel grid and payline layout are identical across themes; only the symbol
// art, paytable and reel weighting differ per game.

export const REELS = 5;
export const ROWS = 4;

// 40 fixed paylines over a 5x4 grid. Each entry lists the row index
// (0=top .. 3=bottom) selected on each of the 5 reels. Original hand-designed paths.
export const PAYLINES = [
  [0, 0, 0, 0, 0], // 1  top row
  [1, 1, 1, 1, 1], // 2
  [2, 2, 2, 2, 2], // 3
  [3, 3, 3, 3, 3], // 4  bottom row
  [0, 1, 2, 1, 0], // 5  shallow V (upper)
  [1, 2, 3, 2, 1], // 6  shallow V (lower)
  [3, 2, 1, 2, 3], // 7  shallow ^ (lower)
  [2, 1, 0, 1, 2], // 8  shallow ^ (upper)
  [0, 0, 1, 0, 0], // 9
  [1, 1, 2, 1, 1], // 10
  [2, 2, 3, 2, 2], // 11
  [1, 1, 0, 1, 1], // 12
  [2, 2, 1, 2, 2], // 13
  [3, 3, 2, 3, 3], // 14
  [0, 1, 1, 1, 0], // 15
  [3, 2, 2, 2, 3], // 16
  [0, 1, 0, 1, 0], // 17 zig-zag
  [1, 2, 1, 2, 1], // 18
  [2, 3, 2, 3, 2], // 19
  [1, 0, 1, 0, 1], // 20
  [2, 1, 2, 1, 2], // 21
  [3, 2, 3, 2, 3], // 22
  [0, 2, 0, 2, 0], // 23 wide zig-zag
  [1, 3, 1, 3, 1], // 24
  [3, 1, 3, 1, 3], // 25
  [0, 0, 2, 0, 0], // 26
  [3, 3, 1, 3, 3], // 27
  [0, 1, 2, 3, 3], // 28 descending stair
  [3, 2, 1, 0, 0], // 29 ascending stair
  [0, 0, 1, 2, 3], // 30 diagonal
  [3, 3, 2, 1, 0], // 31 diagonal
  [1, 0, 0, 0, 1], // 32 cup
  [2, 3, 3, 3, 2], // 33 cap
  [0, 2, 3, 2, 0], // 34 deep V
  [3, 1, 0, 1, 3], // 35 deep ^
  [1, 2, 2, 2, 1], // 36
  [2, 1, 1, 1, 2], // 37
  [0, 3, 0, 3, 0], // 38 extreme zig-zag
  [3, 0, 3, 0, 3], // 39
  [2, 0, 2, 0, 2], // 40
];

// Bet tiers shared across themes (total stake per spin, spread over 40 lines).
export const BET_TIERS = [40, 80, 200, 400, 800, 2000, 4000];
export const DEFAULT_BET = 200;

export const STARTING_COINS = 10000;
export const WELCOME_FREE_SPINS = 100;

// Expand a { symbol: count } weighting into a flat reel strip array.
export function strip(weights) {
  const out = [];
  for (const [sym, count] of Object.entries(weights)) {
    for (let i = 0; i < count; i++) out.push(sym);
  }
  return out;
}

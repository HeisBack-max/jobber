// Phnom Penh Nights — original, colorful Cambodian city themed game.
// Celebrates Phnom Penh landmarks and everyday culture: the Royal Palace, Khmer
// temples, the naga, apsara dance, tuk-tuks, the riverside and the Water Festival.
//
// Original work — NOT a clone of any commercial game or franchise. Contains no
// real-world adult/nightlife venues or persons. Virtual currency only.
//
// The math (paytable, reel weighting, scatter/free-spin config) intentionally
// mirrors Roma Elite's tuned balance so both games share the same ~88% social RTP.
import { strip, STARTING_COINS, WELCOME_FREE_SPINS, BET_TIERS, DEFAULT_BET } from './shared.js';

export default {
  id: 'phnom-penh',
  theme: {
    name: 'Phnom Penh Nights',
    tagline: 'City of Gold on the Riverside',
    palette: {
      bg0: '#0d1a2b', bg1: '#132a44', accent: '#ffd23f', accent2: '#f08a24',
      marble: '#fff4e0', crimson: '#c1121f', ink: '#fff6e5', jade: '#2a9d8f',
    },
    scenery: 'riverside',
    freeSpinName: 'Riverside Tycoon Bonus',
    bonusHost: 'tycoon',
  },
  symbols: {
    PALACE:  { id: 'PALACE',  name: 'Royal Palace',        tier: 'premium', glyph: '🏯' },
    TEMPLE:  { id: 'TEMPLE',  name: 'Golden Pagoda',       tier: 'premium', glyph: '🛕' },
    NAGA:    { id: 'NAGA',    name: 'Golden Naga',         tier: 'premium', glyph: '🐉' },
    APSARA:  { id: 'APSARA',  name: 'Apsara Dancer',       tier: 'premium', glyph: '💃' },
    TUKTUK:  { id: 'TUKTUK',  name: 'Tuk-Tuk',             tier: 'medium',  glyph: '🛺' },
    LOTUS:   { id: 'LOTUS',   name: 'Lotus Blossom',       tier: 'medium',  glyph: '🪷' },
    BOAT:    { id: 'BOAT',    name: 'Dragon Boat',         tier: 'medium',  glyph: '🛶' },
    NUMPANG: { id: 'NUMPANG', name: 'Num Pang',            tier: 'low',     glyph: '🥖' },
    KRAMA:   { id: 'KRAMA',   name: 'Krama Scarf',         tier: 'low',     glyph: '🧣' },
    RIEL:    { id: 'RIEL',    name: 'Riel Coin',           tier: 'low',     glyph: '🪙' },
    WILD:    { id: 'WILD',    name: 'Independence Monument',tier: 'wild',   glyph: '🏛️' },
    // Original fictional bonus host — not based on any real person.
    SCATTER: { id: 'SCATTER', name: 'The Riverside Tycoon', tier: 'scatter', glyph: '🕴️' },
  },
  paytable: {
    PALACE:  { 3: 60,  4: 240, 5: 1200 },
    TEMPLE:  { 3: 46,  4: 175, 5: 800 },
    NAGA:    { 3: 35,  4: 130, 5: 580 },
    APSARA:  { 3: 29,  4: 92,  5: 400 },
    TUKTUK:  { 3: 17,  4: 52,  5: 220 },
    LOTUS:   { 3: 15,  4: 40,  5: 160 },
    BOAT:    { 3: 12,  4: 35,  5: 130 },
    NUMPANG: { 3: 9,   4: 23,  5: 87 },
    KRAMA:   { 3: 6,   4: 17,  5: 64 },
    RIEL:    { 3: 6,   4: 15,  5: 46 },
    WILD:    { 3: 72,  4: 290, 5: 1450 },
  },
  scatterPay: { 3: 2, 4: 8, 5: 40 },
  scatterFreeSpins: { 3: 6, 4: 10, 5: 15 },
  freeSpinMultiplier: 2,
  reelStrips: [
    strip({ RIEL: 5, KRAMA: 5, NUMPANG: 5, BOAT: 4, LOTUS: 4, TUKTUK: 4,
            APSARA: 3, NAGA: 3, TEMPLE: 2, PALACE: 2, WILD: 2, SCATTER: 1 }),
    strip({ RIEL: 5, KRAMA: 5, NUMPANG: 5, BOAT: 4, LOTUS: 4, TUKTUK: 4,
            APSARA: 3, NAGA: 3, TEMPLE: 2, PALACE: 2, WILD: 2, SCATTER: 1 }),
    strip({ RIEL: 6, KRAMA: 5, NUMPANG: 5, BOAT: 4, LOTUS: 4, TUKTUK: 3,
            APSARA: 3, NAGA: 3, TEMPLE: 2, PALACE: 2, WILD: 3, SCATTER: 1 }),
    strip({ RIEL: 6, KRAMA: 5, NUMPANG: 5, BOAT: 4, LOTUS: 4, TUKTUK: 4,
            APSARA: 3, NAGA: 2, TEMPLE: 2, PALACE: 2, WILD: 2, SCATTER: 1 }),
    strip({ RIEL: 6, KRAMA: 6, NUMPANG: 5, BOAT: 5, LOTUS: 4, TUKTUK: 4,
            APSARA: 3, NAGA: 2, TEMPLE: 2, PALACE: 1, WILD: 2, SCATTER: 1 }),
  ],
  betTiers: BET_TIERS,
  defaultBet: DEFAULT_BET,
  startingCoins: STARTING_COINS,
  welcomeFreeSpins: WELCOME_FREE_SPINS,
};

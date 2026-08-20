// Authentication helpers: password hashing (scrypt), magic-link tokens, sessions,
// and honest account provisioning. No real-money coupling — accounts are free.
import crypto from 'node:crypto';
import * as store from './store.js';
import { getGame, DEFAULT_GAME } from './games/index.js';

const SCRYPT_KEYLEN = 64;

export function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const derived = crypto.scryptSync(password, salt, SCRYPT_KEYLEN).toString('hex');
  return `scrypt$${salt}$${derived}`;
}

export function verifyPassword(password, stored) {
  try {
    const [scheme, salt, hash] = stored.split('$');
    if (scheme !== 'scrypt') return false;
    const derived = crypto.scryptSync(password, salt, SCRYPT_KEYLEN);
    const expected = Buffer.from(hash, 'hex');
    return derived.length === expected.length && crypto.timingSafeEqual(derived, expected);
  } catch {
    return false;
  }
}

export function newToken() {
  return crypto.randomBytes(24).toString('base64url');
}

export function newSessionId() {
  return crypto.randomBytes(24).toString('base64url');
}

// Rank ladder derived from lifetime spins — cosmetic progression only.
const RANKS = [
  [0, 'Plebeian'], [50, 'Legionnaire'], [200, 'Centurion'], [500, 'Tribune'],
  [1200, 'Praetor'], [3000, 'Senator'], [7000, 'Consul'], [15000, 'Imperator'],
];
export function rankForSpins(spins) {
  let name = RANKS[0][1];
  for (const [threshold, label] of RANKS) if (spins >= threshold) name = label;
  return name;
}

// Generate a friendly, original username like "GoldenEagle482".
const ADJ = ['Golden', 'Iron', 'Marble', 'Crimson', 'Imperial', 'Noble', 'Bronze', 'Radiant'];
const NOUN = ['Eagle', 'Legion', 'Chariot', 'Laurel', 'Consul', 'Aurelius', 'Maximus', 'Valeria'];
export function generateUsername() {
  const a = ADJ[crypto.randomInt(ADJ.length)];
  const n = NOUN[crypto.randomInt(NOUN.length)];
  return `${a}${n}${crypto.randomInt(100, 999)}`;
}

export function generatePassword() {
  return crypto.randomBytes(6).toString('base64url'); // ~8 chars, shown once
}

// Create a brand-new player, seeded with FREE welcome coins + free spins.
// No payment is required or accepted — this is the honest onboarding path.
export function provisionUser({ username, password, source = 'direct' } = {}) {
  const game = getGame(DEFAULT_GAME);
  const uname = username || generateUsername();
  const pass = password || generatePassword();
  const id = 'u_' + crypto.randomBytes(8).toString('hex');
  const now = Date.now();

  const user = {
    id,
    username: uname,
    passwordHash: hashPassword(pass),
    createdAt: now,
    source,
    ageConfirmed: false,
    coins: game.startingCoins,
    freeSpins: game.welcomeFreeSpins,
    lifetimeSpins: 0,
    prestige: 0,
    biggestWin: 0,
    lastGame: DEFAULT_GAME,
  };
  store.createUser(user);
  // Return the plaintext password ONCE so it can be shown to the new user.
  return { user, plainPassword: pass };
}

// Issue a single-use magic-login token for an existing user.
export function issueMagicToken(userId, ttlMs = 1000 * 60 * 60 * 24 * 7) {
  const token = newToken();
  store.putToken(token, { userId, expiresAt: Date.now() + ttlMs });
  return token;
}

// Redeem a magic token -> returns the user or null.
export function redeemMagicToken(token) {
  const rec = store.getToken(token);
  if (!rec) return null;
  if (rec.expiresAt < Date.now()) { store.consumeToken(token); return null; }
  store.consumeToken(token);
  return store.getUser(rec.userId);
}

export function login(username, password) {
  const user = store.getUserByUsername(username);
  if (!user) return null;
  if (!verifyPassword(password, user.passwordHash)) return null;
  return user;
}

// Public projection of a user (never leak the password hash).
export function publicUser(user) {
  if (!user) return null;
  return {
    id: user.id,
    username: user.username,
    createdAt: user.createdAt,
    ageConfirmed: user.ageConfirmed,
    coins: user.coins,
    freeSpins: user.freeSpins,
    lifetimeSpins: user.lifetimeSpins,
    prestige: user.prestige,
    biggestWin: user.biggestWin,
    rank: rankForSpins(user.lifetimeSpins),
    lastGame: user.lastGame,
  };
}

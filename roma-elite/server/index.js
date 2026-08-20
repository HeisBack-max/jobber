// Roma Elite — HTTP server (zero external dependencies).
// Serves the static frontend and a small JSON API. All game outcomes are decided
// here, server-side; the client only renders what it is told.
//
// SOCIAL GAME ONLY: virtual, non-cashable coins. No real-money deposits, no
// withdrawals, nothing of value can be won. See LEGAL.md.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

import * as store from './lib/store.js';
import * as auth from './lib/auth.js';
import { playSpin } from './lib/slot-engine.js';
import { getGame, gameList, publicGameConfig } from './lib/games/index.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = path.join(__dirname, '..', 'public');
const PORT = process.env.PORT || 3000;

store.load();

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
};

const TOPUP_AMOUNT = 5000;
const TOPUP_THRESHOLD = 500;        // only top up when nearly broke
const TOPUP_COOLDOWN_MS = 1000 * 60 * 30;

// --- helpers ---------------------------------------------------------------
function send(res, status, body, headers = {}) {
  const data = typeof body === 'string' ? body : JSON.stringify(body);
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', ...headers });
  res.end(data);
}

function parseCookies(req) {
  const header = req.headers.cookie || '';
  const out = {};
  for (const part of header.split(';')) {
    const i = part.indexOf('=');
    if (i > -1) out[part.slice(0, i).trim()] = decodeURIComponent(part.slice(i + 1).trim());
  }
  return out;
}

function readBody(req) {
  return new Promise((resolve) => {
    let data = '';
    req.on('data', (c) => {
      data += c;
      if (data.length > 1e6) req.destroy(); // basic guard
    });
    req.on('end', () => {
      if (!data) return resolve({});
      try { resolve(JSON.parse(data)); } catch { resolve({}); }
    });
  });
}

function setSessionCookie(res, sid) {
  res.setHeader('Set-Cookie',
    `re_sid=${sid}; HttpOnly; SameSite=Lax; Path=/; Max-Age=${60 * 60 * 24 * 30}`);
}

function currentUser(req) {
  const sid = parseCookies(req).re_sid;
  if (!sid) return null;
  const sess = store.getSession(sid);
  if (!sess) return null;
  return store.getUser(sess.userId);
}

function startSession(res, user) {
  const sid = auth.newSessionId();
  store.putSession(sid, user.id);
  setSessionCookie(res, sid);
}

// --- static files ----------------------------------------------------------
function serveStatic(req, res, urlPath) {
  let rel = decodeURIComponent(urlPath.split('?')[0]);
  if (rel === '/' || rel === '') rel = '/index.html';
  // prevent path traversal
  const safe = path.normalize(rel).replace(/^(\.\.[/\\])+/, '');
  const filePath = path.join(PUBLIC_DIR, safe);
  if (!filePath.startsWith(PUBLIC_DIR)) return send(res, 403, { error: 'forbidden' });

  fs.readFile(filePath, (err, buf) => {
    if (err) {
      // SPA fallback to index.html for unknown non-API routes
      if (!safe.includes('.')) {
        return fs.readFile(path.join(PUBLIC_DIR, 'index.html'), (e2, idx) => {
          if (e2) return send(res, 404, { error: 'not found' });
          res.writeHead(200, { 'Content-Type': MIME['.html'] });
          res.end(idx);
        });
      }
      return send(res, 404, { error: 'not found' });
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
    res.end(buf);
  });
}

// --- API -------------------------------------------------------------------
async function handleApi(req, res, url) {
  const route = url.pathname;
  const method = req.method;

  // Public: list games + configs
  if (route === '/api/games' && method === 'GET') {
    return send(res, 200, {
      games: gameList(),
      configs: Object.fromEntries(gameList().map((g) => [g.id, publicGameConfig(getGame(g.id))])),
    });
  }

  // Register — honest, free. Never asks for or accepts payment.
  if (route === '/api/register' && method === 'POST') {
    const body = await readBody(req);
    const username = (body.username || '').trim();
    const password = (body.password || '').trim();
    if (username) {
      // Usernames are matched case-insensitively, so `Alice` and `alice` collide.
      if (username.length < 3 || username.length > 20 || !/^[\w]+$/.test(username)) {
        return send(res, 400, { error: 'Username must be 3–20 letters, numbers or underscore.' });
      }
      if (store.getUserByUsername(username)) {
        return send(res, 409, { error: 'That username is taken.' });
      }
    }
    // Checked outside the username block: a caller may supply only a password,
    // and that account is just as loginable, so it must meet the same minimum.
    if (password && password.length < 6) {
      return send(res, 400, { error: 'Password must be at least 6 characters.' });
    }
    const { user, plainPassword } = auth.provisionUser({
      username: username || undefined,
      password: password || undefined,
      source: body.source || 'web',
    });
    startSession(res, user);
    return send(res, 200, {
      user: auth.publicUser(user),
      // Only set for credentials WE generated — never echo a caller's own password.
      generated: (username || password) ? null : { username: user.username, password: plainPassword },
    });
  }

  // Login with username/password
  if (route === '/api/login' && method === 'POST') {
    const body = await readBody(req);
    const user = auth.login((body.username || '').trim(), body.password || '');
    if (!user) return send(res, 401, { error: 'Invalid username or password.' });
    startSession(res, user);
    return send(res, 200, { user: auth.publicUser(user) });
  }

  // Redeem a magic-login token (from ?token= link)
  if (route === '/api/magic' && method === 'POST') {
    const body = await readBody(req);
    const user = auth.redeemMagicToken((body.token || '').trim());
    if (!user) return send(res, 401, { error: 'This login link is invalid or has expired.' });
    startSession(res, user);
    return send(res, 200, { user: auth.publicUser(user) });
  }

  // Everything below requires a session
  const user = currentUser(req);

  if (route === '/api/me' && method === 'GET') {
    if (!user) return send(res, 401, { error: 'not authenticated' });
    return send(res, 200, { user: auth.publicUser(user) });
  }

  if (route === '/api/logout' && method === 'POST') {
    const sid = parseCookies(req).re_sid;
    if (sid) store.deleteSession(sid);
    res.setHeader('Set-Cookie', 're_sid=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0');
    return send(res, 200, { ok: true });
  }

  if (!user) return send(res, 401, { error: 'not authenticated' });

  // Confirm 18+ age gate
  if (route === '/api/confirm-age' && method === 'POST') {
    user.ageConfirmed = true;
    store.updateUser(user);
    return send(res, 200, { user: auth.publicUser(user) });
  }

  // Issue a magic link for the current user (demo of the honest magic-link flow)
  if (route === '/api/magic-link' && method === 'POST') {
    const token = auth.issueMagicToken(user.id);
    return send(res, 200, { token, url: `/play?token=${token}` });
  }

  // Honest top-up: free virtual coins when nearly broke (no payment, cooldown-limited)
  if (route === '/api/topup' && method === 'POST') {
    if (user.coins > TOPUP_THRESHOLD) {
      return send(res, 400, { error: 'Top-up is only available when you are low on coins.' });
    }
    const now = Date.now();
    if (user.lastTopupAt && now - user.lastTopupAt < TOPUP_COOLDOWN_MS) {
      const mins = Math.ceil((TOPUP_COOLDOWN_MS - (now - user.lastTopupAt)) / 60000);
      return send(res, 429, { error: `Next free top-up available in ${mins} min.` });
    }
    user.coins += TOPUP_AMOUNT;
    user.lastTopupAt = now;
    store.updateUser(user);
    return send(res, 200, { user: auth.publicUser(user), granted: TOPUP_AMOUNT });
  }

  // The spin: server decides the outcome and updates the balance.
  if (route === '/api/spin' && method === 'POST') {
    if (!user.ageConfirmed) return send(res, 403, { error: 'Please confirm you are 18+ first.' });
    const body = await readBody(req);
    const game = getGame(body.gameId);
    let bet = Number(body.bet);
    if (!game.betTiers.includes(bet)) bet = game.defaultBet;

    const usingFreeSpin = user.freeSpins > 0;
    if (usingFreeSpin) {
      user.freeSpins -= 1;
    } else {
      if (user.coins < bet) {
        return send(res, 400, { error: 'Not enough coins for that bet.', code: 'INSUFFICIENT' });
      }
      user.coins -= bet;
    }

    const result = playSpin(game, bet, { isFreeSpin: usingFreeSpin });
    user.coins += result.totalWin;
    user.freeSpins += result.scatter.freeSpinsAwarded;
    user.lifetimeSpins += 1;
    user.lastGame = game.id;
    if (result.totalWin > (user.biggestWin || 0)) user.biggestWin = result.totalWin;
    store.updateUser(user);

    return send(res, 200, {
      spin: {
        columns: result.columns,
        lineWins: result.lineWins,
        scatter: result.scatter,
        totalWin: result.totalWin,
        bet: result.bet,
        wasFreeSpin: usingFreeSpin,
      },
      user: auth.publicUser(user),
    });
  }

  return send(res, 404, { error: 'unknown endpoint' });
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    if (url.pathname.startsWith('/api/')) return await handleApi(req, res, url);
    return serveStatic(req, res, req.url);
  } catch (err) {
    console.error('[server] error:', err);
    send(res, 500, { error: 'internal error' });
  }
});

server.listen(PORT, () => {
  console.log(`\n  🏛️  Roma Elite — social demo running`);
  console.log(`  ▶  http://localhost:${PORT}`);
  console.log(`  ⚖️  Entertainment only. Virtual coins, no real money.\n`);
});

// Flush pending writes on shutdown.
for (const sig of ['SIGINT', 'SIGTERM']) {
  process.on(sig, () => { try { store.saveNow(); } catch {} process.exit(0); });
}

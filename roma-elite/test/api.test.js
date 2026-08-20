// API integration tests for the zero-dependency Roma Elite HTTP server.
//
// The server module calls server.listen() at import time and persists to
// data/roma-elite.json (a path fixed relative to server/lib/store.js, with no
// env override). So we boot it as a child process on a free ephemeral port and
// snapshot/restore the data file around the suite, which keeps repeated runs
// deterministic without destroying a developer's existing local data.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import net from 'node:net';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

import { REELS, ROWS, BET_TIERS, DEFAULT_BET } from '../server/lib/games/shared.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.join(__dirname, '..');
const SERVER_ENTRY = path.join(REPO_ROOT, 'server', 'index.js');
const DATA_FILE = path.join(REPO_ROOT, 'data', 'roma-elite.json');

let child = null;
let BASE = '';
let dataBackup = null; // Buffer if the file existed before the suite, else null.

// --- boot helpers -----------------------------------------------------------

function freePort() {
  return new Promise((resolve, reject) => {
    const probe = net.createServer();
    probe.on('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const { port } = probe.address();
      probe.close(() => resolve(port));
    });
  });
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function waitForServer(base, proc, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (proc.exitCode !== null || proc.signalCode !== null) return false;
    try {
      const res = await fetch(`${base}/api/games`);
      if (res.ok) { await res.arrayBuffer(); return true; }
    } catch {
      // not listening yet
    }
    await sleep(50);
  }
  return false;
}

async function startServer() {
  let lastErr = '';
  for (let attempt = 0; attempt < 5; attempt++) {
    const port = await freePort();
    const base = `http://127.0.0.1:${port}`;
    const proc = spawn(process.execPath, [SERVER_ENTRY], {
      cwd: REPO_ROOT,
      env: { ...process.env, PORT: String(port) },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    let stderr = '';
    proc.stdout.on('data', () => {});
    proc.stderr.on('data', (c) => { stderr += c; });

    if (await waitForServer(base, proc)) return { proc, base };

    lastErr = stderr;
    proc.kill('SIGKILL');
    await sleep(50);
  }
  throw new Error(`server failed to start. stderr:\n${lastErr}`);
}

async function stopServer(proc) {
  if (!proc || proc.exitCode !== null || proc.signalCode !== null) return;
  const exited = new Promise((resolve) => proc.once('exit', resolve));
  proc.kill('SIGTERM');
  const timer = setTimeout(() => proc.kill('SIGKILL'), 3000);
  await exited;
  clearTimeout(timer);
}

// --- request helpers --------------------------------------------------------

// Sessions are cookie-based; fetch does not keep a jar, so we pass the cookie
// explicitly on every authenticated call.
function sessionCookie(res) {
  const cookies = typeof res.headers.getSetCookie === 'function'
    ? res.headers.getSetCookie()
    : [res.headers.get('set-cookie')].filter(Boolean);
  for (const c of cookies) {
    const pair = c.split(';')[0];
    if (pair.startsWith('re_sid=')) return pair;
  }
  return null;
}

async function api(route, { method = 'GET', body, cookie, rawBody } = {}) {
  const headers = {};
  if (cookie) headers.cookie = cookie;
  let payload;
  if (rawBody !== undefined) {
    payload = rawBody;
    headers['content-type'] = 'application/json';
  } else if (body !== undefined) {
    payload = JSON.stringify(body);
    headers['content-type'] = 'application/json';
  }
  const res = await fetch(BASE + route, { method, headers, body: payload });
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch { /* non-JSON body */ }
  return { status: res.status, json, text, cookie: sessionCookie(res) };
}

function uniqueName(prefix = 'tu') {
  return `${prefix}${crypto.randomBytes(5).toString('hex')}`; // \w only, <= 20 chars
}

// Register a fresh player and return { cookie, user, username, password }.
async function newPlayer({ ageConfirmed = false } = {}) {
  const username = uniqueName();
  const password = 'passw0rd!';
  const reg = await api('/api/register', { method: 'POST', body: { username, password } });
  assert.equal(reg.status, 200, `register failed: ${reg.text}`);
  assert.ok(reg.cookie, 'register should set a session cookie');
  if (ageConfirmed) {
    const ok = await api('/api/confirm-age', { method: 'POST', cookie: reg.cookie });
    assert.equal(ok.status, 200);
    return { cookie: reg.cookie, user: ok.json.user, username, password };
  }
  return { cookie: reg.cookie, user: reg.json.user, username, password };
}

// --- lifecycle --------------------------------------------------------------

before(async () => {
  dataBackup = fs.existsSync(DATA_FILE) ? fs.readFileSync(DATA_FILE) : null;
  const started = await startServer();
  child = started.proc;
  BASE = started.base;
});

after(async () => {
  await stopServer(child);
  // Restore the data file to exactly what it was before the suite ran.
  try {
    if (dataBackup !== null) fs.writeFileSync(DATA_FILE, dataBackup);
    else fs.rmSync(DATA_FILE, { force: true });
    fs.rmSync(`${DATA_FILE}.tmp`, { force: true });
  } catch { /* best effort cleanup */ }
});

// --- games ------------------------------------------------------------------

test('GET /api/games returns games and public configs', async () => {
  const res = await api('/api/games');
  assert.equal(res.status, 200);
  assert.ok(Array.isArray(res.json.games));
  assert.ok(res.json.games.length >= 1);
  for (const g of res.json.games) {
    assert.equal(typeof g.id, 'string');
    assert.equal(typeof g.name, 'string');
    assert.ok(res.json.configs[g.id], `missing config for ${g.id}`);
  }
  const cfg = res.json.configs[res.json.games[0].id];
  assert.deepEqual(cfg.betTiers, BET_TIERS);
  assert.equal(cfg.defaultBet, DEFAULT_BET);
  assert.ok(cfg.symbols.WILD && cfg.symbols.SCATTER);
});

test('GET /api/games never leaks server-side reel strips', async () => {
  const res = await api('/api/games');
  assert.equal(res.status, 200);
  for (const [id, cfg] of Object.entries(res.json.configs)) {
    assert.equal(cfg.reelStrips, undefined, `${id} leaked reelStrips`);
  }
  // Belt and braces: the raw payload must not mention the key at all.
  assert.equal(res.text.includes('reelStrips'), false);
});

// --- registration -----------------------------------------------------------

test('POST /api/register with no body auto-generates credentials', async () => {
  const res = await api('/api/register', { method: 'POST' });
  assert.equal(res.status, 200, res.text);
  assert.ok(res.json.generated, 'should return generated credentials');
  assert.equal(typeof res.json.generated.username, 'string');
  assert.equal(typeof res.json.generated.password, 'string');
  assert.ok(res.json.generated.username.length > 0);
  assert.ok(res.json.generated.password.length > 0);
  assert.equal(res.json.user.username, res.json.generated.username);

  // Fresh players are seeded with free virtual coins and free spins.
  assert.ok(res.json.user.coins > 0, 'new user should start with coins');
  assert.ok(res.json.user.freeSpins > 0, 'new user should start with free spins');
  assert.equal(res.json.user.ageConfirmed, false);
  assert.equal(res.json.user.lifetimeSpins, 0);
  assert.equal(res.json.user.passwordHash, undefined, 'must not leak passwordHash');
  assert.ok(res.cookie, 'should start a session');

  // The generated credentials really work.
  const login = await api('/api/login', {
    method: 'POST',
    body: { username: res.json.generated.username, password: res.json.generated.password },
  });
  assert.equal(login.status, 200, login.text);
  assert.equal(login.json.user.id, res.json.user.id);
});

test('POST /api/register with chosen credentials works', async () => {
  const username = uniqueName();
  const res = await api('/api/register', {
    method: 'POST',
    body: { username, password: 'hunter22' },
  });
  assert.equal(res.status, 200, res.text);
  assert.equal(res.json.user.username, username);
  assert.equal(res.json.generated, null, 'chosen credentials must not be echoed back');
  assert.ok(res.cookie);

  const me = await api('/api/me', { cookie: res.cookie });
  assert.equal(me.status, 200);
  assert.equal(me.json.user.username, username);
});

test('POST /api/register rejects a duplicate username with 409', async () => {
  const username = uniqueName();
  const first = await api('/api/register', {
    method: 'POST', body: { username, password: 'hunter22' },
  });
  assert.equal(first.status, 200, first.text);

  const dup = await api('/api/register', {
    method: 'POST', body: { username, password: 'different1' },
  });
  assert.equal(dup.status, 409);
  assert.equal(typeof dup.json.error, 'string');
});

test('POST /api/register rejects a too-short password with 400', async () => {
  const res = await api('/api/register', {
    method: 'POST', body: { username: uniqueName(), password: 'abc' },
  });
  assert.equal(res.status, 400, res.text);
  assert.match(res.json.error, /password/i);
});

test('POST /api/register rejects invalid username characters with 400', async () => {
  for (const bad of ['bad name', 'bad-name', 'bad!', 'ab', 'x'.repeat(21)]) {
    const res = await api('/api/register', {
      method: 'POST', body: { username: bad, password: 'hunter22' },
    });
    assert.equal(res.status, 400, `expected 400 for ${JSON.stringify(bad)}: ${res.text}`);
    assert.match(res.json.error, /username/i);
  }
});

// --- login / session --------------------------------------------------------

test('POST /api/login succeeds with correct credentials', async () => {
  const { username, password, user } = await newPlayer();
  const res = await api('/api/login', { method: 'POST', body: { username, password } });
  assert.equal(res.status, 200, res.text);
  assert.equal(res.json.user.id, user.id);
  assert.ok(res.cookie, 'login should issue a session cookie');

  const me = await api('/api/me', { cookie: res.cookie });
  assert.equal(me.status, 200);
  assert.equal(me.json.user.id, user.id);
});

test('POST /api/login rejects a wrong password with 401', async () => {
  const { username } = await newPlayer();
  const res = await api('/api/login', {
    method: 'POST', body: { username, password: 'definitely-not-it' },
  });
  assert.equal(res.status, 401);
  assert.equal(res.cookie, null, 'a failed login must not start a session');

  const unknown = await api('/api/login', {
    method: 'POST', body: { username: uniqueName('nope'), password: 'passw0rd!' },
  });
  assert.equal(unknown.status, 401);
});

test('GET /api/me without a session returns 401', async () => {
  const anon = await api('/api/me');
  assert.equal(anon.status, 401);
  assert.equal(anon.json.error, 'not authenticated');

  const bogus = await api('/api/me', { cookie: 're_sid=not-a-real-session' });
  assert.equal(bogus.status, 401);
});

// --- age gate + spinning ----------------------------------------------------

test('POST /api/spin before confirming age returns 403', async () => {
  const { cookie } = await newPlayer();
  const res = await api('/api/spin', { method: 'POST', cookie, body: { bet: DEFAULT_BET } });
  assert.equal(res.status, 403, res.text);
  assert.match(res.json.error, /18\+/);

  // The blocked spin must not have touched the balance.
  const me = await api('/api/me', { cookie });
  assert.equal(me.json.user.lifetimeSpins, 0);
});

test('POST /api/confirm-age then /api/spin returns a well-formed grid', async () => {
  const { cookie } = await newPlayer();
  const confirmed = await api('/api/confirm-age', { method: 'POST', cookie });
  assert.equal(confirmed.status, 200);
  assert.equal(confirmed.json.user.ageConfirmed, true);

  const res = await api('/api/spin', { method: 'POST', cookie, body: { bet: DEFAULT_BET } });
  assert.equal(res.status, 200, res.text);

  const { spin, user } = res.json;
  assert.ok(spin, 'response should carry a spin');
  assert.ok(user, 'response should carry the updated user');

  assert.equal(spin.columns.length, REELS);
  const symbolIds = Object.keys(
    (await api('/api/games')).json.configs[user.lastGame].symbols,
  );
  for (const col of spin.columns) {
    assert.equal(col.length, ROWS);
    for (const sym of col) assert.ok(symbolIds.includes(sym), `unknown symbol ${sym}`);
  }

  assert.ok(Array.isArray(spin.lineWins));
  assert.equal(spin.bet, DEFAULT_BET);
  assert.equal(typeof spin.totalWin, 'number');
  assert.ok(spin.totalWin >= 0);
  assert.equal(typeof spin.scatter.count, 'number');
  assert.equal(typeof spin.scatter.freeSpinsAwarded, 'number');

  assert.equal(user.lifetimeSpins, 1);
  assert.equal(user.passwordHash, undefined, 'spin response must not leak passwordHash');
  // Every reported line win must be consistent with the total.
  const lineTotal = spin.lineWins.reduce((a, w) => a + w.amount, 0);
  assert.equal(spin.totalWin, lineTotal + spin.scatter.win);
});

test('a spin consumes a free spin and leaves coins untouched by the stake', async () => {
  const { cookie, user: before } = await newPlayer({ ageConfirmed: true });
  assert.ok(before.freeSpins > 0, 'fixture expects welcome free spins');

  const res = await api('/api/spin', { method: 'POST', cookie, body: { bet: DEFAULT_BET } });
  assert.equal(res.status, 200, res.text);
  const { spin, user: after } = res.json;

  assert.equal(spin.wasFreeSpin, true);
  // Coins move only by the win — the stake was covered by the free spin.
  assert.equal(after.coins, before.coins + spin.totalWin);
  assert.equal(after.freeSpins, before.freeSpins - 1 + spin.scatter.freeSpinsAwarded);
  assert.equal(after.lifetimeSpins, before.lifetimeSpins + 1);

  // The persisted user matches what the spin returned.
  const me = await api('/api/me', { cookie });
  assert.equal(me.json.user.coins, after.coins);
  assert.equal(me.json.user.freeSpins, after.freeSpins);
});

test('repeated spins keep free-spin and coin bookkeeping consistent', async () => {
  const { cookie } = await newPlayer({ ageConfirmed: true });
  let prev = (await api('/api/me', { cookie })).json.user;

  for (let i = 0; i < 5; i++) {
    const res = await api('/api/spin', { method: 'POST', cookie, body: { bet: BET_TIERS[0] } });
    assert.equal(res.status, 200, res.text);
    const { spin, user } = res.json;
    assert.equal(spin.bet, BET_TIERS[0]);
    assert.equal(spin.wasFreeSpin, true, 'welcome free spins should still be in play');
    assert.equal(user.coins, prev.coins + spin.totalWin);
    assert.equal(user.freeSpins, prev.freeSpins - 1 + spin.scatter.freeSpinsAwarded);
    assert.equal(user.lifetimeSpins, prev.lifetimeSpins + 1);
    assert.ok(user.biggestWin >= prev.biggestWin);
    prev = user;
  }
});

test('an invalid bet falls back to the game default instead of erroring', async () => {
  const { cookie } = await newPlayer({ ageConfirmed: true });

  for (const bad of [{ bet: 12345 }, { bet: -1 }, { bet: 'lots' }, { bet: null }, {}]) {
    const res = await api('/api/spin', { method: 'POST', cookie, body: bad });
    assert.equal(res.status, 200, `bet ${JSON.stringify(bad)} -> ${res.text}`);
    assert.equal(res.json.spin.bet, DEFAULT_BET, `bet ${JSON.stringify(bad)} did not fall back`);
  }

  // A valid tier is honoured as given.
  const good = await api('/api/spin', { method: 'POST', cookie, body: { bet: BET_TIERS[1] } });
  assert.equal(good.status, 200);
  assert.equal(good.json.spin.bet, BET_TIERS[1]);
});

test('an unknown gameId falls back to the default game', async () => {
  const { cookie } = await newPlayer({ ageConfirmed: true });
  const res = await api('/api/spin', {
    method: 'POST', cookie, body: { gameId: 'no-such-game', bet: DEFAULT_BET },
  });
  assert.equal(res.status, 200, res.text);
  const games = (await api('/api/games')).json.games.map((g) => g.id);
  assert.ok(games.includes(res.json.user.lastGame));
});

// --- magic links ------------------------------------------------------------

test('POST /api/magic-link issues a token that /api/magic redeems exactly once', async () => {
  const { cookie, user } = await newPlayer();

  const issued = await api('/api/magic-link', { method: 'POST', cookie });
  assert.equal(issued.status, 200, issued.text);
  assert.equal(typeof issued.json.token, 'string');
  assert.ok(issued.json.token.length > 0);
  assert.match(issued.json.url, /token=/);

  const redeem = await api('/api/magic', { method: 'POST', body: { token: issued.json.token } });
  assert.equal(redeem.status, 200, redeem.text);
  assert.equal(redeem.json.user.id, user.id);
  assert.ok(redeem.cookie, 'redeeming should create a session');

  // The new session really works.
  const me = await api('/api/me', { cookie: redeem.cookie });
  assert.equal(me.status, 200);
  assert.equal(me.json.user.id, user.id);

  // Single use: the same token cannot be redeemed again.
  const again = await api('/api/magic', { method: 'POST', body: { token: issued.json.token } });
  assert.equal(again.status, 401, 'magic tokens must be single-use');
  assert.equal(again.cookie, null);
});

test('POST /api/magic rejects a bogus or missing token with 401', async () => {
  const bogus = await api('/api/magic', { method: 'POST', body: { token: 'not-a-token' } });
  assert.equal(bogus.status, 401);

  const empty = await api('/api/magic', { method: 'POST', body: {} });
  assert.equal(empty.status, 401);
});

test('POST /api/magic-link requires a session', async () => {
  const res = await api('/api/magic-link', { method: 'POST' });
  assert.equal(res.status, 401);
});

// --- misc -------------------------------------------------------------------

test('POST /api/logout ends the session', async () => {
  const { cookie } = await newPlayer();
  assert.equal((await api('/api/me', { cookie })).status, 200);

  const out = await api('/api/logout', { method: 'POST', cookie });
  assert.equal(out.status, 200);
  assert.equal(out.json.ok, true);

  assert.equal((await api('/api/me', { cookie })).status, 401);
});

test('unknown API routes return 404 JSON', async () => {
  const { cookie } = await newPlayer();
  const res = await api('/api/definitely-not-a-route', { cookie });
  assert.equal(res.status, 404);
  assert.equal(res.json.error, 'unknown endpoint');
});

test('a malformed JSON body is tolerated rather than crashing the server', async () => {
  const res = await api('/api/register', { method: 'POST', rawBody: '{not json' });
  // Treated as an empty body -> auto-generated credentials.
  assert.equal(res.status, 200, res.text);
  assert.ok(res.json.generated);

  // Server is still healthy afterwards.
  assert.equal((await api('/api/games')).status, 200);
});

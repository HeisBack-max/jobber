// Build a single self-contained HTML file that runs the whole game offline.
//
// Output: dist/RomaElite.html — no server, no install, no network. Double-click it.
//
// How it works: the real app talks to the server over fetch('/api/...'). Here we
// ship a prelude that (a) contains a faithful client-side port of the slot engine
// and (b) intercepts those /api calls, backing them with localStorage. The app's
// own modules are then bundled in unchanged, so the standalone build and the
// served build run the exact same UI code and the same spin maths.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { GAMES } from '../server/lib/games/index.js';
import { PAYLINES, BET_TIERS, DEFAULT_BET, STARTING_COINS, WELCOME_FREE_SPINS } from '../server/lib/games/shared.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const PUB = path.join(ROOT, 'public');
const DIST = path.join(ROOT, 'dist');

const read = (p) => fs.readFileSync(p, 'utf8');

// --- 1. Bundle the client ES modules --------------------------------------
// These modules only import from each other and have no colliding top-level
// names, so stripping import/export and concatenating in dependency order
// produces a valid single module.
const MODULE_ORDER = ['particles.js', 'symbols.js', 'hosts.js', 'legal.js', 'game.js', 'app.js'];

function stripModuleSyntax(src) {
  return src
    // drop `import ... from './x.js';` (single- and multi-line forms)
    .replace(/^\s*import\s+[\s\S]*?from\s+['"][^'"]+['"];?\s*$/gm, '')
    .replace(/^\s*import\s+['"][^'"]+['"];?\s*$/gm, '')
    // `export function foo` -> `function foo`, `export const x` -> `const x`
    .replace(/^\s*export\s+(?=(function|const|let|class)\b)/gm, '');
}

const bundle = MODULE_ORDER
  .map((f) => `\n/* ===== ${f} ===== */\n${stripModuleSyntax(read(path.join(PUB, 'js', f)))}`)
  .join('\n');

// --- 2. Serialise the game configs (reel strips included) ------------------
// In the served build reel strips stay server-side; offline there is no server
// to hide them from, so they ship with the file.
const gamesJson = JSON.stringify(
  Object.fromEntries(Object.entries(GAMES).map(([id, g]) => [id, {
    id: g.id, theme: g.theme, symbols: g.symbols, paytable: g.paytable,
    scatterPay: g.scatterPay, scatterFreeSpins: g.scatterFreeSpins,
    freeSpinMultiplier: g.freeSpinMultiplier, reelStrips: g.reelStrips,
    betTiers: g.betTiers, defaultBet: g.defaultBet,
    startingCoins: g.startingCoins, welcomeFreeSpins: g.welcomeFreeSpins,
  }]))
);

// --- 3. The offline prelude: engine + store + fetch shim -------------------
const prelude = `
/* Roma Elite — offline runtime. Mirrors server/lib/slot-engine.js exactly. */
(function () {
  var GAMES = ${gamesJson};
  var PAYLINES = ${JSON.stringify(PAYLINES)};
  var REELS = 5, ROWS = 4;
  var BET_TIERS = ${JSON.stringify(BET_TIERS)}, DEFAULT_BET = ${DEFAULT_BET};
  var STARTING_COINS = ${STARTING_COINS}, WELCOME_FREE_SPINS = ${WELCOME_FREE_SPINS};
  var TOPUP_AMOUNT = 5000, TOPUP_THRESHOLD = 500, TOPUP_COOLDOWN_MS = 1000 * 60 * 30;

  // --- storage (localStorage, with an in-memory fallback for locked-down file://)
  var mem = {};
  var LS = (function () {
    try { var k = '__re_t'; localStorage.setItem(k, '1'); localStorage.removeItem(k); return localStorage; }
    catch (e) { return { getItem: function (k) { return mem[k] || null; },
                         setItem: function (k, v) { mem[k] = String(v); },
                         removeItem: function (k) { delete mem[k]; } }; }
  })();
  var KEY = 'romaEliteSave.v1';
  function load() { try { return JSON.parse(LS.getItem(KEY)) || null; } catch (e) { return null; } }
  function save(u) { try { LS.setItem(KEY, JSON.stringify(u)); } catch (e) {} }

  // --- crypto-strength RNG
  function rng() {
    var a = new Uint32Array(2);
    (self.crypto || self.msCrypto).getRandomValues(a);
    return (a[0] * 4294967296 + a[1]) / 18446744073709552000;
  }

  // --- engine (identical logic to the server module)
  function spinReel(strip) {
    var stop = Math.floor(rng() * strip.length) % strip.length, col = [];
    for (var r = 0; r < ROWS; r++) col.push(strip[(stop + r) % strip.length]);
    return col;
  }
  function spinGrid(game) {
    var cols = [];
    for (var r = 0; r < REELS; r++) cols.push(spinReel(game.reelStrips[r]));
    return cols;
  }
  function evaluateLine(cols, line, paytable) {
    var first = cols[0][line[0]];
    if (first === 'SCATTER') return null;
    var base = first;
    if (base === 'WILD') {
      for (var r = 1; r < REELS; r++) {
        var s = cols[r][line[r]];
        if (s !== 'WILD' && s !== 'SCATTER') { base = s; break; }
      }
    }
    var positions = [], count = 0;
    for (var i = 0; i < REELS; i++) {
      var sym = cols[i][line[i]];
      if (sym === base || sym === 'WILD') { count++; positions.push([i, line[i]]); }
      else break;
    }
    if (count < 3) return null;
    var t = paytable[base];
    if (!t || !t[count]) return null;
    return { symbol: base, count: count, positions: positions.slice(0, count) };
  }
  function evaluateSpin(game, cols, bet, isFree) {
    var lineBet = bet / PAYLINES.length, lineWins = [], lineTotal = 0;
    for (var i = 0; i < PAYLINES.length; i++) {
      var res = evaluateLine(cols, PAYLINES[i], game.paytable);
      if (!res) continue;
      var amt = Math.round(game.paytable[res.symbol][res.count] * lineBet * (isFree ? game.freeSpinMultiplier : 1));
      lineTotal += amt;
      lineWins.push({ line: i + 1, symbol: res.symbol, count: res.count, positions: res.positions, amount: amt });
    }
    var sp = [];
    for (var r = 0; r < REELS; r++) for (var row = 0; row < ROWS; row++)
      if (cols[r][row] === 'SCATTER') sp.push([r, row]);
    var scatterWin = 0, freeSpins = 0;
    if (sp.length >= 3) {
      var capped = Math.min(sp.length, 5);
      scatterWin = Math.round((game.scatterPay[capped] || 0) * bet);
      freeSpins = game.scatterFreeSpins[capped] || 0;
    }
    return { columns: cols, bet: bet, lineWins: lineWins,
             scatter: { count: sp.length, positions: sp, win: scatterWin, freeSpinsAwarded: freeSpins },
             totalWin: lineTotal + scatterWin };
  }

  // --- player record
  var RANKS = [[0,'Plebeian'],[50,'Legionnaire'],[200,'Centurion'],[500,'Tribune'],
               [1200,'Praetor'],[3000,'Senator'],[7000,'Consul'],[15000,'Imperator']];
  function rankFor(n) { var r = RANKS[0][1]; for (var i=0;i<RANKS.length;i++) if (n>=RANKS[i][0]) r=RANKS[i][1]; return r; }
  var ADJ=['Golden','Iron','Marble','Crimson','Imperial','Noble','Bronze','Radiant'];
  var NOUN=['Eagle','Legion','Chariot','Laurel','Consul','Aurelius','Maximus','Valeria'];
  function pick(a){ return a[Math.floor(rng()*a.length)]; }
  function newUser(username) {
    return { id:'u_'+Math.floor(rng()*1e12).toString(16), username: username || (pick(ADJ)+pick(NOUN)+(100+Math.floor(rng()*899))),
             password: null, createdAt: Date.now(), ageConfirmed:false,
             coins: STARTING_COINS, freeSpins: WELCOME_FREE_SPINS, lifetimeSpins:0,
             prestige:0, biggestWin:0, lastGame:'roma-elite' };
  }
  function pub(u) {
    return { id:u.id, username:u.username, createdAt:u.createdAt, ageConfirmed:u.ageConfirmed,
             coins:u.coins, freeSpins:u.freeSpins, lifetimeSpins:u.lifetimeSpins, prestige:u.prestige,
             biggestWin:u.biggestWin, rank:rankFor(u.lifetimeSpins), lastGame:u.lastGame };
  }
  function publicCfg(g) {
    return { id:g.id, theme:g.theme, symbols:g.symbols, paytable:g.paytable, scatterPay:g.scatterPay,
             scatterFreeSpins:g.scatterFreeSpins, freeSpinMultiplier:g.freeSpinMultiplier,
             betTiers:g.betTiers, defaultBet:g.defaultBet };
  }

  // --- fetch shim: answer /api/* locally, pass anything else through
  var realFetch = self.fetch ? self.fetch.bind(self) : null;
  function reply(status, body) {
    return Promise.resolve(new Response(JSON.stringify(body),
      { status: status, headers: { 'Content-Type': 'application/json' } }));
  }
  self.fetch = function (input, init) {
    var url = typeof input === 'string' ? input : (input && input.url) || '';
    if (url.indexOf('/api/') === -1) return realFetch ? realFetch(input, init) : Promise.reject(new Error('offline'));
    var route = url.slice(url.indexOf('/api/'));
    var body = {};
    try { if (init && init.body) body = JSON.parse(init.body); } catch (e) {}
    var u = load();

    if (route === '/api/games') {
      var list = [], cfgs = {};
      for (var id in GAMES) {
        list.push({ id: id, name: GAMES[id].theme.name, tagline: GAMES[id].theme.tagline, palette: GAMES[id].theme.palette });
        cfgs[id] = publicCfg(GAMES[id]);
      }
      return reply(200, { games: list, configs: cfgs });
    }
    if (route === '/api/register') {
      var name = (body.username || '').trim();
      var pass = (body.password || '').trim();
      if (name && !/^[\\w]{3,20}$/.test(name)) return reply(400, { error: 'Username must be 3–20 letters, numbers or underscore.' });
      // Same rule as the server: a password-only account is just as loginable.
      if (pass && pass.length < 6) return reply(400, { error: 'Password must be at least 6 characters.' });
      var nu = newUser(name || null);
      var pw = pass || Math.floor(rng() * 1e10).toString(36);
      nu.password = pw;
      save(nu);
      return reply(200, { user: pub(nu), generated: (name || pass) ? null : { username: nu.username, password: pw } });
    }
    if (route === '/api/login') {
      if (!u) return reply(401, { error: 'No saved account on this device yet.' });
      if ((body.username||'').toLowerCase() !== u.username.toLowerCase() || body.password !== u.password)
        return reply(401, { error: 'Invalid username or password.' });
      return reply(200, { user: pub(u) });
    }
    if (route === '/api/magic') {
      if (!u) return reply(401, { error: 'This login link is invalid or has expired.' });
      return reply(200, { user: pub(u) });
    }
    if (!u) return reply(401, { error: 'not authenticated' });

    if (route === '/api/me') return reply(200, { user: pub(u) });
    if (route === '/api/logout') { try { LS.removeItem(KEY); } catch (e) {} return reply(200, { ok: true }); }
    if (route === '/api/confirm-age') { u.ageConfirmed = true; save(u); return reply(200, { user: pub(u) }); }
    if (route === '/api/magic-link') return reply(200, { token: 'offline', url: '?token=offline' });
    if (route === '/api/topup') {
      if (u.coins > TOPUP_THRESHOLD) return reply(400, { error: 'Top-up is only available when you are low on coins.' });
      if (u.lastTopupAt && Date.now() - u.lastTopupAt < TOPUP_COOLDOWN_MS) {
        var mins = Math.ceil((TOPUP_COOLDOWN_MS - (Date.now() - u.lastTopupAt)) / 60000);
        return reply(429, { error: 'Next free top-up available in ' + mins + ' min.' });
      }
      u.coins += TOPUP_AMOUNT; u.lastTopupAt = Date.now(); save(u);
      return reply(200, { user: pub(u), granted: TOPUP_AMOUNT });
    }
    if (route === '/api/spin') {
      if (!u.ageConfirmed) return reply(403, { error: 'Please confirm you are 18+ first.' });
      var game = GAMES[body.gameId] || GAMES['roma-elite'];
      var bet = Number(body.bet);
      if (BET_TIERS.indexOf(bet) === -1) bet = DEFAULT_BET;
      var free = u.freeSpins > 0;
      if (free) u.freeSpins -= 1;
      else {
        if (u.coins < bet) return reply(400, { error: 'Not enough coins for that bet.', code: 'INSUFFICIENT' });
        u.coins -= bet;
      }
      var result = evaluateSpin(game, spinGrid(game), bet, free);
      u.coins += result.totalWin;
      u.freeSpins += result.scatter.freeSpinsAwarded;
      u.lifetimeSpins += 1;
      u.lastGame = game.id;
      if (result.totalWin > (u.biggestWin || 0)) u.biggestWin = result.totalWin;
      save(u);
      return reply(200, { spin: { columns: result.columns, lineWins: result.lineWins, scatter: result.scatter,
                                  totalWin: result.totalWin, bet: result.bet, wasFreeSpin: free },
                          user: pub(u) });
    }
    return reply(404, { error: 'unknown endpoint' });
  };
})();
`;

// --- 4. Assemble the HTML --------------------------------------------------
let html = read(path.join(PUB, 'index.html'));
const css = read(path.join(PUB, 'css', 'styles.css'));

html = html
  // fully offline: no webfont fetch (the stack already has serif/sans fallbacks)
  .replace(/<link rel="preconnect"[\s\S]*?crossorigin \/>/, '')
  .replace(/<link href="https:\/\/fonts\.googleapis\.com[\s\S]*?\/>/, '')
  .replace('<link rel="stylesheet" href="/css/styles.css" />', `<style>\n${css}\n</style>`)
  .replace('<script type="module" src="/js/app.js"></script>',
    `<script>${prelude}</script>\n<script type="module">${bundle}</script>`)
  .replace('<title>Roma Elite — Social Slots (Free to Play)</title>',
    '<title>Roma Elite — Social Slots (Offline, Free to Play)</title>');

fs.mkdirSync(DIST, { recursive: true });
const out = path.join(DIST, 'RomaElite.html');
fs.writeFileSync(out, html);

const kb = (fs.statSync(out).size / 1024).toFixed(0);
console.log(`built ${path.relative(ROOT, out)}  (${kb} KB, self-contained)`);

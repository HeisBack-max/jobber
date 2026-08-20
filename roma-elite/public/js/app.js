// Roma Elite — front-end orchestration: auth/onboarding flow, game state, and UI.
import { buildReels, setGrid, spinTo, showWins, clearWins } from './game.js';
import { setAccent, burst } from './particles.js';
import { TERMS_HTML } from './legal.js';
import { hostArt } from './hosts.js';
import { symUse } from './symbols.js';

const $ = (id) => document.getElementById(id);
const api = async (path, body) => {
  const res = await fetch('/api' + path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body || {}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.error || 'Request failed'), { data, status: res.status });
  return data;
};

const state = {
  user: null,
  configs: {},
  games: [],
  gameId: 'roma-elite',
  bet: 200,
  spinning: false,
  auto: false,
};

// ---------------------------------------------------------------- overlays
function show(id) { $(id).classList.remove('hidden'); }
function hide(id) { $(id).classList.add('hidden'); }
function toast(msg, ms = 2600) {
  const t = $('toast'); t.textContent = msg; t.classList.add('show');
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove('show'), ms);
}

// ---------------------------------------------------------------- theming
function applyTheme(gameId) {
  const cfg = state.configs[gameId];
  if (!cfg) return;
  const p = cfg.theme.palette;
  const root = document.documentElement.style;
  for (const [k, v] of Object.entries(p)) root.setProperty('--' + k, v);
  setAccent(p.accent);
  $('brandName').innerHTML = `${cfg.theme.name.toUpperCase()}<small>SOCIAL · FOR FUN ONLY</small>`;
  $('gameTitle').textContent = cfg.theme.tagline.toUpperCase();
  document.getElementById('skyline').className = 'skyline scenery-' + cfg.theme.scenery;
  document.getElementById('skylineFar').className = 'skyline far scenery-' + cfg.theme.scenery;
  $('freeSpinFlag').textContent = `FREE SPIN ×${cfg.freeSpinMultiplier}`;
}

// Paint sprite-backed art that can only render once the sprite is injected.
function paintSpriteRefs() {
  $('brandCrest').innerHTML = symUse('WILD');
  const laurel = $('machine').querySelector('.laurel');
  if (laurel) laurel.innerHTML = symUse('SCATTER');
}

// ---------------------------------------------------------------- HUD
function renderHUD() {
  const u = state.user; if (!u) return;
  $('statCoins').textContent = u.coins.toLocaleString();
  $('statFree').textContent = u.freeSpins.toLocaleString();
  $('statRank').textContent = u.rank;
  const sub = $('spinSub');
  if (u.freeSpins > 0) { sub.textContent = `FREE ×${u.freeSpins}`; sub.style.color = 'var(--crimson)'; }
  else { sub.textContent = `BET ${state.bet}`; sub.style.color = ''; }
  $('betVal').textContent = state.bet.toLocaleString();
}

function setUser(u) { state.user = u; renderHUD(); }

// ---------------------------------------------------------------- boot
async function boot() {
  const data = await api('/games');
  state.games = data.games;
  state.configs = data.configs;

  // Magic-link token in URL?
  const params = new URLSearchParams(location.search);
  const token = params.get('token');

  // Age gate first (persisted per browser).
  const ageOk = localStorage.getItem('re_age_ok') === '1';

  applyTheme(state.gameId);
  renderGameCards();
  renderPaytable();

  if (token) {
    try {
      const r = await api('/magic', { token });
      history.replaceState({}, '', location.pathname);
      afterAuth(r.user, false);
      return;
    } catch (e) { toast(e.message); }
  }

  // Try existing session.
  try {
    const me = await api('/me');
    if (ageOk) { afterAuth(me.user, false); return; }
    state.user = me.user; // will re-confirm age below
  } catch { /* not logged in */ }

  if (!ageOk) show('ageGate');
  else showAuthOrGame();
}

function showAuthOrGame() {
  if (state.user) afterAuth(state.user, false);
  else { hide('ageGate'); show('authGate'); }
}

// ---------------------------------------------------------------- age gate
$('ageYes').onclick = async () => {
  localStorage.setItem('re_age_ok', '1');
  hide('ageGate');
  if (state.user) {
    try { const r = await api('/confirm-age', {}); setUser(r.user); } catch {}
    afterAuth(state.user, false);
  } else {
    show('authGate');
  }
};
$('ageNo').onclick = () => {
  document.body.innerHTML = '<div style="display:grid;place-items:center;height:100vh;text-align:center;font-family:Georgia,serif;color:#e8c15a;padding:24px">' +
    '<div><div style="font-size:52px">🏛️</div><h1>Come back when you are 18+</h1>' +
    '<p style="opacity:0.7;margin-top:10px">Roma Elite is an adults-only entertainment game.</p></div></div>';
};

// ---------------------------------------------------------------- auth tabs
document.querySelectorAll('#authTabs button').forEach((b) => {
  b.onclick = () => {
    document.querySelectorAll('#authTabs button').forEach((x) => x.classList.remove('active'));
    b.classList.add('active');
    for (const t of ['Quick', 'Register', 'Login']) hide('tab' + t);
    show('tab' + b.dataset.tab.charAt(0).toUpperCase() + b.dataset.tab.slice(1));
    $('authError').textContent = '';
  };
});

async function confirmAgeServer() {
  try { const r = await api('/confirm-age', {}); setUser(r.user); } catch {}
}

$('quickPlay').onclick = async () => {
  $('authError').textContent = '';
  try {
    const r = await api('/register', { source: 'quick' });
    setUser(r.user);
    await confirmAgeServer();
    if (r.generated) {
      $('credUser').textContent = r.generated.username;
      $('credPass').textContent = r.generated.password;
      hide('authGate'); show('credsGate');
    } else { afterAuth(r.user, true); }
  } catch (e) { $('authError').textContent = e.message; }
};

$('credsContinue').onclick = () => { hide('credsGate'); afterAuth(state.user, true); };

$('registerBtn').onclick = async () => {
  $('authError').textContent = '';
  try {
    const r = await api('/register', {
      username: $('regUser').value.trim(), password: $('regPass').value, source: 'register',
    });
    setUser(r.user); await confirmAgeServer();
    afterAuth(r.user, true);
  } catch (e) { $('authError').textContent = e.message; }
};

$('loginBtn').onclick = async () => {
  $('authError').textContent = '';
  try {
    const r = await api('/login', { username: $('loginUser').value.trim(), password: $('loginPass').value });
    setUser(r.user); await confirmAgeServer();
    afterAuth(r.user, false);
  } catch (e) { $('authError').textContent = e.message; }
};

// ---------------------------------------------------------------- after auth
function afterAuth(user, isNew) {
  setUser(user);
  hide('authGate'); hide('ageGate'); hide('credsGate');
  state.gameId = user.lastGame || 'roma-elite';
  applyTheme(state.gameId);
  buildReels(state.configs[state.gameId]);
  paintSpriteRefs();
  // idle grid
  const cfg = state.configs[state.gameId];
  setGrid(idleGrid(cfg));
  show('topbar'); show('stage');
  renderHUD();
  renderPaytable();

  if (isNew && user.freeSpins > 0) {
    $('welcomeSpins').textContent = user.freeSpins;
    show('welcomeGate');
  }
}

$('welcomeStart').onclick = () => {
  hide('welcomeGate');
  // celebratory burst
  for (let i = 0; i < 6; i++) setTimeout(() => burst(0.5, 0.4, 30, 'gold'), i * 90);
};

function idleGrid(cfg) {
  const ids = Object.keys(cfg.symbols).filter((s) => s !== 'SCATTER' && s !== 'WILD');
  const cols = [];
  for (let r = 0; r < 5; r++) {
    const col = [];
    for (let row = 0; row < 4; row++) col.push(ids[(r * 4 + row) % ids.length]);
    cols.push(col);
  }
  return cols;
}

// ---------------------------------------------------------------- bet
$('betUp').onclick = () => changeBet(1);
$('betDown').onclick = () => changeBet(-1);
function changeBet(dir) {
  const tiers = state.configs[state.gameId].betTiers;
  let i = tiers.indexOf(state.bet);
  if (i < 0) i = tiers.indexOf(200);
  i = Math.max(0, Math.min(tiers.length - 1, i + dir));
  state.bet = tiers[i];
  renderHUD();
}

// ---------------------------------------------------------------- spin
$('spinBtn').onclick = () => doSpin();
$('autoBtn').onclick = () => {
  state.auto = !state.auto;
  $('autoBtn').classList.toggle('active', state.auto);
  if (state.auto && !state.spinning) doSpin();
};

async function doSpin() {
  if (state.spinning) return;
  const u = state.user;
  if (u.freeSpins === 0 && u.coins < state.bet) {
    toast('Not enough coins — grab a free top-up from the menu.');
    state.auto = false; $('autoBtn').classList.remove('active');
    return;
  }
  state.spinning = true;
  const btn = $('spinBtn'); btn.disabled = true; btn.classList.add('spinning');
  $('winBanner').classList.remove('show');
  clearWins();
  $('winText').textContent = '';

  try {
    const r = await api('/spin', { gameId: state.gameId, bet: state.bet });
    const wasFree = r.spin.wasFreeSpin;
    $('freeSpinFlag').classList.toggle('hidden', !wasFree);

    await spinTo(r.spin.columns);
    setUser(r.user);

    if (r.spin.totalWin > 0) {
      showWins(r.spin.lineWins, r.spin.scatter);
      presentWin(r.spin);
    } else {
      $('winText').textContent = wasFree ? 'Free spin — no win this time.' : 'No win — spin again!';
    }
    if (r.spin.scatter.freeSpinsAwarded > 0) {
      await showBonusWinner(r.spin.scatter.freeSpinsAwarded);
    }
  } catch (e) {
    toast(e.message || 'Spin failed');
    state.auto = false; $('autoBtn').classList.remove('active');
  } finally {
    state.spinning = false;
    btn.disabled = false; btn.classList.remove('spinning');
    $('freeSpinFlag').classList.add('hidden');
    if (state.auto) setTimeout(() => { if (state.auto) doSpin(); }, 900);
  }
}

function presentWin(spin) {
  const mult = spin.totalWin / Math.max(spin.bet, 1);
  let kind = 'WIN';
  if (mult >= 50) kind = 'MEGA WIN';
  else if (mult >= 20) kind = 'EPIC WIN';
  else if (mult >= 8) kind = 'BIG WIN';

  const banner = $('winBanner');
  $('winKind').textContent = kind;
  // count-up
  const amtEl = $('winAmt');
  const target = spin.totalWin;
  const start = performance.now();
  const dur = kind === 'WIN' ? 500 : 1100;
  banner.classList.remove('show'); void banner.offsetHeight; banner.classList.add('show');
  if (mult >= 8) {
    for (let i = 0; i < 10; i++) setTimeout(() => burst(0.5, 0.42, 26, 'gold'), i * 80);
  }
  function step(now) {
    const t = Math.min(1, (now - start) / dur);
    amtEl.textContent = Math.floor(target * (1 - Math.pow(1 - t, 3))).toLocaleString();
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);

  const lines = spin.lineWins.length;
  $('winText').textContent = `${lines ? lines + ' line' + (lines > 1 ? 's' : '') : ''}` +
    `${spin.scatter.count >= 3 ? (lines ? ' + ' : '') + 'Scatter' : ''} · +${target.toLocaleString()} coins`;
}

// ---------------------------------------------------------------- bonus winner
function showBonusWinner(freeSpins) {
  const cfg = state.configs[state.gameId];
  const scatter = cfg.symbols.SCATTER;
  $('bonusHostArt').innerHTML = hostArt(cfg.theme.bonusHost);
  $('bonusHostName').textContent = scatter.name;
  $('bonusSpins').textContent = freeSpins;
  $('bonusMult').textContent = `Line wins pay ×${cfg.freeSpinMultiplier} during the bonus`;
  show('bonusGate');
  // celebratory bursts
  for (let i = 0; i < 14; i++) setTimeout(() => burst(0.5, 0.4, 24, 'gold'), i * 70);
  return new Promise((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) return; settled = true;
      hide('bonusGate'); resolve();
    };
    $('bonusStart').onclick = finish;
    // Auto-advance (esp. for auto-spin) after a beat.
    setTimeout(finish, state.auto ? 2600 : 6000);
  });
}

// ---------------------------------------------------------------- game switch
function renderGameCards() {
  const el = $('gameCards'); el.innerHTML = '';
  for (const g of state.games) {
    const cfg = state.configs[g.id];
    const card = document.createElement('div');
    card.className = 'game-card' + (g.id === state.gameId ? ' active' : '');
    // Card art is a static swatch (the live sprite belongs to the active game only).
    card.innerHTML = `<div class="gc-crest" style="--c1:${cfg.theme.palette.accent};--c2:${cfg.theme.palette.accent2}"></div>
      <div class="gc-name">${g.name}</div><div class="gc-tag">${g.tagline}</div>`;
    card.onclick = () => switchGame(g.id);
    el.appendChild(card);
  }
}

function switchGame(id) {
  if (state.spinning) return;
  state.gameId = id;
  applyTheme(id);
  buildReels(state.configs[id]);
  paintSpriteRefs();
  setGrid(idleGrid(state.configs[id]));
  const tiers = state.configs[id].betTiers;
  if (!tiers.includes(state.bet)) state.bet = state.configs[id].defaultBet;
  renderGameCards(); renderPaytable(); renderHUD();
  hide('gamesGate');
  toast('Now playing: ' + state.configs[id].theme.name);
}

// ---------------------------------------------------------------- paytable
function renderPaytable() {
  const cfg = state.configs[state.gameId]; if (!cfg) return;
  $('ptTitle').textContent = cfg.theme.name + ' — Paytable';
  const grid = $('ptGrid'); grid.innerHTML = '';
  const order = Object.keys(cfg.paytable);
  for (const id of order) {
    const s = cfg.symbols[id]; const p = cfg.paytable[id];
    const row = document.createElement('div');
    row.className = 'pt-row';
    row.innerHTML = `<span class="g">${symUse(id)}</span><div class="info">
      <div class="nm">${s.name}${id === 'WILD' ? ' · Wild' : ''}</div>
      <div class="pay">3: ${p[3]} · 4: ${p[4]} · 5: ${p[5]}</div></div>`;
    grid.appendChild(row);
  }
  const sc = cfg.symbols.SCATTER;
  const scatterRow = document.createElement('div');
  scatterRow.className = 'pt-row pt-special';
  scatterRow.innerHTML = `<span class="g">${symUse('SCATTER')}</span><div class="info">
    <div class="nm">${sc.name} · Scatter</div>
    <div class="pay">3+ anywhere pays on total bet &amp; awards ${cfg.scatterFreeSpins[3]}–${cfg.scatterFreeSpins[5]} free spins (×${cfg.freeSpinMultiplier})</div></div>`;
  grid.appendChild(scatterRow);
}

// ---------------------------------------------------------------- menu / misc
$('btnGames').onclick = () => { renderGameCards(); show('gamesGate'); };
$('btnPaytable').onclick = () => { renderPaytable(); show('paytableGate'); };
$('btnMenu').onclick = () => {
  const u = state.user;
  $('menuUser').textContent = u.username;
  $('menuCoins').textContent = u.coins.toLocaleString();
  $('menuRank').textContent = `${u.rank} · Prestige ${u.prestige}`;
  $('menuSpins').textContent = u.lifetimeSpins.toLocaleString();
  $('menuBig').textContent = u.biggestWin.toLocaleString() + ' coins';
  show('menuGate');
};
$('menuTopup').onclick = async () => {
  try { const r = await api('/topup', {}); setUser(r.user); toast(`+${r.granted.toLocaleString()} free coins!`); burst(0.5, 0.5, 30); }
  catch (e) { toast(e.message); }
};
$('menuMagic').onclick = async () => {
  try {
    const r = await api('/magic-link', {});
    const url = location.origin + r.url;
    await navigator.clipboard.writeText(url).catch(() => {});
    toast('Magic login link copied to clipboard');
  } catch (e) { toast(e.message); }
};
$('menuLogout').onclick = async () => {
  try { await api('/logout', {}); } catch {}
  location.reload();
};

// terms / responsible play
function openTerms() { $('termsBody').innerHTML = TERMS_HTML; hide('menuGate'); show('termsGate'); }
$('footerTerms').onclick = openTerms;
$('footerResp').onclick = openTerms;
$('menuResp').onclick = openTerms;
$('menuTermsBtn').onclick = openTerms;
$('ageTerms').onclick = () => { $('termsBody').innerHTML = TERMS_HTML; show('termsGate'); };

// generic close buttons
document.querySelectorAll('[data-close]').forEach((b) => { b.onclick = () => hide(b.dataset.close); });
document.querySelectorAll('.overlay').forEach((ov) => {
  ov.addEventListener('click', (e) => {
    if (e.target === ov && !['ageGate', 'authGate', 'welcomeGate', 'credsGate'].includes(ov.id)) hide(ov.id);
  });
});

// keyboard: space to spin
addEventListener('keydown', (e) => {
  if (e.code === 'Space' && !state.spinning && $('stage').classList.contains('hidden') === false) {
    const anyOverlay = [...document.querySelectorAll('.overlay')].some((o) => !o.classList.contains('hidden'));
    if (!anyOverlay) { e.preventDefault(); doSpin(); }
  }
});

boot().catch((e) => { console.error(e); toast('Failed to load game: ' + e.message); });

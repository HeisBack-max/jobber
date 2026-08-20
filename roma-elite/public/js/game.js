// Slot machine rendering + spin animation. The server decides outcomes; this
// module only animates reels to the grid it is given and presents wins.
//
// Performance notes:
//  - Symbols are <use> refs into one shared SVG sprite (shared gradients/filters).
//  - Reels animate with transform only (GPU compositing), never top/height.
//  - Cell DOM is reused across spins where possible instead of full re-creation.
import { burst } from './particles.js';
import { buildSprite, symUse } from './symbols.js';

const REELS = 5, ROWS = 4;
const reelsEl = document.getElementById('reels');
const winlinesEl = document.getElementById('winlines');

let symbols = {};
let symbolPool = [];   // ids eligible to appear as filler while spinning

function cellPx() {
  const v = getComputedStyle(document.documentElement).getPropertyValue('--cell');
  return parseInt(v, 10) || 84;
}

function randomSymbolId() {
  return symbolPool[(Math.random() * symbolPool.length) | 0];
}

// Build the empty reel DOM + inject the game's symbol sprite.
export function buildReels(gameConfig) {
  symbols = gameConfig.symbols;
  symbolPool = Object.keys(symbols).filter((s) => s !== 'SCATTER');

  const old = document.getElementById('symbol-sprite');
  if (old) old.remove();
  document.body.insertAdjacentHTML('afterbegin', buildSprite(gameConfig));

  reelsEl.innerHTML = '';
  for (let r = 0; r < REELS; r++) {
    const reel = document.createElement('div');
    reel.className = 'reel';
    reel.style.setProperty('--reel-i', r);
    const strip = document.createElement('div');
    strip.className = 'reel-strip';
    reel.appendChild(strip);
    reelsEl.appendChild(reel);
  }
  clearWins();
}

function makeCell(id) {
  const c = document.createElement('div');
  // Tier drives the cell's richness (premium symbols sit on a warmer, brighter well).
  c.className = 'cell tier-' + ((symbols[id] && symbols[id].tier) || 'low');
  c.dataset.sym = id;
  c.innerHTML = symUse(id);
  return c;
}

function fillStrip(strip, ids) {
  strip.innerHTML = '';
  const frag = document.createDocumentFragment();
  for (const id of ids) frag.appendChild(makeCell(id));
  strip.appendChild(frag);
}

// Instantly show a grid (columns[reel][row]) with no animation.
export function setGrid(columns) {
  for (let r = 0; r < REELS; r++) {
    const strip = reelsEl.children[r].firstChild;
    strip.style.transition = 'none';
    strip.style.transform = 'translate3d(0,0,0)';
    fillStrip(strip, columns[r]);
  }
}

// Animate all reels spinning, landing on `columns`. Resolves when settled.
// Reels stop left-to-right with a slight overshoot bounce; the last two reels
// get an "anticipation" beat when a bonus symbol is still live.
export function spinTo(columns) {
  clearWins();
  const cp = cellPx();
  const BUFFER = 14;
  const done = [];

  // Anticipation: if reels 0..2 already hold 2+ scatters, slow the later reels.
  let earlyScatters = 0;
  for (let r = 0; r < 3; r++) for (let row = 0; row < ROWS; row++) {
    if (columns[r][row] === 'SCATTER') earlyScatters++;
  }
  const anticipate = earlyScatters >= 2;

  for (let r = 0; r < REELS; r++) {
    const reel = reelsEl.children[r];
    const strip = reel.firstChild;
    reel.classList.add('spinning');

    const filler = [];
    for (let i = 0; i < BUFFER; i++) filler.push(randomSymbolId());
    fillStrip(strip, filler.concat(columns[r]));

    strip.style.transition = 'none';
    strip.style.transform = 'translate3d(0,0,0)';
    void strip.offsetHeight; // reflow so the transition takes effect

    let duration = 620 + r * 145;
    if (anticipate && r >= 3) {
      duration += 950;
      reel.classList.add('anticipate');
    }
    const travel = BUFFER * cp;
    strip.style.transition = `transform ${duration}ms cubic-bezier(0.12, 0.72, 0.18, 1.04)`;
    strip.style.transform = `translate3d(0,${-travel}px,0)`;

    done.push(new Promise((resolve) => {
      let settled = false;
      const onEnd = () => {
        if (settled) return; settled = true;
        reel.classList.remove('spinning', 'anticipate');
        strip.style.transition = 'none';
        strip.style.transform = 'translate3d(0,0,0)';
        fillStrip(strip, columns[r]);
        // Land pop on the freshly-settled cells.
        reel.classList.remove('landed'); void reel.offsetWidth; reel.classList.add('landed');
        resolve();
      };
      strip.addEventListener('transitionend', onEnd, { once: true });
      setTimeout(onEnd, duration + 240); // safety net
    }));
  }
  return Promise.all(done);
}

function cellAt(reel, row) {
  const strip = reelsEl.children[reel]?.firstChild;
  return strip ? strip.children[row] : null;
}

// Highlight winning cells and draw the winning paylines.
export function showWins(lineWins, scatter) {
  clearWins();
  if ((!lineWins || !lineWins.length) && (!scatter || scatter.count < 3)) return;

  const winningCells = new Set();
  const paths = [];

  for (const w of lineWins) {
    for (const [reel, row] of w.positions) winningCells.add(reel + ':' + row);
    paths.push(w.positions.map(([reel, row]) => {
      const x = ((reel + 0.5) / REELS) * 100;
      const y = ((row + 0.5) / ROWS) * 100;
      return `${x},${y}`;
    }).join(' '));
  }
  if (scatter && scatter.count >= 3) {
    for (const [reel, row] of scatter.positions) winningCells.add(reel + ':' + row);
  }

  for (let r = 0; r < REELS; r++) {
    for (let row = 0; row < ROWS; row++) {
      const cell = cellAt(r, row);
      if (!cell) continue;
      cell.classList.add(winningCells.has(r + ':' + row) ? 'win' : 'dim');
    }
  }

  const ns = 'http://www.w3.org/2000/svg';
  const frag = document.createDocumentFragment();
  for (const d of paths) {
    // Draw each line twice: a soft wide glow under a crisp bright core.
    for (const [w, o, cls] of [[3.4, 0.35, 'wl-glow'], [1.2, 0.95, 'wl-core']]) {
      const pl = document.createElementNS(ns, 'polyline');
      pl.setAttribute('points', d);
      pl.setAttribute('fill', 'none');
      pl.setAttribute('stroke', 'var(--win)');
      pl.setAttribute('stroke-width', w);
      pl.setAttribute('opacity', o);
      pl.setAttribute('stroke-linecap', 'round');
      pl.setAttribute('stroke-linejoin', 'round');
      pl.setAttribute('vector-effect', 'non-scaling-stroke');
      pl.setAttribute('class', cls);
      frag.appendChild(pl);
    }
  }
  winlinesEl.appendChild(frag);

  // Coin bursts from a sample of winning cells (capped for performance).
  let i = 0;
  for (const key of winningCells) {
    if (i++ % 3 !== 0 || i > 12) continue;
    const [r, row] = key.split(':').map(Number);
    const el = cellAt(r, row); if (!el) continue;
    const cr = el.getBoundingClientRect();
    burst((cr.left + cr.width / 2) / innerWidth, (cr.top + cr.height / 2) / innerHeight, 14, 'gold');
  }
}

export function clearWins() {
  winlinesEl.textContent = '';
  for (let r = 0; r < REELS; r++) {
    for (let row = 0; row < ROWS; row++) {
      cellAt(r, row)?.classList.remove('win', 'dim');
    }
  }
}

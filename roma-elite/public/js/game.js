// Slot machine rendering + spin animation. The server decides outcomes; this
// module only animates reels to the grid it is given and presents wins.
import { burst } from './particles.js';

const REELS = 5, ROWS = 4;
const reelsEl = document.getElementById('reels');
const winlinesEl = document.getElementById('winlines');

let symbols = {};      // id -> {glyph,...}
let currentGrid = null;

function cellPx() {
  const v = getComputedStyle(document.documentElement).getPropertyValue('--cell');
  return parseInt(v, 10) || 84;
}

function glyph(id) { return (symbols[id] && symbols[id].glyph) || '❔'; }

function randomSymbolId() {
  const ids = Object.keys(symbols).filter((s) => s !== 'SCATTER');
  return ids[Math.floor(Math.random() * ids.length)];
}

// Build the empty reel DOM for a game config.
export function buildReels(gameConfig) {
  symbols = gameConfig.symbols;
  reelsEl.innerHTML = '';
  for (let r = 0; r < REELS; r++) {
    const reel = document.createElement('div');
    reel.className = 'reel';
    const strip = document.createElement('div');
    strip.className = 'reel-strip';
    reel.appendChild(strip);
    reelsEl.appendChild(reel);
  }
  clearWins();
}

function makeCell(id) {
  const c = document.createElement('div');
  c.className = 'cell';
  c.dataset.sym = id;
  c.textContent = glyph(id);
  return c;
}

// Instantly show a grid (columns[reel][row]) with no animation.
export function setGrid(columns) {
  currentGrid = columns;
  const reels = reelsEl.children;
  for (let r = 0; r < REELS; r++) {
    const strip = reels[r].firstChild;
    strip.style.transition = 'none';
    strip.style.transform = 'translateY(0)';
    strip.innerHTML = '';
    for (let row = 0; row < ROWS; row++) strip.appendChild(makeCell(columns[r][row]));
  }
}

// Animate all reels spinning, landing on `columns`. Resolves when settled.
export function spinTo(columns) {
  clearWins();
  const cp = cellPx();
  const BUFFER = 16; // random cells scrolled before the result
  const reels = reelsEl.children;
  const done = [];

  for (let r = 0; r < REELS; r++) {
    const reel = reels[r];
    const strip = reel.firstChild;
    reel.classList.add('spinning');

    // Build: BUFFER random cells, then the 4 result cells at the bottom.
    strip.style.transition = 'none';
    strip.style.transform = 'translateY(0)';
    strip.innerHTML = '';
    for (let i = 0; i < BUFFER; i++) strip.appendChild(makeCell(randomSymbolId()));
    for (let row = 0; row < ROWS; row++) strip.appendChild(makeCell(columns[r][row]));

    // Force reflow so the transition applies.
    void strip.offsetHeight;

    const travel = BUFFER * cp;
    const duration = 700 + r * 130;
    strip.style.transition = `transform ${duration}ms cubic-bezier(0.16, 0.9, 0.28, 1.02)`;
    strip.style.transform = `translateY(-${travel}px)`;

    done.push(new Promise((resolve) => {
      const onEnd = () => {
        reel.classList.remove('spinning');
        // Snap: rebuild strip to just the 4 result cells at rest.
        strip.style.transition = 'none';
        strip.style.transform = 'translateY(0)';
        strip.innerHTML = '';
        for (let row = 0; row < ROWS; row++) strip.appendChild(makeCell(columns[r][row]));
        resolve();
      };
      strip.addEventListener('transitionend', onEnd, { once: true });
      // Safety timeout in case transitionend doesn't fire.
      setTimeout(onEnd, duration + 260);
    }));
  }
  currentGrid = columns;
  return Promise.all(done);
}

function cellAt(reel, row) {
  const strip = reelsEl.children[reel].firstChild;
  return strip.children[row];
}

// Highlight winning cells and draw the winning paylines.
export function showWins(lineWins, scatter, paylines) {
  clearWins();
  if ((!lineWins || !lineWins.length) && (!scatter || scatter.count < 3)) return;

  const winningCells = new Set();
  const svgLines = [];

  for (const w of lineWins) {
    for (const [reel, row] of w.positions) winningCells.add(reel + ':' + row);
    // Build a polyline across this payline's winning span.
    const path = w.positions.map(([reel, row]) => {
      const x = ((reel + 0.5) / REELS) * 100;
      const y = ((row + 0.5) / ROWS) * 100;
      return `${x},${y}`;
    }).join(' ');
    svgLines.push(path);
  }
  if (scatter && scatter.count >= 3) {
    for (const [reel, row] of scatter.positions) winningCells.add(reel + ':' + row);
  }

  // Dim non-winning, light winning.
  for (let r = 0; r < REELS; r++) {
    for (let row = 0; row < ROWS; row++) {
      const cell = cellAt(r, row);
      if (winningCells.has(r + ':' + row)) cell.classList.add('win');
      else cell.classList.add('dim');
    }
  }

  // Draw win lines.
  winlinesEl.innerHTML = '';
  for (const path of svgLines) {
    const pl = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    pl.setAttribute('points', path);
    pl.setAttribute('fill', 'none');
    pl.setAttribute('stroke', 'var(--win)');
    pl.setAttribute('stroke-width', '1.1');
    pl.setAttribute('stroke-linecap', 'round');
    pl.setAttribute('stroke-linejoin', 'round');
    pl.setAttribute('opacity', '0.85');
    pl.setAttribute('vector-effect', 'non-scaling-stroke');
    winlinesEl.appendChild(pl);
  }

  // Coin bursts from a couple of winning cells.
  const rect = reelsEl.getBoundingClientRect();
  let i = 0;
  for (const key of winningCells) {
    if (i++ % 3 !== 0) continue;
    const [r, row] = key.split(':').map(Number);
    const cr = cellAt(r, row).getBoundingClientRect();
    const nx = (cr.left + cr.width / 2) / innerWidth;
    const ny = (cr.top + cr.height / 2) / innerHeight;
    burst(nx, ny, 16, 'gold');
  }
}

export function clearWins() {
  winlinesEl.innerHTML = '';
  for (let r = 0; r < REELS; r++) {
    for (let row = 0; row < ROWS; row++) {
      const cell = cellAt(r, row);
      if (cell) cell.classList.remove('win', 'dim');
    }
  }
}

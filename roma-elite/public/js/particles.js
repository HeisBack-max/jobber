// Lightweight canvas particle system: ambient drifting embers/dust, plus a
// celebratory coin/spark burst on wins. No dependencies.

const canvas = document.getElementById('particles');
const ctx = canvas.getContext('2d');
let W = 0, H = 0, dpr = Math.min(window.devicePixelRatio || 1, 2);
const ambient = [];
const bursts = [];
let accent = '#e8c15a';
// Respect the OS "reduce motion" setting: skip ambient drift and win bursts.
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

function resize() {
  W = canvas.width = innerWidth * dpr;
  H = canvas.height = innerHeight * dpr;
  canvas.style.width = innerWidth + 'px';
  canvas.style.height = innerHeight + 'px';
}
addEventListener('resize', resize);
resize();

function rand(a, b) { return a + Math.random() * (b - a); }

function seedAmbient() {
  ambient.length = 0;
  if (reduceMotion) return;
  // Scale with viewport but cap so large displays don't pay a huge per-frame cost.
  const count = Math.min(90, Math.round((innerWidth * innerHeight) / 42000));
  for (let i = 0; i < count; i++) {
    ambient.push({
      x: rand(0, W), y: rand(0, H), r: rand(0.6, 2.4) * dpr,
      vy: rand(-0.15, -0.5) * dpr, vx: rand(-0.15, 0.15) * dpr,
      a: rand(0.1, 0.5), tw: rand(0.005, 0.02), t: rand(0, 6.28),
    });
  }
}
seedAmbient();

export function setAccent(color) { accent = color; }

// Emit a burst of `n` particles from normalized screen point (nx, ny in 0..1).
export function burst(nx, ny, n = 40, kind = 'gold') {
  if (reduceMotion) return;
  const cx = nx * W, cy = ny * H;
  const room = Math.max(0, MAX_BURST - bursts.length);
  n = Math.min(n, room);
  for (let i = 0; i < n; i++) {
    const ang = rand(0, Math.PI * 2);
    const spd = rand(1, 7) * dpr;
    bursts.push({
      x: cx, y: cy, vx: Math.cos(ang) * spd, vy: Math.sin(ang) * spd - rand(1, 3) * dpr,
      r: rand(1.5, 4.5) * dpr, life: 1, decay: rand(0.006, 0.018),
      hue: kind === 'gold' ? rand(38, 52) : rand(0, 360), spin: rand(-0.2, 0.2), rot: rand(0, 6.28),
    });
  }
}

const MAX_BURST = 320;      // hard cap on live burst particles
let running = true;
document.addEventListener('visibilitychange', () => {
  running = !document.hidden;
  if (running) requestAnimationFrame(tick);
});

function tick() {
  if (!running) return;
  ctx.clearRect(0, 0, W, H);

  // ambient
  for (const p of ambient) {
    p.x += p.vx; p.y += p.vy; p.t += p.tw;
    if (p.y < -10) { p.y = H + 10; p.x = rand(0, W); }
    const alpha = p.a * (0.6 + 0.4 * Math.sin(p.t));
    ctx.beginPath();
    ctx.fillStyle = `rgba(232,193,90,${alpha})`;
    ctx.arc(p.x, p.y, p.r, 0, 6.28);
    ctx.fill();
  }

  // bursts
  for (let i = bursts.length - 1; i >= 0; i--) {
    const b = bursts[i];
    b.vy += 0.12 * dpr; // gravity
    b.x += b.vx; b.y += b.vy; b.life -= b.decay; b.rot += b.spin;
    if (b.life <= 0) { bursts.splice(i, 1); continue; }
    ctx.save();
    ctx.globalAlpha = Math.max(0, b.life);
    ctx.translate(b.x, b.y); ctx.rotate(b.rot);
    ctx.fillStyle = `hsl(${b.hue} 90% 60%)`;
    ctx.fillRect(-b.r, -b.r * 0.6, b.r * 2, b.r * 1.2);
    ctx.restore();
  }
  requestAnimationFrame(tick);
}
tick();

# 🏛️ Roma Elite — Social Slots

An original, **free-to-play, entertainment-only** slot experience with two themed
games sharing one engine:

- **Roma Elite** — Ancient Roman Empire (marble, gold, imperial).
- **Phnom Penh Nights** — an original, colourful Cambodian city theme (Royal Palace,
  Khmer temples, the naga, apsara dance, tuk-tuks, riverside, Water Festival).

> ⚖️ **This is a social casino-style game.** You play with **virtual coins that have
> no monetary value**. There are **no real-money deposits**, **no withdrawals**, and
> **nothing of value can be won**. 18+. See [`LEGAL.md`](./LEGAL.md).

---

## What it is (and isn't)

This project deliberately implements the **honest, safe** version of a slot game:

| Included | Deliberately excluded |
| --- | --- |
| Virtual, non-cashable coins | Real-money deposits / payments |
| Free 100 welcome spins on signup (no payment) | "Pay to unlock free spins" funnels |
| 18+ age gate + responsible-play messaging | Cash prizes / withdrawals |
| Truthful "for fun only" onboarding & ads copy | Deceptive "free" advertising |
| Server-authoritative, seeded RNG | Any third-party / licensed IP |
| Hand-authored original SVG artwork | Stock art, emoji art, licensed assets |

The two games are **100% original** — no copied artwork, brands, or franchises.

---

## Quick start

Requires **Node.js 20+**. No dependencies to install — it runs on Node built-ins.

```bash
cd roma-elite
npm start
# open http://localhost:3000
```

Run the test suite (engine math, paylines, RTP sanity, HTTP API):

```bash
npm test                          # -> node --test
node --test 'test/**/*.test.js'   # equivalent, explicit
```

> ⚠️ Do **not** write this as `node --test test/`. On Node 22 the bare directory
> argument is resolved as a module path and the run dies with
> `Cannot find module .../test`. Plain `node --test` (which discovers `test/`
> automatically) or the explicit glob both work.

Inspect the payout math (full RTP including free-spin rounds and re-triggers):

```bash
node scripts/rtp-sim.js roma-elite 200 200000
node scripts/rtp-sim.js phnom-penh 200 200000
```

Measured on a 200,000-spin run at the default 200-coin bet:

| Game | Full RTP | Base hit freq | Free-spin trigger | Big win ≥20× |
| --- | --- | --- | --- | --- |
| `roma-elite` | **88.2%** | 16.3% | 0.87% (≈1 in 115) | 0.57% |
| `phnom-penh` | **88.0%** | 16.2% | 0.85% (≈1 in 117) | 0.59% |

(These are stochastic samples — expect ±0.5pp between runs.)

---

## Game design

- **5 reels × 4 rows**, **40 fixed paylines** (hand-designed paths in `shared.js`).
- **Symbols:** 4 premium, 3 medium, 3 low, plus a **Wild** (substitutes) and a
  **Scatter** (pays anywhere + triggers free spins) — 12 per game.
- **Free spins:** 3/4/5 scatters award **6 / 10 / 15** free spins at a **×2** line-win
  multiplier; they can re-trigger. Scatter pays 2× / 8× / 40× total bet.
- **Bets:** 40 / 80 / 200 / 400 / 800 / 2000 / 4000 coins per spin (default 200),
  spread across the 40 lines.
- **Balance:** tuned to ~**88% social RTP**, ~1-in-115 free-spin trigger. Because it
  is non-cashable, a **free top-up** (5,000 coins) is available when you drop below
  500 coins, on a 30-minute cooldown — no payment, ever.
- **Progression:** cosmetic Empire Rank ladder based on lifetime spins
  (Plebeian → Legionnaire → Centurion → Tribune → Praetor → Senator → Consul →
  Imperator).

### The BONUS WINNER screen

When a spin lands **3 or more scatters** and awards free spins, the game interrupts
with a full-screen **BONUS WINNER** celebration: coin bursts, the free-spin count,
the ×2 multiplier reminder, and an illustrated **bonus host** for the current theme —
*The Riverside Tycoon* for Phnom Penh Nights, *the Emperor* for Roma Elite.

> These bonus hosts are **original fictional characters**, drawn from scratch as
> inline SVG in `public/js/hosts.js`. They are **deliberately not likenesses of, and
> are not intended to resemble, any real or identifiable person.** They are generic
> archetypes (a suited figure at a neon riverside sunset; a laurelled figure in a
> toga), and nothing in the game references a real individual.

### Fairness

Every outcome is decided **server-side** in `server/lib/slot-engine.js` using a
cryptographically-seeded RNG (`crypto.randomBytes`). The client only animates the
grid the server returns; reel strips are never sent to the browser
(`publicGameConfig()` strips them out of the client payload).

---

## Art & presentation

All artwork is **hand-authored SVG in this repo**. There are **no third-party or
licensed assets, no stock art, and no emoji used as symbol art**.

**Symbol art** (`public/js/symbols.js`) is drawn in a **cel-shaded anime key-art**
style:

- Saturated base colours with **hard-edged shadow bands** — never soft gradients on
  skin, which is what makes the shading read as cel rather than airbrushed.
- **Big expressive eyes**: thick lash line, gradient iris, twin specular highlights.
- **Rim light** on one edge plus thick dark outlines for separation.
- Premium symbols are **bust portraits**, composed so the shoulders overflow and get
  **cropped by the medallion** ring — they read as framed character art, not floating
  dolls. Medium/low symbols sit on a bevelled plaque instead.
- **Dark, low-saturation themed backdrops** (lit sky + architecture silhouettes) sit
  well below the character in value, so the lit bust keeps separation and the tile
  doesn't muddy.

For performance, every symbol is emitted **once** into a single hidden `<svg>` sprite
as reusable `<symbol>` defs (`buildSprite()`); each reel cell references it with
`<use>` (`symUse()`), so gradients and filters are shared across dozens of on-screen
cells.

**3D staging** is pure CSS — no WebGL, no 3D assets:

- CSS `perspective` on the reel bank, so the drum reads as a real object.
- Each reel is rotated inward by its index (`rotateY`), giving the five-reel bank a
  **curved drum face**.
- A **cylinder falloff** gradient per reel darkens the top and bottom rows so they
  fall away from the viewer.
- A **specular sweep** across the "glass" in front of the reels.
- Reels animate with `transform` only (GPU compositing), with a left-to-right stagger,
  an overshoot bounce, and an **anticipation** slowdown on the last two reels when 2+
  scatters are already live.
- Wins draw glow-under-core payline polylines and fire canvas coin bursts.

`prefers-reduced-motion` is respected: ambient particles and win bursts are skipped
and animations are damped.

---

## Architecture

```
roma-elite/
├── server/
│   ├── index.js              # zero-dependency HTTP server + JSON API
│   └── lib/
│       ├── slot-engine.js    # pure, tested spin/evaluate engine
│       ├── auth.js           # scrypt passwords, magic-link tokens, ranks
│       ├── store.js          # atomic JSON persistence (swap for a DB at scale)
│       └── games/
│           ├── shared.js     # 40 paylines, grid dims, bet tiers, strip builder
│           ├── roma-elite.js # Roman theme config (symbols/paytable/strips)
│           ├── phnom-penh.js # Cambodian theme config
│           └── index.js      # game registry + client-safe projection
├── public/                   # single-page frontend (no build step)
│   ├── index.html            # all screens: age gate, auth, bonus, paytable, menu
│   ├── css/styles.css        # palette-driven theming + CSS 3D reel staging
│   └── js/
│       ├── app.js            # boot, auth flows, HUD, spin loop, overlays
│       ├── game.js           # reel DOM, spin animation, win presentation
│       ├── symbols.js        # ORIGINAL cel-shaded anime SVG symbol art (sprite)
│       ├── hosts.js          # ORIGINAL fictional bonus-host characters (SVG)
│       ├── particles.js      # canvas ambient dust + win coin bursts
│       └── legal.js          # in-app terms / responsible-play template copy
├── scripts/rtp-sim.js        # payout simulator (base + free-spin rounds)
├── test/
│   ├── slot-engine.test.js   # node:test engine unit tests
│   └── api.test.js           # HTTP API integration tests (boots a child server)
├── data/                     # JSON store (gitignored, created at runtime)
└── LEGAL.md                  # template terms — counsel review required
```

### API (all JSON)

| Method | Route | Auth | Purpose |
| --- | --- | --- | --- |
| `GET`  | `/api/games` | — | List games + client-safe configs (no reel strips) |
| `POST` | `/api/register` | — | Create a **free** account (auto or chosen credentials) |
| `POST` | `/api/login` | — | Username/password login |
| `POST` | `/api/magic` | — | Redeem a magic-login token (`/play?token=…`) |
| `GET`  | `/api/me` | session | Current player |
| `POST` | `/api/logout` | session | End session |
| `POST` | `/api/confirm-age` | session | Record 18+ confirmation |
| `POST` | `/api/magic-link` | session | Issue an honest magic-login link |
| `POST` | `/api/topup` | session | Free virtual-coin top-up when low (cooldown-limited) |
| `POST` | `/api/spin` | session + 18+ | **Server decides the outcome** and updates balance |

Sessions are an HttpOnly `re_sid` cookie. Anything not under `/api/` is served from
`public/`, with an SPA fallback to `index.html` for extensionless paths.

---

## Adding another themed game

Drop a config module in `server/lib/games/`, following `roma-elite.js`, and register
it in `games/index.js`. The engine, UI, animations, and paytable are all driven from
that config — no other server code changes needed. Reuse the shared paytable/strip
numbers to inherit the tuned ~88% RTP.

To give the new theme bespoke artwork, add an art table to the `ART` registry in
`public/js/symbols.js` (keyed by game id); any symbol without a hand-drawn entry
falls back to an empty bevelled plaque. Add a bonus-host illustration in
`public/js/hosts.js` and point `theme.bonusHost` at it.

---

## Notes & limitations

- **Persistence:** the JSON store (`server/lib/store.js`) writes a single file with
  debounced atomic writes. It is for a **single-process demo only** — there is no
  locking, so two processes sharing the file will clobber each other. Use a real
  database before any multi-instance or production use.
- **Auth is a starting point, not a hardened system.** Passwords use `scrypt` and
  sessions are HttpOnly cookies, but there is **no rate limiting, no CSRF protection,
  no HTTPS enforcement**, no session expiry/rotation, and no secrets management.
  Sessions and magic-link tokens live in the same plaintext JSON file. Add all of
  that before any public deployment.
- **Test coverage is server-side only.** `test/slot-engine.test.js` covers reel
  reads, grid shape, payline evaluation, wild substitution, minimum run length,
  scatter awards, the free-spin multiplier, and paytable/payline integrity across
  both games. `test/api.test.js` boots the server as a child process on an ephemeral
  port and covers the routes, registration/login validation, the age gate, spin
  bookkeeping, magic-link single-use redemption, logout, and malformed input.
  **Not covered:** the entire frontend (`public/js/*` — reel animation, symbol
  sprite, bonus screen, particles), the store's persistence/atomic-write behaviour
  in isolation, and the top-up threshold/cooldown paths.
- **Legal text in the app and `LEGAL.md` is a counsel-review template, not legal
  advice.** The support-helpline list is placeholder. Have qualified counsel review
  compliance for your jurisdiction before launch.
- The RTP figures above are simulation samples, not a certified lab result.

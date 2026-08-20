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

The two games are **100% original** — no copied artwork, brands, or franchises.

---

## Quick start

Requires **Node.js 20+**. No dependencies to install — it runs on Node built-ins.

```bash
cd roma-elite
npm start
# open http://localhost:3000
```

Run the test suite (engine math, paylines, RTP sanity):

```bash
npm test
```

Inspect the payout math (full RTP including free-spin rounds):

```bash
node scripts/rtp-sim.js roma-elite 200 300000
node scripts/rtp-sim.js phnom-penh 200 300000
```

---

## Game design

- **5 reels × 4 rows**, **40 fixed paylines**.
- **Symbols:** 4 premium, 3 medium, 3 low, plus a **Wild** (substitutes) and a
  **Scatter** (pays anywhere + triggers free spins).
- **Free spins:** 3+ scatters award 6–15 free spins at a ×2 line-win multiplier;
  they can re-trigger.
- **Balance:** tuned to ~**88% social RTP**, ~1-in-120 free-spin trigger. Because it
  is non-cashable, a **free top-up** is available when you run low (no payment).
- **Progression:** cosmetic Empire Rank ladder based on lifetime spins.

### Fairness

Every outcome is decided **server-side** in `server/lib/slot-engine.js` using a
cryptographically-seeded RNG (`crypto.randomBytes`). The client only animates the
grid the server returns; reel strips are never sent to the browser.

---

## Architecture

```
roma-elite/
├── server/
│   ├── index.js              # zero-dependency HTTP server + JSON API
│   └── lib/
│       ├── slot-engine.js    # pure, tested spin/evaluate engine
│       ├── auth.js           # scrypt passwords, magic-link tokens, sessions
│       ├── store.js          # atomic JSON persistence (swap for a DB at scale)
│       └── games/
│           ├── shared.js     # 40 paylines, grid dims, bet tiers
│           ├── roma-elite.js # Roman theme config (symbols/paytable/strips)
│           ├── phnom-penh.js # Cambodian theme config
│           └── index.js      # game registry + client-safe projection
├── public/                   # single-page frontend (no build step)
│   ├── index.html
│   ├── css/styles.css        # palette-driven theming
│   └── js/{app,game,particles,legal}.js
├── scripts/rtp-sim.js        # payout simulator
└── test/slot-engine.test.js  # node:test unit tests
```

### API (all JSON)

| Method | Route | Purpose |
| --- | --- | --- |
| `GET`  | `/api/games` | List games + client-safe configs |
| `POST` | `/api/register` | Create a **free** account (auto or chosen credentials) |
| `POST` | `/api/login` | Username/password login |
| `POST` | `/api/magic` | Redeem a magic-login token (`/play?token=…`) |
| `POST` | `/api/confirm-age` | Record 18+ confirmation |
| `GET`  | `/api/me` | Current player |
| `POST` | `/api/spin` | **Server decides the outcome** and updates balance |
| `POST` | `/api/topup` | Free virtual-coin top-up when low (cooldown-limited) |
| `POST` | `/api/magic-link` | Issue an honest magic-login link |
| `POST` | `/api/logout` | End session |

---

## Adding another themed game

Drop a config module in `server/lib/games/`, following `roma-elite.js`, and register
it in `games/index.js`. The engine, UI, animations, and paytable are all driven from
that config — no other code changes needed. Reuse the shared paytable/strip numbers
to inherit the tuned ~88% RTP.

---

## Notes & limitations

- The JSON store is for a **single-process demo**. Use a real database before any
  multi-instance or production use.
- Passwords use `scrypt`; sessions are HttpOnly cookies. This is a starting point,
  not a hardened auth system — add rate-limiting, CSRF protection, HTTPS, and a
  proper secrets story before any public deployment.
- **Legal text in the app and `LEGAL.md` is a template, not legal advice.** Have
  qualified counsel review compliance for your jurisdiction before launch.

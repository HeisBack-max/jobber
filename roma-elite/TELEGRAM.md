# Telegram acquisition bot

Brings a player from an ad into the game with a unique account, in one tap.

```
Ad  →  Telegram bot  →  [ ✅ Confirm & Play Free ]  →  username + password
                                                       + one-tap magic link
                                                    →  auto-login into the game
```

Each player gets their **own** account, their **own** credentials, and a
**single-use** magic-login token tied to that account.

---

## No payment step — by design

This bot **never requests, displays or processes a payment**, and there is no
deposit, KHQR, invoice or webhook anywhere in this flow. Accounts are free here,
exactly as they are on the website.

That is not an oversight, it is the product:

- The games are **social / entertainment only**. Coins are virtual, have **no cash
  value**, and **cannot be redeemed, withdrawn or exchanged**. See `LEGAL.md`.
- Because nothing of value can be won, charging for entry — and especially
  advertising paid spins as "free" — would be deceptive, and in many markets
  unlawful. Taking real money would also pull in payment licensing, refunds, tax,
  KYC and consumer-protection obligations that none of this code implements.

**Advertising must match reality.** Do not describe the welcome spins as
requiring, or being unlocked by, a deposit. Honest copy that fits this build:

> 🏛️ **Roma Elite** — 100 welcome free spins, free to play.
> Social game for adults. Virtual coins only, no cash value,
> nothing of value can be won. 18+.

---

## Setup

1. **Create the bot** — message [@BotFather](https://t.me/BotFather), send
   `/newbot`, and copy the token it gives you.

2. **Pick a shared secret.** The bot authenticates to the site with it, so it
   must be the same value in both processes and must not be public:

   ```bash
   export BOT_API_SECRET="$(openssl rand -hex 24)"
   ```

3. **Run the website** with that secret:

   ```bash
   BOT_API_SECRET="$BOT_API_SECRET" npm start
   ```

4. **Run the bot** (separate terminal):

   ```bash
   BOT_TOKEN="123456:ABC..." \
   BOT_API_SECRET="$BOT_API_SECRET" \
   SITE_URL="https://your-site.example" \
   npm run bot
   ```

5. Open your bot in Telegram and send `/start`.

### Environment variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `BOT_TOKEN` | yes | Bot token from @BotFather |
| `BOT_API_SECRET` | yes | Shared secret; must match the web server's |
| `SITE_URL` | yes in prod | Public site origin used to build the login link |
| `API_URL` | no | Where the bot reaches the API (defaults to `SITE_URL`) — set it if the bot talks to the server on a private address |
| `HERO_IMAGE_URL` | no | Image shown with the welcome message |

If `BOT_API_SECRET` is unset on the **server**, `/api/bot/provision` returns
`503` and provisioning is disabled — it never falls open.

---

## How it works

`POST /api/bot/provision` (server-to-server, `X-Bot-Secret` header):

```json
{ "telegramId": "123456789" }
```

Returns:

```json
{
  "username": "BronzeEagle593",
  "password": "--saWaO6",
  "token":    "zctAftrRnMGh...",
  "path":     "/play?token=zctAftrRnMGh...",
  "returning": false
}
```

- Creates a free account seeded with **100 free spins + 10,000 virtual coins**.
- Links the Telegram chat id to that account, so `/start` from a **returning**
  player returns their existing account (`returning: true`) rather than a
  duplicate — and no password is re-sent, because the plaintext is never stored.
- Mints a **single-use** magic token (7-day TTL). Redeeming it at `/api/magic`
  consumes it and starts a session; a second attempt fails.
- The link `/play?token=…` signs the player in automatically.

### The 18+ gate still applies

A magic link authenticates but does **not** waive age confirmation. New players
are shown the 18+ gate on arrival, and the server refuses `/api/spin` with `403`
until age is confirmed.

---

## Security notes

- The provisioning endpoint is guarded **only** by the shared secret — treat it
  like a password, keep it out of source control, and serve the site over HTTPS
  so it is not sent in clear.
- Passwords are shown to the player **once**; the server stores only an scrypt
  hash and cannot re-display them.
- There is no rate limiting on provisioning. Before any public launch, put the
  endpoint behind a rate limiter so a leaked secret cannot be used to mass-create
  accounts.

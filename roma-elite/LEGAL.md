# Legal & Compliance Notes — Roma Elite

> **⚠️ TEMPLATE ONLY — NOT LEGAL ADVICE.**
> This document is a starting-point checklist and placeholder policy text. It has
> **not** been reviewed by a lawyer. Before advertising or launching this product
> publicly, you **must** engage qualified gaming/advertising counsel for every
> jurisdiction you operate in or target.

## What this build is

Roma Elite is a **social casino-style game**:

- Play uses **virtual coins with no monetary value**.
- **No real-money deposits** are accepted by this software.
- **No withdrawals, cash-outs, prizes, or anything of value** can be won.
- Intended for an **adult (18+) audience** for **entertainment only**.

These properties are what keep it distinct from regulated real-money gambling. If
you change any of them — for example, by selling coins for real money, adding
cash-out, or coupling play to payments — the legal picture changes substantially and
you will likely trigger gambling, payment, consumer-protection, and advertising
regulations.

## Advertising requirements (as implemented in-app)

Per the product owner's direction, advertising and onboarding copy must clearly and
truthfully state that:

1. The game is **free to play**.
2. Welcome free spins (e.g. "100 free spins") are **virtual, non-cashable** spins.
3. The game is for **entertainment only**; **no real money** or item of value can be
   won.
4. The game is **18+**.

The in-app onboarding, age gate, welcome popup, and persistent footer all carry these
statements. **Advertising must not** describe the game as a way to win money, imply
real-money prizes, or omit the "for fun only / no cash value" disclosure.

> Note on "depositing players": this build intentionally does **not** implement
> real-money deposits. Any offer framed around "depositing" real money would convert
> this into a paid/regulated product and is out of scope here. If that model is
> genuinely intended, it must be scoped and built separately, under counsel, with the
> appropriate licensing, KYC, refunds, and jurisdictional controls.

## Pre-launch checklist (non-exhaustive)

- [ ] Counsel review of Terms, Privacy Policy, and all advertising creatives.
- [ ] Confirm social-casino legality and any disclosure rules in each target market.
- [ ] Platform policy review (e.g. Facebook/Meta, Google, Apple, Telegram) for
      social-casino advertising and distribution.
- [ ] Robust **age verification** appropriate to your market (the in-app self-attest
      gate is a minimum, not necessarily sufficient).
- [ ] Responsible-gaming resources with **correct local helplines**.
- [ ] Data-protection compliance (GDPR/CCPA/etc.) for any personal data collected.
- [ ] If coins are ever sold for real money: payment licensing, refunds, tax, and
      "no cash value" enforceability review.
- [ ] Security hardening (HTTPS, rate limiting, CSRF, secrets management, audited
      RNG) before any public exposure.

## Responsible play

The app surfaces responsible-play messaging and placeholder helpline references.
Replace the placeholders with the correct resources for your jurisdiction before
launch. Even for a no-money game, be mindful that slot-style mechanics can normalise
real-money gambling behaviours; keep the messaging prominent and honest.

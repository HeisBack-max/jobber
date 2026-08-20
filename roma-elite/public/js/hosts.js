// Original, fictional bonus-host illustrations rendered as inline SVG.
// These are generic stylised characters invented for this game. They are NOT
// portraits of, and are not intended to resemble, any real or identifiable person.

// A generic "tycoon" host: suit, sunglasses, neon riverside sunset. No likeness.
export const TYCOON_SVG = `
<svg viewBox="0 0 220 220" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="The Riverside Tycoon (original character)">
  <defs>
    <radialGradient id="sun" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#ffd23f"/><stop offset="55%" stop-color="#f08a24"/><stop offset="100%" stop-color="#c1121f"/>
    </radialGradient>
    <linearGradient id="suit" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#20304a"/><stop offset="100%" stop-color="#0d1a2b"/>
    </linearGradient>
  </defs>
  <circle cx="110" cy="110" r="104" fill="url(#sun)"/>
  <circle cx="110" cy="110" r="104" fill="none" stroke="#fff4e0" stroke-opacity="0.5" stroke-width="3"/>
  <!-- palm silhouettes -->
  <g fill="#0d1a2b" opacity="0.55">
    <rect x="34" y="120" width="6" height="60"/><path d="M37 120c-16-6-26 2-30 10 12-4 20-2 30 6z"/><path d="M37 120c16-6 26 2 30 10-12-4-20-2-30 6z"/>
    <rect x="182" y="120" width="6" height="60"/><path d="M185 120c-16-6-26 2-30 10 12-4 20-2 30 6z"/><path d="M185 120c16-6 26 2 30 10-12-4-20-2-30 6z"/>
  </g>
  <!-- shoulders + suit -->
  <path d="M50 210c0-38 27-64 60-64s60 26 60 64z" fill="url(#suit)"/>
  <path d="M96 150l14 22 14-22 -6 60h-16z" fill="#fff4e0"/>
  <path d="M110 172l10 8-4 30-6-10-6 10-4-30z" fill="#2a9d8f"/><!-- tie -->
  <!-- head -->
  <circle cx="110" cy="104" r="34" fill="#caa06a"/>
  <path d="M78 96c2-20 18-30 32-30s30 10 32 30c-8-8-20-12-32-12s-24 4-32 12z" fill="#2b2118"/><!-- hair -->
  <!-- sunglasses -->
  <g fill="#0d1a2b">
    <rect x="84" y="98" width="22" height="14" rx="7"/><rect x="114" y="98" width="22" height="14" rx="7"/>
    <rect x="106" y="103" width="8" height="4"/>
  </g>
  <path d="M96 126c8 6 20 6 28 0" fill="none" stroke="#6b4a2a" stroke-width="3" stroke-linecap="round"/>
</svg>`;

// A generic "emperor" host for the Roman game: laurel, toga. No likeness.
export const EMPEROR_SVG = `
<svg viewBox="0 0 220 220" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="The Emperor (original character)">
  <defs>
    <radialGradient id="gold" cx="50%" cy="40%" r="65%">
      <stop offset="0%" stop-color="#ffe9a8"/><stop offset="55%" stop-color="#e8c15a"/><stop offset="100%" stop-color="#7a1f1f"/>
    </radialGradient>
  </defs>
  <circle cx="110" cy="110" r="104" fill="url(#gold)"/>
  <circle cx="110" cy="110" r="104" fill="none" stroke="#f2ead9" stroke-opacity="0.6" stroke-width="3"/>
  <!-- columns -->
  <g fill="#3a2410" opacity="0.4"><rect x="30" y="70" width="12" height="120"/><rect x="178" y="70" width="12" height="120"/></g>
  <!-- toga shoulders -->
  <path d="M52 210c0-36 26-62 58-62s58 26 58 62z" fill="#f2ead9"/>
  <path d="M110 150l-26 60h52z" fill="#e0d3b6"/>
  <path d="M84 156l26 12 26-12-8 20-18 8-18-8z" fill="#c9b98f"/>
  <!-- head -->
  <circle cx="110" cy="104" r="34" fill="#d8b184"/>
  <path d="M78 100c4-18 18-28 32-28s28 10 32 28c-9-7-20-11-32-11s-23 4-32 11z" fill="#5a3d1e"/>
  <!-- laurel -->
  <g fill="#2f7d32"><path d="M78 92c-10-6-16-2-18 6 8-2 14 0 18 6zM142 92c10-6 16-2 18 6-8-2-14 0-18 6z"/>
    <path d="M84 84c-8-8-14-6-16 2 8 0 12 2 16 6zM136 84c8-8 14-6 16 2-8 0-12 2-16 6z"/></g>
  <!-- eyes -->
  <circle cx="98" cy="104" r="4" fill="#2b2118"/><circle cx="122" cy="104" r="4" fill="#2b2118"/>
  <path d="M98 122c7 5 17 5 24 0" fill="none" stroke="#8a5a2a" stroke-width="3" stroke-linecap="round"/>
</svg>`;

export function hostArt(hostId) {
  if (hostId === 'emperor') return EMPEROR_SVG;
  return TYCOON_SVG;
}

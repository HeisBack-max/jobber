// Original SVG symbol artwork for Roma Elite.
// Every symbol is hand-authored vector art (no emoji, no third-party assets).
// Symbols are emitted once into a hidden <svg> sprite as reusable <symbol> defs;
// each reel cell references them with <use>, so gradients/filters are shared and
// the renderer stays lightweight even with dozens of cells on screen.

// ---- shared gradient + filter defs (authored once per sprite) --------------
function sharedDefs(accent) {
  return `
  <linearGradient id="gGold" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#fff6d2"/><stop offset=".35" stop-color="#f4d270"/>
    <stop offset=".7" stop-color="#d69a2a"/><stop offset="1" stop-color="#8a5c12"/>
  </linearGradient>
  <linearGradient id="gGoldSoft" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffe9a8"/><stop offset="1" stop-color="#b07d1e"/>
  </linearGradient>
  <radialGradient id="gPlaque" cx=".5" cy=".38" r=".7">
    <stop offset="0" stop-color="#3a2c4f"/><stop offset=".6" stop-color="#241a33"/>
    <stop offset="1" stop-color="#120b1c"/>
  </radialGradient>
  <radialGradient id="gGlow" cx=".5" cy=".5" r=".5">
    <stop offset="0" stop-color="${accent}" stop-opacity=".9"/>
    <stop offset="1" stop-color="${accent}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="gRed" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ff6b5e"/><stop offset="1" stop-color="#8a1414"/>
  </linearGradient>
  <linearGradient id="gBlue" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#7fd4ff"/><stop offset="1" stop-color="#1c4f8a"/>
  </linearGradient>
  <linearGradient id="gGreen" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#8fe6a0"/><stop offset="1" stop-color="#1f7d43"/>
  </linearGradient>
  <linearGradient id="gPink" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffc3e0"/><stop offset="1" stop-color="#d24d8f"/>
  </linearGradient>
  <linearGradient id="gStone" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#e9e0cc"/><stop offset="1" stop-color="#9c8f72"/>
  </linearGradient>
  <linearGradient id="gShine" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#fff" stop-opacity=".85"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>
  <filter id="fSoft" x="-30%" y="-30%" width="160%" height="160%">
    <feDropShadow dx="0" dy="1.2" stdDeviation="1.4" flood-color="#000" flood-opacity=".55"/>
  </filter>
  <filter id="fGlow" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur stdDeviation="2.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>`;
}

// A round gold medallion backing used by premium symbols. Art is scaled up from
// the 100x100 authoring box so it fills the medallion instead of floating in it.
function medallion(inner) {
  return `
    <circle cx="50" cy="50" r="47" fill="url(#gGlow)" opacity=".6"/>
    <circle cx="50" cy="50" r="44" fill="url(#gPlaque)" stroke="url(#gGold)" stroke-width="5"/>
    <circle cx="50" cy="50" r="39" fill="none" stroke="#000" stroke-opacity=".35" stroke-width="1"/>
    <g filter="url(#fSoft)" transform="translate(50 51) scale(1.34) translate(-50 -50)">${inner}</g>
    <path d="M22 32a40 40 0 0 1 34-11" fill="none" stroke="url(#gShine)" stroke-width="3.5" stroke-linecap="round" opacity=".75"/>`;
}
// A softer plaque for medium/low symbols.
function plaque(inner) {
  return `
    <circle cx="50" cy="50" r="44" fill="url(#gGlow)" opacity=".32"/>
    <rect x="9" y="9" width="82" height="82" rx="18" fill="url(#gPlaque)" stroke="url(#gGoldSoft)" stroke-width="3"/>
    <g filter="url(#fSoft)" transform="translate(50 51) scale(1.3) translate(-50 -50)">${inner}</g>
    <path d="M18 26a30 30 0 0 1 26-12" fill="none" stroke="url(#gShine)" stroke-width="2.5" stroke-linecap="round" opacity=".45"/>`;
}

// ---- Roma Elite symbol inner art -------------------------------------------
const ROMA = {
  // Emperor: broad shoulders, crimson cape, laurel wreath — heavy, martial silhouette.
  EMPEROR: medallion(`
    <path d="M30 70c2-11 9-17 20-17s18 6 20 17z" fill="url(#gRed)"/>
    <path d="M34 70c1-9 7-14 16-14s15 5 16 14z" fill="url(#gGold)"/>
    <circle cx="50" cy="40" r="13" fill="#e6b98a"/>
    <path d="M37 38c1-8 6-12 13-12s12 4 13 12c-4-4-8-6-13-6s-9 2-13 6z" fill="#4a3218"/>
    <g fill="#2f7d32"><path d="M36 34c-6-4-11-2-12 4 5-2 9-1 12 2zM64 34c6-4 11-2 12 4-5-2-9-1-12 2z"/></g>
    <path d="M42 28l8-7 8 7z" fill="url(#gGold)"/>
    <circle cx="45" cy="41" r="1.8" fill="#241a33"/><circle cx="55" cy="41" r="1.8" fill="#241a33"/>
    <path d="M45 48c3 2 7 2 10 0" stroke="#8a5c12" stroke-width="1.6" fill="none" stroke-linecap="round"/>`),
  // Empress: slender neck, tall jewelled diadem, flowing hair — elegant silhouette.
  EMPRESS: medallion(`
    <path d="M34 70c2-10 8-15 16-15s14 5 16 15z" fill="url(#gPink)"/>
    <path d="M36 44c-6 3-8 12-6 24h6zM64 44c6 3 8 12 6 24h-6z" fill="#4a3218"/>
    <circle cx="50" cy="42" r="12" fill="#f0c9a0"/>
    <path d="M38 40c0-9 5-14 12-14s12 5 12 14c-3-6-7-8-12-8s-9 2-12 8z" fill="#5a3d1e"/>
    <path d="M38 30l4 6 8-9 8 9 4-6-3 9H41z" fill="url(#gGold)"/>
    <circle cx="50" cy="25" r="3" fill="url(#gBlue)" stroke="url(#gGold)" stroke-width="1"/>
    <circle cx="45" cy="43" r="1.7" fill="#241a33"/><circle cx="55" cy="43" r="1.7" fill="#241a33"/>
    <circle cx="42" cy="58" r="2.5" fill="url(#gGold)"/><circle cx="58" cy="58" r="2.5" fill="url(#gGold)"/>`),
  COMMANDER: medallion(`
    <path d="M50 20c-3 0-4 3-4 6l-14 4v3l14 2v2c-6 2-10 8-10 15h28c0-7-4-13-10-15v-2l14-2v-3l-14-4c0-3-1-6-4-6z" fill="url(#gRed)"/>
    <path d="M38 40c-4 1-7 5-7 11 0 6 4 11 9 13h20c5-2 9-7 9-13 0-6-3-10-7-11-2 8-8 12-17 12s-9-4-9-12z" fill="url(#gGold)"/>
    <rect x="44" y="52" width="12" height="10" rx="2" fill="#241a33"/>`),
  EAGLE: medallion(`
    <path d="M50 34c-3 0-5 2-5 5 0 2 1 3 2 4-8-3-16-4-24-1 6 1 10 4 13 8-5-1-9 0-13 3 7-1 13 1 18 5-3 2-5 5-5 8h38c0-3-2-6-5-8 5-4 11-6 18-5-4-3-8-4-13-3 3-4 7-7 13-8-8-3-16-2-24 1 1-1 2-2 2-4 0-3-2-5-5-5z" fill="url(#gGold)"/>
    <circle cx="50" cy="38" r="2" fill="#241a33"/>`),
  CHARIOT: plaque(`
    <circle cx="42" cy="58" r="16" fill="none" stroke="url(#gGold)" stroke-width="4"/>
    <g stroke="url(#gGoldSoft)" stroke-width="2"><path d="M42 44v28M28 58h28M32 48l20 20M52 48 32 68"/></g>
    <path d="M58 40c6-2 12 0 16 5-4-1-7 0-10 2l-3 8-5-2z" fill="url(#gGold)"/>`),
  LAUREL: plaque(`
    <path d="M50 24c-12 4-20 15-20 30 0 6 2 11 5 15 1-14 6-24 15-31z" fill="url(#gGreen)"/>
    <path d="M50 24c12 4 20 15 20 30 0 6-2 11-5 15-1-14-6-24-15-31z" fill="url(#gGreen)"/>
    <circle cx="50" cy="70" r="4" fill="url(#gGold)"/>`),
  TREASURY: plaque(`
    <rect x="28" y="48" width="44" height="24" rx="3" fill="url(#gGoldSoft)"/>
    <path d="M28 48c0-10 10-14 22-14s22 4 22 14z" fill="url(#gGold)"/>
    <rect x="28" y="52" width="44" height="5" fill="#8a5c12" opacity=".6"/>
    <rect x="46" y="54" width="8" height="10" rx="2" fill="#3a2410"/>
    <circle cx="40" cy="42" r="4" fill="#f4d270"/><circle cx="60" cy="44" r="3.5" fill="#f4d270"/>`),
  SHIELD: plaque(`
    <path d="M50 26c8 4 16 5 16 5v18c0 12-8 20-16 24-8-4-16-12-16-24V31s8-1 16-5z" fill="url(#gRed)" stroke="url(#gGold)" stroke-width="2.5"/>
    <path d="M50 34v34M40 47h20" stroke="url(#gGold)" stroke-width="3"/>`),
  AMPHORA: plaque(`
    <path d="M50 30c-4 0-7 2-7 5 0 2 1 3 3 4-6 3-9 9-9 16 0 8 6 13 13 13s13-5 13-13c0-7-3-13-9-16 2-1 3-2 3-4 0-3-3-5-7-5z" fill="url(#gStone)" stroke="url(#gGoldSoft)" stroke-width="1.5"/>
    <path d="M38 46c-4 0-6 3-5 7 2-2 4-2 6-1zM62 46c4 0 6 3 5 7-2-2-4-2-6-1z" fill="none" stroke="url(#gGoldSoft)" stroke-width="2.5"/>`),
  COIN: plaque(`
    <circle cx="50" cy="50" r="21" fill="url(#gGold)" stroke="#8a5c12" stroke-width="2"/>
    <circle cx="50" cy="50" r="16" fill="none" stroke="#8a5c12" stroke-width="1.5" opacity=".5"/>
    <path d="M50 40l3 7 7 .5-5.5 4.5 2 7-6.5-4-6.5 4 2-7L36 47.5l7-.5z" fill="#8a5c12" opacity=".7"/>`),
  WILD: `
    <rect x="20" y="16" width="60" height="68" rx="10" fill="url(#gGlow)" opacity=".5"/>
    <rect x="34" y="18" width="6" height="64" rx="3" fill="url(#gGold)"/>
    <path d="M40 22h34l-6 9 6 9H40z" fill="url(#gRed)" stroke="url(#gGold)" stroke-width="2" filter="url(#fGlow)"/>
    <text x="57" y="34" font-family="Cinzel,serif" font-size="9" font-weight="900" fill="#fff6d2" text-anchor="middle">SPQR</text>
    <text x="50" y="66" font-family="Cinzel,serif" font-size="15" font-weight="900" fill="url(#gGold)" text-anchor="middle" filter="url(#fGlow)">WILD</text>`,
  SCATTER: `
    <ellipse cx="50" cy="48" rx="40" ry="36" fill="url(#gGlow)" opacity=".55"/>
    <path d="M22 60c0-16 12-28 28-28s28 12 28 28v6H22z" fill="none" stroke="url(#gGold)" stroke-width="3.5" filter="url(#fGlow)"/>
    <g fill="url(#gGoldSoft)"><rect x="28" y="46" width="7" height="18" rx="3"/><rect x="40" y="42" width="7" height="22" rx="3"/><rect x="53" y="42" width="7" height="22" rx="3"/><rect x="65" y="46" width="7" height="18" rx="3"/></g>
    <text x="50" y="80" font-family="Cinzel,serif" font-size="11" font-weight="900" fill="url(#gGold)" text-anchor="middle" filter="url(#fGlow)">BONUS</text>`,
};

// ---- Phnom Penh Nights symbol inner art ------------------------------------
const PHNOM = {
  PALACE: medallion(`
    <path d="M50 24l5 10h-10z" fill="url(#gGold)"/>
    <path d="M50 30c8 6 12 14 12 22v20H38V52c0-8 4-16 12-22z" fill="url(#gGold)"/>
    <path d="M38 52l12-10 12 10zM35 62l15-12 15 12z" fill="url(#gGoldSoft)"/>
    <rect x="46" y="60" width="8" height="12" rx="2" fill="#241a33"/>`),
  TEMPLE: medallion(`
    <path d="M50 22l3 8h-6z" fill="url(#gGold)"/>
    <path d="M42 32h16l-2 8h-12zM39 42h22l-2 9H41zM36 53h28l-3 10H39zM33 65h34v9H33z" fill="url(#gGold)" stroke="#8a5c12" stroke-width=".8"/>
    <rect x="46" y="66" width="8" height="8" fill="#241a33"/>`),
  NAGA: medallion(`
    <path d="M50 68c-8 0-12-6-12-12 0-8 8-10 8-18 0-5-3-8-3-12 4 0 7 3 7 8 0 6-4 9-4 14 0 4 2 6 4 6s4-2 4-6c0-5-4-8-4-14 0-5 3-8 7-8 0 4-3 7-3 12 0 8 8 10 8 18 0 6-4 12-12 12z" fill="url(#gGold)"/>
    <path d="M40 30c-3-1-5 1-5 4 2-1 4-1 5 0zM60 30c3-1 5 1 5 4-2-1-4-1-5 0z" fill="url(#gGoldSoft)"/>
    <circle cx="47" cy="30" r="1.4" fill="#241a33"/><circle cx="53" cy="30" r="1.4" fill="#241a33"/>`),
  APSARA: medallion(`
    <path d="M50 22l6 12H44z" fill="url(#gGold)"/>
    <circle cx="50" cy="38" r="7" fill="url(#gGoldSoft)"/>
    <path d="M50 45c-6 0-9 4-9 9 0 3 2 6 4 8l-8 6h26l-8-6c2-2 4-5 4-8 0-5-3-9-9-9z" fill="url(#gGold)"/>
    <path d="M41 52l-10 3 10 4zM59 52l10 3-10 4z" fill="url(#gGoldSoft)"/>`),
  TUKTUK: plaque(`
    <path d="M30 62V48h16l6-8h12v22z" fill="url(#gGreen)" stroke="url(#gGold)" stroke-width="1.5"/>
    <path d="M30 44h34v4H30z" fill="url(#gGold)"/>
    <circle cx="38" cy="64" r="6" fill="#241a33" stroke="url(#gGold)" stroke-width="2"/>
    <circle cx="62" cy="64" r="6" fill="#241a33" stroke="url(#gGold)" stroke-width="2"/>
    <path d="M24 56l8-2v6h-8z" fill="url(#gGoldSoft)"/>`),
  LOTUS: plaque(`
    <path d="M50 34c4 6 5 14 0 24-5-10-4-18 0-24z" fill="url(#gPink)"/>
    <path d="M50 58c-6-6-8-14-6-22 6 4 9 12 6 22zM50 58c6-6 8-14 6-22-6 4-9 12-6 22z" fill="#ffb3d6"/>
    <path d="M50 58c-9-3-14-9-15-17 8 2 14 8 15 17zM50 58c9-3 14-9 15-17-8 2-14 8-15 17z" fill="url(#gPink)"/>
    <ellipse cx="50" cy="62" rx="16" ry="4" fill="url(#gGreen)"/>`),
  BOAT: plaque(`
    <path d="M22 54c8 8 48 8 56 0-4 10-14 14-28 14s-24-4-28-14z" fill="url(#gGold)" stroke="#8a5c12" stroke-width="1"/>
    <path d="M22 54c-3-2-4-6-2-9 3 2 5 4 6 7zM78 54c3-2 4-6 2-9-3 2-5 4-6 7z" fill="url(#gRed)"/>
    <g stroke="url(#gGoldSoft)" stroke-width="2"><path d="M34 54v-8M44 54v-10M56 54v-10M66 54v-8"/></g>`),
  NUMPANG: plaque(`
    <path d="M28 56c0-8 10-12 22-12s22 4 22 12c0 4-4 7-10 8H38c-6-1-10-4-10-8z" fill="url(#gGoldSoft)" stroke="#8a5c12" stroke-width="1"/>
    <path d="M34 54h32" stroke="#8a5c12" stroke-width="1.2" opacity=".5"/>
    <path d="M32 58c10 3 26 3 36 0-2 3-5 4-8 5H40c-3-1-6-2-8-5z" fill="url(#gGreen)"/>
    <path d="M30 60c12 4 28 4 40 0" stroke="url(#gRed)" stroke-width="3" fill="none" stroke-linecap="round"/>`),
  KRAMA: plaque(`
    <g>
      <rect x="30" y="30" width="40" height="40" rx="4" fill="#c1121f"/>
      <g fill="#fff4e0" opacity=".92">
        <rect x="30" y="30" width="10" height="10"/><rect x="50" y="30" width="10" height="10"/>
        <rect x="40" y="40" width="10" height="10"/><rect x="60" y="40" width="10" height="10"/>
        <rect x="30" y="50" width="10" height="10"/><rect x="50" y="50" width="10" height="10"/>
        <rect x="40" y="60" width="10" height="10"/><rect x="60" y="60" width="10" height="10"/>
      </g>
      <rect x="30" y="30" width="40" height="40" rx="4" fill="none" stroke="url(#gGold)" stroke-width="2"/>
    </g>`),
  RIEL: plaque(`
    <circle cx="50" cy="50" r="21" fill="url(#gGold)" stroke="#8a5c12" stroke-width="2"/>
    <path d="M44 62V40l6 8 6-8v22" fill="none" stroke="#8a5c12" stroke-width="3" opacity=".7"/>`),
  WILD: `
    <rect x="20" y="14" width="60" height="72" rx="10" fill="url(#gGlow)" opacity=".5"/>
    <path d="M50 20c4 6 4 12 0 16-4-4-4-10 0-16z" fill="url(#gGold)" filter="url(#fGlow)"/>
    <path d="M40 40h20l-3 20H43z" fill="url(#gGoldSoft)" stroke="url(#gGold)" stroke-width="1.5"/>
    <rect x="36" y="60" width="28" height="6" rx="2" fill="url(#gGold)"/>
    <text x="50" y="80" font-family="Cinzel,serif" font-size="15" font-weight="900" fill="url(#gGold)" text-anchor="middle" filter="url(#fGlow)">WILD</text>`,
  SCATTER: `
    <circle cx="50" cy="44" r="34" fill="url(#gGlow)" opacity=".6"/>
    <circle cx="50" cy="44" r="26" fill="url(#gPlaque)" stroke="url(#gGold)" stroke-width="3" filter="url(#fGlow)"/>
    <path d="M50 30a9 9 0 0 1 9 9c0 4-2 6-4 8h-10c-2-2-4-4-4-8a9 9 0 0 1 9-9z" fill="url(#gGoldSoft)"/>
    <rect x="41" y="38" width="7" height="4" rx="2" fill="#120b1c"/><rect x="52" y="38" width="7" height="4" rx="2" fill="#120b1c"/>
    <path d="M36 60c2-5 8-8 14-8s12 3 14 8z" fill="url(#gGold)"/>
    <text x="50" y="82" font-family="Cinzel,serif" font-size="11" font-weight="900" fill="url(#gGold)" text-anchor="middle" filter="url(#fGlow)">BONUS</text>`,
};

const ART = { 'roma-elite': ROMA, 'phnom-penh': PHNOM };

// Build the sprite markup for a game config. Injected once; cells reference it.
export function buildSprite(gameConfig) {
  const art = ART[gameConfig.id] || ROMA;
  const accent = gameConfig.theme.palette.accent;
  let syms = '';
  for (const id of Object.keys(gameConfig.symbols)) {
    const inner = art[id] || plaque('');
    syms += `<symbol id="s-${id}" viewBox="0 0 100 100">${inner}</symbol>`;
  }
  return `<svg id="symbol-sprite" aria-hidden="true" style="position:absolute;width:0;height:0;overflow:hidden">
    <defs>${sharedDefs(accent)}</defs>${syms}</svg>`;
}

// Markup for a single symbol reference (used inside a reel cell).
export function symUse(id) {
  return `<svg class="sym" viewBox="0 0 100 100"><use href="#s-${id}"/></svg>`;
}

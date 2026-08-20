// Original anime/cel-shaded symbol artwork for Roma Elite.
//
// Style: modern anime key-art — saturated base colours, HARD-EDGED shadow shapes
// (never soft gradients on skin), bright rim light on one edge, thick dark
// outlines, and large expressive eyes with layered highlights. Depth ("3D" feel)
// comes from form shading + bevelled bases + specular sweeps rather than from any
// rendered 3D asset.
//
// All art is hand-authored here. No emoji, no third-party or licensed assets.
//
// Symbols are emitted once into a hidden <svg> sprite as reusable <symbol> defs;
// each reel cell references them with <use>, so gradients/filters are shared and
// dozens of on-screen cells stay cheap to render.

// ---- shared gradient + filter defs (authored once per sprite) --------------
function sharedDefs(accent) {
  return `
  <linearGradient id="gGold" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#fff8de"/><stop offset=".3" stop-color="#ffdc73"/>
    <stop offset=".62" stop-color="#e0a52c"/><stop offset="1" stop-color="#8a5c12"/>
  </linearGradient>
  <linearGradient id="gGoldSoft" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffeeb0"/><stop offset="1" stop-color="#c08a20"/>
  </linearGradient>
  <radialGradient id="gPlaque" cx=".5" cy=".34" r=".78">
    <stop offset="0" stop-color="#4a3a68"/><stop offset=".55" stop-color="#2a1f42"/>
    <stop offset="1" stop-color="#100a1e"/>
  </radialGradient>
  <radialGradient id="gGlow" cx=".5" cy=".5" r=".5">
    <stop offset="0" stop-color="${accent}" stop-opacity=".95"/>
    <stop offset="1" stop-color="${accent}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="gSky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffb457"/><stop offset=".5" stop-color="#ff6f91"/>
    <stop offset="1" stop-color="#7b3fa0"/>
  </linearGradient>
  <linearGradient id="gRed" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ff7a6b"/><stop offset=".55" stop-color="#e02d3c"/>
    <stop offset="1" stop-color="#7d0f1c"/>
  </linearGradient>
  <linearGradient id="gBlue" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#9fe4ff"/><stop offset="1" stop-color="#1d4f9c"/>
  </linearGradient>
  <linearGradient id="gGreen" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#a6f5b4"/><stop offset="1" stop-color="#158a45"/>
  </linearGradient>
  <linearGradient id="gPink" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffd0e8"/><stop offset="1" stop-color="#d63b86"/>
  </linearGradient>
  <linearGradient id="gStone" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#fbf4e2"/><stop offset="1" stop-color="#9c8f72"/>
  </linearGradient>
  <linearGradient id="gShine" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset=".55" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>
  <!-- anime iris: bright rim, deep centre -->
  <linearGradient id="gIrisAmber" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#5a2a00"/><stop offset=".45" stop-color="#e08a1e"/>
    <stop offset="1" stop-color="#ffd980"/>
  </linearGradient>
  <linearGradient id="gIrisBlue" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#0d2b5e"/><stop offset=".45" stop-color="#2f7fd4"/>
    <stop offset="1" stop-color="#a8e4ff"/>
  </linearGradient>
  <linearGradient id="gIrisJade" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#06382a"/><stop offset=".45" stop-color="#1f9e70"/>
    <stop offset="1" stop-color="#a8ffd8"/>
  </linearGradient>
  <linearGradient id="gHairDark" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#4a3b6b"/><stop offset="1" stop-color="#1a1030"/>
  </linearGradient>
  <linearGradient id="gSkyWarm" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffcf7a"/><stop offset=".45" stop-color="#e0713f"/>
    <stop offset="1" stop-color="#5c2352"/>
  </linearGradient>
  <linearGradient id="gSkyNight" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffb457"/><stop offset=".42" stop-color="#e8557f"/>
    <stop offset="1" stop-color="#2b2470"/>
  </linearGradient>
  <clipPath id="clipMed"><circle cx="50" cy="50" r="41.5"/></clipPath>
  <clipPath id="clipPlq"><rect x="11" y="11" width="78" height="78" rx="16"/></clipPath>
  <filter id="fSoft" x="-30%" y="-30%" width="160%" height="160%">
    <feDropShadow dx="0" dy="1.4" stdDeviation="1.5" flood-color="#000" flood-opacity=".6"/>
  </filter>
  <filter id="fGlow" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur stdDeviation="2.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>`;
}

// ---- anime face construction helpers ---------------------------------------
// Large expressive eye: thick lash line, gradient iris, twin specular highlights.
// (cx,cy) centre, s = scale, iris = gradient id, flip mirrors the highlight.
function eye(cx, cy, s, iris, flip = 1) {
  return `
    <g transform="translate(${cx} ${cy}) scale(${s * flip} ${s})">
      <ellipse cx="0" cy="0" rx="4.6" ry="5.6" fill="#fffdf7"/>
      <ellipse cx="0" cy=".4" rx="3.5" ry="4.9" fill="url(#${iris})"/>
      <ellipse cx="0" cy="1.2" rx="1.7" ry="2.6" fill="#160a20"/>
      <circle cx="-1.5" cy="-2.2" r="1.7" fill="#fff"/>
      <circle cx="1.4" cy="2.1" r=".8" fill="#fff" opacity=".8"/>
      <path d="M-5 -3.4c1.6-2.6 8.4-2.6 10 0" fill="none" stroke="#160a20" stroke-width="2.4" stroke-linecap="round"/>
      <path d="M-5.2 -3.6l-1.6-2.2M5.2 -3.6l1.6-2.2" stroke="#160a20" stroke-width="1.8" stroke-linecap="round"/>
    </g>`;
}
// Anime head: rounded cranium tapering to a soft pointed chin, HARD shadow band
// beneath the fringe (never a soft gradient — that is what makes it read as cel).
// Anchored at (cx,cy) = centre of the cranium; r = cranium radius.
function head(cx, cy, r, skin, shade) {
  const chin = cy + r * 1.45;
  return `
    <path d="M${cx - r} ${cy}a${r} ${r} 0 0 1 ${r * 2} 0
             c0 ${r * .62} -${r * .5} ${r * 1.1} -${r} ${r * 1.45}
             c-${r * .5} -${r * .35} -${r} -${r * .83} -${r} -${r * 1.45}z"
          fill="${skin}" stroke="#3a1f14" stroke-width="1.2" stroke-linejoin="round"/>
    <path d="M${cx - r * .97} ${cy - r * .1}a${r} ${r} 0 0 1 ${r * 1.94} 0
             c0 ${r * .3} -${r * 1.94} ${r * .3} -${r * 1.94} 0z" fill="${shade}"/>
    <path d="M${cx + r * .2} ${cy + r * .5}l1.7 2.2h-3.2z" fill="${shade}"/>
    <path d="M${cx - 3} ${chin - r * .34}q3 2.6 6 0" fill="none" stroke="#8a3a2a" stroke-width="1.6" stroke-linecap="round"/>`;
}
// Neck + shoulders. Shoulders deliberately overflow the frame and are clipped,
// so the character reads as a cropped bust portrait rather than a floating doll.
function bust(cx, cy, r, skin, shade, robe, robeEdge, collar = '') {
  const chin = cy + r * 1.45;
  const neckTop = chin - r * .34;
  const shTop = chin + r * .52;           // shoulder line, just below the neck
  return `
    <path d="M${cx - r * 3.3} 104
             C${cx - r * 2.5} ${shTop + r * .3} ${cx - r * 1.15} ${shTop} ${cx} ${shTop}
             C${cx + r * 1.15} ${shTop} ${cx + r * 2.5} ${shTop + r * .3} ${cx + r * 3.3} 104z"
          fill="${robe}" stroke="${robeEdge}" stroke-width="1.3"/>
    <path d="M${cx - r * .34} ${neckTop}h${r * .68}v${shTop - neckTop + 1}h-${r * .68}z" fill="${skin}" stroke="#3a1f14" stroke-width="1"/>
    <path d="M${cx - r * .34} ${neckTop}h${r * .68}v${r * .34}h-${r * .68}z" fill="${shade}"/>${collar}`;
}

// Themed backdrops. A lit sky plus architecture silhouettes behind the bust is
// what separates "character portrait" from "figure floating on a flat disc".
// Kept deliberately DARK and low-saturation: the backdrop must sit well below the
// lit character in value, or the bust loses separation and the whole tile muddies.
const BG_ROMA = `
  <rect x="0" y="0" width="100" height="100" fill="#1d1030"/>
  <circle cx="50" cy="42" r="30" fill="url(#gSkyWarm)" opacity=".38"/>
  <circle cx="50" cy="42" r="17" fill="#ffcf7a" opacity=".22"/>
  <g fill="#0e0720" opacity=".8">
    <rect x="3" y="32" width="10" height="72"/><rect x="17" y="26" width="10" height="78"/>
    <rect x="73" y="26" width="10" height="78"/><rect x="87" y="32" width="10" height="72"/>
    <path d="M0 32h16v-6H0zM14 26h16v-6H14zM70 26h16v-6H70zM84 32h16v-6H84z"/>
  </g>`;
const BG_PP = `
  <rect x="0" y="0" width="100" height="100" fill="#100b2c"/>
  <circle cx="50" cy="40" r="30" fill="url(#gSkyNight)" opacity=".42"/>
  <circle cx="50" cy="40" r="16" fill="#ffd7a0" opacity=".24"/>
  <g fill="#080520" opacity=".82">
    <path d="M2 80V50l9-11 9 11v30zM80 80V52l9-11 9 11v28z"/>
    <path d="M22 80V58l7-9 7 9v22zM64 80V58l7-9 7 9v22z"/>
  </g>`;

// A round bevelled medallion for premium (character) symbols. Inner art is
// CLIPPED to the disc so busts crop cleanly at the gold ring.
function medallion(inner) {
  return `
    <circle cx="50" cy="50" r="47" fill="url(#gGlow)" opacity=".6"/>
    <circle cx="50" cy="50" r="44" fill="url(#gPlaque)"/>
    <g clip-path="url(#clipMed)"><g filter="url(#fSoft)">${inner}</g></g>
    <circle cx="50" cy="50" r="44" fill="none" stroke="url(#gGold)" stroke-width="5"/>
    <circle cx="50" cy="50" r="40.5" fill="none" stroke="#000" stroke-opacity=".38" stroke-width="1.2"/>
    <path d="M22 32a40 40 0 0 1 34-11" fill="none" stroke="url(#gShine)" stroke-width="3.5" stroke-linecap="round" opacity=".7"/>`;
}
// A bevelled plaque for medium/low (object) symbols.
function plaque(inner) {
  return `
    <circle cx="50" cy="50" r="44" fill="url(#gGlow)" opacity=".34"/>
    <rect x="9" y="9" width="82" height="82" rx="18" fill="url(#gPlaque)"/>
    <g clip-path="url(#clipPlq)"><g filter="url(#fSoft)" transform="translate(50 52) scale(1.3) translate(-50 -50)">${inner}</g></g>
    <rect x="9" y="9" width="82" height="82" rx="18" fill="none" stroke="url(#gGoldSoft)" stroke-width="3"/>
    <path d="M18 26a30 30 0 0 1 26-12" fill="none" stroke="url(#gShine)" stroke-width="2.5" stroke-linecap="round" opacity=".5"/>`;
}

// ---- Roma Elite ------------------------------------------------------------
const ROMA = {
  // Young emperor: swept dark hair, gold laurel hugging the temples, crimson
  // cape over gold cuirass, fierce amber eyes.
  EMPEROR: medallion(`${BG_ROMA}
    ${bust(50, 34, 18, '#f6cda3', '#d99a70', 'url(#gRed)', '#5c0d16', `
      <path d="M28 104c1-14 10-22 22-22s21 8 22 22z" fill="url(#gGold)"/>
      <path d="M38 84c4 3 8 5 12 5s8-2 12-5l4 7c-6 4-11 6-16 6s-10-2-16-6z" fill="#c9202f"/>`)}
    ${head(50, 34, 18, '#f6cda3', '#d99a70')}
    <path d="M31 33c0-14 8-22 19-22s19 8 19 22c-2-8-5-12-9-14l-3 7-5-8-6 9-5-7c-5 2-8 6-10 13z"
      fill="url(#gHairDark)" stroke="#160a20" stroke-width="1.1"/>
    <path d="M36 17c4 4 8 6 13 5l-3 6z" fill="#6b56a0" opacity=".85"/>
    <path d="M31 27a20 20 0 0 1 38 0" fill="none" stroke="#14521c" stroke-width="2.4"/>
    <g fill="#2f8f3a" stroke="#14521c" stroke-width=".8">
      <ellipse cx="34" cy="30" rx="5.6" ry="2.8" transform="rotate(-64 34 30)"/>
      <ellipse cx="37" cy="22" rx="5.6" ry="2.8" transform="rotate(-44 37 22)"/>
      <ellipse cx="43" cy="17" rx="5.6" ry="2.8" transform="rotate(-24 43 17)"/>
      <ellipse cx="66" cy="30" rx="5.6" ry="2.8" transform="rotate(64 66 30)"/>
      <ellipse cx="63" cy="22" rx="5.6" ry="2.8" transform="rotate(44 63 22)"/>
      <ellipse cx="57" cy="17" rx="5.6" ry="2.8" transform="rotate(24 57 17)"/>
    </g>
    <ellipse cx="50" cy="15" rx="4.5" ry="4" fill="url(#gGold)" stroke="#8a5c12" stroke-width="1"/>
    ${eye(42.5, 38, 1.25, 'gIrisAmber')}${eye(57.5, 38, 1.25, 'gIrisAmber', -1)}
    `),

  // Empress: long violet hair falling past the shoulders, tall jewelled diadem,
  // soft blue eyes, rose gown with gold trim.
  EMPRESS: medallion(`${BG_ROMA}
    <path d="M27 44c-11 8-14 32-11 60h12zM73 44c11 8 14 32 11 60H72z"
      fill="url(#gHairDark)" stroke="#160a20" stroke-width="1.1"/>
    ${bust(50, 36, 17, '#fbdcc0', '#e0ab86', 'url(#gPink)', '#8c1e58', `
      <path d="M34 104c2-11 8-17 16-17s14 6 16 17z" fill="#ffe3f1" opacity=".5"/>`)}
    ${head(50, 36, 17, '#fbdcc0', '#e0ab86')}
    <path d="M32 35c0-15 8-23 18-23s18 8 18 23c-3-9-9-13-18-13s-15 4-18 13z"
      fill="url(#gHairDark)" stroke="#160a20" stroke-width="1.1"/>
    <path d="M38 19c5 4 9 5 14 4l-4 6z" fill="#6b56a0" opacity=".85"/>
    <path d="M30 48c-4 8-5 20-3 30l4 1c-2-11-1-22 2-30zM70 48c4 8 5 20 3 30l-4 1c2-11 1-22-2-30z" fill="#6b56a0"/>
    <path d="M33 20l6 8 11-13 11 13 6-8-4 12H37z" fill="url(#gGold)" stroke="#8a5c12" stroke-width="1"/>
    <circle cx="50" cy="7" r="4.5" fill="url(#gBlue)" stroke="url(#gGold)" stroke-width="1.6"/>
    ${eye(42.5, 40, 1.25, 'gIrisBlue')}${eye(57.5, 40, 1.25, 'gIrisBlue', -1)}
    <circle cx="31" cy="70" r="3.4" fill="url(#gGold)"/><circle cx="69" cy="70" r="3.4" fill="url(#gGold)"/>
    `),

  // Legion Commander: crested galea, shadowed visor slot, glowing jade eyes.
  COMMANDER: medallion(`${BG_ROMA}
    ${bust(50, 38, 17, '#f6cda3', '#d99a70', 'url(#gGold)', '#7a4d0c', `
      <path d="M32 88h36l3 8H29z" fill="#c9202f"/>
      <path d="M34 98h32v6H34z" fill="url(#gGoldSoft)"/>`)}
    ${head(50, 38, 17, '#f6cda3', '#d99a70')}
    <path d="M31 40c0-16 8-25 19-25s19 9 19 25v4h-8c0-11-4-17-11-17s-11 6-11 17z"
      fill="url(#gGold)" stroke="#7a4d0c" stroke-width="1.3"/>
    <path d="M31 36h38v8H31z" fill="#241a33" opacity=".5"/>
    <path d="M50 2c10 3 15 12 15 24h-6C59 15 56 8 50 6z" fill="url(#gRed)" stroke="#7d0f1c" stroke-width="1"/>
    <path d="M44 4c-8 5-12 13-12 22h6c0-8 3-15 8-18z" fill="url(#gRed)" stroke="#7d0f1c" stroke-width="1"/>
    <path d="M40 18h20l-3 7H43z" fill="url(#gGoldSoft)"/>
    <path d="M35 44c-4 2-6 6-6 11l5 1c0-5 1-9 4-11zM65 44c4 2 6 6 6 11l-5 1c0-5-1-9-4-11z"
      fill="url(#gGold)" stroke="#7a4d0c" stroke-width="1"/>
    ${eye(42.5, 41, 1.15, 'gIrisJade')}${eye(57.5, 41, 1.15, 'gIrisJade', -1)}
    `),

  // Roman Eagle: heraldic aquila, wings raised in tiers of cel-shaded feathers.
  EAGLE: medallion(`${BG_ROMA}
    <!-- raised wings, built as three feather tiers per side -->
    <g fill="url(#gGold)" stroke="#7a4d0c" stroke-width="1.2" stroke-linejoin="round">
      <path d="M44 44 16 22c-3 9-1 18 5 25l20 6z"/>
      <path d="M44 52 12 42c-1 9 3 17 10 22l21 1z"/>
      <path d="M44 60 16 60c2 8 8 14 16 17l13-6z"/>
      <path d="M56 44 84 22c3 9 1 18-5 25l-20 6z"/>
      <path d="M56 52 88 42c1 9-3 17-10 22l-21 1z"/>
      <path d="M56 60 84 60c-2 8-8 14-16 17l-13-6z"/>
    </g>
    <g fill="#fff8de" opacity=".45">
      <path d="M20 26c6 5 13 10 20 14l-2 3c-8-4-14-9-20-14z"/>
      <path d="M80 26c-6 5-13 10-20 14l2 3c8-4 14-9 20-14z"/>
    </g>
    <!-- body, tail and head -->
    <path d="M50 24c-6 0-10 5-10 11v34c0 6 4 11 10 11s10-5 10-11V35c0-6-4-11-10-11z"
      fill="url(#gGold)" stroke="#7a4d0c" stroke-width="1.3"/>
    <path d="M44 76h12l-2 14h-8z" fill="url(#gGoldSoft)" stroke="#7a4d0c" stroke-width="1.1"/>
    <path d="M46 44h8v22h-8z" fill="#c9202f" opacity=".85"/>
    <circle cx="50" cy="26" r="10" fill="url(#gGoldSoft)" stroke="#7a4d0c" stroke-width="1.2"/>
    <path d="M50 30l7 5-7 3-7-3z" fill="#e0a52c" stroke="#7a4d0c" stroke-width=".9"/>
    <circle cx="46" cy="23" r="3.2" fill="#fffdf7"/><circle cx="46.6" cy="23" r="1.9" fill="#160a20"/>
    <circle cx="54" cy="23" r="3.2" fill="#fffdf7"/><circle cx="53.4" cy="23" r="1.9" fill="#160a20"/>
    <circle cx="45.4" cy="22" r=".9" fill="#fff"/><circle cx="54.6" cy="22" r=".9" fill="#fff"/>
    `),

  CHARIOT: plaque(`
    <circle cx="40" cy="60" r="17" fill="none" stroke="url(#gGold)" stroke-width="5"/>
    <g stroke="url(#gGoldSoft)" stroke-width="2.4"><path d="M40 45v30M25 60h30M30 50l20 20M50 50 30 70"/></g>
    <circle cx="40" cy="60" r="5" fill="url(#gGold)"/>
    <path d="M56 40c8-3 16 0 21 7-5-2-10-1-13 2l-4 10-7-3z" fill="url(#gRed)" stroke="#7d0f1c" stroke-width="1"/>
    <path d="M58 42c5-2 10-1 14 2" stroke="#fff6d2" stroke-width="1.6" fill="none" opacity=".7"/>`),

  // Victory wreath: an open ring of leaves, tied with a ribbon at the base.
  LAUREL: plaque(`
    <path d="M50 22a30 30 0 0 1 26 44" fill="none" stroke="#0d5c2e" stroke-width="3"/>
    <path d="M50 22a30 30 0 0 0-26 44" fill="none" stroke="#0d5c2e" stroke-width="3"/>
    <g fill="url(#gGreen)" stroke="#0d5c2e" stroke-width=".9">
      <ellipse cx="42" cy="25" rx="7" ry="3.6" transform="rotate(-28 42 25)"/>
      <ellipse cx="31" cy="34" rx="7" ry="3.6" transform="rotate(-52 31 34)"/>
      <ellipse cx="25" cy="47" rx="7" ry="3.6" transform="rotate(-76 25 47)"/>
      <ellipse cx="25" cy="61" rx="7" ry="3.6" transform="rotate(-104 25 61)"/>
      <ellipse cx="58" cy="25" rx="7" ry="3.6" transform="rotate(28 58 25)"/>
      <ellipse cx="69" cy="34" rx="7" ry="3.6" transform="rotate(52 69 34)"/>
      <ellipse cx="75" cy="47" rx="7" ry="3.6" transform="rotate(76 75 47)"/>
      <ellipse cx="75" cy="61" rx="7" ry="3.6" transform="rotate(104 75 61)"/>
    </g>
    <g fill="#a6f5b4" opacity=".65">
      <ellipse cx="30" cy="33" rx="4" ry="1.6" transform="rotate(-52 30 33)"/>
      <ellipse cx="24" cy="46" rx="4" ry="1.6" transform="rotate(-76 24 46)"/>
    </g>
    <path d="M38 70c5 6 19 6 24 0l6 10c-9 6-27 6-36 0z" fill="url(#gRed)" stroke="#7d0f1c" stroke-width="1"/>
    <circle cx="50" cy="70" r="5" fill="url(#gGold)" stroke="#7a4d0c" stroke-width="1"/>`),

  TREASURY: plaque(`
    <rect x="24" y="48" width="52" height="28" rx="4" fill="url(#gGoldSoft)" stroke="#7a4d0c" stroke-width="1.2"/>
    <path d="M24 48c0-12 12-17 26-17s26 5 26 17z" fill="url(#gGold)" stroke="#7a4d0c" stroke-width="1.2"/>
    <rect x="24" y="52" width="52" height="6" fill="#8a5c12" opacity=".55"/>
    <rect x="44" y="56" width="12" height="14" rx="3" fill="#241a33"/>
    <circle cx="50" cy="62" r="2.4" fill="url(#gGold)"/>
    <path d="M30 36c5-4 12-6 20-6" stroke="#fff6d2" stroke-width="2" fill="none" opacity=".7"/>
    <circle cx="34" cy="42" r="4.5" fill="#ffdc73"/><circle cx="66" cy="44" r="3.8" fill="#ffdc73"/>`),

  SHIELD: plaque(`
    <path d="M50 22c9 5 19 6 19 6v21c0 14-9 24-19 29-10-5-19-15-19-29V28s10-1 19-6z" fill="url(#gRed)" stroke="url(#gGold)" stroke-width="3"/>
    <path d="M50 30v40M38 46h24" stroke="url(#gGold)" stroke-width="3.5"/>
    <path d="M36 30c4-2 9-3 14-5v8c-5 1-10 2-14 3z" fill="#fff" opacity=".22"/>`),

  // Wine amphora: flared lip, narrow neck, swelling body, tapered foot.
  AMPHORA: plaque(`
    <path d="M40 20h20l-2 6H42z" fill="url(#gStone)" stroke="#7a6b4a" stroke-width="1.2"/>
    <path d="M44 26h12l2 8H42z" fill="url(#gStone)" stroke="#7a6b4a" stroke-width="1.2"/>
    <path d="M42 34h16c9 5 14 14 14 24 0 12-10 20-22 20s-22-8-22-20c0-10 5-19 14-24z"
      fill="url(#gStone)" stroke="#7a6b4a" stroke-width="1.4"/>
    <path d="M46 78h8l2 8H44z" fill="url(#gStone)" stroke="#7a6b4a" stroke-width="1.2"/>
    <path d="M42 30c-8 1-13 7-12 15 1-5 5-9 12-10zM58 30c8 1 13 7 12 15-1-5-5-9-12-10z"
      fill="none" stroke="url(#gGoldSoft)" stroke-width="3.4" stroke-linecap="round"/>
    <path d="M40 42c-5 6-7 14-6 22l4 1c-1-9 0-17 5-22z" fill="#fff" opacity=".5"/>
    <path d="M32 56h36" stroke="#c9202f" stroke-width="3" opacity=".65"/>
    <path d="M34 64h32" stroke="#7a6b4a" stroke-width="1.4" opacity=".5"/>`),

  COIN: plaque(`
    <circle cx="50" cy="50" r="24" fill="url(#gGold)" stroke="#7a4d0c" stroke-width="2.4"/>
    <circle cx="50" cy="50" r="18" fill="none" stroke="#8a5c12" stroke-width="1.6" opacity=".6"/>
    <path d="M50 37l4 8.5 9 .8-6.8 5.6 2.2 8.6L50 55.6 41.6 60.5l2.2-8.6L37 46.3l9-.8z" fill="#8a5c12" opacity=".75"/>
    <path d="M34 38a22 22 0 0 1 14-9" stroke="#fff8de" stroke-width="2.6" fill="none" opacity=".8"/>`),

  WILD: `
    <rect x="16" y="12" width="68" height="76" rx="12" fill="url(#gGlow)" opacity=".55"/>
    <rect x="32" y="14" width="7" height="72" rx="3.5" fill="url(#gGold)" stroke="#7a4d0c" stroke-width="1"/>
    <path d="M39 18h38l-7 10 7 10H39z" fill="url(#gRed)" stroke="url(#gGold)" stroke-width="2.4" filter="url(#fGlow)"/>
    <text x="57" y="32" font-family="Cinzel,serif" font-size="10" font-weight="900" fill="#fff8de" text-anchor="middle">SPQR</text>
    <path d="M35 16c1 6 1 40 0 60" stroke="#fff8de" stroke-width="1.6" fill="none" opacity=".7"/>
    <text x="50" y="72" font-family="Cinzel,serif" font-size="17" font-weight="900" fill="url(#gGold)" stroke="#3a2410" stroke-width=".8" text-anchor="middle" filter="url(#fGlow)">WILD</text>`,

  SCATTER: `
    <ellipse cx="50" cy="46" rx="44" ry="40" fill="url(#gGlow)" opacity=".6"/>
    <path d="M14 62c0-20 16-34 36-34s36 14 36 34v6H14z" fill="url(#gPlaque)" stroke="url(#gGold)" stroke-width="4" filter="url(#fGlow)"/>
    <g fill="url(#gGoldSoft)" stroke="#7a4d0c" stroke-width=".8">
      <rect x="22" y="44" width="9" height="24" rx="4"/><rect x="36" y="38" width="9" height="30" rx="4"/>
      <rect x="55" y="38" width="9" height="30" rx="4"/><rect x="69" y="44" width="9" height="24" rx="4"/>
    </g>
    <path d="M20 50c4-10 15-17 28-17" stroke="#fff8de" stroke-width="2.4" fill="none" opacity=".65"/>
    <text x="50" y="86" font-family="Cinzel,serif" font-size="13" font-weight="900" fill="url(#gGold)" stroke="#3a2410" stroke-width=".8" text-anchor="middle" filter="url(#fGlow)">BONUS</text>`,
};

// ---- Phnom Penh Nights -----------------------------------------------------
const PHNOM = {
  PALACE: medallion(`${BG_PP}
    <path d="M50 12l4 11h-8z" fill="url(#gGold)"/>
    <path d="M50 20c11 8 16 19 16 30v30H34V50c0-11 5-22 16-30z" fill="url(#gGold)" stroke="#7a4d0c" stroke-width="1.3"/>
    <path d="M34 50l16-13 16 13zM30 64l20-15 20 15z" fill="url(#gGoldSoft)" stroke="#7a4d0c" stroke-width="1"/>
    <path d="M40 54c3-3 7-5 10-6v6c-4 1-7 2-10 3z" fill="#fff8de" opacity=".55"/>
    <rect x="44" y="64" width="12" height="16" rx="3" fill="#241a33"/>
    <path d="M30 80h40v6H30z" fill="url(#gGoldSoft)" stroke="#7a4d0c" stroke-width="1"/>
    `),

  TEMPLE: medallion(`${BG_PP}
    <path d="M50 10l3 9h-6z" fill="url(#gGold)"/>
    <path d="M42 20h16l-3 9H45zM38 31h24l-3 10H41zM34 43h32l-4 11H38zM30 56h40l-4 12H34zM27 70h46v12H27z"
      fill="url(#gGold)" stroke="#7a4d0c" stroke-width="1.1"/>
    <path d="M44 22h4l-1 7h-2zM40 33h5l-1 8h-3zM36 45h6l-2 9h-4z" fill="#fff8de" opacity=".5"/>
    <rect x="44" y="72" width="12" height="10" rx="2" fill="#241a33"/>
    `),

  // Golden Naga: anime dragon — big jade eye, cel-shaded scale bands, flowing body.
  NAGA: medallion(`${BG_PP}
    <path d="M50 84c-11 0-17-8-17-17 0-11 11-14 11-25 0-7-4-11-4-16 6 0 10 5 10 12 0 8-6 12-6 19 0 5 3 8 6 8s6-3 6-8c0-7-6-11-6-19 0-7 4-12 10-12 0 5-4 9-4 16 0 11 11 14 11 25 0 9-6 17-17 17z"
      fill="url(#gGold)" stroke="#7a4d0c" stroke-width="1.3"/>
    <path d="M42 52c-3 8 0 15 4 19l3-2c-4-4-6-10-4-17z" fill="#fff8de" opacity=".5"/>
    <g fill="url(#gGoldSoft)" stroke="#7a4d0c" stroke-width=".7">
      <path d="M36 24c-6-3-10 0-10 6 4-2 7-2 10 1z"/><path d="M64 24c6-3 10 0 10 6-4-2-7-2-10 1z"/>
      <path d="M40 16c-4-5-9-4-11 1 4 0 7 1 9 3zM60 16c4-5 9-4 11 1-4 0-7 1-9 3z"/>
    </g>
    ${eye(44, 28, .95, 'gIrisJade')}${eye(56, 28, .95, 'gIrisJade', -1)}
    <path d="M46 38q4 4 8 0" fill="none" stroke="#7a4d0c" stroke-width="1.8" stroke-linecap="round"/>
    `),

  // Apsara dancer: celestial dancer with the tall tiered gold mokot headdress,
  // gold collar and amber eyes.
  APSARA: medallion(`${BG_PP}
    <path d="M28 46c-10 8-13 32-11 58h11zM72 46c10 8 13 32 11 58H72z"
      fill="url(#gHairDark)" stroke="#160a20" stroke-width="1.1"/>
    ${bust(50, 41, 16, '#f3c79b', '#d1976a', 'url(#gPink)', '#8c1e58', `
      <path d="M31 92c4-6 11-9 19-9s15 3 19 9l3 12H28z" fill="url(#gGold)" stroke="#7a4d0c" stroke-width="1.1"/>
      <g fill="url(#gGoldSoft)"><circle cx="39" cy="97" r="3"/><circle cx="50" cy="95" r="3"/><circle cx="61" cy="97" r="3"/></g>`)}
    ${head(50, 41, 16, '#f3c79b', '#d1976a')}
    <path d="M33 41c0-14 8-22 17-22s17 8 17 22c-3-9-9-13-17-13s-14 4-17 13z"
      fill="url(#gHairDark)" stroke="#160a20" stroke-width="1.1"/>
    <!-- tiered mokot headdress, sized to sit inside the medallion crop -->
    <path d="M50 9l5 9H45z" fill="url(#gGold)" stroke="#7a4d0c" stroke-width="1"/>
    <path d="M43 18h14l-2 6H45zM40 24h20l-2 6H42z" fill="url(#gGold)" stroke="#7a4d0c" stroke-width="1"/>
    <path d="M36 30h28l-3 8H39z" fill="url(#gGoldSoft)" stroke="#7a4d0c" stroke-width="1"/>
    <circle cx="50" cy="13" r="2.6" fill="url(#gGreen)" stroke="url(#gGold)" stroke-width=".9"/>
    <path d="M45 20h4l-1 4h-2z" fill="#fff8de" opacity=".6"/>
    ${eye(42.5, 44, 1.2, 'gIrisAmber')}${eye(57.5, 44, 1.2, 'gIrisAmber', -1)}
    `),

  TUKTUK: plaque(`
    <path d="M26 64V46h18l7-9h15v27z" fill="url(#gGreen)" stroke="#0d5c2e" stroke-width="1.4"/>
    <path d="M26 42h40v5H26z" fill="url(#gGold)" stroke="#7a4d0c" stroke-width="1"/>
    <path d="M30 48h12v10H30z" fill="#a8e4ff" opacity=".55"/>
    <circle cx="36" cy="68" r="7" fill="#241a33" stroke="url(#gGold)" stroke-width="2.4"/>
    <circle cx="64" cy="68" r="7" fill="#241a33" stroke="url(#gGold)" stroke-width="2.4"/>
    <circle cx="36" cy="68" r="2.4" fill="url(#gGoldSoft)"/><circle cx="64" cy="68" r="2.4" fill="url(#gGoldSoft)"/>
    <path d="M20 56l8-3v7h-8z" fill="url(#gGoldSoft)"/>
    <path d="M28 44c4-1 9-2 14-2" stroke="#fff8de" stroke-width="1.8" fill="none" opacity=".7"/>`),

  LOTUS: plaque(`
    <path d="M50 28c5 8 6 18 0 30-6-12-5-22 0-30z" fill="url(#gPink)" stroke="#8c1e58" stroke-width="1"/>
    <path d="M50 58c-8-7-10-18-8-28 8 5 12 16 8 28zM50 58c8-7 10-18 8-28-8 5-12 16-8 28z" fill="#ffd0e8" stroke="#8c1e58" stroke-width=".9"/>
    <path d="M50 58c-11-3-18-11-19-21 10 2 18 10 19 21zM50 58c11-3 18-11 19-21-10 2-18 10-19 21z" fill="url(#gPink)" stroke="#8c1e58" stroke-width=".9"/>
    <circle cx="50" cy="54" r="5" fill="url(#gGold)"/>
    <ellipse cx="50" cy="66" rx="20" ry="5" fill="url(#gGreen)" stroke="#0d5c2e" stroke-width="1"/>`),

  BOAT: plaque(`
    <path d="M18 54c10 10 54 10 64 0-5 12-16 17-32 17s-27-5-32-17z" fill="url(#gGold)" stroke="#7a4d0c" stroke-width="1.3"/>
    <path d="M18 54c-4-3-5-8-2-11 4 3 6 5 7 8zM82 54c4-3 5-8 2-11-4 3-6 5-7 8z" fill="url(#gRed)" stroke="#7d0f1c" stroke-width="1"/>
    <g stroke="url(#gGoldSoft)" stroke-width="2.6" stroke-linecap="round"><path d="M32 54V42M43 54V40M57 54V40M68 54V42"/></g>
    <g fill="#c9202f"><circle cx="32" cy="40" r="2.6"/><circle cx="43" cy="38" r="2.6"/><circle cx="57" cy="38" r="2.6"/><circle cx="68" cy="40" r="2.6"/></g>
    <path d="M24 60c14 5 38 5 52 0" stroke="#a8e4ff" stroke-width="2" fill="none" opacity=".5"/>`),

  NUMPANG: plaque(`
    <path d="M22 56c0-10 12-15 28-15s28 5 28 15c0 5-5 9-12 10H34c-7-1-12-5-12-10z" fill="url(#gGoldSoft)" stroke="#8a5c12" stroke-width="1.3"/>
    <path d="M30 46c6-3 13-4 20-4" stroke="#fff8de" stroke-width="2" fill="none" opacity=".7"/>
    <path d="M26 58c14 4 34 4 48 0-3 4-7 6-11 7H37c-4-1-8-3-11-7z" fill="url(#gGreen)" stroke="#0d5c2e" stroke-width="1"/>
    <path d="M24 60c15 5 37 5 52 0" stroke="url(#gRed)" stroke-width="4" fill="none" stroke-linecap="round"/>
    <circle cx="38" cy="62" r="2.2" fill="#ff7a6b"/><circle cx="58" cy="63" r="2.2" fill="#ff7a6b"/>`),

  KRAMA: plaque(`
    <rect x="26" y="26" width="48" height="48" rx="5" fill="#e02d3c" stroke="#7d0f1c" stroke-width="1.3"/>
    <g fill="#fffdf7" opacity=".95">
      <rect x="26" y="26" width="12" height="12"/><rect x="50" y="26" width="12" height="12"/>
      <rect x="38" y="38" width="12" height="12"/><rect x="62" y="38" width="12" height="12"/>
      <rect x="26" y="50" width="12" height="12"/><rect x="50" y="50" width="12" height="12"/>
      <rect x="38" y="62" width="12" height="12"/><rect x="62" y="62" width="12" height="12"/>
    </g>
    <rect x="26" y="26" width="48" height="48" rx="5" fill="none" stroke="url(#gGold)" stroke-width="2.6"/>
    <path d="M30 32c4-3 9-4 14-4" stroke="#fff" stroke-width="2" fill="none" opacity=".6"/>`),

  RIEL: plaque(`
    <circle cx="50" cy="50" r="24" fill="url(#gGold)" stroke="#7a4d0c" stroke-width="2.4"/>
    <circle cx="50" cy="50" r="18" fill="none" stroke="#8a5c12" stroke-width="1.6" opacity=".6"/>
    <path d="M42 62V38l8 10 8-10v24" fill="none" stroke="#8a5c12" stroke-width="3.6" opacity=".8"/>
    <path d="M34 38a22 22 0 0 1 14-9" stroke="#fff8de" stroke-width="2.6" fill="none" opacity=".8"/>`),

  WILD: `
    <rect x="16" y="10" width="68" height="80" rx="12" fill="url(#gGlow)" opacity=".55"/>
    <path d="M50 14c5 7 5 14 0 20-5-6-5-13 0-20z" fill="url(#gGold)" stroke="#7a4d0c" stroke-width="1" filter="url(#fGlow)"/>
    <path d="M38 36h24l-4 26H42z" fill="url(#gGoldSoft)" stroke="url(#gGold)" stroke-width="1.8"/>
    <path d="M42 38h5l-3 22h-4z" fill="#fff8de" opacity=".55"/>
    <rect x="33" y="62" width="34" height="7" rx="3" fill="url(#gGold)" stroke="#7a4d0c" stroke-width="1"/>
    <text x="50" y="86" font-family="Cinzel,serif" font-size="17" font-weight="900" fill="url(#gGold)" stroke="#3a2410" stroke-width=".8" text-anchor="middle" filter="url(#fGlow)">WILD</text>`,

  // Bonus host: original fictional anime character (suit + shades, neon skyline).
  SCATTER: `
    <circle cx="50" cy="44" r="40" fill="url(#gGlow)" opacity=".65"/>
    <circle cx="50" cy="44" r="34" fill="url(#gSky)" stroke="url(#gGold)" stroke-width="3.5" filter="url(#fGlow)"/>
    <g opacity=".4" fill="#2a1030"><rect x="16" y="50" width="9" height="30"/><rect x="29" y="42" width="8" height="38"/><rect x="64" y="44" width="8" height="36"/><rect x="76" y="52" width="9" height="28"/></g>
    <g clip-path="url(#clipMed)">
      ${bust(50, 36, 15, '#e8b88a', '#c08a5e', '#1b2440', '#0b1020', `
        <path d="M42 60l8 11 8-11-3 24H45z" fill="#fffdf7"/>
        <path d="M50 71l6 4-3 16-3-7-3 7-3-16z" fill="#1f9e70" stroke="#0d5c46" stroke-width=".7"/>
        <path d="M34 78c-4 4-6 10-6 18h5c0-7 1-13 4-16zM66 78c4 4 6 10 6 18h-5c0-7-1-13-4-16z" fill="#2b3a5e"/>`)}
      ${head(50, 36, 15, '#e8b88a', '#c08a5e')}
      <path d="M34 36c1-14 7-21 16-21s15 7 16 21c-4-8-9-11-16-11s-12 3-16 11z"
        fill="#241a33" stroke="#0b0616" stroke-width="1.1"/>
      <path d="M39 21c4 3 8 4 12 3l-3 5z" fill="#4a3b6b" opacity=".8"/>
      <g fill="#0d1020" stroke="#000" stroke-width=".9">
        <rect x="34" y="37" width="14" height="9" rx="4.5"/><rect x="52" y="37" width="14" height="9" rx="4.5"/>
        <rect x="47" y="39.5" width="6" height="3" rx="1"/>
      </g>
      <path d="M36 40l5-1.4 4 3.4" stroke="#fff" stroke-width="1.6" fill="none" opacity=".85"/>
      <path d="M54 40l5-1.4 4 3.4" stroke="#fff" stroke-width="1.6" fill="none" opacity=".5"/>
      <path d="M46 55q4 3 8 0" fill="none" stroke="#8a3a2a" stroke-width="1.7" stroke-linecap="round"/>
      
    </g>
    <text x="50" y="93" font-family="Cinzel,serif" font-size="12" font-weight="900" fill="url(#gGold)" stroke="#3a2410" stroke-width=".8" text-anchor="middle" filter="url(#fGlow)">BONUS</text>`,
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

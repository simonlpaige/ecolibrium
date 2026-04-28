/* Reusable SVG primitives for the Commonweave brand mark.
   We deliberately keep these simple: a wordmark ("commonweave")
   set in italic display, with a horizontal warp/weft rule that
   threads through the descenders, OR a typographic monogram. */

window.CommonweaveLogo = (function () {

  // Direction A: "The Weave" — wordmark with a thread that
  // crosses under and through the descenders.
  function weaveSVG({ size = 480, color = "#16201A", thread = "#2F4A33", accent = "#B4593A", showThread = true } = {}) {
    const w = size, h = size * 0.34;
    return `
<svg viewBox="0 0 600 200" width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="commonweave">
  <defs>
    <style>
      .word { font-family: 'Instrument Serif', 'Source Serif 4', Georgia, serif; font-style: italic; font-weight: 400; }
    </style>
  </defs>
  <!-- weft thread (horizontal) -->
  ${showThread ? `<path d="M 20 132 Q 150 132 150 132 T 580 132" stroke="${thread}" stroke-width="1.4" fill="none"/>` : ""}
  <!-- the wordmark -->
  <text x="20" y="130" class="word" font-size="148" fill="${color}" letter-spacing="-3">commonweave</text>
  <!-- warp threads (vertical, subtle) crossing the w's -->
  ${showThread ? `
    <line x1="395" y1="60" x2="395" y2="172" stroke="${accent}" stroke-width="1.2" opacity="0.85"/>
    <line x1="455" y1="60" x2="455" y2="172" stroke="${thread}" stroke-width="1.2" opacity="0.85"/>
  ` : ""}
  <!-- the dot of the i (commonweave has none, but a punctum after the e) -->
  <circle cx="572" cy="120" r="4" fill="${accent}"/>
</svg>`.trim();
  }

  // Direction B: "The Common" — a circular field enclosing
  // a small woven cross. Standalone mark, scales to favicon.
  function commonSVG({ size = 200, color = "#16201A", inner = "#2F4A33", accent = "#B4593A" } = {}) {
    return `
<svg viewBox="0 0 200 200" width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="commonweave mark">
  <!-- the field: a hand-feeling circle -->
  <circle cx="100" cy="100" r="86" fill="none" stroke="${color}" stroke-width="2"/>
  <!-- horizon line -->
  <line x1="14" y1="100" x2="186" y2="100" stroke="${color}" stroke-width="1" opacity="0.4"/>
  <!-- the weave: two crossing arcs forming a knot at center -->
  <path d="M 60 60 C 80 100, 120 100, 140 140" stroke="${inner}" stroke-width="3" fill="none" stroke-linecap="round"/>
  <path d="M 140 60 C 120 100, 80 100, 60 140" stroke="${inner}" stroke-width="3" fill="none" stroke-linecap="round"/>
  <!-- the seed at the cross -->
  <circle cx="100" cy="100" r="4.5" fill="${accent}"/>
</svg>`.trim();
  }

  // Lockup: mark + wordmark side by side
  function lockupSVG({ width = 520, color = "#16201A", inner = "#2F4A33", accent = "#B4593A" } = {}) {
    return `
<svg viewBox="0 0 520 130" width="${width}" height="${width * 0.25}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="commonweave">
  <g transform="translate(0,5)">
    <circle cx="60" cy="60" r="56" fill="none" stroke="${color}" stroke-width="1.6"/>
    <line x1="6" y1="60" x2="114" y2="60" stroke="${color}" stroke-width="0.8" opacity="0.4"/>
    <path d="M 30 30 C 50 60, 70 60, 90 90" stroke="${inner}" stroke-width="2.2" fill="none" stroke-linecap="round"/>
    <path d="M 90 30 C 70 60, 50 60, 30 90" stroke="${inner}" stroke-width="2.2" fill="none" stroke-linecap="round"/>
    <circle cx="60" cy="60" r="3" fill="${accent}"/>
  </g>
  <text x="140" y="80" font-family="Instrument Serif, Source Serif 4, Georgia, serif" font-style="italic" font-size="64" fill="${color}" letter-spacing="-1.5">commonweave</text>
</svg>`.trim();
  }

  // Stacked lockup
  function stackedSVG({ width = 280, color = "#16201A", inner = "#2F4A33", accent = "#B4593A" } = {}) {
    return `
<svg viewBox="0 0 280 260" width="${width}" height="${width * (260/280)}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="commonweave">
  <g transform="translate(60,10)">
    <circle cx="80" cy="80" r="76" fill="none" stroke="${color}" stroke-width="1.8"/>
    <line x1="6" y1="80" x2="154" y2="80" stroke="${color}" stroke-width="0.8" opacity="0.4"/>
    <path d="M 36 36 C 64 80, 96 80, 124 124" stroke="${inner}" stroke-width="2.6" fill="none" stroke-linecap="round"/>
    <path d="M 124 36 C 96 80, 64 80, 36 124" stroke="${inner}" stroke-width="2.6" fill="none" stroke-linecap="round"/>
    <circle cx="80" cy="80" r="4" fill="${accent}"/>
  </g>
  <text x="140" y="230" text-anchor="middle" font-family="Instrument Serif, Source Serif 4, Georgia, serif" font-style="italic" font-size="48" fill="${color}" letter-spacing="-1">commonweave</text>
</svg>`.trim();
  }

  return { weaveSVG, commonSVG, lockupSVG, stackedSVG };
})();

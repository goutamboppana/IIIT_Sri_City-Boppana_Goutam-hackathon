
const path = require("path");
const pptxgen = require("pptxgenjs");

const DOCS = path.join(__dirname, "..", "docs");
const pres = new pptxgen();

pres.layout = "LAYOUT_WIDE";
pres.title = "AI/NLP Risk Engine + Tactical Index Rebalancer + Portfolio Stress Testing";
pres.author = "Goutam Boppana";
pres.subject = "S&P Global & Crisil Campus Hackathon 2026";

const THEME = {
  name: "RiskDesk Dark",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "0B1220",
    lt1: "F1F5F9",
    dk2: "14213A",
    lt2: "9FB0C8",
    accent1: "2DD4BF",
    accent2: "38BDF8",
    accent3: "F59E0B",
    accent4: "60A5FA",
    accent5: "94A3B8",
    accent6: "E2E8F0",
    hlink: "38BDF8",
    folHlink: "94A3B8",
  },
};

pres.theme = {
  headFontFace: THEME.headFontFace,
  bodyFontFace: THEME.bodyFontFace,
};

const BG = "0B1220";
const PANEL = "14213A";
const EDGE = "22345A";
const TXT = "F1F5F9";
const MUTED = "A9B8CE";
const TEAL = "2DD4BF";
const CYAN = "38BDF8";
const AMBER = "F59E0B";
const BLUE = "60A5FA";
const SLATE = "94A3B8";
const FONT = "Calibri";
const MONO = "Courier New";

const VIDEO_URL = "https://youtu.be/91JTRFemLJA";

const FOOT =
  "Goutam Boppana  ·  IIIT Sri City  ·  S&P Global & Crisil Campus Hackathon 2026";

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: BG },
  objects: [
    {
      text: {
        text: FOOT,
        options: {
          x: 0.6,
          y: 7.05,
          w: 9,
          h: 0.3,
          fontFace: FONT,
          fontSize: 10,
          color: SLATE,
          margin: 0,
        },
      },
    },
  ],
  slideNumber: {
    x: 12.1,
    y: 7.05,
    w: 0.63,
    h: 0.3,
    fontFace: FONT,
    fontSize: 10,
    color: SLATE,
    align: "right",
  },
});

pres.defineSlideMaster({
  title: "TITLE_SLIDE",
  background: { color: BG },
  objects: [],
});

function addTitle(slide, text) {
  slide.addText(text, {
    x: 0.6,
    y: 0.35,
    w: 12.13,
    h: 0.75,
    fontFace: FONT,
    fontSize: 34,
    bold: true,
    color: TXT,
    align: "left",
    valign: "middle",
    margin: 0,
    isTextBox: true,
    objectName: "Slide title",
  });
}

function card(slide, x, y, w, h, opts = {}) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color: opts.fill || PANEL },
    line: { color: opts.line || EDGE, width: opts.lw || 1 },
    objectName: opts.name || "Card",
  });
}

function badge(slide, n, x, y, color, d = 0.42) {
  slide.addText(String(n), {
    shape: pres.shapes.OVAL,
    x,
    y,
    w: d,
    h: d,
    fill: { color },
    align: "center",
    valign: "middle",
    fontFace: FONT,
    fontSize: 14,
    bold: true,
    color: BG,
    margin: 0,
    isTextBox: true,
    objectName: `Badge ${n}`,
  });
}

// ----------------------------------------------------------------
// Slide 1: Title and submission details
// ----------------------------------------------------------------
{
  const s = pres.addSlide({ masterName: "TITLE_SLIDE" });

  s.addText("S&P GLOBAL & CRISIL CAMPUS HACKATHON 2026", {
    x: 0.7,
    y: 0.65,
    w: 7.9,
    h: 0.4,
    fontFace: FONT,
    fontSize: 14,
    bold: true,
    color: TEAL,
    charSpacing: 3,
    margin: 0,
    isTextBox: true,
  });

  s.addText(
    [
      { text: "AI/NLP Risk Engine +", options: { breakLine: true } },
      { text: "Tactical Index Rebalancer +", options: { breakLine: true } },
      { text: "Portfolio Stress Testing" },
    ],
    {
      x: 0.7,
      y: 1.2,
      w: 7.9,
      h: 2.0,
      fontFace: FONT,
      fontSize: 36,
      bold: true,
      color: TXT,
      valign: "top",
      margin: 0,
      isTextBox: true,
      objectName: "Title",
    }
  );

  s.addText(
    "Financial NLP, tactical portfolio rebalancing and scenario stress testing in one explainable decision-support prototype",
    {
      x: 0.7,
      y: 3.3,
      w: 7.8,
      h: 0.72,
      fontFace: FONT,
      fontSize: 15,
      color: MUTED,
      valign: "top",
      margin: 0,
      isTextBox: true,
    }
  );

  // Candidate and institution details.
  const details = [
    ["Candidate Name: ", "Boppana Goutam"],
    ["College Email ID: ", "goutam.b23@iiits.in"],
    [
      "College / Campus: ",
      "Indian Institute of Information Technology, Sri City",
    ],
  ];

  details.forEach(([label, value], i) => {
    s.addText(
      [
        { text: label, options: { bold: true, color: TXT } },
        { text: value, options: { color: MUTED } },
      ],
      {
        x: 0.7,
        y: 4.2 + i * 0.43,
        w: 8.0,
        h: 0.36,
        fontFace: FONT,
        fontSize: 13,
        margin: 0,
        valign: "mid",
        isTextBox: true,
      }
    );
  });

  // Clickable demo video link.
  s.addText(
    [
      { text: "Demo Video Link: ", options: { bold: true } },
      { text: VIDEO_URL, options: { underline: true } },
    ],
    {
      x: 0.7,
      y: 5.56,
      w: 8.0,
      h: 0.34,
      fontFace: FONT,
      fontSize: 13,
      color: CYAN,
      hyperlink: { url: VIDEO_URL },
      margin: 0,
      isTextBox: true,
      objectName: "Demo Video Link",
    }
  );

  s.addText(
    [
      { text: "Slide Deck Link: ", options: { bold: true } },
      { text: "Not hosted externally" },
    ],
    {
      x: 0.7,
      y: 5.97,
      w: 8.0,
      h: 0.34,
      fontFace: FONT,
      fontSize: 13,
      color: MUTED,
      margin: 0,
      isTextBox: true,
      objectName: "Slide Deck Link",
    }
  );

  // Workflow motif: text -> signals -> weights -> stress.
  const chips = [
    ["Financial text", "news headlines · stock tweets", SLATE],
    ["NLP risk signals", "FinBERT · BART-MNLI · impact score", TEAL],
    ["Module A: index weights", "sentiment-driven tilts", CYAN],
    ["Module B: stress tests", "hypothetical shock scenarios", AMBER],
  ];

  const cx = 9.1;
  const cw = 3.55;
  const ch = 1.0;
  const cg = 0.38;

  chips.forEach(([t, sub, col], i) => {
    const y = 1.0 + i * (ch + cg);

    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: cx,
      y,
      w: cw,
      h: ch,
      rectRadius: 0.08,
      fill: { color: PANEL },
      line: { color: col, width: 1.75 },
      objectName: `Flow ${i + 1}`,
    });

    s.addText(t, {
      x: cx + 0.2,
      y: y + 0.12,
      w: cw - 0.4,
      h: 0.4,
      fontFace: FONT,
      fontSize: 16,
      bold: true,
      color: TXT,
      margin: 0,
      isTextBox: true,
    });

    s.addText(sub, {
      x: cx + 0.2,
      y: y + 0.52,
      w: cw - 0.4,
      h: 0.36,
      fontFace: FONT,
      fontSize: 12,
      color: col,
      margin: 0,
      isTextBox: true,
    });

    if (i < 3) {
      s.addShape(pres.shapes.DOWN_ARROW, {
        x: cx + cw / 2 - 0.15,
        y: y + ch + 0.05,
        w: 0.3,
        h: cg - 0.1,
        fill: { color: SLATE },
        line: { color: SLATE, width: 0.5 },
      });
    }
  });

  s.addNotes(
    "Title slide. Candidate details follow the requested hackathon submission format. " +
      "The demo video is hosted on YouTube as an unlisted video."
  );
}

// ----------------------------------------------------------------
// Slide 2: Problem and workflow
// ----------------------------------------------------------------
{
  const s = pres.addSlide({ masterName: "CONTENT" });

  addTitle(s, "From unstructured text to explainable signals");

  s.addText(
    "Financial news and social commentary carry risk information, but turning noisy, unstructured text into consistent, explainable portfolio signals is hard.",
    {
      x: 0.6,
      y: 1.3,
      w: 12.13,
      h: 0.85,
      fontFace: FONT,
      fontSize: 18,
      color: MUTED,
      valign: "top",
      margin: 0,
      isTextBox: true,
    }
  );

  const steps = [
    ["Unstructured text", "news headlines · stock tweets", SLATE],
    ["NLP analysis", "sentiment · event type · impact", TEAL],
    ["Structured risk signals", "ticker · sentiment · event · impact 1–10", BLUE],
    ["Decision support", "rebalancing + stress testing", AMBER],
  ];

  const bw = 2.65;
  const gap = 0.51;
  const y0 = 2.4;
  const bh = 1.25;

  steps.forEach(([t, sub, col], i) => {
    const x = 0.6 + i * (bw + gap);

    card(s, x, y0, bw, bh, {
      line: col,
      lw: 1.75,
      name: `Step ${i + 1}`,
    });

    s.addText(t, {
      x: x + 0.15,
      y: y0 + 0.14,
      w: bw - 0.3,
      h: 0.4,
      fontFace: FONT,
      fontSize: 16,
      bold: true,
      color: TXT,
      margin: 0,
      isTextBox: true,
    });

    s.addText(sub, {
      x: x + 0.15,
      y: y0 + 0.58,
      w: bw - 0.3,
      h: 0.55,
      fontFace: FONT,
      fontSize: 13,
      color: col,
      valign: "top",
      margin: 0,
      isTextBox: true,
    });

    if (i < 3) {
      s.addShape(pres.shapes.RIGHT_ARROW, {
        x: x + bw + 0.08,
        y: y0 + bh / 2 - 0.17,
        w: gap - 0.16,
        h: 0.34,
        fill: { color: SLATE },
        line: { color: SLATE, width: 0.5 },
      });
    }
  });

  const cy = 3.95;
  const chh = 1.85;
  const cw2 = 5.95;

  card(s, 0.6, cy, cw2, chh, { name: "Card demonstrates" });

  s.addText("What the prototype demonstrates", {
    x: 0.85,
    y: cy + 0.15,
    w: cw2 - 0.5,
    h: 0.4,
    fontFace: FONT,
    fontSize: 16,
    bold: true,
    color: TEAL,
    margin: 0,
    isTextBox: true,
  });

  s.addText(
    [
      { text: "Text becomes structured, searchable signals", options: { bullet: true, breakLine: true } },
      { text: "Signals tilt a mock index by transparent rules", options: { bullet: true, breakLine: true } },
      { text: "Resulting weights face hypothetical shocks", options: { bullet: true } },
    ],
    {
      x: 0.85,
      y: cy + 0.62,
      w: cw2 - 0.5,
      h: 1.3,
      fontFace: FONT,
      fontSize: 15,
      color: TXT,
      valign: "top",
      paraSpaceAfter: 6,
      margin: 0,
      isTextBox: true,
    }
  );

  const x2 = 0.6 + cw2 + 0.23;

  card(s, x2, cy, cw2, chh, { name: "Card complement" });

  s.addText("Why two modules complement each other", {
    x: x2 + 0.25,
    y: cy + 0.15,
    w: cw2 - 0.5,
    h: 0.4,
    fontFace: FONT,
    fontSize: 16,
    bold: true,
    color: CYAN,
    margin: 0,
    isTextBox: true,
  });

  s.addText(
    [
      { text: "A asks: how should news shift weights?", options: { bullet: true, breakLine: true } },
      { text: "B asks: how fragile is the resulting portfolio?", options: { bullet: true, breakLine: true } },
      { text: "B stress-tests A's final rebalanced weights", options: { bullet: true } },
    ],
    {
      x: x2 + 0.25,
      y: cy + 0.62,
      w: cw2 - 0.5,
      h: 1.3,
      fontFace: FONT,
      fontSize: 15,
      color: TXT,
      valign: "top",
      paraSpaceAfter: 6,
      margin: 0,
      isTextBox: true,
    }
  );

  s.addText(
    "A prototype for analyst decision support, not an autonomous trading system",
    {
      x: 0.6,
      y: 6.1,
      w: 12.13,
      h: 0.6,
      shape: pres.shapes.ROUNDED_RECTANGLE,
      rectRadius: 0.08,
      fill: { color: BG },
      line: { color: AMBER, width: 1.5 },
      fontFace: FONT,
      fontSize: 16,
      bold: true,
      color: AMBER,
      align: "center",
      valign: "middle",
      margin: 0,
      isTextBox: true,
      objectName: "Prototype banner",
    }
  );

  s.addNotes(
    "Workflow: unstructured text -> NLP analysis -> structured signals -> Module A rebalancing and Module B stress testing. " +
      "The stress tab runs on the final rebalanced weights."
  );
}

// ----------------------------------------------------------------
// Slide 3: Architecture
// ----------------------------------------------------------------
{
  const s = pres.addSlide({ masterName: "CONTENT" });

  addTitle(s, "Architecture: one NLP pipeline, two modules");

  const w = 11.9;
  const h = (w * 5.85) / 12.3;

  s.addImage({
    path: path.join(DOCS, "architecture.png"),
    x: (13.333 - w) / 2,
    y: 1.2,
    w,
    h,
    altText:
      "Architecture diagram: sources, ingest and filter, FinBERT, zero-shot events, impact score, signal generation and store, Module A, Module B, Streamlit dashboard",
  });

  s.addNotes(
    "Diagram generated from the project architecture: src/ingest.py -> src/engine.py -> src/impact.py -> " +
      "src/run_engine.py and src/schema.py -> data/signals.csv -> src/rebalance.py and src/stress.py -> app.py."
  );
}

// ----------------------------------------------------------------
// Slide 4: Engineering highlights and formula
// ----------------------------------------------------------------
{
  const s = pres.addSlide({ masterName: "CONTENT" });

  addTitle(s, "Engineering highlights: signals to weights");

  const rows = [
    ["Sentiment + event, together", "FinBERT direction and BART-MNLI category in one record"],
    ["Transparent impact score", "Hand-set severity × sentiment × confidence; inspectable"],
    ["Confidence-aware tickers", "Exchange tag > cashtag > name + finance; multi-ticker kept"],
    ["Clean inputs", "Relevance filter and >85% near-duplicate drop cut noise"],
    ["One expansion, two views", "Replay display and rebalancer share signal expansion"],
    ["Auto time buckets, tunable knobs", "Day to year closest to 20 steps; sensitivity, decay, caps"],
    ["Validated and tested", "Schema check before write; 87 offline unit tests pass"],
  ];

  const y0 = 1.35;
  const rh = 0.79;

  rows.forEach(([t, d], i) => {
    const y = y0 + i * rh;

    badge(s, i + 1, 0.6, y + 0.08, TEAL, 0.38);

    s.addText(t, {
      x: 1.2,
      y,
      w: 6.9,
      h: 0.36,
      fontFace: FONT,
      fontSize: 16,
      bold: true,
      color: TXT,
      margin: 0,
      isTextBox: true,
    });

    s.addText(d, {
      x: 1.2,
      y: y + 0.36,
      w: 6.9,
      h: 0.34,
      fontFace: FONT,
      fontSize: 14,
      color: MUTED,
      margin: 0,
      isTextBox: true,
    });
  });

  const px = 8.45;
  const pw = 4.28;

  s.addText("Signal → weight (Module A)", {
    x: px,
    y: 1.3,
    w: pw,
    h: 0.4,
    fontFace: FONT,
    fontSize: 18,
    bold: true,
    color: CYAN,
    margin: 0,
    isTextBox: true,
  });

  const F = [
    ["IMPACT, 1–10", "severity × (0.5 + 0.5·|sent|)\n× (0.5 + 0.5·conf)"],
    ["NET SIGNAL, PER STOCK/STEP", "Σ sentiment × impact / 10\nclipped to ±2"],
    ["TILT", "w ← w · exp(1.5 × net signal)\nthen normalise to 100%"],
    ["DECAY + LIMITS", "0.95·tilt + 0.05·w₀\nclip each weight to 1%–15%"],
  ];

  const fy0 = 1.85;
  const fh = 1.12;
  const fg = 0.13;

  F.forEach(([lab, f], i) => {
    const y = fy0 + i * (fh + fg);

    card(s, px, y, pw, fh, { name: `Formula ${i + 1}` });

    s.addText(lab, {
      x: px + 0.2,
      y: y + 0.1,
      w: pw - 0.4,
      h: 0.26,
      fontFace: FONT,
      fontSize: 11,
      bold: true,
      color: TEAL,
      charSpacing: 1,
      margin: 0,
      isTextBox: true,
    });

    s.addText(f, {
      x: px + 0.2,
      y: y + 0.4,
      w: pw - 0.35,
      h: 0.66,
      fontFace: MONO,
      fontSize: 12,
      color: TXT,
      valign: "top",
      margin: 0,
      isTextBox: true,
    });
  });

  s.addText(
    "Defaults shown (sensitivity 1.5, decay 0.05); sliders adjust them.",
    {
      x: px,
      y: 6.78,
      w: pw,
      h: 0.25,
      fontFace: FONT,
      fontSize: 10,
      color: SLATE,
      margin: 0,
      isTextBox: true,
    }
  );

  s.addNotes(
    "Formulas reflect src/impact.py and src/rebalance.py. Dashboard defaults: sensitivity 1.5, decay 0.05, " +
      "maximum weight 0.15 and minimum weight 0.01. Five network-dependent tests require Hugging Face access."
  );
}

// ----------------------------------------------------------------
// Slide 5: Results
// ----------------------------------------------------------------
{
  const s = pres.addSlide({ masterName: "CONTENT" });

  addTitle(s, "Results: verifiable prototype outputs");

  const iw = 6.9;
  const ih = (iw * 810) / 1160;

  s.addImage({
    path: path.join(DOCS, "dashboard_overview.png"),
    x: 0.6,
    y: 1.3,
    w: iw,
    h: ih,
    altText:
      "Dashboard screenshot: weight changes from start to now for 11 stocks; NVDA +2.17 points, MSFT -1.76 points",
  });

  s.addText(
    "Streamlit dashboard, Portfolio Overview. Committed data/signals.csv, default parameters. Weight changes are simulated tilts, not returns.",
    {
      x: 0.6,
      y: 1.3 + ih + 0.12,
      w: iw,
      h: 0.55,
      fontFace: FONT,
      fontSize: 12,
      color: MUTED,
      valign: "top",
      margin: 0,
      isTextBox: true,
    }
  );

  const stats = [
    ["70%", TEAL, "FinBERT accuracy, 0.63 macro-F1", "off-the-shelf model, 300 validation tweets"],
    ["129", CYAN, "signals in the committed dataset", "76 tweets (Oct 2021–Sep 2022) + 53 headlines (9 Oct 2026)"],
    ["13", BLUE, "monthly replay steps", "98 signals move 11 stocks: NVDA +2.17 pp, MSFT −1.76 pp"],
    ["87", AMBER, "unit tests pass offline", "5 more tests need network access to load data"],
  ];

  const sx = 7.85;
  const sw = 4.88;
  const sh = 1.2;
  const sg = 0.14;

  stats.forEach(([n, col, l1, l2], i) => {
    const y = 1.3 + i * (sh + sg);

    card(s, sx, y, sw, sh, { name: `Stat ${i + 1}` });

    s.addText(n, {
      x: sx + 0.15,
      y: y + 0.1,
      w: 1.25,
      h: sh - 0.2,
      fontFace: FONT,
      fontSize: 36,
      bold: true,
      color: col,
      align: "center",
      valign: "middle",
      margin: 0,
      isTextBox: true,
    });

    s.addText(
      [
        { text: l1, options: { bold: true, fontSize: 15, color: TXT, breakLine: true } },
        { text: l2, options: { fontSize: 13, color: MUTED } },
      ],
      {
        x: sx + 1.5,
        y: y + 0.1,
        w: sw - 1.65,
        h: sh - 0.2,
        fontFace: FONT,
        valign: "middle",
        margin: 0,
        isTextBox: true,
      }
    );
  });

  s.addNotes(
    "Committed data/signals.csv has 129 rows: 76 tweets from 2021–2022 and 53 news headlines from 9 October 2026. " +
      "The default dashboard produces 13 replay steps and 11 index stocks. NVDA changes by +2.17 percentage points " +
      "and MSFT by -1.76 percentage points. These are simulated allocations, not returns."
  );
}

// ----------------------------------------------------------------
// Slide 6: Domain impact and stress testing
// ----------------------------------------------------------------
{
  const s = pres.addSlide({ masterName: "CONTENT" });

  addTitle(s, "Domain impact: explainable decision support");

  const rows = [
    ["Structured, searchable signals", "Text becomes ticker, sentiment, event and impact fields"],
    ["Explainable by design", "Analysts trace each weight move to its source signals"],
    ["News-aware mock index", "Rules-based tilts show how sentiment could shift weights"],
    ["Shock sensitivity testing", "Hypothetical scenarios run on the rebalanced portfolio"],
    ["Where the risk sits", "Scenario comparison, sector and holding attribution"],
  ];

  const y0 = 1.35;
  const rh = 0.8;

  rows.forEach(([t, d], i) => {
    const y = y0 + i * rh;

    badge(s, i + 1, 0.6, y + 0.08, CYAN, 0.38);

    s.addText(t, {
      x: 1.2,
      y,
      w: 6.5,
      h: 0.36,
      fontFace: FONT,
      fontSize: 16,
      bold: true,
      color: TXT,
      margin: 0,
      isTextBox: true,
    });

    s.addText(d, {
      x: 1.2,
      y: y + 0.37,
      w: 6.5,
      h: 0.34,
      fontFace: FONT,
      fontSize: 14,
      color: MUTED,
      margin: 0,
      isTextBox: true,
    });
  });

  card(s, 0.6, 5.6, 7.1, 1.2, {
    line: AMBER,
    lw: 1.5,
    name: "Deployment caveat",
  });

  s.addText(
    [
      { text: "Before real deployment", options: { bold: true, color: AMBER, fontSize: 16, breakLine: true } },
      { text: "Stronger validation, reliable data feeds, risk controls, market-data calibration", options: { color: TXT, fontSize: 14 } },
    ],
    {
      x: 0.85,
      y: 5.7,
      w: 6.6,
      h: 1.0,
      fontFace: FONT,
      valign: "middle",
      margin: 0,
      isTextBox: true,
    }
  );

  const px = 8.05;
  const pw = 4.68;

  card(s, px, 1.3, pw, 5.5, { name: "Chart panel" });

  s.addText("Simulated portfolio impact by scenario", {
    x: px + 0.2,
    y: 1.42,
    w: pw - 0.4,
    h: 0.4,
    fontFace: FONT,
    fontSize: 16,
    bold: true,
    color: TXT,
    margin: 0,
    isTextBox: true,
  });

  s.addChart(
    pres.charts.BAR,
    [
      {
        name: "Simulated return (%)",
        labels: [
          "Broad sell-off",
          "Rates / inflation",
          "Geopolitical / energy",
          "Credit stress",
          "Tech shock",
        ],
        values: [-18.0, -20.15, -17.16, -28.26, -26.42],
      },
    ],
    {
      x: px + 0.1,
      y: 1.85,
      w: pw - 0.2,
      h: 3.75,
      barDir: "bar",
      barGapWidthPct: 45,
      chartColors: [AMBER],
      invertedColors: [AMBER],
      showValue: true,
      dataLabelPosition: "outEnd",
      dataLabelFormatCode: '0.0"%"',
      dataLabelColor: TXT,
      dataLabelFontSize: 12,
      dataLabelFontFace: FONT,
      catAxisLabelColor: TXT,
      catAxisLabelFontSize: 12,
      catAxisLabelFontFace: FONT,
      catAxisLabelPos: "low",
      catAxisOrientation: "maxMin",
      catGridLine: { style: "none" },
      valGridLine: { style: "none" },
      valAxisHidden: true,
      valAxisMinVal: -40,
      valAxisMaxVal: 0,
      showLegend: false,
      showTitle: false,
    }
  );

  s.addText(
    "Hypothetical sector shocks applied to Module A's final weights (11 stocks). Not historical losses, forecasts or calibrated estimates.",
    {
      x: px + 0.2,
      y: 5.7,
      w: pw - 0.4,
      h: 1.0,
      fontFace: FONT,
      fontSize: 12,
      color: MUTED,
      valign: "top",
      margin: 0,
      isTextBox: true,
    }
  );

  s.addNotes(
    "Chart values are hypothetical sector shocks applied to Module A's final weights: market sell-off -18.00%, " +
      "rate/inflation -20.15%, geopolitical/energy -17.16%, credit -28.26%, and technology -26.42%. " +
      "They are arithmetic scenario estimates, not historical backtests or forecasts."
  );
}

// ----------------------------------------------------------------
// Slide 7: Limitations and roadmap
// ----------------------------------------------------------------
{
  const s = pres.addSlide({ masterName: "CONTENT" });

  addTitle(s, "Engineering boundaries and roadmap");

  const hdr = (t, col) => ({
    text: t,
    options: {
      bold: true,
      color: col,
      fontSize: 14,
      fill: { color: "1B2B4B" },
      fontFace: FONT,
    },
  });

  const cell = (t, col) => ({
    text: t,
    options: {
      color: col,
      fontSize: 14,
      fill: { color: PANEL },
      fontFace: FONT,
    },
  });

  const data = [
    [
      "Sentiment checked on 300 tweets; event labels not scored against ground truth",
      "Larger labeled evaluation for sentiment and event classes",
    ],
    [
      "Impact weights are hand-chosen heuristics",
      "Calibrate impact to observed market reactions",
    ],
    [
      "Ticker matching is keyword-based and can misattribute",
      "Stronger entity resolution and ticker attribution",
    ],
    [
      "Module A has no historical price backtest",
      "Market-data integration and walk-forward backtesting",
    ],
    [
      "Module B shocks are hypothetical, with no volatility or correlation calibration",
      "Calibrate risk parameters on historical market data",
    ],
    [
      "Sparse, gapped data: tweets Oct 2021–Sep 2022, then 53 headlines from one 45-minute window in Oct 2026",
      "Continuous multi-source feed, data-quality monitoring, reproducible evaluation",
    ],
  ];

  const rows = [[hdr("Engineering boundary", AMBER), hdr("Next step", TEAL)]];
  data.forEach(([a, b]) => rows.push([cell(a, TXT), cell(b, "CFE9E4")]));

  s.addTable(rows, {
    x: 0.6,
    y: 1.3,
    w: 12.13,
    colW: [6.6, 5.53],
    rowH: [0.42, 0.62, 0.62, 0.62, 0.62, 0.62, 0.78],
    border: { type: "solid", pt: 1, color: BG },
    valign: "middle",
    margin: [0.04, 0.14, 0.04, 0.14],
    objectName: "Limitations table",
  });

  card(s, 0.6, 5.95, 12.13, 0.95, {
    line: TEAL,
    lw: 1.5,
    name: "Takeaway",
  });

  s.addText(
    [
      {
        text: "TAKEAWAY",
        options: {
          bold: true,
          color: TEAL,
          fontSize: 14,
          charSpacing: 2,
          breakLine: true,
        },
      },
      {
        text: "A working prototype that connects financial NLP to explainable portfolio decision-support workflows.",
        options: { bold: true, color: TXT, fontSize: 18 },
      },
    ],
    {
      x: 0.9,
      y: 6.0,
      w: 11.6,
      h: 0.85,
      fontFace: FONT,
      valign: "middle",
      margin: 0,
      isTextBox: true,
    }
  );

  s.addNotes(
    "The dataset contains tweets from October 2021 to September 2022 and a batch of 53 news headlines from " +
      "9 October 2026. Event labels have not been scored against ground truth. The impact score is heuristic, " +
      "Module A has no historical price backtest, and Module B uses hypothetical shocks."
  );
}

// ----------------------------------------------------------------
// Write the presentation
// ----------------------------------------------------------------
(async () => {
  const out = path.join(DOCS, "presentation.pptx");

  await pres.writeFile({ fileName: out });

  try {
    const { applyTheme } = require("/mnt/skills/public/pptx/scripts/apply_theme.js");
    await applyTheme(out, THEME);
  } catch (e) {
    console.log("theme not applied:", e.message);
  }

  console.log("wrote", out);
})();

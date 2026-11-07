// Original SVG illustrations (no image files: the CSP allows same-origin images only).  Colours come from CSS classes,
// so they follow the light / dark theme.
import { svg, h } from "./dom.js";

const el = (tag, attrs) => svg(tag, attrs);
const root = (label) => svg("svg", { viewBox: "0 0 360 260", class: "il", role: "img", "aria-label": label });

// Landing / sign-in hero: growing bars, a rising line, a coin and a shield.
export function heroArt() {
  const s = root("Illustration: bars growing over time with a rising line, a coin and a shield");
  s.append(
    el("circle", { cx: 190, cy: 128, r: 112, class: "il-soft" }),
    el("rect", { x: 56, y: 40, width: 248, height: 176, rx: 22, class: "il-surf", "stroke-width": 1.5 }),
    el("rect", { x: 84, y: 150, width: 26, height: 40, rx: 6, class: "il-mut" }),
    el("rect", { x: 122, y: 130, width: 26, height: 60, rx: 6, class: "il-mut" }),
    el("rect", { x: 160, y: 112, width: 26, height: 78, rx: 6, class: "il-b" }),
    el("rect", { x: 198, y: 92, width: 26, height: 98, rx: 6, class: "il-a" }),
    el("rect", { x: 236, y: 68, width: 26, height: 122, rx: 6, class: "il-a" }),
    el("polyline", { points: "80,140 126,120 172,100 214,76 262,52", "stroke-width": 3, "stroke-linecap": "round", "stroke-linejoin": "round", class: "il-sa" }),
    el("circle", { cx: 262, cy: 52, r: 6, class: "il-a" }),
    el("circle", { cx: 306, cy: 70, r: 30, class: "il-c" }),
    el("circle", { cx: 306, cy: 70, r: 22, fill: "none", stroke: "#fff", "stroke-opacity": 0.55, "stroke-width": 2 }),
    el("path", { d: "M298 62h16M298 70h16M302 62c8 0 8 12 0 12l10 10", fill: "none", stroke: "#fff", "stroke-width": 2.4, "stroke-linecap": "round", "stroke-linejoin": "round" }),
    el("path", { d: "M72 196l26-9 26 9v26c0 14-12 24-26 30-14-6-26-16-26-30z", class: "il-b" }),
    el("path", { d: "M86 214l9 9 16-18", fill: "none", stroke: "#fff", "stroke-width": 3.5, "stroke-linecap": "round", "stroke-linejoin": "round" }));
  return s;
}

const ART = {
  chart: (s) => s.append(
    el("rect", { x: 70, y: 50, width: 220, height: 150, rx: 18, class: "il-surf", "stroke-width": 1.5 }),
    el("path", { d: "M96 170h168M96 140h168M96 110h168", class: "il-sl", "stroke-width": 1.5, "stroke-dasharray": "4 6" }),
    el("polyline", { points: "100,168 140,150 176,156 214,118 256,86", "stroke-width": 4, "stroke-linecap": "round", "stroke-linejoin": "round", class: "il-sa" }),
    el("circle", { cx: 256, cy: 86, r: 7, class: "il-a" }),
    el("circle", { cx: 292, cy: 52, r: 22, class: "il-soft" }),
    el("path", { d: "M282 52l7 7 12-14", fill: "none", class: "il-sa", "stroke-width": 3.5, "stroke-linecap": "round", "stroke-linejoin": "round" })),
  chat: (s) => s.append(
    el("rect", { x: 56, y: 56, width: 170, height: 70, rx: 20, class: "il-surf", "stroke-width": 1.5 }),
    el("rect", { x: 76, y: 78, width: 100, height: 8, rx: 4, class: "il-mut" }),
    el("rect", { x: 76, y: 96, width: 70, height: 8, rx: 4, class: "il-mut" }),
    el("rect", { x: 134, y: 142, width: 170, height: 70, rx: 20, class: "il-a" }),
    el("rect", { x: 154, y: 164, width: 110, height: 8, rx: 4, fill: "#fff", "fill-opacity": 0.85 }),
    el("rect", { x: 154, y: 182, width: 76, height: 8, rx: 4, fill: "#fff", "fill-opacity": 0.6 })),
  doc: (s) => s.append(
    el("rect", { x: 98, y: 36, width: 164, height: 196, rx: 16, class: "il-surf", "stroke-width": 1.5 }),
    el("rect", { x: 120, y: 62, width: 70, height: 10, rx: 5, class: "il-a" }),
    el("rect", { x: 120, y: 92, width: 120, height: 8, rx: 4, class: "il-mut" }),
    el("rect", { x: 120, y: 112, width: 100, height: 8, rx: 4, class: "il-mut" }),
    el("rect", { x: 120, y: 132, width: 120, height: 8, rx: 4, class: "il-mut" }),
    el("rect", { x: 120, y: 152, width: 84, height: 8, rx: 4, class: "il-mut" }),
    el("circle", { cx: 236, cy: 196, r: 28, class: "il-soft" }),
    el("path", { d: "M224 196l9 9 16-18", fill: "none", class: "il-sa", "stroke-width": 4, "stroke-linecap": "round", "stroke-linejoin": "round" })),
  bell: (s) => s.append(
    el("circle", { cx: 180, cy: 130, r: 84, class: "il-soft" }),
    el("path", { d: "M180 62c-24 0-40 18-40 42v30l-12 22h104l-12-22v-30c0-24-16-42-40-42z", class: "il-surf", "stroke-width": 1.5 }),
    el("path", { d: "M166 172a14 14 0 0 0 28 0", fill: "none", class: "il-sa", "stroke-width": 4, "stroke-linecap": "round" }),
    el("circle", { cx: 214, cy: 82, r: 9, class: "il-a" })),
  coin: (s) => s.append(
    el("circle", { cx: 180, cy: 134, r: 88, class: "il-soft" }),
    el("circle", { cx: 150, cy: 150, r: 44, class: "il-c" }),
    el("circle", { cx: 214, cy: 112, r: 32, class: "il-a" }),
    el("path", { d: "M138 140h24M138 152h24M144 140c14 0 14 20 0 20l16 18", fill: "none", stroke: "#fff", "stroke-width": 4, "stroke-linecap": "round", "stroke-linejoin": "round" })),
};

// Friendly empty state: picture, short title, one helpful sentence, optional action node.
export function emptyState(kind, title, text, action, level = 3) {
  const s = root(title);
  (ART[kind] || ART.chart)(s);
  return h("div", { class: "empty" }, s, h("h" + level, { text: title }), h("p", { class: "muted", text }), action || null);
}

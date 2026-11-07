// Dependency-free SVG charts.  Attributes only (CSP forbids inline style); colours come from CSS classes.
import { svg, h } from "./dom.js";

export function donut(items, label) {
  const total = items.reduce((a, b) => a + Math.max(0, Number(b.value) || 0), 0);
  const R = 70, C = 2 * Math.PI * R;
  const g = svg("g", { transform: "rotate(-90 100 100)" });
  let offset = 0;
  items.forEach((it, i) => {
    const frac = total ? Math.max(0, Number(it.value) || 0) / total : 0;
    g.appendChild(svg("circle", {
      cx: 100, cy: 100, r: R, "stroke-width": 28, class: "stk s" + (i % 5),
      "stroke-dasharray": `${frac * C} ${C}`, "stroke-dashoffset": -offset * C,
    }));
    offset += frac;
  });
  const chart = svg("svg", { viewBox: "0 0 200 200", class: "chart", role: "img", "aria-label": label }, g);
  const legend = h("div", { class: "legend" }, items.map((it, i) =>
    h("span", {}, h("i", { class: "s" + (i % 5) }), `${it.label} ${total ? Math.round((it.value / total) * 100) : 0}%`)));
  return h("div", {}, chart, legend);
}

export function lines(labels, series, label) {
  const W = 480, H = 220, pl = 12, pr = 12, pt = 14, pb = 28;
  const max = Math.max(1, ...series.flatMap((s) => s.values.map((v) => Number(v) || 0)));
  const x = (i) => pl + (i * (W - pl - pr)) / Math.max(1, labels.length - 1);
  const y = (v) => H - pb - ((Number(v) || 0) / max) * (H - pt - pb);
  const root = svg("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart", role: "img", "aria-label": label });
  root.appendChild(svg("line", { x1: pl, y1: H - pb, x2: W - pr, y2: H - pb, stroke: "currentColor", "stroke-opacity": 0.25 }));
  series.forEach((s, si) => {
    const pts = s.values.map((v, i) => `${x(i)},${y(v)}`).join(" ");
    root.appendChild(svg("polyline", { points: pts, "stroke-width": 3, class: "stk s" + si }));
    s.values.forEach((v, i) => root.appendChild(svg("circle", { cx: x(i), cy: y(v), r: 4, class: "fil s" + si })));
  });
  labels.forEach((t, i) => {
    const el = svg("text", { x: x(i), y: H - 8, "text-anchor": i === 0 ? "start" : i === labels.length - 1 ? "end" : "middle", "font-size": 12, fill: "currentColor" });
    el.textContent = t;
    root.appendChild(el);
  });
  const legend = h("div", { class: "legend" }, series.map((s, i) => h("span", {}, h("i", { class: "s" + i }), s.name)));
  return h("div", {}, root, legend);
}

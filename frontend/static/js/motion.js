// Small, honest motion: numbers count up and settle, bars grow, charts draw in.  Every animation ends on the exact final
// value (text is restored verbatim).  Nothing moves for people who ask for reduced motion.  Attributes / textContent only.
const reduced = () => !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
const easeOut = (t) => 1 - Math.pow(1 - t, 3);
const done = new WeakSet();

function frames(ms, step, finish) {
  const t0 = performance.now();
  const tick = (now) => {
    const t = Math.min(1, (now - t0) / ms);
    step(t);
    if (t < 1) requestAnimationFrame(tick); else if (finish) finish();
  };
  requestAnimationFrame(tick);
}

export function countUp(el, ms = 1100) {
  if (reduced() || done.has(el)) return;
  done.add(el);
  const final = el.textContent || "";
  const m = final.match(/\d[\d,]*\.?\d*/);
  if (!m) return;
  const raw = m[0];
  const decimals = (raw.split(".")[1] || "").length;
  const target = parseFloat(raw.replace(/,/g, ""));
  if (!Number.isFinite(target) || target === 0) return;
  const grouped = raw.includes(",");
  const fmt = grouped ? new Intl.NumberFormat("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) : null;
  const before = final.slice(0, m.index), after = final.slice(m.index + raw.length);
  frames(ms, (t) => {
    const v = target * easeOut(t);
    el.textContent = before + (fmt ? fmt.format(v) : v.toFixed(decimals)) + after;
  }, () => { el.textContent = final; });
}

export function growBar(span) {
  if (reduced() || done.has(span)) return;
  done.add(span);
  const m = /\bw(\d+)\b/.exec(span.className);
  if (!m) return;
  const target = "w" + m[1];
  span.classList.replace(target, "w0");
  requestAnimationFrame(() => requestAnimationFrame(() => span.classList.replace("w0", target)));
}

// Donut: segments sweep round once while the ring turns a little and settles.
export function sweepDonut(g, circles, fracs, C, base = -90) {
  if (reduced()) return;
  const starts = []; let acc = 0;
  fracs.forEach((f) => { starts.push(acc); acc += f; });
  frames(1300, (t) => {
    const p = easeOut(t);
    circles.forEach((c, i) => {
      const len = Math.max(0, Math.min(fracs[i], p - starts[i])) * C;
      c.setAttribute("stroke-dasharray", `${len} ${C}`);
    });
    g.setAttribute("transform", `rotate(${base - 50 * (1 - p)} 100 100)`);
  }, () => {
    circles.forEach((c, i) => c.setAttribute("stroke-dasharray", `${fracs[i] * C} ${C}`));
    g.setAttribute("transform", `rotate(${base} 100 100)`);
  });
}

// Line charts: each line draws left to right, then its dots appear.
export function drawLines(root) {
  if (reduced()) return;
  requestAnimationFrame(() => requestAnimationFrame(() => {
    const lines = [...root.querySelectorAll("polyline.stk")];
    const dots = [...root.querySelectorAll("circle.fil")];
    let lens;
    try { lens = lines.map((l) => l.getTotalLength()); } catch (e) { return; }
    dots.forEach((d) => d.setAttribute("opacity", "0"));
    frames(1100, (t) => {
      const p = easeOut(t);
      lines.forEach((l, i) => { l.setAttribute("stroke-dasharray", String(lens[i])); l.setAttribute("stroke-dashoffset", String(lens[i] * (1 - p))); });
      dots.forEach((d) => d.setAttribute("opacity", String(Math.max(0, (t - 0.6) / 0.4))));
    }, () => {
      lines.forEach((l) => { l.removeAttribute("stroke-dasharray"); l.removeAttribute("stroke-dashoffset"); });
      dots.forEach((d) => d.removeAttribute("opacity"));
    });
  }));
}

// Watches the page container: anything new that should animate does so once.
export function watch(root) {
  const run = () => {
    root.querySelectorAll(".metric .value, .tile-value, .score-val").forEach((el) => countUp(el));
    root.querySelectorAll(".bar > span").forEach((el) => growBar(el));
  };
  new MutationObserver(() => requestAnimationFrame(run)).observe(root, { childList: true, subtree: true });
  run();
}

// Tiny DOM helpers.  Everything goes in through textContent / createTextNode: model or user text can never
// become markup.  Do not add an innerHTML helper.

export function h(tag, props, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "text") el.textContent = String(v);
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === "value") el.value = v;
    else if (k === "checked" || k === "disabled" || k === "selected") el[k] = !!v;
    else el.setAttribute(k, v === true ? "" : String(v));
  }
  append(el, children);
  return el;
}

export function append(el, children) {
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    el.appendChild(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

export function clear(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
  return el;
}

export function svg(tag, attrs, ...children) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, String(v));
  append(el, children);
  return el;
}

const inr = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

export function money(n) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  const v = Number(n);
  return (v < 0 ? "-" : "") + "₹" + inr.format(Math.abs(Math.round(v)));
}

export function num(n, digits = 1) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return Number(n).toFixed(digits);
}

export function pctClass(p) {
  const v = Math.max(0, Math.min(100, Math.round(Number(p) / 5) * 5));
  return "w" + (Number.isFinite(v) ? v : 0);
}

let toastTimer = null;
export function toast(message) {
  const t = document.getElementById("toast");
  if (!t) return;
  t.textContent = message;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 3500);
}

export function uid() {
  const a = new Uint8Array(12);
  crypto.getRandomValues(a);
  return Array.from(a, (b) => b.toString(16).padStart(2, "0")).join("");
}

// Signed integer paise -> "₹1,234.50" with integer maths only (never floats). null/undefined -> "unknown".
export function paise(p) {
  if (p === null || p === undefined || !Number.isInteger(p)) return "unknown";
  const a = Math.abs(p);
  return (p < 0 ? "-" : "") + "₹" + Math.floor(a / 100).toLocaleString("en-IN") + "." + String(a % 100).padStart(2, "0");
}

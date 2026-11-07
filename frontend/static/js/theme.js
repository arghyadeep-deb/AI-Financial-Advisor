// Light / dark toggle.  Default follows the system; a click stores an explicit choice (a per-device preference only).
const root = document.documentElement;
const media = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

export function currentTheme() {
  const t = root.getAttribute("data-theme");
  if (t === "light" || t === "dark") return t;
  return media && media.matches ? "dark" : "light";
}

export function toggleTheme() {
  const next = currentTheme() === "dark" ? "light" : "dark";
  root.setAttribute("data-theme", next);
  try { localStorage.setItem("theme", next); } catch (e) { /* ignore */ }
  return next;
}

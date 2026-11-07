// Hash router, nav, auth guard.
import { h, clear, svg } from "./dom.js";
import { api, session } from "./api.js";
import { state, resetState } from "./state.js";
import { currentTheme, toggleTheme } from "./theme.js";
import { watch } from "./motion.js";
import { landing } from "./views/landing.js";
import { authView } from "./views/auth.js";
import { dashboard } from "./views/dashboard.js";
import { health } from "./views/health.js";
import { portfolio } from "./views/portfolio.js";
import { stocks } from "./views/stocks.js";
import { credit } from "./views/credit.js";
import { reports } from "./views/reports.js";
import { profile } from "./views/profile.js";
import { chat } from "./views/chat.js";
import { settings } from "./views/settings.js";
import { statements } from "./views/statements.js";
import { monthly } from "./views/monthly.js";
import { demo } from "./views/demo.js";

const ROUTES = {
  "": { view: landing, public: true },
  demo: { view: demo, public: true },
  login: { view: (c) => authView(c, "login"), public: true },
  signup: { view: (c) => authView(c, "signup"), public: true },
  dashboard: { view: dashboard, label: "Dashboard", icon: "grid" },
  health: { view: health, icon: "pulse", label: "Health" },
  portfolio: { view: portfolio, icon: "pie", label: "Portfolio" },
  stocks: { view: stocks, icon: "trend", label: "Stocks" },
  credit: { view: credit, icon: "card", label: "Credit" },
  reports: { view: reports, icon: "bars", label: "Reports" },
  profile: { view: profile, label: "Profile", icon: "user", foot: true },
  chat: { view: chat, label: "Ask the advisor", icon: "chat" },
  statements: { view: statements, icon: "file", label: "Statements" },
  monthly: { view: monthly, icon: "bars", label: "Monthly report" },
  settings: { view: settings, label: "Settings", icon: "sliders", foot: true },
};

const main = document.getElementById("main");
const navRoot = document.getElementById("nav-root");
let renderToken = 0;

export function go(route) { location.hash = "#/" + route; }

function currentRoute() {
  const raw = location.hash.replace(/^#\/?/, "").split("?")[0];
  return raw in ROUTES ? raw : "";
}

const ICONS = {
  grid: [["rect", { x: 3, y: 3, width: 7, height: 7, rx: 1.5 }], ["rect", { x: 14, y: 3, width: 7, height: 7, rx: 1.5 }], ["rect", { x: 3, y: 14, width: 7, height: 7, rx: 1.5 }], ["rect", { x: 14, y: 14, width: 7, height: 7, rx: 1.5 }]],
  pulse: [["polyline", { points: "3 12 7 12 10 4 14 20 17 12 21 12" }]],
  pie: [["path", { d: "M12 3a9 9 0 1 0 9 9h-9z" }], ["path", { d: "M15 3.5A9 9 0 0 1 20.5 9H15z" }]],
  trend: [["polyline", { points: "3 17 9 11 13 15 21 6" }], ["polyline", { points: "15 6 21 6 21 12" }]],
  card: [["rect", { x: 3, y: 5, width: 18, height: 14, rx: 2.5 }], ["path", { d: "M3 10h18" }]],
  bars: [["path", { d: "M5 20V10M12 20V4M19 20v-7" }]],
  file: [["path", { d: "M6 3h9l4 4v14H6z" }], ["path", { d: "M9 12h7M9 16h7" }]],
  chat: [["path", { d: "M4 5h16v11H9l-5 4z" }]],
  moon: [["path", { d: "M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z" }]],
  sun: [["circle", { cx: 12, cy: 12, r: 4 }], ["path", { d: "M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" }]],
  user: [["circle", { cx: 12, cy: 8, r: 4 }], ["path", { d: "M4 21c1-4 4-6 8-6s7 2 8 6" }]],
  sliders: [["path", { d: "M4 7h10M18 7h2M4 17h2M10 17h10" }], ["circle", { cx: 16, cy: 7, r: 2 }], ["circle", { cx: 8, cy: 17, r: 2 }]],
};

function icon(name) {
  const el = svg("svg", { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": 2,
    "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true" });
  for (const [tag, attrs] of ICONS[name] || []) el.appendChild(svg(tag, attrs));
  return el;
}

function themeButton() {
  const btn = h("button", { class: "theme-btn", type: "button" });
  const paint = () => {
    const dark = currentTheme() === "dark";
    clear(btn);
    btn.append(icon(dark ? "sun" : "moon"), dark ? "Light mode" : "Dark mode");
    btn.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
  };
  btn.addEventListener("click", () => { toggleTheme(); paint(); });
  paint();
  return btn;
}

function renderNav(route) {
  clear(navRoot);
  document.body.classList.toggle("shell", session.active);
  if (!session.active) {
    navRoot.appendChild(h("header", { class: "nav" }, h("div", { class: "wrap" },
      h("a", { class: "brand", href: "#/", text: "Advisor" }),
      h("div", { class: "nav-links" }),
      h("div", { class: "nav-user" },
        themeButton(),
        h("a", { class: "btn ghost", href: "#/login", text: "Log in" }),
        h("a", { class: "btn primary", href: "#/signup", text: "Create account" })))));
    return;
  }
  const link = (k, r, cls) => h("a", { href: "#/" + k, class: cls || null, "aria-current": k === route ? "page" : null }, icon(r.icon), r.label);
  const entries = Object.entries(ROUTES).filter(([, r]) => r.label);
  const main_ = entries.filter(([, r]) => !r.foot).map(([k, r]) => link(k, r));
  const foot = entries.filter(([, r]) => r.foot).map(([k, r]) => link(k, r, "item"));
  const out = h("button", { type: "button", text: "Log out" });
  out.addEventListener("click", logout);
  const name = state.user ? state.user.name : "";
  const initials = name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("") || "?";
  navRoot.appendChild(h("aside", { class: "side" },
    h("a", { class: "brand", href: "#/dashboard", text: "Advisor" }),
    h("nav", { class: "side-nav", "aria-label": "Main" }, main_),
    h("div", { class: "side-foot" }, themeButton(), foot,
      h("div", { class: "who" }, h("span", { class: "avatar", "aria-hidden": "true", text: initials }),
        h("div", {}, h("div", { class: "who-name", text: name }), out)))));
}

async function logout() {
  await api("/auth/logout", { method: "POST" });   // revoke server-side; ignore the outcome
  session.clear();
}

async function render() {
  const route = currentRoute();
  const def = ROUTES[route];
  const mine = ++renderToken;
  if (!def.public && !session.active) { go("login"); return; }
  if (def.public && session.active && (route === "login" || route === "signup")) { go("dashboard"); return; }
  renderNav(route);
  clear(main);
  const wrap = h("div", { class: "wrap page" });
  main.appendChild(wrap);
  try {
    await def.view(wrap, { go, isCurrent: () => mine === renderToken });
  } catch (e) {
    clear(wrap);
    wrap.appendChild(h("div", { class: "banner bad", role: "alert", text: "Something went wrong showing this page. Please reload." }));
    console.error(e);
  }
  document.title = (def.label ? def.label + " - " : "") + "Advisor";
  main.focus({ preventScroll: true });
}

watch(main);
session.onChange(() => { resetState(); go("login"); render(); });
window.addEventListener("hashchange", render);
render();

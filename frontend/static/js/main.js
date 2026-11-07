// Hash router, nav, auth guard.
import { h, clear } from "./dom.js";
import { api, session } from "./api.js";
import { state, resetState } from "./state.js";
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

const ROUTES = {
  "": { view: landing, public: true },
  login: { view: (c) => authView(c, "login"), public: true },
  signup: { view: (c) => authView(c, "signup"), public: true },
  dashboard: { view: dashboard, label: "Dashboard" },
  health: { view: health, label: "Health" },
  portfolio: { view: portfolio, label: "Portfolio" },
  stocks: { view: stocks, label: "Stocks" },
  credit: { view: credit, label: "Credit" },
  reports: { view: reports, label: "Reports" },
  profile: { view: profile, label: "Profile" },
  chat: { view: chat, label: "Advisor chat" },
};

const main = document.getElementById("main");
const navRoot = document.getElementById("nav-root");
let renderToken = 0;

export function go(route) { location.hash = "#/" + route; }

function currentRoute() {
  const raw = location.hash.replace(/^#\/?/, "").split("?")[0];
  return raw in ROUTES ? raw : "";
}

function renderNav(route) {
  clear(navRoot);
  if (!session.active) {
    navRoot.appendChild(h("header", { class: "nav" }, h("div", { class: "wrap" },
      h("a", { class: "brand", href: "#/" , text: "Advisor" }),
      h("div", { class: "nav-links" }),
      h("div", { class: "nav-user" },
        h("a", { class: "btn ghost", href: "#/login", text: "Log in" }),
        h("a", { class: "btn primary", href: "#/signup", text: "Create account" })))));
    return;
  }
  const links = Object.entries(ROUTES).filter(([, r]) => r.label).map(([k, r]) =>
    h("a", { href: "#/" + k, text: r.label, "aria-current": k === route ? "page" : null }));
  const out = h("button", { class: "btn", type: "button", text: "Log out" });
  out.addEventListener("click", logout);
  navRoot.appendChild(h("header", { class: "nav" }, h("div", { class: "wrap" },
    h("a", { class: "brand", href: "#/dashboard", text: "Advisor" }),
    h("nav", { class: "nav-links", "aria-label": "Main" }, links),
    h("div", { class: "nav-user" }, h("span", { class: "muted small", text: state.user ? state.user.name : "" }), out))));
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

session.onChange(() => { resetState(); go("login"); render(); });
window.addEventListener("hashchange", render);
render();

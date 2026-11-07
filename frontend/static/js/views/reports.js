import { h, money, clear } from "../dom.js";
import { loadProfile, loadLast, section } from "../state.js";
import { banner, card, pageHead, list, runStatus, nothingToInvest, nothingToInvestNote, disclaimer, kv } from "../components.js";
import { renderHealth } from "./health.js";
import { renderPortfolio } from "./portfolio.js";

const TABS = ["Summary", "Health", "Investment", "Optimizer", "Projection"];

export async function reports(c) {
  const [p, last] = await Promise.all([loadProfile(true), loadLast(true)]);
  c.appendChild(pageHead("Reports", "Your latest saved results, one tab per area."));
  if (!p) { c.appendChild(banner("info", "Complete your profile first. ", h("a", { href: "#/profile", text: "Go to profile" }))); return; }
  if (!last.found) { c.appendChild(banner("info", "No saved analysis yet. ", h("a", { href: "#/dashboard", text: "Run one from the dashboard" }))); return; }

  runStatus(last, last.section_status).forEach((b) => c.appendChild(b));
  const snap = last.snapshot || {};
  const panel = h("div", { class: "stack", id: "report-panel", role: "tabpanel" });
  const tabs = h("div", { class: "tabs", role: "tablist", "aria-label": "Report sections" });

  const views = {
    Summary: (t) => {
      const s = section("summary");
      if (!s) return t.appendChild(banner("info", "No summary yet."));
      if (s.executive_summary) t.appendChild(card("Summary", h("p", { text: s.executive_summary })));
      const k = s.key_numbers || {};
      t.appendChild(card("Key numbers", h("div", { class: "stack" },
        kv("Monthly surplus", money(k.monthly_surplus)), kv("Monthly shortfall", money(k.monthly_shortfall)),
        nothingToInvest(snap) ? null : kv("Suggested SIP", money(k.recommended_sip)),
        kv("Emergency fund gap", money(k.emergency_fund_gap)),
        kv("Annual tax saving", k.annual_tax_saving === null || k.annual_tax_saving === undefined ? "Not available" : money(k.annual_tax_saving)))));
      const q = list(s.quick_wins); if (q) t.appendChild(card("Quick wins", q));
      if (s.personalized_message) t.appendChild(card(null, h("p", { text: s.personalized_message })));
    },
    Health: (t) => { const x = section("health"); x ? renderHealth(x, t) : t.appendChild(banner("info", "No health result yet.")); },
    Investment: (t) => { const x = section("investment"); x ? renderPortfolio(x, snap, t) : t.appendChild(banner("info", "No investment result yet.")); },
    Optimizer: (t) => {
      const o = section("optimizer");
      if (!o) return t.appendChild(banner("info", "No optimizer result yet."));
      const ops = list((o.optimization_opportunities || []).map((x) => (typeof x === "string" ? x : x.title || x.action || JSON.stringify(x))));
      t.appendChild(card("Opportunities", ops || h("p", { class: "muted", text: "None found." })));
      t.appendChild(card("Tax", h("p", { class: "muted", text: o.tax_status === "unavailable" ? "Tax suggestions are not available yet." : "See suggestions above." })));
    },
    Projection: (t) => {
      if (nothingToInvest(snap)) return t.appendChild(nothingToInvestNote());
      const s = section("simulation");
      if (!s) return t.appendChild(banner("info", "No projection yet."));
      const row = (n, a, b) => h("tr", {}, h("td", { text: n }), h("td", { class: "num", text: money(a) }), h("td", { class: "num", text: money(b) }));
      const ct = s.current_trajectory || {}, ot = s.optimized_trajectory || {};
      t.appendChild(card("Projection", h("div", { class: "table-scroll" }, h("table", {},
        h("thead", {}, h("tr", {}, h("th", { text: "Horizon" }), h("th", { class: "num", text: "Current path" }), h("th", { class: "num", text: "Optimized path" }))),
        h("tbody", {}, row("5 years", ct.corpus_5yr, ot.corpus_5yr), row("10 years", ct.corpus_10yr, ot.corpus_10yr), row("20 years", ct.corpus_20yr, ot.corpus_20yr)))),
        h("p", { class: "muted small", text: s.projection_label || "Assumed returns, not a forecast." })));
      if (s.key_insight) t.appendChild(card(null, h("p", { text: s.key_insight })));
    },
  };

  const select = (name) => {
    tabs.querySelectorAll("button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === name)));
    clear(panel); views[name](panel);
  };
  TABS.forEach((t) => {
    const b = h("button", { type: "button", role: "tab", "data-tab": t, text: t, "aria-selected": "false" });
    b.addEventListener("click", () => select(t));
    tabs.appendChild(b);
  });
  c.appendChild(tabs); c.appendChild(panel);
  select("Summary");
  c.appendChild(disclaimer());
}

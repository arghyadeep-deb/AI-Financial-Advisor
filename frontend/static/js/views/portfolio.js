import { h, money, clear } from "../dom.js";
import { loadProfile, loadLast, section, runAnalysis, state } from "../state.js";
import { banner, card, pageHead, list, runStatus, nothingToInvest, nothingToInvestNote, busyButton, disclaimer } from "../components.js";
import { donut } from "../charts.js";

export function renderPortfolio(inv, snapshot, target) {
  const none = nothingToInvest(snapshot);
  const contrib = inv.contribution || {};
  if (none) {
    target.appendChild(nothingToInvestNote());
    if (contrib.reason) target.appendChild(h("p", { class: "muted", text: contrib.reason }));
  } else {
    target.appendChild(h("div", { class: "grid c3" },
      h("div", { class: "card metric" }, h("div", { class: "label", text: "Available each month" }),
        h("div", { class: "value", text: money(contrib.available_monthly) }), h("div", { class: "sub", text: "estimate from your declared numbers" })),
      h("div", { class: "card metric" }, h("div", { class: "label", text: "Suggested monthly investment" }),
        h("div", { class: "value", text: money(inv.total_monthly_investment) }), h("div", { class: "sub", text: "never above what is available" })),
      h("div", { class: "card metric" }, h("div", { class: "label", text: "10-year projection" }),
        h("div", { class: "value", text: money(inv.projected_corpus_10yr) }), h("div", { class: "sub", text: inv.projection_label || "Illustration, not a promise" }))));
    const alloc = Object.entries(inv.portfolio_allocation || {}).map(([k, v]) => ({ label: k[0].toUpperCase() + k.slice(1), value: v }));
    if (alloc.length) target.appendChild(card("Suggested allocation", donut(alloc, "Suggested allocation")));
    const sip = inv.monthly_sip_plan || [];
    if (sip.length) {
      target.appendChild(card("Monthly SIP breakdown", h("div", { class: "table-scroll" }, h("table", {},
        h("thead", {}, h("tr", {}, h("th", { text: "Instrument" }), h("th", { text: "Category" }), h("th", { class: "num", text: "Per month" }), h("th", { text: "Why" }))),
        h("tbody", {}, sip.map((s) => h("tr", {}, h("td", { text: s.instrument }), h("td", { text: s.category }),
          h("td", { class: "num", text: money(s.monthly_amount) }), h("td", { class: "muted", text: s.rationale || "" }))))))));
    }
    const lump = inv.lumpsum_suggestions || [];
    if (lump.length) target.appendChild(card("One-time suggestions", list(lump.map((l) => `${l.instrument}: ${money(l.amount)}. ${l.rationale || ""}`))));
  }
  const em = inv.emergency_fund_status;
  if (em) target.appendChild(card("Emergency fund", h("p", { text: `${em.current_months ?? "—"} of ${em.target_months ?? "—"} months. ${em.action || ""}` })));
  const tax = inv.tax_saving_plan || {};
  target.appendChild(card("Tax saving", tax.status === "unavailable"
    ? h("p", { class: "muted", text: "Not available: " + (tax.reason || "tax figures need details we do not have yet.") })
    : h("p", { text: "Estimated annual tax saved: " + money(tax.total_tax_saved_annually) })));
  if (inv.key_advice) target.appendChild(card("Key advice", h("p", { text: inv.key_advice })));
  if (inv.disclaimer) target.appendChild(h("p", { class: "muted small", text: inv.disclaimer }));
}

export async function portfolio(c) {
  const [p, last] = await Promise.all([loadProfile(true), loadLast(true)]);
  c.appendChild(pageHead("Portfolio planner", "How much you can invest each month, and a rules-based split."));
  if (!p) { c.appendChild(banner("info", "Complete your profile first. ", h("a", { href: "#/profile", text: "Go to profile" }))); return; }

  const risk = h("select", { id: "pf_risk" }, [["low", "Low"], ["moderate", "Moderate"], ["high", "High"], ["very_high", "Very high"]]
    .map(([v, t]) => h("option", { value: v, text: t, selected: v === p.risk_tolerance })));
  const hor = h("select", { id: "pf_hor" }, [["short", "Short"], ["medium", "Medium"], ["long", "Long"]]
    .map(([v, t]) => h("option", { value: v, text: t, selected: v === p.investment_horizon })));
  const msg = h("div", { "aria-live": "polite" });
  const out = h("div", { class: "stack" });

  const show = (resp) => {
    clear(out);
    runStatus(resp, resp.section_status).forEach((b) => out.appendChild(b));
    const inv = (resp.results || {}).investment;
    if (inv) renderPortfolio(inv, resp.snapshot || {}, out); else out.appendChild(banner("warn", "No result returned."));
  };
  const saved = h("button", { class: "btn primary", type: "button", text: "Plan on saved profile" });
  busyButton(saved, "Working...", async () => { msg.replaceChildren(); const r = await runAnalysis("investment"); r.ok ? show(r.data) : msg.appendChild(banner("bad", r.error)); });
  const what = h("button", { class: "btn", type: "button", text: "Try these preferences" });
  busyButton(what, "Working...", async () => {
    msg.replaceChildren();
    const r = await runAnalysis("investment", { risk_tolerance: risk.value, investment_horizon: hor.value });
    r.ok ? show(r.data) : msg.appendChild(banner("bad", r.error));
  });
  c.appendChild(card("Preferences", h("div", { class: "grid c3" },
    h("div", { class: "field" }, h("label", { for: "pf_risk", text: "Risk comfort" }), risk),
    h("div", { class: "field" }, h("label", { for: "pf_hor", text: "Time horizon" }), hor)),
    h("div", { class: "row" }, saved, what)));
  c.appendChild(msg);
  c.appendChild(out);

  const inv = section("investment");
  if (inv) { runStatus(last, last.section_status).forEach((b) => out.appendChild(b)); renderPortfolio(inv, last.snapshot || {}, out); }
  else out.appendChild(banner("info", "No saved plan yet. Run it on your saved profile above."));
  c.appendChild(disclaimer());
}

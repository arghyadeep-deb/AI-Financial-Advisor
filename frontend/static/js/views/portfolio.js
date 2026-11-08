import { h, money, clear, paise } from "../dom.js";
import { api } from "../api.js";
import { failure } from "./planning.js";
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
  c.classList.add("finance-evidence");
  await observedPortfolio(c);
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

async function observedPortfolio(c) {
  const area = card("Observed holdings", h("p", { text: "Declared observations, separate from projections. Named stock/fund picks and public advice are disabled." }));
  c.append(area);
  const r = await api("/portfolio/valuation");
  if (!r.ok) { area.append(failure(r)); return; }
  const v = r.data;
  area.append(h("p", { text: "Valuation status: " + v.status + (v.status === "complete" && !v.stale ? " (current dated valuation)" : "") + " • as of: " + v.as_of + " • observation date: " + v.observation_date + " • holdings revision " + v.holdings_revision }),
    h("p", { text: "Total value: " + paise(v.total_value_paise) + " • dated total: " + paise(v.dated_total_value_paise) + " • known subtotal (priced subset): " + paise(v.known_subtotal_paise) }),
    h("p", { text: "Currency: " + (v.currency ?? "unknown") + " • verification: " + v.verification + " • stale: " + v.stale }),
    h("p", { text: "Coverage: " + (v.coverage || []).join(", ") + " • priced positions: " + v.priced_positions + "/" + v.total_positions }),
    h("p", { text: "Concentration scope: " + v.concentration_scope + ". No low-risk claim. " + v.concentration_method }),
    h("p", { text: "Issuer HHI: " + (v.issuer_hhi ?? "unknown") + " • largest issuer share: " + (v.largest_issuer_share ?? "unknown") }),
    h("p", { text: "Unclassified value: " + paise(v.unknown_class_paise) + " • unknown issuer value: " + paise(v.unknown_issuer_paise) }),
    h("p", { text: v.performance_status }));
  for (const [label, amounts] of [["Asset class", v.asset_class_paise], ["Issuer", v.issuer_paise]]) {
    for (const [name, amount] of Object.entries(amounts || {})) area.append(h("p", { text: label + " " + name + ": " + paise(amount) }));
  }
  // Engine observation IDs enumerate open positions only. Never recompute finance in the browser.
  let openIndex = 0;
  for (const p of v.observations || []) {
    const missing = !p.closed && (v.missing_price_observations || []).includes(String(openIndex));
    if (!p.closed) openIndex++;
    area.append(h("details", {}, h("summary", { text: p.instrument_id + " • " + p.account_ref }),
      h("p", { text: "Holding: " + p.units + " units • currency: " + p.currency + " • observed: " + p.observation_date + " • closed: " + p.closed }),
      h("p", { text: "Quote status: " + (p.closed ? "closed" : missing ? "unavailable" : "available at valuation date") + " • portfolio valuation status: " + v.status }),
      h("p", { text: "Unit price: " + paise(p.price_paise) + " • price date: " + (p.price_date ?? "unknown") + " • source: " + (p.price_source ?? "unknown") + " • version: " + (p.price_version ?? "unknown") + " • expires: " + (p.price_expires ?? "unknown") }),
      h("p", { text: "Cost basis: " + paise(p.cost_basis_paise) + " • issuer: " + (p.issuer_id ?? "unknown") + " • asset class: " + (p.asset_class ?? "unknown") })));
  }
}

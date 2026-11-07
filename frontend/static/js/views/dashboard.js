import { h, money, num, clear } from "../dom.js";
import { state, loadProfile, loadLast, section, runAnalysis } from "../state.js";
import { banner, metric, card, pageHead, list, runStatus, nothingToInvest, nothingToInvestNote, busyButton, disclaimer } from "../components.js";
import { donut, lines } from "../charts.js";
import { emptyState } from "../illustrations.js";

export async function dashboard(c) {
  const [profile, last] = await Promise.all([loadProfile(true), loadLast(true)]);
  c.appendChild(pageHead("Dashboard", state.user ? "Hello, " + state.user.name + "." : null));

  if (!profile) {
    c.appendChild(banner("info", "Complete your profile first so we can calculate anything. ",
      h("a", { href: "#/profile", text: "Go to profile" })));
    return;
  }
  if ((profile.needs_reentry || []).length) {
    c.appendChild(banner("warn", "Some saved values need to be re-entered before analysis can run. ", h("a", { href: "#/profile", text: "Fix profile" })));
  }

  const out = h("div", { class: "stack" });
  c.appendChild(out);

  const runBtn = h("button", { class: "btn primary", type: "button", text: last.found ? "Re-run full analysis" : "Run full analysis" });
  const msg = h("div", { "aria-live": "polite" });
  busyButton(runBtn, "Analysing...", async () => {
    msg.replaceChildren(h("span", { class: "spinner" }), " Working on it. This can take up to 30 seconds.");
    const r = await runAnalysis("full");
    msg.replaceChildren();
    if (!r.ok) { msg.appendChild(banner("bad", r.error)); return; }
    clear(c);
    await dashboard(c);
  });
  c.appendChild(h("div", { class: "row" }, runBtn));
  c.appendChild(msg);

  if (!last.found) {
    out.appendChild(card(null, emptyState("chart", "No analysis yet", "Run your first full analysis to see your health score, a suggested split and a projection.")));
    return;
  }

  runStatus(last, last.section_status).forEach((b) => out.appendChild(b));
  const snap = last.snapshot || {};
  const none = nothingToInvest(snap);
  const hl = section("health") || {};
  const inv = section("investment") || {};
  const sim = section("simulation") || {};
  const sum = section("summary") || {};
  const known = typeof hl.overall_score === "number";

  out.appendChild(h("div", { class: "grid c4" },
    metric("Health score", known ? num(hl.overall_score, 0) : "—", known ? "Grade " + (hl.grade || "N/A") : "Not enough information"),
    metric("Monthly SIP", none ? money(0) : money(inv.total_monthly_investment), none ? "nothing investable now" : "estimate"),
    metric("10-year corpus", none ? "—" : money(inv.projected_corpus_10yr), none ? "needs a monthly amount" : "projection, not a promise"),
    metric("Monthly surplus", money((snap.surplus_paise || 0) / 100), snap.shortfall_paise ? "shortfall " + money(snap.shortfall_paise / 100) : "income minus expenses")));

  if (none) {
    out.appendChild(nothingToInvestNote());
  } else {
    const alloc = inv.portfolio_allocation || {};
    const items = Object.entries(alloc).map(([k, v]) => ({ label: k[0].toUpperCase() + k.slice(1), value: v }));
    const ct = sim.current_trajectory, ot = sim.optimized_trajectory;
    out.appendChild(h("div", { class: "grid c2" },
      items.length ? card("Suggested allocation", donut(items, "Suggested allocation")) : null,
      ct && ot ? card("Wealth projection",
        lines(["5 yr", "10 yr", "20 yr"], [
          { name: "Current path", values: [ct.corpus_5yr, ct.corpus_10yr, ct.corpus_20yr] },
          { name: "Optimized path", values: [ot.corpus_5yr, ot.corpus_10yr, ot.corpus_20yr] }], "Wealth projection"),
        h("p", { class: "muted small", text: sim.projection_label || "Projection from assumed returns; not a forecast." })) : null));
  }

  const pri = (sum.top_priorities || []).map((p) => (typeof p === "string" ? p : p.title || p.action || ""));
  const prio = list(pri.length ? pri : (hl.priority_actions || []));
  if (prio) out.appendChild(card("Priority actions", prio));
  const wins = list(sum.quick_wins);
  if (wins) out.appendChild(card("Quick wins", wins));
  if (sum.executive_summary) out.appendChild(card("Summary", h("p", { text: sum.executive_summary })));
  out.appendChild(disclaimer());
}

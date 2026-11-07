// Monthly report: pick a month and accounts, build the report from confirmed entries, inspect the evidence.
import { h, clear, paise } from "../dom.js";
import { api, fetchBlob } from "../api.js";
import { banner, card, pageHead, disclaimer } from "../components.js";
import { emptyState } from "../illustrations.js";

const LABEL = { income_paise: "Money in", spending_paise: "Money out", recognized_surplus_paise: "Left over" };

function previousMonth() {
  const d = new Date();
  d.setDate(1);
  d.setMonth(d.getMonth() - 1);
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0");
}

function coverageNotes(report) {
  const snap = report.snapshot;
  const out = [];
  if (report.stale) out.push(banner("warn", h("strong", { text: "Out of date. " }),
    "Your accounts changed after this report was made. Create it again to refresh."));
  if (!snap.selected_scope_complete) {
    const gaps = Object.values(snap.coverage || {}).reduce((n, c) => n + (c.missing_verified_dates || []).length, 0);
    out.push(banner("warn", h("strong", { text: "Not every day is covered. " }),
      gaps + " day(s) in this month have no checked statement, so these totals may be incomplete."));
  }
  if (snap.metrics && snap.metrics.classification_complete === false)
    out.push(banner("info", "Some entries are not categorised yet, so spending is shown as a total without a breakdown."));
  return out;
}

function metricsRow(m) {
  return h("div", { class: "summary" }, Object.entries(LABEL).map(([key, label]) =>
    h("div", {}, h("div", { class: "k", text: label }),
      h("div", { class: "v " + (key === "recognized_surplus_paise" && m[key] < 0 ? "neg" : ""), text: paise(m[key]) }))));
}

function affordability(m) {
  if (m.shortfall_paise) return banner("warn", h("strong", { text: "Spending was higher than money in. " }),
    "The gap is " + paise(m.shortfall_paise) + ". Nothing is suggested for investing until this is closed.");
  return banner("info", h("strong", { text: "How much can you invest? We can't say yet. " }),
    "Observed activity alone does not show future bills or how quickly you could reach your money, so no amount is suggested.");
}

function sourcesTable(snap) {
  const rows = (snap.sources || []).slice(0, 200);
  if (!rows.length) return h("p", { class: "muted", text: "No confirmed entries in this month." });
  return h("div", { class: "table-scroll" }, h("table", {},
    h("thead", {}, h("tr", {}, ["Date", "Description", "Amount", "Category"].map((t, i) => h("th", { class: i === 2 ? "right" : null, text: t })))),
    h("tbody", {}, rows.map((r) => h("tr", {},
      h("td", { text: r.posting_date }), h("td", { text: r.description || "" }),
      h("td", { class: "right " + (r.amount_paise >= 0 ? "pos" : "neg"), text: paise(r.amount_paise) }),
      h("td", { text: (r.components || []).map((c) => c.category).join(", ") || "unknown" }))))),
    snap.sources.length > rows.length ? h("p", { class: "muted small", text: "Showing the first " + rows.length + " of " + snap.sources.length + " entries. Download the CSV for all of them." }) : null);
}

async function downloadCsv(id, msg) {
  const blob = await fetchBlob(`/monthly-reports/${id}/export.csv`);
  if (!blob) { msg.replaceChildren(banner("bad", "Could not download the file.")); return; }
  const url = URL.createObjectURL(blob);
  const a = h("a", { href: url, download: "monthly-report.csv" });
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

function showReport(report, out) {
  clear(out);
  const snap = report.snapshot;
  const msg = h("div", { "aria-live": "polite" });
  coverageNotes(report).forEach((b) => out.appendChild(b));
  out.appendChild(card("Report for " + report.month, metricsRow(snap.metrics), affordability(snap.metrics),
    snap.comparison && snap.comparison.status === "available"
      ? h("p", { class: "muted", text: "Compared with last month: money in " + paise(snap.comparison.changes_paise.income_paise) +
          ", money out " + paise(snap.comparison.changes_paise.spending_paise) + "." })
      : h("p", { class: "muted small", text: "No month-on-month comparison: it needs checked reports for both months." }),
    snap.net_worth && snap.net_worth.status === "unavailable"
      ? h("p", { class: "muted small", text: "Net worth is not shown: it needs dated holdings and debt balances." }) : null));
  const dl = h("button", { class: "btn", type: "button", text: "Download CSV" });
  dl.addEventListener("click", () => downloadCsv(report.id, msg));
  out.appendChild(card("Entries behind these numbers", sourcesTable(snap), msg, h("div", { class: "row" }, dl)));
}

export async function monthly(c) {
  c.appendChild(pageHead("Monthly report", "Totals come only from entries you confirmed. Anything unknown stays unknown."));
  const fmt = await api("/statement-formats");
  if (!fmt.ok || !fmt.data || !fmt.data.enabled) {
    c.appendChild(banner("info", "Monthly reports are not available yet. Your other tools work as usual."));
    return;
  }
  const [accounts, vector, history] = await Promise.all([api("/statement-accounts"), api("/statement-accounts/vector"), api("/monthly-reports")]);
  if (!accounts.ok || !vector.ok) { c.appendChild(banner("bad", accounts.error || vector.error)); return; }
  if (!accounts.data.length) {
    c.appendChild(emptyState("chart", "No accounts yet", "Add an account and confirm a statement first.",
      h("a", { class: "btn primary", href: "#/statements", text: "Go to statements" }), 2));
    return;
  }
  const out = h("div", { class: "stack" });
  const msg = h("div", { "aria-live": "polite" });
  const month = h("input", { id: "mr_month", type: "month", value: previousMonth(), max: new Date().toISOString().slice(0, 7) });
  const boxes = accounts.data.map((a) => ({ a, box: h("input", { type: "checkbox", id: "mr_" + a.id, checked: true }) }));
  const create = h("button", { class: "btn primary", type: "submit", text: "Create report" });
  const form = h("form", { novalidate: true },
    h("div", { class: "field" }, h("label", { for: "mr_month", text: "Month" }), month),
    h("fieldset", { class: "field" }, h("legend", { text: "Accounts to include" }),
      boxes.map(({ a, box }) => h("div", { class: "check" }, box, h("label", { for: "mr_" + a.id, text: a.label })))), create);
  form.addEventListener("submit", async (e) => {
    e.preventDefault(); msg.replaceChildren();
    const ids = boxes.filter(({ box }) => box.checked).map(({ a }) => a.id);
    if (!/^\d{4}-\d{2}$/.test(month.value)) { msg.appendChild(banner("bad", "Choose a month.")); return; }
    if (!ids.length) { msg.appendChild(banner("bad", "Pick at least one account.")); return; }
    create.disabled = true;
    const fresh = await api("/statement-accounts/vector");        // always the current revisions, never a cached copy
    const r = fresh.ok ? await api("/monthly-reports", { method: "POST", body: { month: month.value, account_ids: ids, expected_vector: fresh.data } }) : fresh;
    create.disabled = false;
    if (r.ok) showReport(r.data, out);
    else msg.appendChild(banner(r.status === 409 ? "warn" : "bad", r.status === 409 ? "Your accounts changed while this was being made. Please try again." : r.error));
  });
  c.appendChild(card("Create a report", form, msg));
  c.appendChild(out);
  const past = history.ok ? history.data : [];
  if (past.length) {
    showReport(past[0], out);
    if (past.length > 1) c.appendChild(card("Earlier reports", h("ul", { class: "list" }, past.slice(1, 13).map((r) => {
      const b = h("button", { class: "btn ghost", type: "button", text: r.month + (r.stale ? " (out of date)" : "") });
      b.addEventListener("click", () => showReport(r, out));
      return h("li", {}, b);
    }))));
  } else out.appendChild(emptyState("chart", "No report yet", "Choose a month above and create your first report.", null, 2));
  c.appendChild(disclaimer());
}

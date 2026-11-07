import { h, clear, uid, paise } from "../dom.js";
import { api } from "../api.js";
import { banner, card, pageHead } from "../components.js";
import { emptyState } from "../illustrations.js";
import { mappedCard } from "./mapped-import.js";

const rupees = paise;
const STATE = {
  queued: "Waiting to be read", needs_review: "Needs your review", completed: "Imported", cancelled: "Cancelled",
  quarantined: "Stopped for safety", reversed: "Undone", failed: "Failed",
};
const op = (rev, reason) => ({ expected_revision: rev, idempotency_key: uid() + uid(), reason });

async function accountsCard(onChange) {
  const r = await api("/statement-accounts");
  const msg = h("div", { "aria-live": "polite" });
  const label = h("input", { id: "acct_label", maxlength: 60 });
  const token = h("input", { id: "acct_token", maxlength: 60 });
  const go = h("button", { class: "btn", type: "submit", text: "Add account" });
  const form = h("form", { novalidate: true },
    h("div", { class: "grid c2" },
      h("div", { class: "field" }, h("label", { for: "acct_label", text: "Name you will recognise" }), label),
      h("div", { class: "field" }, h("label", { for: "acct_token", text: "Account token from the file header" }), token)), go);
  form.addEventListener("submit", async (e) => {
    e.preventDefault(); msg.replaceChildren();
    const d = await api("/statement-accounts", { method: "POST", body: { label: label.value.trim(), token: token.value.trim(), account_type: "synthetic_debit" } });
    if (d.ok) onChange(); else msg.appendChild(banner("bad", d.error));
  });
  const rows = r.ok ? r.data : [];
  return { rows, node: card("Accounts",
    r.ok ? (rows.length ? h("ul", { class: "list" }, rows.map((a) => h("li", { text: a.label + " (" + a.token + ")" }))) : h("p", { class: "muted", text: "No accounts yet." })) : banner("bad", r.error),
    msg, form) };
}

function uploadCard(accounts, onChange) {
  const msg = h("div", { "aria-live": "polite" });
  if (!accounts.length) return card("Upload a statement", h("p", { class: "muted", text: "Add an account first." }));
  const sel = h("select", { id: "up_acct" }, accounts.map((a) => h("option", { value: a.id, text: a.label })));
  const file = h("input", { id: "up_file", type: "file", accept: ".csv,.txt,text/csv,text/plain" });
  const go = h("button", { class: "btn primary", type: "submit", text: "Upload" });
  const form = h("form", { novalidate: true },
    h("div", { class: "field" }, h("label", { for: "up_acct", text: "Account" }), sel),
    h("div", { class: "field" }, h("label", { for: "up_file", text: "Statement file (text or CSV)" }), file), go);
  form.addEventListener("submit", async (e) => {
    e.preventDefault(); msg.replaceChildren();
    const f = file.files[0];
    if (!f) { msg.appendChild(banner("bad", "Choose a file first.")); return; }
    go.disabled = true;
    const bytes = await f.arrayBuffer();
    const d = await api(`/statement-accounts/${sel.value}/uploads`, { method: "POST", raw: bytes, contentType: f.name.toLowerCase().endsWith(".csv") ? "text/csv" : "text/plain" });
    go.disabled = false;
    if (d.ok) { msg.appendChild(banner("ok", "Uploaded. It is being read; this page shows its status below.")); onChange(); }
    else msg.appendChild(banner("bad", d.error));
  });
  return card("Upload a statement", h("p", { class: "muted", text: "Only the documented sample format works here. For any other bank, use the CSV option below. PDFs, photos and scanned files are not supported yet." }), msg, form);
}

async function reviewPanel(job, onChange) {
  const rows = await api(`/statement-imports/${job.id}/rows`);
  const msg = h("div", { "aria-live": "polite" });
  if (!rows.ok) return banner("bad", rows.error);
  const mismatch = job.difference_paise !== null && job.difference_paise !== 0;
  const unverified = job.difference_paise === null;
  const choices = rows.data.map((r) => {
    const sel = h("select", { "aria-label": "Decision for row " + r.source_row });
    sel.appendChild(h("option", { value: "keep", text: "Add as new entry" }));
    (r.candidate_entry_ids || []).forEach((id) => sel.appendChild(h("option", { value: "m:" + id, text: "Same as an existing entry" })));
    if ((r.candidate_entry_ids || []).length) sel.appendChild(h("option", { value: "distinct", text: "Different from those entries" }));
    return { r, sel };
  });
  const ack = h("input", { type: "checkbox", id: "ack_" + job.id });
  const confirm = h("button", { class: "btn primary", type: "button", text: "Confirm import", disabled: mismatch });
  confirm.addEventListener("click", async () => {
    msg.replaceChildren(); confirm.disabled = true;
    const decisions = choices.map(({ r, sel }) => {
      const v = sel.value;
      return { row_id: r.id, category: r.category, match_entry_id: v.startsWith("m:") ? v.slice(2) : null, distinct: v === "distinct" };
    });
    const d = await api(`/statement-imports/${job.id}/resume`, { method: "POST",
      body: { ...op(job.revision, "Reviewed and confirmed by the account owner"), decisions, acknowledge_unverified: ack.checked } });
    if (d.ok) onChange(); else { confirm.disabled = false; msg.appendChild(banner("bad", d.error)); }
  });
  const cancel = h("button", { class: "btn", type: "button", text: "Cancel this import" });
  cancel.addEventListener("click", async () => {
    const d = await api(`/statement-imports/${job.id}/cancel`, { method: "POST", body: op(job.revision, "Cancelled by the account owner") });
    if (d.ok) onChange(); else msg.appendChild(banner("bad", d.error));
  });
  return h("div", { class: "stack" },
    mismatch ? banner("bad", h("strong", { text: "The numbers do not add up. " }), "Opening balance plus the entries does not equal the closing balance (off by " + rupees(job.difference_paise) + "). This file cannot be imported.") : null,
    unverified ? banner("warn", h("strong", { text: "Balances not verified. " }), "You can still import, but these days will count as unverified.") : null,
    h("div", { class: "summary" },
      h("div", {}, h("div", { class: "k", text: "Entries" }), h("div", { class: "v", text: String(rows.data.length) })),
      h("div", {}, h("div", { class: "k", text: "Money in" }), h("div", { class: "v", text: rupees(rows.data.filter((r) => r.amount_paise > 0).reduce((a, r) => a + r.amount_paise, 0)) })),
      h("div", {}, h("div", { class: "k", text: "Money out" }), h("div", { class: "v", text: rupees(rows.data.filter((r) => r.amount_paise < 0).reduce((a, r) => a + r.amount_paise, 0)) })),
      h("div", {}, h("div", { class: "k", text: "Balance check" }), h("div", { class: "v", text: job.difference_paise === 0 ? "Matches" : job.difference_paise === null ? "Unverified" : "Off by " + rupees(job.difference_paise) }))),
    h("div", { class: "table-scroll" }, h("table", {},
      h("thead", {}, h("tr", {}, ["Date", "Description", "Amount", "Category", "Decision"].map((t) => h("th", { text: t })))),
      h("tbody", {}, choices.map(({ r, sel }) => h("tr", {},
        h("td", { text: r.posting_date }), h("td", { text: r.description }), h("td", { class: "right " + (r.amount_paise >= 0 ? "pos" : "neg"), text: rupees(r.amount_paise) }),
        h("td", { text: r.category }), h("td", {}, sel)))))),
    unverified ? h("div", { class: "check" }, ack, h("label", { for: "ack_" + job.id, text: "Import anyway, balances unverified" })) : null,
    msg, h("div", { class: "row" }, confirm, cancel));
}

async function importsCard(onChange) {
  const r = await api("/statement-imports");
  if (!r.ok) return card("Your imports", banner("bad", r.error));
  const items = [];
  for (const job of r.data) {
    const head = h("div", { class: "row" }, h("strong", { text: (job.start_date || "?") + " to " + (job.end_date || "?") }), " ",
      h("span", { class: "pill", text: STATE[job.state] || job.state }),
      job.error_code ? h("span", { class: "muted", text: " " + (job.error_message || "(" + job.error_code + ")") }) : null);
    const body = job.state === "needs_review" ? await reviewPanel(job, onChange) : null;
    items.push(h("div", { class: "stack" }, head, body));
  }
  return card("Your imports", items.length ? h("div", { class: "stack" }, items) : emptyState("doc", "Nothing uploaded yet", "Upload a statement file above. You review every row before anything counts."),
    h("button", { class: "btn", type: "button", text: "Refresh status", onClick: onChange }));
}

export async function statements(c) {
  async function render() {
    clear(c);
    c.appendChild(pageHead("Statements", "Upload a statement, check it, then confirm it before anything counts."));
    const fmt = await api("/statement-formats");
    if (!fmt.ok || !fmt.data || !fmt.data.enabled) {
      c.appendChild(banner("info", "Statement upload is not available yet. Your other tools work as usual."));
      return;
    }
    c.appendChild(banner("info", "Nothing is added to your records until you confirm it. This is a limited preview: sample format only, no PDF."));
    const acc = await accountsCard(render);
    c.appendChild(acc.node);
    c.appendChild(uploadCard(acc.rows, render));
    const mapped = mappedCard(acc.rows, render);
    if (mapped) c.appendChild(mapped);
    c.appendChild(await importsCard(render));
  }
  await render();
}

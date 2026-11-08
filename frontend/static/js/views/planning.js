import { h, clear, paise, uid } from "../dom.js";
import { api } from "../api.js";
import { banner, card, pageHead } from "../components.js";

// Field definitions follow the existing strict planning contracts. Amount inputs are integer paise.
const fields = {
  budgets: [["month", "Month", "month"], ["rollover", "Rollover", ["none", "positive"]]],
  obligations: [["label", "Label"], ["amount_paise", "Amount (paise)", "number"], ["due_date", "Due date", "date"], ["cadence", "Cadence", ["once", "monthly", "annual"]], ["variable", "Variable amount", "checkbox"], ["paused", "Paused", "checkbox"], ["reminder_opt_in", "In-app reminder", "checkbox"]],
  goals: [["label", "Label"], ["target_paise", "Target (paise)", "number"], ["allocated_paise", "Allocated (paise)", "number", 0], ["target_date", "Target date", "date"], ["value_basis", "Value basis", ["future", "present"]], ["inflation_bps", "Inflation assumption (basis points)", "number", 0], ["priority", "Priority", "number", 1], ["funding_account_id", "Funding account ID"], ["reminder_opt_in", "In-app reminder", "checkbox"]],
  debts: [["label", "Label"], ["obligation_id", "Confirmed obligation ID"], ["principal_paise", "Principal (paise)", "number"], ["annual_rate_bps", "Annual rate (basis points; blank means unknown)", "optional"], ["rate_type", "Rate type", ["fixed", "floating"]], ["minimum_payment_paise", "Minimum payment (paise)", "number"], ["monthly_fee_paise", "Monthly fee (paise)", "number", 0], ["prepayment_fee_paise", "Prepayment fee (paise)", "number", 0], ["term_months", "Term in months (blank means unknown)", "optional"], ["evidence_date", "Evidence date", "date"]],
};

export function failure(r) {
  if ([404,503].includes(r.status)) return banner("info", "This feature is not available yet, or the resource is missing or not shared with you.");
  return banner("bad", r.status === 409 ? "Conflict: your input is preserved. Reload this screen to review the latest revision before retrying. " + r.error : r.error);
}

export function field(id, label, type = "text", value = "") {
  const input = Array.isArray(type) ? h("select", { id }, type.map(v => h("option", { value: v, text: v }))) : h("input", { id, type: type === "optional" ? "number" : type, step: type === "number" || type === "optional" ? "1" : null, min: type === "number" || type === "optional" ? "0" : null });
  if (type === "checkbox") input.checked = !!value;
  else input.value = value === "" && Array.isArray(type) ? type[0] : value ?? "";
  return { input, node: h("div", { class: "field" }, h("label", { for: id, text: label }), input) };
}

function editor(kind, row, refresh) {
  const data = row?.data || {};
  const prefix = kind + "-" + (row?.id || "new");
  const defs = [...fields[kind], ["archived", "Archived", "checkbox"]];
  const controls = defs.map(([key, label, type, fallback]) => ({ key, type, ...field(prefix + key, label, type, data[key] ?? fallback) }));
  const lines = h("div", { class: "stack" });
  const lineInputs = [];
  function line(category = "", amount = "") {
    const key = field(prefix + "category" + lineInputs.length, "Budget category", "text", category);
    const val = field(prefix + "amount" + lineInputs.length, "Allocation (paise)", "number", amount);
    lineInputs.push([key.input, val.input]); lines.append(h("div", { class: "grid c2" }, key.node, val.node));
  }
  if (kind === "budgets") {
    Object.entries(data.lines || { groceries: "" }).forEach(([k,v]) => line(k,v));
    lines.append(h("button", { type: "button", class: "btn", text: "Add category", onClick: () => line() }));
  }
  const reason = field(prefix + "reason", "Reason for change");
  const msg = h("div", { "aria-live": "polite" });
  const save = h("button", { type: "submit", class: "btn primary", text: row ? "Save changes" : "Create " + kind.slice(0,-1) });
  const form = h("form", {}, h("div", { class: "grid c2" }, controls.map(f => f.node)), lines, reason.node, msg, save);
  let pending = null;
  form.addEventListener("submit", async e => {
    e.preventDefault(); clear(msg);
    const next = { ...data };
    for (const f of controls) next[f.key] = f.type === "checkbox" ? f.input.checked : f.type === "optional" && f.input.value === "" ? null : ["number", "optional"].includes(f.type) ? (f.input.value === "" ? null : Number(f.input.value)) : f.input.value.trim();
    if (kind === "budgets") {
      next.lines = {};
      for (const [k,v] of lineInputs) {
        if (Object.hasOwn(next.lines, k.value.trim())) { msg.append(banner("bad", "Each category must be unique.")); return; }
        next.lines[k.value.trim()] = v.value === "" ? null : Number(v.value);
      }
    }
    // An exact retry retains the operation key after a lost response; changed inputs get a new key.
    const signature = JSON.stringify([next, reason.input.value]);
    if (!pending || pending.signature !== signature) pending = { signature, key: uid() };
    save.disabled = true;
    const r = await api("/" + kind + (row ? "/" + encodeURIComponent(row.id) : ""), { method: row ? "PUT" : "POST", body: { data: next, expected_revision: row?.revision || 0, idempotency_key: pending.key, reason: reason.input.value } });
    save.disabled = false;
    if (r.ok) await refresh(r.data); else msg.append(failure(r));
  });
  return form;
}

function budgetTools(row, replace) {
  const area = h("div", { class: "stack" });
  const msg = h("div", { "aria-live": "polite" });
  if (row.revision > 1) {
    const reason = field("undo-" + row.id, "Reason for undo");
    const undo = h("button", { type: "button", class: "btn", text: "Undo last budget edit" });
    let pending = null;
    undo.addEventListener("click", async () => {
      clear(msg);
      if (!reason.input.value.trim()) { msg.append(banner("bad", "Enter a reason for undo.")); return; }
      const signature = reason.input.value.trim();
      if (!pending || pending.signature !== signature) pending = { signature, key: uid() };
      undo.disabled = true;
      const previous = await api("/budgets/" + encodeURIComponent(row.id) + "?revision=" + (row.revision - 1));
      if (!previous.ok) { msg.append(failure(previous)); undo.disabled = false; return; }
      const r = await api("/budgets/" + encodeURIComponent(row.id), { method: "PUT", body: {
        data: previous.data.data, expected_revision: row.revision, idempotency_key: pending.key,
        reason: reason.input.value.trim()
      } });
      undo.disabled = false;
      if (r.ok) replace(r.data); else msg.append(failure(r));
    });
    area.append(reason.node, undo);
  }
  const report = field("explain-" + row.id, "Monthly report ID for budget explanation");
  const explain = h("button", { type: "button", class: "btn", text: "Explain budget" });
  explain.addEventListener("click", async () => {
    clear(msg); explain.disabled = true;
    const r = await api("/monthly-reports/" + encodeURIComponent(report.input.value.trim()));
    explain.disabled = false;
    if (!r.ok) { msg.append(failure(r)); return; }
    const b = r.data.snapshot?.budget;
    if (b?.budget?.id !== row.id || !b.lines) { msg.append(banner("info", "Budget explanation unavailable: this report does not include this budget.")); return; }
    msg.append(h("p", { text: "Report month: " + r.data.month + " • budget revision " + b.budget.revision + " • stale: " + r.data.stale + " • selected scope complete: " + r.data.snapshot.selected_scope_complete + ". Frozen report numbers; budget allocation is not investment capacity." }));
    for (const [category, values] of Object.entries(b.lines)) msg.append(h("p", { text: category + ": allocated " + paise(values.allocated_paise) + ", actual " + paise(values.actual_paise) + ", overspend " + paise(values.overspend_paise) + "." }));
  });
  area.append(report.node, explain, msg);
  return area;
}

export async function planning(c) {
  c.classList.add("finance-evidence");
  async function render() {
    clear(c); c.append(pageHead("Plan", "Budgets and declared commitments. Goals and debt are experimental previews; no payments, trades or promised returns."));
    for (const kind of Object.keys(fields)) {
      const r = await api("/" + kind);
      if (!r.ok) { c.append([404,503].includes(r.status) ? banner("info", "Planning is not available yet.") : failure(r)); return; }
      const section = card(kind[0].toUpperCase() + kind.slice(1));
      const listing = h("div");
      const identities = new Set(r.data.map(row => row.id));
      function rowNode(row) {
        const detail = h("details", {}, h("summary", { text: (row.data.label || row.data.month) + " — revision " + row.revision }));
        detail.append(h("p", { class: "muted", text: "Source: user-declared • recorded " + row.created_at + " • ID: " + row.id }));
        for (const [k,v] of Object.entries(row.data)) if (k.endsWith("_paise")) detail.append(h("p", { text: k.replaceAll("_", " ") + ": " + paise(v) }));
        if (row.data.lines) for (const [k,v] of Object.entries(row.data.lines)) detail.append(h("p", { text: k + ": " + paise(v) }));
        detail.append(editor(kind, row, saved => {
          detail.replaceWith(rowNode(saved));
        }));
        if (kind === "budgets") detail.append(budgetTools(row, saved => detail.replaceWith(rowNode(saved))));
        return detail;
      }
      r.data.forEach(row => listing.append(rowNode(row)));
      const empty = h("p", { text: "No " + kind + " yet.", hidden: !!r.data.length });
      let offset = r.data.length;
      const more = h("button", { type: "button", class: "btn", text: "Load more " + kind, hidden: r.data.length < 100 });
      const loadMsg = h("div", { "aria-live": "polite" });
      more.addEventListener("click", async () => {
        more.disabled = true; clear(loadMsg);
        const next = await api("/" + kind + "?offset=" + offset); more.disabled = false;
        if (!next.ok) { loadMsg.append(failure(next)); return; }
        next.data.forEach(row => { if (!identities.has(row.id)) { identities.add(row.id); listing.append(rowNode(row)); } });
        offset += next.data.length; more.hidden = next.data.length < 100;
      });
      const create = h("details", {}, h("summary", { text: "Add " + kind.slice(0,-1) }));
      function newForm() {
        const form = editor(kind, null, saved => {
          empty.hidden = true; identities.add(saved.id); listing.append(rowNode(saved)); form.replaceWith(newForm());
        });
        return form;
      }
      create.append(newForm()); section.append(empty, listing, more, loadMsg, create);
      c.append(section);
    }
  }
  await render();
}


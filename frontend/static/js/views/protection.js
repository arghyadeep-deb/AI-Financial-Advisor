import { h, clear, paise, uid } from "../dom.js";
import { api } from "../api.js";
import { banner, card, pageHead } from "../components.js";
import { field, failure } from "./planning.js";

const facts = [["policy_type", "Policy type", ["unknown", "life", "health", "property", "other"]],
  ["insurer", "Insurer"], ["coverage_paise", "Coverage (paise)", "number"], ["premium_paise", "Premium (paise)", "number"],
  ["renewal_date", "Renewal date", "date"], ["exclusions", "Exclusions"], ["waiting_period", "Waiting period"], ["dependent_coverage", "Dependent coverage"]];
const checks = [["nominee_check_complete", "Nominee checklist complete"], ["emergency_location_check_complete", "Emergency document location checklist complete"],
  ["reminder_opt_in", "Opt in to in-app renewal reminder"], ["archived", "Archived"]];

export async function protection(c) {
  c.classList.add("finance-evidence");
  c.append(pageHead("Protection inventory preview", "Your personal declared policies only. No insurance adequacy or legal succession assessment. No beneficiary identity documents collected. Reminders are opt-in and in-app only, subject to your reminder preferences."),
    h("a", { href: "#/reminders", text: "Review reminder preferences" }));
  const area = h("div", { class: "stack" }); c.append(area);
  let book;
  let revision;
  function editor(item, index) {
    const baseline = book;
    const prefix = uid();
    const ref = field(prefix + "reference", "Policy reference", "text", item?.reference);
    const controls = facts.map(([key, label, type]) => ({ key, type, ...field(prefix + key, label + " (blank means unknown)", type, item?.[key] ?? (key === "policy_type" ? "unknown" : "")),
      evidence: field(prefix + key + "evidence", label + " evidence / declaration reference", "text", item?.evidence?.[key]) }));
    const flags = checks.map(([key, label]) => ({ key, ...field(prefix + key, label, "checkbox", item?.[key]) }));
    const reason = field(prefix + "reason", "Reason for policy change");
    const msg = h("div", { "aria-live": "polite" });
    const save = h("button", { type: "submit", class: "btn primary", text: item ? "Save policy" : "Add policy" });
    const form = h("form", {}, ref.node, controls.map(f => h("div", { class: "grid c2" }, f.node, f.evidence.node)), flags.map(f => f.node), reason.node, msg, save);
    let pending;
    form.addEventListener("submit", async e => {
      e.preventDefault(); clear(msg);
      const policy = { reference: ref.input.value.trim(), source: "user_declared", evidence: {} };
      for (const f of controls) {
        const value = f.input.value.trim();
        policy[f.key] = value === "" ? null : f.type === "number" ? Number(value) : value;
        if (f.evidence.input.value.trim()) policy.evidence[f.key] = f.evidence.input.value.trim();
      }
      for (const f of flags) policy[f.key] = f.input.checked;
      const policies = [...baseline.data.policies];
      if (item) policies[index] = policy; else policies.push(policy);
      const signature = JSON.stringify([policies, reason.input.value]);
      if (!pending || pending.signature !== signature) pending = { signature, key: uid() };
      save.disabled = true;
      const r = await api("/policies", { method: "POST", body: { expected_revision: baseline.revision, idempotency_key: pending.key, reason: reason.input.value.trim(), data: { policies } } });
      save.disabled = false;
      if (!r.ok) { msg.append(failure(r)); return; }
      book = r.data;
      revision.textContent = "Protection revision " + book.revision;
      if (item) form.closest("details").replaceWith(policyNode(book.data.policies[index], index));
      else {
        const ordinal = book.data.policies.length - 1;
        form.closest("details").before(policyNode(book.data.policies[ordinal], ordinal));
        form.replaceWith(editor(null));
      }
      // Other forms retain drafts and their original revision; stale writes conflict.
    });
    return form;
  }
  function policyNode(item, index) {
    return h("details", {}, h("summary", { text: "Policy " + item.reference }),
      h("p", { text: "Source: " + item.source + " • personal inventory • recorded date: " + (book.created_at ?? "unknown") }),
      facts.map(([key, label]) => h("p", { text: label + ": " + (key.endsWith("_paise") ? paise(item[key]) : item[key] ?? "unknown") + " • evidence: " + (item.evidence?.[key] ?? "unknown") })),
      checks.map(([key, label]) => h("p", { text: label + ": " + item[key] })), editor(item, index));
  }
  function show() {
    clear(area);
    revision = h("p", { text: "Protection revision " + book.revision });
    area.append(banner("info", "Declared inventory only; insurance adequacy and legal succession are not evaluated."), revision);
    book.data.policies.forEach((p, i) => area.append(policyNode(p, i)));
    area.append(h("details", {}, h("summary", { text: "Add insurance policy" }), editor(null)));
  }
  const r = await api("/policies");
  if (r.ok) { book = r.data; show(); return; }
  if (![404,503].includes(r.status)) { area.append(failure(r)); return; }
  area.append(banner("info", "Protection inventory is not available yet, or no inventory has been created."));
  const start = h("button", { type: "button", class: "btn", text: "Start synthetic protection inventory" });
  const key = uid();
  start.addEventListener("click", async () => {
    start.disabled = true;
    const saved = await api("/policies", { method: "POST", body: { expected_revision: 0, idempotency_key: key, reason: "Explicit synthetic protection initialization", data: { policies: [] } } });
    if (saved.ok) { book = saved.data; show(); }
    else { clear(area); area.append(failure(saved)); }
  });
  area.append(start);
}

import { h, clear } from "../dom.js";
import { api } from "../api.js";
import { banner, card, pageHead } from "../components.js";
import { field, failure } from "./planning.js";

export async function notifications(c) {
  c.append(pageHead("Reminders", "In-app only. Email and push are deferred. Quiet hours use Asia/Kolkata."));
  const pref = await api("/preferences");
  if (!pref.ok) { c.append([404,503].includes(pref.status) ? banner("info", "Reminders are not available yet.") : failure(pref)); return; }
  const enabled = field("notice-enabled", "Enable in-app notices", "checkbox", pref.data.enabled);
  const report = field("notice-reports", "Report ready", "checkbox", pref.data.categories.includes("report_ready"));
  const reminder = field("notice-reminders", "Planning reminders", "checkbox", pref.data.categories.includes("reminder"));
  const start = field("notice-start", "Quiet hours start (0–23; blank for none)", "optional", pref.data.quiet_start);
  const end = field("notice-end", "Quiet hours end (0–23; blank for none)", "optional", pref.data.quiet_end);
  start.input.max = end.input.max = "23";
  const msg = h("div", { "aria-live": "polite" });
  const save = h("button", { class: "btn primary", type: "submit", text: "Save reminder preferences" });
  const form = h("form", {}, enabled.node, report.node, reminder.node, h("div", { class: "grid c2" }, start.node, end.node), msg, save);
  form.addEventListener("submit", async e => {
    e.preventDefault(); clear(msg);
    if ((start.input.value === "") !== (end.input.value === "") || (start.input.value !== "" && start.input.value === end.input.value)) {
      msg.append(banner("bad", "Both quiet-hour boundaries are required and must differ (Asia/Kolkata).")); return;
    }
    save.disabled = true;
    const r = await api("/preferences", { method: "PUT", body: {
      enabled: enabled.input.checked, email_enabled: false,
      categories: [report.input.checked ? "report_ready" : null, reminder.input.checked ? "reminder" : null].filter(Boolean),
      quiet_start: start.input.value === "" ? null : Number(start.input.value), quiet_end: end.input.value === "" ? null : Number(end.input.value),
    } });
    save.disabled = false; msg.append(r.ok ? banner("ok", "Reminder preferences saved. Email stays off.") : failure(r));
  });
  c.append(card("Preferences", form));
  const feed = card("In-app notices", h("p", { class: "muted", text: "Dismiss hides a notice for this visit only. Server-side dismissal is not available yet." }));
  const rows = h("div", { class: "stack" });
  const dismissed = new Set();
  async function refresh() {
    const r = await api("/notifications"); clear(rows);
    if (!r.ok) { rows.append([404,503].includes(r.status) ? banner("info", "Notices are not available yet.") : failure(r)); return; }
    const notices = r.data.filter(n => !dismissed.has(n.id));
    if (!notices.length) rows.append(h("p", { text: "No notices to show." }));
    for (const n of notices) {
      const item = h("div", {}, h("p", { text: n.message }), h("p", { class: "muted", text: n.category + " • " + n.created_at }));
      item.append(h("button", { class: "btn", type: "button", text: "Dismiss for this visit", "aria-label": "Dismiss " + n.message + " for this visit", onClick: () => { dismissed.add(n.id); item.remove(); if (!rows.children.length) rows.append(h("p", { text: "No notices to show." })); } }));
      rows.append(item);
    }
  }
  feed.append(rows, h("button", { class: "btn", type: "button", text: "Refresh notices", onClick: refresh }));
  c.append(feed); await refresh();
}

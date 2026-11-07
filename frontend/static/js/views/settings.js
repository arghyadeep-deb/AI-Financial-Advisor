import { h, clear } from "../dom.js";
import { api, session } from "../api.js";
import { banner, card, pageHead } from "../components.js";
import { emptyState } from "../illustrations.js";

const NOTICE_VERSION = "v1";
const when = (iso) => { try { return new Date(iso + (iso.endsWith("Z") ? "" : "Z")).toLocaleString(); } catch (e) { return String(iso); } };

async function sessionsCard() {
  const body = h("div", { class: "stack" });
  const msg = h("div", { "aria-live": "polite" });
  async function load() {
    const r = await api("/sessions");
    clear(body);
    if (!r.ok) { body.appendChild(banner("bad", r.error)); return; }
    const rows = (r.data || []).filter((s) => !s.revoked_at);
    body.appendChild(h("div", { class: "table-scroll" }, h("table", {},
      h("thead", {}, h("tr", {}, h("th", { text: "Started" }), h("th", { text: "Expires" }), h("th", { text: "" }))),
      h("tbody", {}, rows.map((s) => h("tr", {},
        h("td", { text: when(s.created_at) + (s.current ? " (this device)" : "") }),
        h("td", { text: when(s.expires_at) }),
        h("td", { class: "right" }, s.current ? null : h("button", { class: "btn", type: "button", text: "Sign out",
          "aria-label": "Sign out the session started " + when(s.created_at),
          onClick: async () => { const d = await api("/sessions/" + s.id, { method: "DELETE" }); msg.replaceChildren(d.ok ? banner("ok", "Session signed out.") : banner("bad", d.error)); load(); } }))))))));
  }
  await load();
  return card("Where you are signed in", h("p", { class: "muted", text: "Sign out any device you do not recognise." }), msg, body);
}

function passwordCard() {
  const msg = h("div", { "aria-live": "polite" });
  const cur = h("input", { id: "pw_cur", type: "password", autocomplete: "current-password", required: true, maxlength: 128 });
  const nw = h("input", { id: "pw_new", type: "password", autocomplete: "new-password", required: true, maxlength: 128 });
  const go = h("button", { class: "btn primary", type: "submit", text: "Change password" });
  const form = h("form", { novalidate: true },
    h("div", { class: "field" }, h("label", { for: "pw_cur", text: "Current password" }), cur),
    h("div", { class: "field" }, h("label", { for: "pw_new", text: "New password" }), nw, h("div", { class: "hint", text: "Changing it signs you out everywhere." })), go);
  form.addEventListener("submit", async (e) => {
    e.preventDefault(); msg.replaceChildren(); go.disabled = true;
    const r = await api("/auth/password-change", { method: "POST", body: { password: cur.value, new_password: nw.value } });
    go.disabled = false; cur.value = ""; nw.value = "";
    if (r.status === 204 || r.ok) { session.clear(); return; }               // every token was revoked: back to login
    msg.appendChild(banner("bad", r.error));
  });
  return card("Password", msg, form);
}

function consentCard() {
  const msg = h("div", { "aria-live": "polite" });
  const row = (purpose, title, text) => {
    const yes = h("button", { class: "btn", type: "button", text: "Allow" });
    const no = h("button", { class: "btn", type: "button", text: "Do not allow" });
    const send = (granted) => async () => {
      const r = await api("/privacy/consents", { method: "POST", body: { purpose, granted, notice_version: NOTICE_VERSION } });
      msg.replaceChildren(r.ok ? banner("ok", `Saved: ${title} ${granted ? "allowed" : "not allowed"}.`) : banner("bad", r.error));
    };
    yes.addEventListener("click", send(true)); no.addEventListener("click", send(false));
    return h("div", { class: "stack" }, h("strong", { text: title }), h("p", { class: "muted", text }), h("div", { class: "row" }, yes, no));
  };
  return card("Your choices", h("p", { class: "muted", text: "Each choice is recorded with the date and notice version. You can change it any time." }), msg,
    row("model_inference", "Use an AI model to explain my numbers", "Without it you get rules-based replies only. The numbers do not change."),
    row("tracing", "Share diagnostic traces", "Metadata only, never your financial figures or messages."));
}

async function preferencesCard() {
  const r = await api("/preferences");
  const msg = h("div", { "aria-live": "polite" });
  if (!r.ok) return card("Notifications", banner("bad", r.error));
  const p = r.data;
  const enabled = h("input", { type: "checkbox", id: "pref_on", checked: p.enabled });
  const cats = [["report_ready", "A report is ready"], ["reminder", "Reminders"]].map(([v, t]) => {
    const cb = h("input", { type: "checkbox", id: "pref_" + v, checked: (p.categories || []).includes(v) });
    cb.dataset.cat = v;
    return [cb, h("div", { class: "check" }, cb, h("label", { for: "pref_" + v, text: t }))];
  });
  const hours = Array.from({ length: 24 }, (_, i) => i);
  const sel = (id, v) => h("select", { id }, h("option", { value: "", text: "Off" }),
    hours.map((x) => h("option", { value: x, text: String(x).padStart(2, "0") + ":00", selected: v === x })));
  const qs = sel("pref_qs", p.quiet_start), qe = sel("pref_qe", p.quiet_end);
  const save = h("button", { class: "btn primary", type: "submit", text: "Save notification settings" });
  const form = h("form", { novalidate: true },
    h("div", { class: "check" }, enabled, h("label", { for: "pref_on", text: "Send me in-app notifications" })),
    cats.map((c) => c[1]),
    h("div", { class: "grid c2" },
      h("div", { class: "field" }, h("label", { for: "pref_qs", text: "Quiet hours start (India time)" }), qs),
      h("div", { class: "field" }, h("label", { for: "pref_qe", text: "Quiet hours end" }), qe)), save);
  form.addEventListener("submit", async (e) => {
    e.preventDefault(); msg.replaceChildren();
    const body = { enabled: enabled.checked, categories: cats.filter((c) => c[0].checked).map((c) => c[0].dataset.cat),
      quiet_start: qs.value === "" ? null : Number(qs.value), quiet_end: qe.value === "" ? null : Number(qe.value) };
    const d = await api("/preferences", { method: "PUT", body });
    msg.replaceChildren(d.ok ? banner("ok", "Saved.") : banner("bad", d.error));
  });
  return card("Notifications", msg, form);
}

async function noticesCard() {
  const r = await api("/notifications");
  const items = r.ok && Array.isArray(r.data) ? r.data : [];
  return card("Recent notices", items.length
    ? h("ul", { class: "list" }, items.map((n) => h("li", {}, h("span", { class: "pill", text: n.category }), " ", n.message, h("div", { class: "muted small", text: when(n.created_at) }))))
    : emptyState("bell", "Nothing yet", "Reminders and report-ready notices will show up here."));
}

export async function settings(c) {
  c.appendChild(pageHead("Settings", "Your sign-ins, password, privacy choices and notifications."));
  c.appendChild(banner("info", "Downloading or deleting all your data is not available in the app yet."));
  const grid = h("div", { class: "grid c2" });
  c.appendChild(grid);
  grid.appendChild(await sessionsCard());
  grid.appendChild(passwordCard());
  grid.appendChild(consentCard());
  grid.appendChild(await preferencesCard());
  c.appendChild(await noticesCard());
}

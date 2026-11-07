import { h, clear, paise, uid } from "../dom.js";
import { api } from "../api.js";
import { banner, card, pageHead } from "../components.js";
import { field, failure } from "./planning.js";

const adultLabel = "I declare that I am at least 18 years old (UNVERIFIED)";
const op = (revision, reason, key) => ({ expected_revision: revision, reason, idempotency_key: key });
const path = value => encodeURIComponent(value);
const revisionValue = input => input.value === "" ? null : Number(input.value);

// A form never replaces its inputs on a failed request, including conflicts and lost responses.
function action(title, defs, submit, success) {
  const prefix = uid();
  const controls = Object.fromEntries(defs.map(([key, label, type, value]) => [key, field(prefix + key, label, type, value)]));
  const msg = h("div", { "aria-live": "polite" });
  const go = h("button", { type: "submit", class: "btn primary", text: title });
  const form = h("form", {}, Object.values(controls).map(f => f.node), msg, go);
  form.addEventListener("submit", async e => {
    e.preventDefault(); clear(msg);
    const values = {};
    for (const [key,f] of Object.entries(controls)) {
      if (f.input.type === "checkbox") values[key] = f.input.checked;
      else if (f.input.type === "number") values[key] = f.input.value === "" ? null : Number(f.input.value);
      else values[key] = f.input.value.trim();
    }
    go.disabled = true;
    try {
      const r = await submit(values);
      if (r.ok) { msg.append(banner("ok", "Saved.")); if (success) await success(r.data); }
      else msg.append([404,503].includes(r.status) ? banner("info", "Not available yet, or this resource is missing or not shared with you.") : failure(r));
    } finally { go.disabled = false; }
  });
  return { node: card(title, form), controls, msg };
}

function snapshot(title, data) {
  const body = card(title, banner("warn", "Partial, unverified user-declared inventory. Dates and coverage may differ. Do not add these values to bank or portfolio totals."));
  const observations = data.observations || [];
  for (const [key,label] of [["assets_paise", "Assets"], ["liabilities_paise", "Liabilities"], ["net_worth_paise", "Net worth"]]) {
    body.append(h("p", { text: label + ": " + paise(data[key]) + " • date: included observation dates below • source: user_declared • share: included ownership shares below" }));
  }
  for (const item of observations) {
    body.append(h("p", { text: item.reference + " (" + item.kind + ") • " + item.valued_on + " • source: " + item.source + " • ownership fraction: " + item.ownership_fraction + " • observed whole value: " + paise(item.value_paise) + " • owned value: " + paise(item.allocated_paise) + " • unallocated value: " + paise(item.unallocated_paise) + " • unallocated share: " + item.unallocated_share }));
  }
  if (!observations.length) body.append(h("p", { text: "Unavailable: no declared observations." }));
  body.append(h("p", { text: "Missing inputs: " + (data.missing_inputs || []).join(", ") }), h("p", { text: "Planning allocation unavailable: shared inventory is not spendable planning capacity." }));
  return body;
}

export async function household(c) {
  c.classList.add("finance-evidence");
  c.append(pageHead("Household preview", "Synthetic pilot only. Read-only, account-by-account sharing. Membership alone grants no access. Adult self-declarations remain UNVERIFIED. Reminders are in-app only; email is deferred."));
  const bookArea = h("div", { class: "stack" });
  const tools = h("div", { class: "stack" });
  c.append(bookArea, tools);
  let book = null;
  let summaryNode = null;
  let revisionNode = null;

  function observationDetails(item, ordinal) {
    return h("details", {}, h("summary", { text: "Edit " + item.reference }), observationEditor(item, ordinal));
  }

  function observationEditor(item, ordinal) {
    const baseline = book.data.observations;
    const expectedRevision = book.revision;
    const defs = [["reference", "Account / holding reference", "text", item?.reference], ["kind", "Asset or liability", ["asset", "liability"], item?.kind || "asset"],
      ["value_paise", "Whole observed value (paise)", "number", item?.value_paise],
      ["share_percent", "Exact ownership percentage", "text", item?.share_percent ?? (item?.share_bps == null ? "" : String(Math.floor(item.share_bps / 100)) + "." + String(item.share_bps % 100).padStart(2,"0"))],
      ["valued_on", "Valuation date", "date", item?.valued_on], ["liquidity", "Liquidity", ["unknown", "liquid", "illiquid"], item?.liquidity || "unknown"], ["reason", "Reason for inventory change"]];
    let pending = null;
    const view = action(item ? "Save observation " + item.reference : "Add observation", defs, async values => {
      const { reason, ...observation } = values;
      const observations = [...baseline];
      observation.source = "user_declared";
      if (item) observations[ordinal] = observation; else observations.push(observation);
      const signature = JSON.stringify([observations, reason]);
      if (!pending || pending.signature !== signature) pending = { signature, key: uid() };
      return api("/networth", { method: "POST", body: { ...op(expectedRevision, reason, pending.key), data: { observations, coverage: "partial" } } });
    }, async () => {
      const r = await api("/networth");
      if (!r.ok) { view.msg.append(banner("warn", "Saved, but the latest inventory could not be loaded. Reload to review it."), failure(r)); return; }
      book = r.data;
      const next = snapshot("Personal net worth — your observations only", book.snapshot);
      summaryNode.replaceWith(next); summaryNode = next;
      revisionNode.textContent = "Personal inventory revision " + book.revision;
      if (item) view.node.closest("details").replaceWith(observationDetails(book.data.observations[ordinal], ordinal));
      else {
        const index = book.data.observations.length - 1;
        view.node.closest("details").before(observationDetails(book.data.observations[index], index));
        view.node.replaceWith(observationEditor(null));
      }
      // Other forms retain drafts and their original revision, so stale saves produce a conflict.
    });
    return view.node;
  }

  async function loadBook() {
    const r = await api("/networth");
    clear(bookArea);
    if (!r.ok) {
      if (![404,503].includes(r.status)) { bookArea.append(failure(r)); return; }
      bookArea.append(banner("info", "Household is not available yet, or no personal inventory has been created."));
      // There is no capability endpoint; this explicit initialization stays subject to the server gate.
      const key = uid();
      const initialize = h("button", { class: "btn", type: "button", text: "Start synthetic personal inventory" });
      initialize.addEventListener("click", async () => {
        initialize.disabled = true;
        const r = await api("/networth", { method: "POST", body: { ...op(0, "Explicitly initialized synthetic inventory", key), data: { observations: [], coverage: "partial" } } });
        if (r.ok) { await loadBook(); showTools(); }
        else { clear(bookArea); bookArea.append([404,503].includes(r.status) ? banner("info", "Household is not available yet.") : failure(r)); }
      });
      bookArea.append(initialize); return;
    }
    book = r.data;
    summaryNode = snapshot("Personal net worth — your observations only", book.snapshot);
    revisionNode = h("p", { class: "muted", text: "Personal inventory revision " + book.revision });
    bookArea.append(summaryNode, revisionNode);
    book.data.observations.forEach((item,i) => bookArea.append(observationDetails(item,i)));
    bookArea.append(h("details", {}, h("summary", { text: "Add asset or liability" }), observationEditor(null)));
  }

  function showTools() {
    if (!book || tools.children.length) return;
    const results = h("div", { class: "stack", "aria-live": "polite" });
    const houseID = field("household-id", "Household ID");
    const houseRevision = field("household-revision", "Household revision", "number");
    const grantRevision = field("grant-revision", "Account grant revision (0 for a new grant)", "number", 0);
    tools.append(card("Open a household", h("p", { text: "Household discovery is not available yet. Enter an ID supplied by the owner. Refresh the shared snapshot before using its current revision. Downloaded exports cannot be remotely recalled." }), houseID.node, houseRevision.node, grantRevision.node));
    const create = action("Create household", [["label", "Household label"], ["adult_confirmed", adultLabel, "checkbox"]], values => api("/households", { method: "POST", body: values }), data => {
      houseID.input.value = data.id; houseRevision.input.value = data.revision;
      results.replaceChildren(banner("info", "Created " + data.label + " • ID: " + data.id + " • UNVERIFIED adult declaration • " + data.adult_declared_at + " • statement: " + data.adult_statement_version));
    });
    const invite = action("Create invitation", [["member_id", "Invitee user ID", "number"], ["adult_confirmed", adultLabel, "checkbox"]], values => api("/households/" + path(houseID.input.value) + "/invites", { method: "POST", body: { ...values, expected_revision: revisionValue(houseRevision.input) } }), data => {
      houseRevision.input.value = data.household_revision;
      results.replaceChildren(banner("info", "Invitation ID: " + data.id + " • expires: " + data.expires_at), h("p", { text: "Invitation token (share privately with the invitee): " + data.token }));
    });
    const accept = action("Accept invitation", [["identity", "Invitation ID"], ["token", "Invitation token", "password"], ["adult_confirmed", adultLabel, "checkbox"]], ({identity,...values}) => api("/household-invites/" + path(identity) + "/accept", { method: "POST", body: values }), data => {
      houseID.input.value = data.household_id;
      results.replaceChildren(banner("info", "Membership accepted. Adult self-declaration UNVERIFIED. No accounts are shared until separately granted."));
      accept.controls.token.input.value = "";
    });
    const grantDefs = [["member_id", "Recipient user ID", "number"], ["view", "Inventory", ["networth", "protection"]], ["resource", "Account / holding reference to share"],
      ...["summaries", "transactions", "documents", "exports"].map(p => [p, "Allow " + p, "checkbox"]), ["granted", "Grant enabled (uncheck to revoke)", "checkbox"]];
    const grant = action("Save account permissions", grantDefs, values => {
      const { member_id, view, resource, granted } = values;
      return api("/households/" + path(houseID.input.value) + "/grants", { method: "PUT", body: { member_id, view, resource, granted, permissions: ["summaries", "transactions", "documents", "exports"].filter(p => values[p]), expected_revision: revisionValue(grantRevision.input) } });
    }, data => {
      grantRevision.input.value = data.revision;
      results.replaceChildren(banner("info", "Account " + data.resource + " • grant revision " + data.revision + " • enabled: " + data.granted + " • permissions: " + data.permissions.join(", ")));
    });
    const shared = h("div", { class: "stack" });
    const refresh = h("button", { class: "btn", type: "button", text: "Refresh shared snapshot" });
    refresh.addEventListener("click", async () => {
      refresh.disabled = true; clear(shared);
      const r = await api("/households/" + path(houseID.input.value) + "/snapshot"); refresh.disabled = false;
      if (r.ok) { houseRevision.input.value = r.data.household_revision; shared.append(snapshot("Household consolidated — personal plus explicitly shared observations", r.data)); }
      else shared.append(failure(r));
    });
    tools.append(create.node, invite.node, accept.node, grant.node, results, refresh, shared);
  }
  await loadBook(); showTools();
}

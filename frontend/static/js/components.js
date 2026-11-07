// Shared UI pieces.  Every string goes through h()/textContent.
import { h, money } from "./dom.js";

export function banner(kind, ...children) {
  return h("div", { class: "banner " + kind, role: kind === "bad" ? "alert" : "status" }, ...children);
}

export function metric(label, value, sub) {
  return h("div", { class: "card metric" },
    h("div", { class: "label", text: label }),
    h("div", { class: "value", text: value }),
    sub ? h("div", { class: "sub", text: sub }) : null);
}

export function card(title, ...children) {
  return h("section", { class: "card" }, title ? h("h2", { text: title }) : null, ...children);
}

export function pageHead(title, sub) {
  return h("div", { class: "stack page-head" },
    h("h1", { text: title }), sub ? h("p", { class: "muted", text: sub }) : null);
}

export function list(items) {
  const xs = (items || []).filter((x) => x !== null && x !== undefined && x !== "");
  if (!xs.length) return null;
  return h("ul", { class: "list" }, xs.map((t) => h("li", { text: typeof t === "string" ? t : JSON.stringify(t) })));
}

// Honest status line for an analysis response (live or from /analysis/last).
export function runStatus(resp, sectionStatus) {
  const out = [];
  const st = resp && resp.status;
  if (resp && resp.is_scenario) {
    out.push(banner("info", h("strong", { text: "What-if result. " }),
      "Calculated from the values you typed. Your saved profile and saved results are unchanged."));
  }
  if (resp && resp.stale) {
    out.push(banner("warn", h("strong", { text: "Out of date. " }),
      "Your profile changed after this analysis. Run it again to refresh."));
  }
  if (st === "degraded" || st === "partial") {
    out.push(banner("warn", h("strong", { text: "Partly automatic. " }),
      "The AI model was unavailable or returned something unusable, so some sections use fixed rules only. The numbers shown are still the checked ones."));
  } else if (st === "failed") {
    out.push(banner("bad", h("strong", { text: "Analysis failed. " }), "Please try again."));
  }
  const bad = Object.entries(sectionStatus || {}).filter(([k, v]) => k !== "_meta" && v && v.status && v.status !== "complete");
  if (bad.length && st !== "degraded" && st !== "partial") {
    out.push(banner("warn", "Some sections are not complete: " + bad.map(([k]) => k).join(", ") + "."));
  }
  return out;
}

// True when nothing can be invested each month (deficit, debt payments use it up, or unknown inputs).
export function nothingToInvest(snapshot) {
  if (!snapshot || !Object.keys(snapshot).length) return false;
  return !snapshot.available_contribution_paise || !!snapshot.shortfall_paise;
}

export function nothingToInvestNote() {
  return banner("info", h("strong", { text: "Nothing to invest each month right now. " }),
    "Your current numbers leave no money to invest, so no allocation, projection or card recommendation is shown. Close the gap first, then re-run the analysis.");
}

// First-run checklist. `steps` = [{label, done, href}]. Hidden once everything is done.
export function startChecklist(steps) {
  if (steps.every((s) => s.done)) return null;
  const next = steps.find((s) => !s.done);
  return card("Getting started", h("ol", { class: "list" }, steps.map((s) => h("li", {},
    s.done ? h("span", { class: "pill ok", text: "Done" }) : s === next ? h("span", { class: "pill warn", text: "Next" }) : h("span", { class: "pill neutral", text: "Later" }),
    " ", h("a", { href: s.href, text: s.label })))));
}

export function disclaimer() {
  return h("p", { class: "muted small", text: "Educational estimates from the information you entered. Not licensed investment, tax or credit advice." });
}

export function busyButton(btn, label, fn) {
  btn.addEventListener("click", async (e) => {
    e.preventDefault();
    if (btn.disabled) return;
    btn.disabled = true;
    const old = btn.textContent;
    btn.textContent = label;
    try { await fn(); } finally { btn.disabled = false; btn.textContent = old; }
  });
  return btn;
}

export function kv(label, value) {
  return h("div", { class: "spread" }, h("span", { class: "muted", text: label }), h("strong", { text: value }));
}

export { money };

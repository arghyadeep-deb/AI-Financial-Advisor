import { h, money, num, pctClass, clear } from "../dom.js";
import { state, loadProfile, loadLast, section, runAnalysis } from "../state.js";
import { banner, card, pageHead, list, runStatus, busyButton, disclaimer } from "../components.js";

const MONEY_RE = /^\d{1,14}(\.\d{1,2})?$/;
const LABELS = { savings_rate: "Savings rate", emergency_fund: "Emergency fund", debt_ratio: "Debt load", investment_rate: "Investing", credit_score: "Credit score" };

export function renderHealth(hl, target) {
  const known = typeof hl.overall_score === "number";
  target.appendChild(h("div", { class: "grid c3" },
    h("div", { class: "card metric" }, h("div", { class: "label", text: "Health score" }),
      h("div", { class: "value", text: known ? num(hl.overall_score, 0) : "Not enough information" }),
      h("div", { class: "sub", text: known ? "Grade " + (hl.grade || "N/A") : "Add the missing details to get a score" })),
    h("div", { class: "card metric" }, h("div", { class: "label", text: "Monthly surplus" }),
      h("div", { class: "value", text: money((hl.raw_metrics || {}).monthly_surplus) }),
      h("div", { class: "sub", text: (hl.raw_metrics || {}).monthly_shortfall ? "Shortfall " + money(hl.raw_metrics.monthly_shortfall) : "Income minus expenses" })),
    h("div", { class: "card metric" }, h("div", { class: "label", text: "Emergency fund" }),
      h("div", { class: "value", text: num((hl.raw_metrics || {}).emergency_months, 1) + " mo" }),
      h("div", { class: "sub", text: "of expenses covered" }))));

  const comps = Object.entries(hl.components || {});
  if (comps.length) {
    target.appendChild(card("Score breakdown", h("div", { class: "stack" }, comps.map(([k, c]) => {
      const unknown = c.value === "unknown" || c.score === null || c.score === undefined;
      const pct = !unknown && c.max ? (c.score / c.max) * 100 : 0;
      return h("div", {},
        h("div", { class: "spread" }, h("strong", { text: LABELS[k] || k }),
          h("span", { class: "muted", text: unknown ? "Not provided" : `${c.value} (target ${c.benchmark})` })),
        h("div", { class: "bar " + (pct < 40 ? "bad" : pct < 70 ? "warn" : ""), role: "img", "aria-label": unknown ? "No score" : `${num(pct, 0)} percent` },
          h("span", { class: pctClass(pct) })));
    }))));
  }
  const strengths = list(hl.strengths);
  if (strengths) target.appendChild(card("Strengths", strengths));

  const warnings = hl.detailed_warnings || [];
  if (warnings.length) {
    target.appendChild(card("Warnings", warnings.map((w) => h("details", {},
      h("summary", {}, h("span", { class: "pill " + (w.severity === "high" ? "bad" : w.severity === "medium" ? "warn" : ""), text: w.severity || "info" }), " " + (w.title || "Warning")),
      h("p", { text: w.summary || "" }), w.detail ? h("p", { class: "muted", text: w.detail }) : null,
      w.impact ? h("p", { class: "muted", text: "Impact: " + w.impact }) : null,
      list(w.action_steps), w.timeline ? h("p", { class: "small muted", text: "Timeline: " + w.timeline }) : null))));
  }
  const imp = hl.improvement_areas || [];
  if (imp.length) {
    target.appendChild(card("Improvement areas", imp.map((a) => h("div", { class: "stack" },
      h("h3", { text: a.area || "" }), h("p", { class: "muted", text: `Now ${a.current || "—"} → target ${a.target || "—"}` }), list(a.action_steps)))));
  }
  const b = hl.monthly_budget_suggestion;
  if (b && (b.needs || b.wants || b.savings_investments)) {
    target.appendChild(card("Suggested monthly budget", h("div", { class: "grid c3" },
      h("div", {}, h("div", { class: "muted small", text: "Needs" }), h("strong", { text: money(b.needs) })),
      h("div", {}, h("div", { class: "muted small", text: "Wants" }), h("strong", { text: money(b.wants) })),
      h("div", {}, h("div", { class: "muted small", text: "Savings and investing" }), h("strong", { text: money(b.savings_investments) }))),
      b.note ? h("p", { class: "muted small", text: b.note }) : null));
  }
  const pa = list(hl.priority_actions);
  if (pa) target.appendChild(card("Priority actions", pa));
}

export async function health(c) {
  const [p, last] = await Promise.all([loadProfile(true), loadLast(true)]);
  c.appendChild(pageHead("Financial health", "See your score on saved numbers, or try a what-if. A what-if never changes your saved profile."));
  if (!p) { c.appendChild(banner("info", "Complete your profile first. ", h("a", { href: "#/profile", text: "Go to profile" }))); return; }

  const credit = h("input", { id: "w_credit", type: "number", min: 300, max: 900, step: 1, value: p.credit_score || "" });
  const unk = h("input", { type: "checkbox", id: "w_unknown", checked: !p.credit_score });
  const sync = () => { credit.disabled = unk.checked; };
  unk.addEventListener("change", sync); sync();
  const f = (id, label, v) => h("div", { class: "field" }, h("label", { for: id, text: label }),
    h("input", { id, type: "text", inputmode: "decimal", autocomplete: "off", value: v === null || v === undefined ? "" : String(v) }));
  const inc = f("w_income", "Monthly income (₹)", p.monthly_income);
  const exp = f("w_expenses", "Monthly expenses (₹)", p.monthly_expenses);
  const sav = f("w_savings", "Savings (₹)", p.existing_savings);
  const debt = f("w_debts", "Total debt (₹)", p.existing_debts);
  const pay = f("w_payment", "Monthly debt payments (₹, blank = not declared)", p.monthly_debt_payment);

  const msg = h("div", { "aria-live": "polite" });
  const out = h("div", { class: "stack" });
  const show = (resp, key) => {
    clear(out);
    runStatus(resp, resp.section_status).forEach((b) => out.appendChild(b));
    const hl = (resp.results || {}).health;
    if (hl) renderHealth(hl, out);
    else out.appendChild(banner("warn", "No health result was returned."));
  };

  const runSaved = busyButton(h("button", { class: "btn primary", type: "button", text: "Analyse saved profile" }), "Working...", async () => {
    msg.replaceChildren(); const r = await runAnalysis("health");
    if (!r.ok) { msg.appendChild(banner("bad", r.error)); return; }
    show(r.data);
  });
  const runWhatIf = busyButton(h("button", { class: "btn", type: "button", text: "Try this what-if" }), "Working...", async () => {
    msg.replaceChildren();
    const read = (el) => el.querySelector("input").value.trim().replace(/,/g, "");
    const sc = {}; const bad = [];
    for (const [el, k, req] of [[inc, "monthly_income", true], [exp, "monthly_expenses", true], [sav, "existing_savings", true], [debt, "existing_debts", true], [pay, "monthly_debt_payment", false]]) {
      const v = read(el);
      if (v === "") { if (req) bad.push(k); continue; }
      if (!MONEY_RE.test(v)) { bad.push(k); continue; }
      sc[k] = v;
    }
    if (bad.length) { msg.appendChild(banner("bad", "Check these amounts: " + bad.join(", "))); return; }
    sc.credit_score = unk.checked || credit.value === "" ? null : Number(credit.value);   // explicit null = unknown
    const r = await runAnalysis("health", sc);
    if (!r.ok) { msg.appendChild(banner("bad", r.error)); return; }
    show(r.data);
  });

  c.appendChild(card("What-if", h("form", { novalidate: true, onSubmit: (e) => e.preventDefault() },
    h("div", { class: "grid c3" }, inc, exp, sav, debt, pay,
      h("div", { class: "field" }, h("label", { for: "w_credit", text: "Credit score" }), credit,
        h("div", { class: "check" }, unk, h("label", { for: "w_unknown", text: "I don't know my credit score" })))),
    h("div", { class: "row" }, runSaved, runWhatIf))));
  c.appendChild(msg);
  c.appendChild(out);

  const saved = section("health");
  if (saved) { runStatus(last, last.section_status).forEach((b) => out.appendChild(b)); renderHealth(saved, out); }
  else out.appendChild(banner("info", "No saved health analysis yet. Run it on your saved profile above."));
  c.appendChild(disclaimer());
}

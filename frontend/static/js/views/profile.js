import { h, money } from "../dom.js";
import { api } from "../api.js";
import { state, loadProfile } from "../state.js";
import { banner, card, pageHead } from "../components.js";

const MONEY = [
  ["monthly_income", "Monthly income (₹)", true],
  ["monthly_expenses", "Monthly expenses (₹)", true],
  ["existing_savings", "Savings (₹)", true],
  ["existing_investments", "Existing investments (₹)", true],
  ["existing_debts", "Total outstanding debt (₹)", true],
  ["monthly_debt_payment", "Monthly debt payments (₹)", false],
  ["monthly_credit_spend", "Monthly credit-card spend (₹)", true],
];
const MONEY_RE = /^\d{1,14}(\.\d{1,2})?$/;

function moneyField(id, label, value, required, hint) {
  const shown = value === null || value === undefined ? "" : String(value);
  return h("div", { class: "field" }, h("label", { for: id, text: label }),
    h("input", { id, name: id, type: "text", inputmode: "decimal", autocomplete: "off", value: shown, required }),
    hint ? h("div", { class: "hint", text: hint }) : null);
}

function select(id, label, options, value) {
  const sel = h("select", { id, name: id }, options.map(([v, t]) => h("option", { value: v, text: t, selected: v === value })));
  return h("div", { class: "field" }, h("label", { for: id, text: label }), sel);
}

export async function profile(c) {
  const p = await loadProfile(true);
  const exists = !!p;
  const needs = (p && p.needs_reentry) || [];
  c.appendChild(pageHead("Your profile", "Everything else is calculated from these numbers. Leave a value blank if you do not know it; we will not guess."));
  if (needs.length) {
    c.appendChild(banner("warn", h("strong", { text: "Some saved values need to be re-entered: " }), needs.join(", ") +
      ". They could not be verified after a data update, so analysis is paused until you enter them."));
  }
  const msg = h("div", { "aria-live": "polite" });
  const form = h("form", { novalidate: true });

  const unknownCredit = h("input", { type: "checkbox", id: "credit_unknown", checked: !p || p.credit_score === null || p.credit_score === undefined });
  const creditIn = h("input", { id: "credit_score", name: "credit_score", type: "number", min: 300, max: 900, step: 1,
    value: p && p.credit_score ? p.credit_score : "" });
  const syncCredit = () => { creditIn.disabled = unknownCredit.checked; };
  unknownCredit.addEventListener("change", syncCredit);
  syncCredit();

  const goals = h("textarea", { id: "financial_goals", name: "financial_goals", rows: 2 });
  goals.value = ((p && p.financial_goals) || []).join(", ");
  const cats = h("textarea", { id: "top_spend_categories", name: "top_spend_categories", rows: 2 });
  cats.value = ((p && p.top_spend_categories) || []).join(", ");

  const get = (k) => (p ? p[k] : null);
  form.append(
    h("fieldset", {}, h("legend", { text: "About you" }),
      h("div", { class: "grid c3" },
        h("div", { class: "field" }, h("label", { for: "age", text: "Age" }),
          h("input", { id: "age", name: "age", type: "number", min: 18, max: 80, required: true, value: get("age") || 30 })),
        select("employment_type", "Employment", [["salaried", "Salaried"], ["self_employed", "Self-employed"], ["business", "Business"]], get("employment_type") || "salaried"),
        select("risk_tolerance", "Risk comfort", [["low", "Low"], ["moderate", "Moderate"], ["high", "High"], ["very_high", "Very high"]], get("risk_tolerance") || "moderate"),
        select("investment_horizon", "Time horizon", [["short", "Short (under 3 years)"], ["medium", "Medium (3-7 years)"], ["long", "Long (7+ years)"]], get("investment_horizon") || "long"))),
    h("fieldset", {}, h("legend", { text: "Money, per month and in total" }),
      h("div", { class: "grid c3" }, MONEY.map(([k, label, req]) =>
        moneyField(k, label, get(k), req,
          k === "monthly_debt_payment" ? "Blank = not declared. We then cannot tell how much you can invest." :
          k === "existing_debts" ? "The outstanding balance, not the monthly payment." : null)))),
    h("fieldset", {}, h("legend", { text: "Credit" }),
      h("div", { class: "field" }, h("label", { for: "credit_score", text: "Credit score (300-900)" }), creditIn),
      h("div", { class: "check" }, unknownCredit, h("label", { for: "credit_unknown", text: "I don't know my credit score" }))),
    h("fieldset", {}, h("legend", { text: "Goals and spending (comma separated)" }),
      h("div", { class: "grid c2" },
        h("div", { class: "field" }, h("label", { for: "financial_goals", text: "Financial goals" }), goals),
        h("div", { class: "field" }, h("label", { for: "top_spend_categories", text: "Top spending categories" }), cats))),
  );
  const save = h("button", { class: "btn primary", type: "submit", text: exists ? "Save changes" : "Save profile" });
  form.append(save);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    msg.replaceChildren();
    const body = {
      age: Number(form.age.value), employment_type: form.employment_type.value,
      risk_tolerance: form.risk_tolerance.value, investment_horizon: form.investment_horizon.value,
      credit_score: unknownCredit.checked || creditIn.value === "" ? null : Number(creditIn.value),
      financial_goals: goals.value.split(",").map((s) => s.trim()).filter(Boolean),
      top_spend_categories: cats.value.split(",").map((s) => s.trim()).filter(Boolean),
    };
    const bad = [];
    for (const [k, label, req] of MONEY) {
      const raw = form[k].value.trim().replace(/,/g, "");
      if (raw === "") {
        if (req && k !== "monthly_credit_spend") { bad.push(label); continue; }
        body[k] = k === "monthly_debt_payment" ? null : "0";
        continue;
      }
      if (!MONEY_RE.test(raw)) { bad.push(label); continue; }
      body[k] = raw;
    }
    if (bad.length) { msg.appendChild(banner("bad", "Please enter a valid amount (digits, up to 2 decimals) for: " + bad.join(", "))); return; }
    if (p && p.revision) body.expected_revision = p.revision;
    save.disabled = true;
    const r = await api("/profile", { method: "POST", body });
    save.disabled = false;
    if (r.status === 409) {
      msg.appendChild(banner("warn", "Your profile was changed somewhere else. Reload to see the latest, then re-apply your edit."));
      return;
    }
    if (!r.ok) { msg.appendChild(banner("bad", r.error)); return; }
    state.profile = r.data;
    state.last = null;
    msg.appendChild(banner("ok", "Saved. Your next analysis will use these numbers."));
    setTimeout(() => { location.hash = "#/dashboard"; }, 700);
  });

  c.appendChild(msg);
  c.appendChild(card(null, form));
  if (p) {
    c.appendChild(card("Quick stats",
      h("div", { class: "grid c3" },
        h("div", {}, h("div", { class: "muted small", text: "Monthly surplus" }),
          h("strong", { text: p.monthly_income === null || p.monthly_expenses === null ? "—" : money(p.monthly_income - p.monthly_expenses) })),
        h("div", {}, h("div", { class: "muted small", text: "Profile revision" }), h("strong", { text: String(p.revision) })),
        h("div", {}, h("div", { class: "muted small", text: "Credit score" }),
          h("strong", { text: p.credit_score ? String(p.credit_score) : "Not provided" })))));
  }
}

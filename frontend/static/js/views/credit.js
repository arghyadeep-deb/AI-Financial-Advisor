import { h, money, clear } from "../dom.js";
import { loadProfile, loadLast, section, runAnalysis } from "../state.js";
import { banner, card, pageHead, list, runStatus, nothingToInvest, busyButton, disclaimer } from "../components.js";

const MONEY_RE = /^\d{1,14}(\.\d{1,2})?$/;

function renderCards(cr, target) {
  if (cr.credit_score_status === "unknown") {
    target.appendChild(banner("info", "Your credit score is unknown, so eligibility is not assumed. Cards below may need a check with the issuer."));
  }
  const recs = cr.recommendations || [];
  if (!recs.length) { target.appendChild(banner("info", "No card matches were produced.")); return; }
  recs.forEach((r) => target.appendChild(card(`#${r.rank || ""} ${r.card_name || "Card"}`.trim(),
    h("p", { class: "muted", text: (r.bank || "") + (r.annual_fee !== undefined ? " · annual fee " + money(r.annual_fee) : "") }),
    r.why_recommended ? h("p", { text: r.why_recommended }) : null,
    list(r.key_benefits),
    r.estimated_annual_savings ? h("p", { text: "Estimated yearly benefit: " + money(r.estimated_annual_savings) }) : null,
    r.watch_out ? h("p", { class: "small muted", text: "Watch out: " + r.watch_out }) : null,
    r.eligibility ? h("span", { class: "pill", text: r.eligibility }) : null)));
  if (cr.strategy_note) target.appendChild(card("Strategy", h("p", { text: cr.strategy_note })));
  const av = list(cr.avoid_pitfalls);
  if (av) target.appendChild(card("Pitfalls to avoid", av));
}

export async function credit(c) {
  const [p, last] = await Promise.all([loadProfile(true), loadLast(true)]);
  c.appendChild(pageHead("Credit cards", "Matches based on how you spend. Only shown when your numbers can support it."));
  if (!p) { c.appendChild(banner("info", "Complete your profile first. ", h("a", { href: "#/profile", text: "Go to profile" }))); return; }

  const spend = h("input", { id: "cc_spend", type: "text", inputmode: "decimal", autocomplete: "off", value: p.monthly_credit_spend ?? "" });
  const cats = h("input", { id: "cc_cats", type: "text", value: (p.top_spend_categories || []).join(", ") });
  const credit = h("input", { id: "cc_score", type: "number", min: 300, max: 900, value: p.credit_score || "" });
  const unk = h("input", { type: "checkbox", id: "cc_unknown", checked: !p.credit_score });
  const sync = () => { credit.disabled = unk.checked; };
  unk.addEventListener("change", sync); sync();

  const msg = h("div", { "aria-live": "polite" });
  const out = h("div", { class: "stack" });
  const show = (resp) => {
    clear(out);
    runStatus(resp, resp.section_status).forEach((b) => out.appendChild(b));
    if (nothingToInvest(resp.snapshot)) {
      out.appendChild(banner("info", h("strong", { text: "No card recommendations right now. " }),
        "Your numbers leave nothing spare each month, so adding a new card is not advised yet. Close the gap first."));
      return;
    }
    const cr = (resp.results || {}).credit;
    cr ? renderCards(cr, out) : out.appendChild(banner("warn", "No result returned."));
  };
  const run = h("button", { class: "btn primary", type: "button", text: "Find cards (what-if on these inputs)" });
  busyButton(run, "Working...", async () => {
    msg.replaceChildren();
    const sv = spend.value.trim().replace(/,/g, "");
    if (!MONEY_RE.test(sv)) { msg.appendChild(banner("bad", "Enter your monthly card spend as an amount.")); return; }
    const sc = { monthly_credit_spend: sv,
      top_spend_categories: cats.value.split(",").map((s) => s.trim()).filter(Boolean),
      credit_score: unk.checked || credit.value === "" ? null : Number(credit.value) };
    const r = await runAnalysis("credit", sc);
    r.ok ? show(r.data) : msg.appendChild(banner("bad", r.error));
  });
  c.appendChild(card("Your spending", h("div", { class: "grid c3" },
    h("div", { class: "field" }, h("label", { for: "cc_spend", text: "Monthly card spend (₹)" }), spend),
    h("div", { class: "field" }, h("label", { for: "cc_cats", text: "Top categories (comma separated)" }), cats),
    h("div", { class: "field" }, h("label", { for: "cc_score", text: "Credit score" }), credit,
      h("div", { class: "check" }, unk, h("label", { for: "cc_unknown", text: "I don't know my credit score" })))),
    h("div", { class: "row" }, run)));
  c.appendChild(msg);
  c.appendChild(out);

  const saved = section("credit");
  if (nothingToInvest(last.snapshot)) {
    out.appendChild(banner("info", "No card recommendations right now: your numbers leave nothing spare each month."));
  } else if (saved) { runStatus(last, last.section_status).forEach((b) => out.appendChild(b)); renderCards(saved, out); }
  else out.appendChild(banner("info", "No saved card analysis yet. Use the form above or run a full analysis from the dashboard."));
  c.appendChild(disclaimer());
}

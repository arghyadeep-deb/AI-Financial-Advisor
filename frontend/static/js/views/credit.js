import { h, money, clear } from "../dom.js";
import { loadProfile, loadLast, section, runAnalysis } from "../state.js";
import { banner, card, pageHead, list, runStatus, nothingToInvest, busyButton, disclaimer } from "../components.js";
import { api } from "../api.js";

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

async function manualScoreCard() {
  const r = await api("/credit/manual");
  const msg = h("div", { "aria-live": "polite" });
  const holder = h("div", { class: "stack" });
  const paint = (data) => {
    clear(holder);
    const l = data.latest;
    holder.appendChild(l.status === "unknown"
      ? banner("info", "No credit score on record. We never guess one.")
      : banner(l.status === "stale" ? "warn" : "ok", h("strong", { text: "Your entry: " + l.score + " " }),
          "as of " + l.as_of + ". " + l.note));
    holder.appendChild(h("p", { class: "muted small", text: "Automatic credit-bureau lookup: " + (data.provider.status === "disabled" ? "not available yet." : data.provider.status) }));
  };
  if (r.ok) paint(r.data); else holder.appendChild(banner("bad", r.error));
  const today = new Date().toISOString().slice(0, 10);
  const score = h("input", { id: "ms_score", type: "number", min: 300, max: 900, step: 1, inputmode: "numeric" });
  const unk = h("input", { id: "ms_unknown", type: "checkbox" });
  const when = h("input", { id: "ms_date", type: "date", max: today, value: today });
  const label = h("input", { id: "ms_label", type: "text", maxlength: 40, autocomplete: "off" });
  unk.addEventListener("change", () => { score.disabled = unk.checked; });
  const save = h("button", { class: "btn primary", type: "submit", text: "Save entry" });
  const form = h("form", { novalidate: true },
    h("div", { class: "grid c3" },
      h("div", { class: "field" }, h("label", { for: "ms_score", text: "Credit score (300 to 900)" }), score,
        h("div", { class: "check" }, unk, h("label", { for: "ms_unknown", text: "I don't know it" }))),
      h("div", { class: "field" }, h("label", { for: "ms_date", text: "Date of this score" }), when),
      h("div", { class: "field" }, h("label", { for: "ms_label", text: "Where it came from (optional)" }), label)), save);
  form.addEventListener("submit", async (e) => {
    e.preventDefault(); msg.replaceChildren();
    const body = { as_of: when.value };
    if (!unk.checked) {
      const n = Number(score.value);
      if (!Number.isInteger(n) || n < 300 || n > 900) { msg.appendChild(banner("bad", "Enter a score from 300 to 900, or tick \"I don't know it\".")); return; }
      body.score = n;
    }
    if (!when.value) { msg.appendChild(banner("bad", "Choose the date of this score.")); return; }
    if (label.value.trim()) body.bureau_label = label.value.trim();
    save.disabled = true;
    const d = await api("/credit/manual", { method: "POST", body });
    save.disabled = false;
    if (!d.ok) { msg.appendChild(banner("bad", d.error)); return; }
    const again = await api("/credit/manual");
    if (again.ok) paint(again.data);
    msg.appendChild(banner("ok", "Saved."));
  });
  return card("Your credit score", h("p", { class: "muted", text: "Enter the score you were shown and when. It is kept as reported by you and is never checked or updated for you." }), holder, form, msg);
}

export async function credit(c) {
  const [p, last] = await Promise.all([loadProfile(true), loadLast(true)]);
  c.appendChild(pageHead("Credit", "Record your credit score with its date, and see card matches when your numbers support it."));
  c.appendChild(await manualScoreCard());
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

import { h, money } from "../dom.js";
import { loadProfile, loadLast, section } from "../state.js";
import { banner, card, pageHead, disclaimer, nothingToInvest, nothingToInvestNote } from "../components.js";

export async function stocks(c) {
  const [p, last] = await Promise.all([loadProfile(true), loadLast(true)]);
  c.appendChild(pageHead("Stock ideas", "General education, not recommendations to buy a named security."));
  if (!p) { c.appendChild(banner("info", "Complete your profile first. ", h("a", { href: "#/profile", text: "Go to profile" }))); return; }
  const inv = section("investment");
  if (!inv) { c.appendChild(banner("info", "Run an analysis first. ", h("a", { href: "#/portfolio", text: "Open the portfolio planner" }))); return; }
  if (nothingToInvest(last.snapshot)) { c.appendChild(nothingToInvestNote()); return; }

  const gate = inv.named_products || {};
  const picks = inv.stock_recommendations || [];
  if (gate.status === "gated" || !picks.length) {
    c.appendChild(banner("info", h("strong", { text: "Named stocks and funds are turned off. " }),
      gate.reason || "Naming specific products needs suitability and licensing checks that are not enabled."));
    if (inv.stock_strategy_note) c.appendChild(card("General approach", h("p", { text: inv.stock_strategy_note })));
  } else {
    c.appendChild(card("Ideas to research", h("div", { class: "table-scroll" }, h("table", {},
      h("thead", {}, h("tr", {}, ["Name", "Why", "Suggested amount"].map((t) => h("th", { text: t })))),
      h("tbody", {}, picks.map((s) => h("tr", {}, h("td", { text: s.name || s.symbol || "" }), h("td", { text: s.rationale || s.reason || "" }),
        h("td", { class: "num", text: s.amount ? money(s.amount) : "—" }))))))));
  }
  c.appendChild(disclaimer());
}

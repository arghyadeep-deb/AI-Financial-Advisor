// A fixed, clearly labelled sample. It makes NO requests and shows no stored data, so it can never mix with a real account.
import { h } from "../dom.js";
import { banner, card, pageHead, disclaimer } from "../components.js";

const ROWS = [
  ["2025-10-01", "Sample salary", "₹1,00,000.00", "pos"],
  ["2025-10-03", "Sample rent", "-₹30,000.00", "neg"],
  ["2025-10-07", "Sample groceries", "-₹6,500.00", "neg"],
  ["2025-10-18", "Sample electricity", "-₹2,300.00", "neg"],
];

export async function demo(c) {
  c.appendChild(pageHead("Sample report", "This is invented data to show what a monthly report looks like."));
  c.appendChild(banner("warn", h("strong", { text: "Sample data, not yours. " }),
    "Nothing here is read from an account, and nothing you do here is saved. Create an account to see your own numbers."));
  c.appendChild(card("October (sample)",
    h("div", { class: "summary" },
      h("div", {}, h("div", { class: "k", text: "Money in" }), h("div", { class: "v", text: "₹1,00,000.00" })),
      h("div", {}, h("div", { class: "k", text: "Money out" }), h("div", { class: "v", text: "₹38,800.00" })),
      h("div", {}, h("div", { class: "k", text: "Left over" }), h("div", { class: "v", text: "₹61,200.00" }))),
    h("p", { class: "muted", text: "A report only counts entries you confirmed, and it says so when some days are not covered." }),
    h("div", { class: "table-scroll" }, h("table", {},
      h("thead", {}, h("tr", {}, ["Date", "Description", "Amount"].map((t, i) => h("th", { class: i === 2 ? "right" : null, text: t })))),
      h("tbody", {}, ROWS.map(([d, t, a, k]) => h("tr", {}, h("td", { text: d }), h("td", { text: t }), h("td", { class: "right " + k, text: a }))))))));
  c.appendChild(h("div", { class: "row" },
    h("a", { class: "btn primary lg", href: "#/signup", text: "Create your account" }),
    h("a", { class: "btn lg", href: "#/", text: "Back" })));
  c.appendChild(disclaimer());
}

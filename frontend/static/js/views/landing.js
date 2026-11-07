import { h } from "../dom.js";
import { disclaimer } from "../components.js";

export async function landing(c) {
  c.appendChild(h("section", { class: "hero" }, h("div", { class: "grid c2" },
    h("div", {},
      h("span", { class: "pill", text: "Personal finance, checked by rules" }),
      h("h1", { text: "Know what you can actually invest each month." }),
      h("p", { class: "lead", text: "Enter your income, spending, savings and debts. The numbers come from fixed rules, not a chatbot's guess. The AI explains them, and says plainly when it cannot." }),
      h("div", { class: "row" },
        h("a", { class: "btn primary", href: "#/signup", text: "Start with your profile" }),
        h("a", { class: "btn", href: "#/login", text: "Log in" }))),
    h("div", { class: "card stack" },
      h("div", { class: "muted small", text: "Example: available to invest each month" }),
      h("div", { class: "metric" }, h("div", { class: "value", text: "₹54,000" })),
      h("p", { class: "muted small", text: "Sample: ₹1,00,000 income, ₹40,000 expenses, no debt payments, with a 10% buffer kept back." }),
      h("p", { class: "muted small", text: "This is an illustration, not your result." })))));

  c.appendChild(h("section", { class: "stack" },
    h("h2", { text: "What it does" }),
    h("div", { class: "grid c3" },
      h("div", { class: "card" }, h("h3", { text: "Honest numbers" }),
        h("p", { class: "muted", text: "Money is stored exactly. One calculation feeds the dashboard, reports and chat, so they never disagree." })),
      h("div", { class: "card" }, h("h3", { text: "Unknown stays unknown" }),
        h("p", { class: "muted", text: "No credit score? We say so. We never fill in 700 for you or treat a missing debt payment as zero." })),
      h("div", { class: "card" }, h("h3", { text: "What-if, not overwrite" }),
        h("p", { class: "muted", text: "Try a different income or spend. Scenario results are labelled and never change your saved profile." }))),
    disclaimer()));
}

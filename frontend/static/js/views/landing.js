import { h } from "../dom.js";
import { disclaimer } from "../components.js";
import { heroArt } from "../illustrations.js";

const feature = (title, text) => h("div", { class: "card flat" }, h("h3", { text: title }), h("p", { class: "muted", text }));
const step = (n, title, text) => h("div", {}, h("div", { class: "big-num", text: n }), h("h3", { text: title }), h("p", { class: "muted", text }));

export async function landing(c) {
  c.appendChild(h("section", { class: "hero" }, h("div", { class: "grid c2" },
    h("div", {},
      h("div", { class: "eyebrow", text: "Personal finance for India" }),
      h("h1", { text: "Know what you can safely invest every month." }),
      h("p", { class: "lead", text: "Enter your income, expenses and debts. Advisor checks the numbers with fixed rules, shows your financial health and builds a plan you can read in a minute. The AI explains it. It never changes the maths." }),
      h("div", { class: "row" },
        h("a", { class: "btn primary lg", href: "#/signup", text: "Start free" }),
        h("a", { class: "btn lg", href: "#/login", text: "Log in" })),
      h("p", { class: "muted small", text: "Educational estimates. Not licensed investment, tax or credit advice." })),
    h("div", {}, h("div", { class: "hero-art" }, heroArt()), h("div", { class: "card preview" },
      h("div", { class: "spread" }, h("strong", { text: "Example month" }), h("span", { class: "pill warn", text: "Sample data" })),
      h("div", { class: "grid c2" },
        h("div", { class: "tile" }, h("div", { class: "muted small", text: "Income minus expenses" }), h("div", { class: "tile-value", text: "₹60,000" })),
        h("div", { class: "tile accent" }, h("div", { class: "small", text: "Can invest monthly" }), h("div", { class: "tile-value", text: "₹54,000" }))),
      h("p", { class: "muted small", text: "Sample: ₹1,00,000 income, ₹40,000 expenses, no debt payments, a 10% buffer kept back. An illustration, not your result." }))))));

  c.appendChild(h("section", { class: "stack" },
    h("h2", { class: "section-title", text: "Built so the numbers can be trusted." }),
    h("p", { class: "muted lead-sm", text: "Most money apps let a chatbot guess. Here, fixed rules do the arithmetic and the AI only explains it." }),
    h("div", { class: "grid c3" },
      feature("Exact to the paisa", "Amounts are stored exactly. One calculation feeds the dashboard, reports and chat, so they never disagree."),
      feature("Honest about gaps", "An unknown credit score stays unknown. Out-of-date results are labelled. If nothing is left to invest, it says so."),
      feature("What-if, not overwrite", "Try a different income or spend. Scenario results are labelled and never change your saved profile."))));

  c.appendChild(h("section", { class: "stack" },
    h("h2", { class: "section-title", text: "From numbers to a plan in three steps." }),
    h("div", { class: "grid c3" },
      step("1", "Tell us your situation", "Income, expenses, debts, goals and risk comfort. About two minutes."),
      step("2", "Review your health score", "See where you stand and which change helps most."),
      step("3", "Follow a clear plan", "A suggested split, a projection with its assumptions stated, and an advisor you can ask in plain language."))));

  c.appendChild(h("section", { class: "cta" },
    h("h2", { text: "See your own numbers in two minutes." }),
    h("a", { class: "btn lg cta-btn", href: "#/signup", text: "Create your account" })));
  c.appendChild(disclaimer());
}

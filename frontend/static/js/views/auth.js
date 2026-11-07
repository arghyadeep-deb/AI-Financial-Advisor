import { h } from "../dom.js";
import { api, session } from "../api.js";
import { state } from "../state.js";
import { banner } from "../components.js";

function field(id, label, attrs, hint) {
  return h("div", { class: "field" }, h("label", { for: id, text: label }),
    h("input", { id, name: id, ...attrs }), hint ? h("div", { class: "hint", text: hint }) : null);
}

export async function authView(c, mode) {
  const signup = mode === "signup";
  const msg = h("div", { "aria-live": "polite" });
  const email = field("email", "Email", { type: "email", autocomplete: "email", required: true });
  const name = signup ? field("full_name", "Full name", { type: "text", autocomplete: "name", required: true, minlength: 2, maxlength: 100 }) : null;
  const pw = field("password", "Password", { type: "password", autocomplete: signup ? "new-password" : "current-password", required: true, maxlength: 128 },
    signup ? "Use a long, unique password. 12 or more characters is a good start." : null);
  const submit = h("button", { class: "btn primary block", type: "submit", text: signup ? "Create account" : "Log in" });

  const form = h("form", { novalidate: true }, name, email, pw, submit);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    msg.replaceChildren();
    submit.disabled = true;
    const body = { email: form.email.value.trim(), password: form.password.value };
    if (signup) body.full_name = form.full_name.value.trim();
    const r = await api(signup ? "/auth/signup" : "/auth/login", { method: "POST", body, auth: false });
    submit.disabled = false;
    if (!r.ok) { msg.appendChild(banner("bad", r.error)); return; }
    session.set(r.data.access_token);
    state.user = { id: r.data.user_id, name: r.data.full_name, email: r.data.email };
    form.password.value = "";
    location.hash = signup ? "#/profile" : "#/dashboard";
  });

  const reset = h("button", { class: "btn ghost", type: "button", text: "Forgot password?" });
  reset.addEventListener("click", async () => {
    const em = form.email.value.trim();
    if (!em) { msg.replaceChildren(banner("warn", "Enter your email above first.")); return; }
    const r = await api("/auth/password-reset/request", { method: "POST", body: { email: em }, auth: false });
    msg.replaceChildren(r.ok
      ? banner("info", "If that account exists, reset instructions will be sent. Email delivery is not set up yet in this environment.")
      : banner("bad", r.error));
  });

  c.appendChild(h("div", { class: "auth-box stack" },
    h("h1", { text: signup ? "Create your account" : "Welcome back" }),
    msg,
    h("div", { class: "card" }, form),
    h("div", { class: "spread" },
      signup ? h("a", { href: "#/login", text: "Already have an account? Log in" })
             : h("a", { href: "#/signup", text: "New here? Create an account" }),
      signup ? null : reset)));
}

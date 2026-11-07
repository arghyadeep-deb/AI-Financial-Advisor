// Import a bank CSV by telling us which column is which. Preview every row first; nothing is saved until you confirm.
import { h, clear, paise, toast } from "../dom.js";
import { api } from "../api.js";
import { banner, card } from "../components.js";

const PROBLEM = {
  invalid_date: "The date does not match the date format you chose.",
  future_date: "The date is in the future.",
  invalid_amount: "The amount is not a valid number with at most 2 decimals (or it is zero, or both debit and credit are filled).",
  invalid_description: "The description is empty or too long.",
  duplicate_reference: "This reference number appears more than once.",
  missing_columns: "This row has fewer columns than the mapping needs.",
  empty_statement: "No data rows were found.",
  possible_duplicate_of_line: "Looks the same as an earlier row (same date, amount and text). Check it is a real repeat.",
  formula_like_text_neutralised: "Text starting with = + - or @ was made safe.",
};
const DATE_FORMATS = [["%d/%m/%Y", "31/12/2025 (day/month/year)"], ["%d-%m-%Y", "31-12-2025"], ["%Y-%m-%d", "2025-12-31"], ["%m/%d/%Y", "12/31/2025 (month/day/year)"]];

// Display-only split of the header line so the user can pick columns. The server does the real, strict parsing.
function headerCells(text, delimiter) {
  const line = text.replace(/^﻿/, "").split(/\r?\n/)[0] || "";
  const cells = []; let cur = "", quoted = false;
  for (const ch of line) {
    if (ch === '"') quoted = !quoted;
    else if (ch === delimiter && !quoted) { cells.push(cur); cur = ""; }
    else cur += ch;
  }
  cells.push(cur);
  return cells.slice(0, 40);
}

export function mappedCard(accounts, onChange) {
  if (!accounts.length) return null;
  const msg = h("div", { "aria-live": "polite" });
  const result = h("div", { class: "stack" });
  const fieldsBox = h("div", { class: "stack" });
  let text = "";

  const acct = h("select", { id: "mp_acct" }, accounts.map((a) => h("option", { value: a.id, text: a.label })));
  const file = h("input", { id: "mp_file", type: "file", accept: ".csv,text/csv" });
  const delim = h("select", { id: "mp_delim" }, [[",", "Comma ( , )"], [";", "Semicolon ( ; )"], ["\t", "Tab"]].map(([v, t]) => h("option", { value: v, text: t })));
  const header = h("input", { id: "mp_header", type: "checkbox", checked: true });
  const fmt = h("select", { id: "mp_fmt" }, DATE_FORMATS.map(([v, t]) => h("option", { value: v, text: t })));
  const mode = h("select", { id: "mp_mode" }, [["signed", "One amount column (negative = money out)"], ["debit_credit", "Separate debit and credit columns"]].map(([v, t]) => h("option", { value: v, text: t })));
  const selects = {};
  const colSelect = (key, label, optional) => {
    const sel = h("select", { id: "mp_" + key });
    selects[key] = sel;
    return h("div", { class: "field", "data-key": key }, h("label", { for: "mp_" + key, text: label }), sel);
  };
  const fields = {
    date: colSelect("date", "Date column"), desc: colSelect("desc", "Description column"),
    ref: colSelect("ref", "Reference column (optional)"), amount: colSelect("amount", "Amount column"),
    debit: colSelect("debit", "Debit column (money out)"), credit: colSelect("credit", "Credit column (money in)"),
  };

  function fillColumns() {
    const cells = headerCells(text, delim.value);
    for (const [key, sel] of Object.entries(selects)) {
      clear(sel);
      if (key === "ref") sel.appendChild(h("option", { value: "", text: "None" }));
      cells.forEach((c, i) => sel.appendChild(h("option", { value: String(i), text: "Column " + (i + 1) + (header.checked && c.trim() ? ": " + c.trim().slice(0, 30) : "") })));
    }
    if (cells.length > 1) selects.desc.value = "1";
    if (cells.length > 2) selects.amount.value = "2";
    fields.amount.hidden = mode.value !== "signed";
    fields.debit.hidden = fields.credit.hidden = mode.value !== "debit_credit";
  }
  [delim, header, mode].forEach((el) => el.addEventListener("change", () => { if (text) fillColumns(); clear(result); }));
  file.addEventListener("change", async () => {
    clear(result); msg.replaceChildren(); text = "";
    const f = file.files[0];
    if (!f) { clear(fieldsBox); return; }
    if (!/\.csv$/i.test(f.name) && f.type !== "text/csv") { msg.appendChild(banner("bad", "Scanned files, photos and PDFs are not supported yet. Export a CSV from your bank instead.")); clear(fieldsBox); return; }
    if (f.size > 5 * 1024 * 1024) { msg.appendChild(banner("bad", "That file is too large.")); return; }
    text = await f.text();
    fillColumns();
    clear(fieldsBox);
    fieldsBox.append(h("div", { class: "grid c2" }, h("div", { class: "field" }, h("label", { for: "mp_delim", text: "Separator" }), delim),
        h("div", { class: "check" }, header, h("label", { for: "mp_header", text: "First row is a header" }))),
      h("div", { class: "grid c2" }, fields.date, h("div", { class: "field" }, h("label", { for: "mp_fmt", text: "Date format" }), fmt)),
      fields.desc, fields.ref,
      h("div", { class: "field" }, h("label", { for: "mp_mode", text: "How amounts are shown" }), mode), fields.amount, fields.debit, fields.credit,
      previewBtn);
  });

  const mapping = () => {
    const n = (k) => (selects[k].value === "" ? null : Number(selects[k].value));
    const m = { delimiter: delim.value, has_header: header.checked, date_column: n("date"), date_format: fmt.value,
      description_column: n("desc"), reference_column: n("ref"), amount_mode: mode.value };
    if (mode.value === "signed") m.amount_column = n("amount"); else { m.debit_column = n("debit"); m.credit_column = n("credit"); }
    return m;
  };
  const body = () => ({ csv_text: text, mapping: mapping() });
  const url = (what) => `/statement-accounts/${acct.value}/${what}`;

  function problems(list, kind) {
    if (!list.length) return null;
    return h("div", { class: "stack" }, banner(kind, h("strong", { text: kind === "bad" ? "Fix these before importing" : "Please check" })),
      h("div", { class: "table-scroll" }, h("table", {}, h("thead", {}, h("tr", {}, ["Line", "Problem"].map((t) => h("th", { text: t })))),
        h("tbody", {}, list.slice(0, 50).map((p) => h("tr", {}, h("td", { text: String(p.line) }),
          h("td", { text: (PROBLEM[p.code] || p.code) + (p.other_line ? " (line " + p.other_line + ")" : "") })))))));
  }

  const previewBtn = h("button", { class: "btn primary", type: "button", text: "Preview" });
  previewBtn.addEventListener("click", async () => {
    msg.replaceChildren(); clear(result);
    if (!text) { msg.appendChild(banner("bad", "Choose a CSV file first.")); return; }
    previewBtn.disabled = true;
    const r = await api(url("mapped-preview"), { method: "POST", body: body() });
    previewBtn.disabled = false;
    if (!r.ok) { msg.appendChild(banner("bad", r.error)); return; }
    const d = r.data;
    result.append(problems(d.errors, "bad"), problems(d.warnings, "warn"));
    if (d.ok) {
      const confirm = h("button", { class: "btn primary", type: "button", text: "Import " + d.row_count + " rows for review" });
      confirm.addEventListener("click", async () => {
        confirm.disabled = true;
        const u = await api(url("mapped-uploads"), { method: "POST", body: { ...body(), confirm: true, expected_rows: d.row_count } });
        if (u.ok) { toast("Imported. Review the rows in the list below before anything counts."); onChange(); }
        else { confirm.disabled = false; msg.appendChild(banner("bad", u.error)); }
      });
      result.append(h("div", { class: "summary" },
          h("div", {}, h("div", { class: "k", text: "Rows" }), h("div", { class: "v", text: String(d.row_count) })),
          h("div", {}, h("div", { class: "k", text: "From" }), h("div", { class: "v", text: d.start_date })),
          h("div", {}, h("div", { class: "k", text: "To" }), h("div", { class: "v", text: d.end_date }))),
        h("div", { class: "table-scroll" }, h("table", {}, h("thead", {}, h("tr", {}, ["Date", "Description", "Amount"].map((t, i) => h("th", { class: i === 2 ? "right" : null, text: t })))),
          h("tbody", {}, d.rows.map((x) => h("tr", {}, h("td", { text: x.posting_date }), h("td", { text: x.description }),
            h("td", { class: "right " + (x.amount_paise >= 0 ? "pos" : "neg"), text: paise(x.amount_paise) })))))),
        d.row_count > d.rows.length ? h("p", { class: "muted small", text: "Showing the first " + d.rows.length + " rows. Every row was checked." }) : null,
        confirm);
    }
  });

  return card("Upload a CSV from any bank",
    h("p", { class: "muted", text: "Tell us which column is which. You see every row checked before anything is saved, then you review it again before it counts." }),
    h("div", { class: "field" }, h("label", { for: "mp_acct", text: "Account" }), acct),
    h("div", { class: "field" }, h("label", { for: "mp_file", text: "CSV file" }), file), fieldsBox, msg, result);
}

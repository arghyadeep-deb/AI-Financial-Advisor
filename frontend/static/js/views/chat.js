import { h, clear, uid } from "../dom.js";
import { api, streamChat } from "../api.js";
import { banner, pageHead } from "../components.js";

export async function chat(c) {
  c.appendChild(pageHead("Advisor chat", "Ask about your numbers. Answers use your checked figures; if the AI is unavailable you get a plain rules-based reply, clearly labelled."));
  let threadId = null;
  let pending = null;            // {text, cid} kept so a retry reuses the same client_message_id
  let busy = false;

  const list = h("div", { class: "threads", role: "list" });
  const box = h("div", { class: "messages", role: "log", "aria-live": "polite", "aria-label": "Conversation" });
  const msg = h("div", { "aria-live": "polite" });
  const input = h("textarea", { id: "chat_in", placeholder: "Ask a question...", "aria-label": "Your message", maxlength: 4000, rows: 2 });
  const send = h("button", { class: "btn primary", type: "button", text: "Send" });
  const retry = h("button", { class: "btn hidden", type: "button", text: "Retry" });

  const bubble = (role, text, tag) => {
    const el = h("div", { class: "msg " + role, text });
    if (tag) el.appendChild(h("span", { class: "tag", text: tag }));
    box.appendChild(el); box.scrollTop = box.scrollHeight;
    return el;
  };

  async function loadThreads() {
    const r = await api("/threads");
    clear(list);
    list.appendChild(h("button", { type: "button", text: "+ New chat", onClick: () => { threadId = null; clear(box); msg.replaceChildren(); loadThreads(); } }));
    const items = r.ok && Array.isArray(r.data) ? r.data : (r.ok && r.data && r.data.threads) || [];
    items.forEach((t) => list.appendChild(h("button", { type: "button", "aria-current": t.id === threadId ? "true" : "false", text: t.title || "Chat " + t.id,
      onClick: () => openThread(t.id) })));
  }
  async function openThread(id) {
    const r = await api(`/threads/${id}/history`);
    if (!r.ok) { msg.replaceChildren(banner("bad", r.error)); return; }
    threadId = id; clear(box);
    (r.data.messages || []).forEach((m) => bubble(m.role === "user" ? "user" : "assistant", m.content));
    loadThreads();
  }

  async function submit(text, cid) {
    if (busy) return;
    busy = true; send.disabled = true; retry.classList.add("hidden"); msg.replaceChildren();
    const mine = bubble("user", text);
    const reply = bubble("assistant", "");
    const res = await streamChat({ message: text, threadId, clientMessageId: cid, onChunk: (t) => { reply.textContent += t; box.scrollTop = box.scrollHeight; } });
    busy = false; send.disabled = false;
    if (res.threadId) threadId = res.threadId;
    if (res.ok) {
      pending = null;
      if (!reply.textContent && res.reply) reply.textContent = res.reply;
      if (res.status === "degraded") reply.appendChild(h("span", { class: "tag", text: "Rules-based reply: the AI model was unavailable." }));
      if (res.replayed) reply.appendChild(h("span", { class: "tag", text: "Repeat of an earlier answer." }));
      loadThreads();
    } else {
      reply.remove();
      pending = { text, cid };
      msg.replaceChildren(banner("warn", (res.error || "The reply failed.") + (res.retryable ? " Your message was kept; press Retry." : "")));
      if (res.retryable) retry.classList.remove("hidden");
      mine.classList.add("pending");
    }
  }

  send.addEventListener("click", () => {
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    submit(text, uid());
  });
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send.click(); } });
  retry.addEventListener("click", () => {
    if (!pending) return;
    box.lastElementChild && box.lastElementChild.classList.contains("user") && box.lastElementChild.remove();
    submit(pending.text, pending.cid);
  });

  c.appendChild(h("div", { class: "chat" },
    h("aside", { class: "card flat", "aria-label": "Conversations" }, list),
    h("section", { class: "card" }, box, msg, h("div", { class: "composer" }, input, send, retry))));
  await loadThreads();
}

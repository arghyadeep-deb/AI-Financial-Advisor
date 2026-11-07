// HTTP layer.  The bearer token lives ONLY in this module's memory (not localStorage / sessionStorage / cookies):
// a page reload means logging in again, and injected script cannot read it from storage.
import { uid } from "./dom.js";

const meta = document.querySelector('meta[name="api-base"]');
const BASE = (meta && meta.content) || "";

let token = null;
const listeners = new Set();

export const session = {
  get active() { return token !== null; },
  set(t) { token = t; },
  clear() { token = null; listeners.forEach((fn) => fn("logout")); },
  onChange(fn) { listeners.add(fn); },
};

export function errorText(data, status) {
  const d = data && typeof data === "object" && "detail" in data ? data.detail : data;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d.map((e) => {
      const where = Array.isArray(e.loc) ? e.loc.filter((x) => x !== "body").join(".") : "";
      return (where ? where + ": " : "") + (e.msg || "invalid");
    }).join("; ");
  }
  if (d && typeof d === "object") {
    const fields = Array.isArray(d.fields) && d.fields.length ? " (" + d.fields.join(", ") + ")" : "";
    return (d.message || d.code || "Request failed") + fields;
  }
  if (status === 429) return "Too many attempts. Please wait and try again.";
  if (status >= 500) return "The server had a problem. Please try again.";
  return "Request failed.";
}

export async function api(path, { method = "GET", body, raw, contentType, auth = true, signal } = {}) {
  const headers = { Accept: "application/json" };
  if (raw !== undefined) headers["Content-Type"] = contentType || "application/octet-stream";   // raw file bytes
  else if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth && token) headers.Authorization = "Bearer " + token;
  let res;
  try {
    const payload = raw !== undefined ? raw : (body === undefined ? undefined : JSON.stringify(body));
    res = await fetch(BASE + path, { method, headers, body: payload, signal });
  } catch (e) {
    return { ok: false, status: 0, data: null, error: "Cannot reach the server. Check your connection." };
  }
  let data = null;
  if (res.status !== 204) {
    try { data = await res.json(); } catch (e) { data = null; }
  }
  if (res.status === 401 && auth && token) {
    session.clear();
    return { ok: false, status: 401, data, error: "Your session has ended. Please log in again." };
  }
  return { ok: res.ok, status: res.status, data, error: res.ok ? null : errorText(data, res.status) };
}

// POST /chat/stream.  Server-sent-event frames can be split across network chunks: buffer until a blank line.
export async function streamChat({ message, threadId, clientMessageId, onChunk, signal }) {
  let res;
  try {
    res = await fetch(BASE + "/chat/stream", {
      method: "POST", signal,
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + token, Accept: "text/event-stream" },
      body: JSON.stringify({ message, thread_id: threadId || null, client_message_id: clientMessageId || uid() }),
    });
  } catch (e) {
    return { ok: false, error: "Cannot reach the server.", retryable: true };
  }
  if (res.status === 401) { session.clear(); return { ok: false, error: "Your session has ended.", retryable: false }; }
  if (!res.ok || !res.body) {
    let data = null;
    try { data = await res.json(); } catch (e) { /* ignore */ }
    return { ok: false, error: errorText(data, res.status), retryable: res.status >= 500 };
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let out = { ok: false, error: "The reply was interrupted. Retry to complete it.", retryable: true, threadId };
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n\n")) !== -1) {
        const frame = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        for (const line of frame.split("\n")) {
          if (!line.startsWith("data:")) continue;
          let ev;
          try { ev = JSON.parse(line.slice(5).trim()); } catch (e) { continue; }
          if (ev.thread_id) out.threadId = ev.thread_id;
          if (ev.chunk) onChunk(ev.chunk);
          if (ev.error) out = { ...out, ok: false, error: ev.error, retryable: !!ev.retryable };
          if (ev.done) out = { ok: true, threadId: ev.thread_id || out.threadId, reply: ev.full_reply || "", status: ev.status || "ok", replayed: !!ev.replayed };
        }
      }
    }
  } catch (e) {
    if (e && e.name === "AbortError") return { ok: false, error: "Cancelled.", retryable: true, threadId: out.threadId };
  }
  return out;
}

// Authenticated file download (the token never leaves this module). Returns a Blob or null.
export async function fetchBlob(path) {
  try {
    const res = await fetch(BASE + path, { headers: token ? { Authorization: "Bearer " + token } : {} });
    if (res.status === 401) { session.clear(); return null; }
    return res.ok ? await res.blob() : null;
  } catch (e) { return null; }
}

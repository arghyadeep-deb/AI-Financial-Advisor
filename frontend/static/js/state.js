// In-memory app state.  Saved analysis and what-if (scenario) results are kept apart on purpose.
import { api } from "./api.js";

export const state = {
  user: null,          // {id, name, email}
  profile: null,       // last GET /profile body
  last: null,          // GET /analysis/last body (saved, non-scenario runs)
  scenario: null,      // most recent what-if response; never shown as the saved result
};

export function resetState() {
  state.user = null; state.profile = null; state.last = null; state.scenario = null;
}

export async function loadProfile(force = false) {
  if (state.profile && !force) return state.profile;
  const r = await api("/profile");
  state.profile = r.ok ? r.data : null;
  return state.profile;
}

export async function loadLast(force = false) {
  if (state.last && !force) return state.last;
  const r = await api("/analysis/last");
  state.last = r.ok ? r.data : { found: false, results: {} };
  return state.last;
}

export function section(name) {
  const l = state.last;
  return (l && l.results && l.results[name]) || null;
}

export async function runAnalysis(type, scenario) {
  const body = { analysis_type: type };
  if (scenario) body.scenario = scenario;
  const r = await api("/analysis", { method: "POST", body });
  if (r.ok && !r.data.is_scenario) state.last = null;      // reload from the server next time
  if (r.ok && r.data.is_scenario) state.scenario = r.data;
  return r;
}

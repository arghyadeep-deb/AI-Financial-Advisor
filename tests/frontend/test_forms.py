"""T107 — the Portfolio / Credit / Health forms send the values the user edited (as a what-if),
label the result honestly, and never invent a credit score.  Streamlit AppTest with the HTTP layer faked."""
import pytest

at_mod = pytest.importorskip("streamlit.testing.v1")
AppTest = at_mod.AppTest

PROFILE = {"id": 1, "user_id": 1, "revision": 3, "age": 30, "employment_type": "salaried",
           "monthly_income": 100000.0, "monthly_expenses": 40000.0, "existing_savings": 240000.0,
           "existing_investments": 0.0, "existing_debts": 0.0, "monthly_debt_payment": 0.0,
           "credit_score": None, "monthly_credit_spend": 10000.0, "risk_tolerance": "moderate",
           "investment_horizon": "long", "financial_goals": [], "top_spend_categories": []}


class FakeResp:
    def __init__(self, body, status=200):
        self._b, self.status_code = body, status

    def json(self):
        return self._b


@pytest.fixture
def calls(monkeypatch):
    sent = []
    result = {"success": True, "status": "complete", "is_scenario": True, "analysis_type": "health",
              "results": {"health": {"overall_score": 80, "grade": "B", "components": {}},
                          "credit": {"recommendations": []}, "investment": {"monthly_sip_plan": []}},
              "profile_revision": 3, "stale": False}

    def post(url, json=None, headers=None, **kw):
        sent.append((url, json))
        return FakeResp(result)

    def get(url, headers=None, **kw):
        if url.endswith("/profile"):
            return FakeResp(PROFILE)
        if url.endswith("/analysis/last"):
            return FakeResp({"found": False, "results": {}, "stale": False})
        return FakeResp({})

    import requests
    monkeypatch.setattr(requests, "post", post)
    monkeypatch.setattr(requests, "get", get)
    return sent


def app(page):
    at = AppTest.from_file(str(__import__("pathlib").Path(__file__).resolve().parents[2] / "frontend" / "app.py"), default_timeout=30)
    at.session_state["token"] = "t"
    at.session_state["user_name"] = "Test User"
    at.session_state["page"] = page
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def analysis_bodies(sent):
    return [b for (u, b) in sent if u.endswith("/analysis")]


def test_health_form_sends_edited_values_as_scenario_and_omits_unknown_credit(calls):
    at = app("health")
    at.number_input[0].set_value(120000)                # Monthly Income
    at.button[[b.label for b in at.button].index("❤️ Calculate Score")].click().run()
    body = analysis_bodies(calls)[-1]
    assert body["analysis_type"] == "health"
    assert body["scenario"]["monthly_income"] == 120000
    assert body["scenario"]["credit_score"] is None       # explicit unknown, never a 700 default or the saved score
    assert any("saved profile and saved analysis were not changed" in i.value for i in at.info)


def test_health_form_sends_credit_score_only_when_user_provides_one(calls):
    at = app("health")
    at.checkbox(key="credit_unknown_hf").uncheck()
    at.slider[0].set_value(780)
    at.button[[b.label for b in at.button].index("❤️ Calculate Score")].click().run()
    assert analysis_bodies(calls)[-1]["scenario"]["credit_score"] == 780


def test_credit_form_sends_spend_inputs_instead_of_ignoring_them(calls):
    at = app("credit")
    at.number_input[1].set_value(25000)                 # Monthly Credit Spend
    at.button[[b.label for b in at.button].index("💳 Get Recommendations")].click().run()
    sc = analysis_bodies(calls)[-1]["scenario"]
    assert sc["monthly_credit_spend"] == 25000 and sc["credit_score"] is None


def test_portfolio_form_sends_preferences(calls):
    at = app("portfolio")
    at.selectbox[0].set_value("high")
    at.button[[b.label for b in at.button].index("📊 Generate Plan")].click().run()
    body = analysis_bodies(calls)[-1]
    assert body["analysis_type"] == "investment" and body["scenario"]["risk_tolerance"] == "high"


def test_degraded_and_stale_results_are_labelled_not_shown_as_success(calls, monkeypatch):
    import requests
    degraded = {"status": "degraded", "is_scenario": False, "results": {"health": {"overall_score": 70}}}
    monkeypatch.setattr(requests, "post", lambda url, json=None, headers=None, **kw: FakeResp(degraded))
    at = app("health")
    at.button[[b.label for b in at.button].index("❤️ Calculate Score")].click().run()
    assert any("unavailable" in w.value for w in at.warning)
    assert not any(s.value == "Done." for s in at.success)


def test_health_results_render_when_credit_score_component_is_unknown(calls, monkeypatch):
    """Regression found in the real browser: a None component score crashed the page."""
    import requests
    comps = {"savings_rate": {"score": 5, "max": 25, "value": "0.0%", "benchmark": "20%+", "status": "poor"},
             "credit_score": {"score": None, "max": 10, "value": "unknown", "benchmark": "", "status": "unknown"}}
    body = {"status": "degraded", "is_scenario": True,
            "results": {"health": {"overall_score": 36.7, "grade": "D", "components": comps}}}
    monkeypatch.setattr(requests, "post", lambda url, json=None, headers=None, **kw: FakeResp(body))
    at = app("health")
    at.button[[b.label for b in at.button].index("❤️ Calculate Score")].click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Not provided" in m.value for m in at.markdown)


def test_portfolio_renders_when_tax_saving_is_unavailable(calls, monkeypatch):
    """Codex review P1: guarded investment results carry total_tax_saved_annually=None."""
    import requests
    inv = {"monthly_sip_plan": [], "total_monthly_investment": 0, "tax_saving_plan": {"total_tax_saved_annually": None}}
    last = {"found": True, "stale": False, "results": {"investment": inv}}
    real_get = requests.get
    monkeypatch.setattr(requests, "get", lambda url, headers=None, **kw:
                        FakeResp(last) if url.endswith("/analysis/last") else real_get(url, headers=headers, **kw))
    at = app("portfolio")
    assert not at.exception, [e.value for e in at.exception]


def test_what_if_result_never_leaks_into_saved_analysis_or_other_pages(calls):
    at = app("health")
    at.button[[b.label for b in at.button].index("❤️ Calculate Score")].click().run()
    assert at.session_state["scenario"]["page"] == "health"
    assert at.session_state["cached_health"] in (None, {})          # saved cache untouched
    at.session_state["page"] = "dashboard"
    at.run()
    assert "scenario" not in at.session_state


def test_profile_editor_opens_when_saved_values_are_unknown(calls, monkeypatch):
    """Codex review round 2: null money fields crashed the editor, blocking repair."""
    import requests
    broken = {**PROFILE, "monthly_income": None, "existing_debts": None, "needs_reentry": ["monthly_income", "existing_debts"]}
    real_get = requests.get
    monkeypatch.setattr(requests, "get", lambda url, headers=None, **kw:
                        FakeResp(broken) if url.endswith("/profile") else real_get(url, headers=headers, **kw))
    at = app("profile")
    assert not at.exception, [e.value for e in at.exception]
    assert any("re-entered" in w.value for w in at.warning)


def test_dashboard_shows_no_investment_plan_when_nothing_is_investable(calls, monkeypatch):
    import requests
    last = {"found": True, "stale": False, "snapshot": {"available_contribution_paise": 0, "shortfall_paise": 500000},
            "results": {"health": {"overall_score": None, "grade": "N/A", "components": {}},
                        "investment": {"total_monthly_investment": 48000, "projected_corpus_10yr": 9999999,
                                       "portfolio_allocation": {"equity": 60, "debt": 40}},
                        "credit": {"recommendations": [{"card_name": "Shiny Rewards Card"}]},
                        "simulation": {"current_trajectory": {"corpus_5yr": 1, "corpus_10yr": 2, "corpus_20yr": 3},
                                       "optimized_trajectory": {"corpus_5yr": 4, "corpus_10yr": 5, "corpus_20yr": 6}}}}
    real_get = requests.get
    monkeypatch.setattr(requests, "get", lambda url, headers=None, **kw:
                        FakeResp(last) if url.endswith("/analysis/last") else real_get(url, headers=headers, **kw))
    at = app("dashboard")
    assert any("nothing to invest" in i.value for i in at.info)
    page = " ".join(m.value for m in at.markdown)
    assert "Shiny Rewards Card" not in page and "48,000" not in page and "99,99,999" not in page
    assert len(at.get("plotly_chart")) == 0

"""T111 — telemetry carries metadata only; export is off by default; failures never leak content."""
import logging
import os
import uuid

import pytest

from backend.core import telemetry

MARKER = "SENSITIVE-MARKER-4711"


def test_tracing_is_off_and_payload_hiding_forced_by_default():
    assert telemetry.export_enabled() is False
    assert os.environ["LANGCHAIN_TRACING_V2"] == "false" and os.environ["LANGSMITH_TRACING"] == "false"
    for flag in ("LANGSMITH_HIDE_INPUTS", "LANGSMITH_HIDE_OUTPUTS", "LANGCHAIN_HIDE_INPUTS", "LANGCHAIN_HIDE_OUTPUTS"):
        assert os.environ[flag] == "true"


def test_parent_child_and_exception_spans_record_only_allow_listed_metadata(caplog):
    telemetry.events.clear()

    @telemetry.traceable(name="child")
    def child(profile):
        return {"advice": MARKER}

    @telemetry.traceable(name="parent")
    def parent(profile):
        child(profile)
        raise ValueError(f"failed for {MARKER}")

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ValueError):
            parent({"income": MARKER})
    assert [e["node"] for e in telemetry.events] == ["child", "parent"]
    assert telemetry.events[-1]["outcome"] == "error" and telemetry.events[-1]["error_type"] == "ValueError"
    for e in telemetry.events:
        assert set(e) <= set(telemetry.ALLOWED_META_KEYS) | {"version"}
        assert MARKER not in repr(e)
    assert MARKER not in caplog.text


def test_streaming_generator_wrapper_does_not_capture_chunks():
    telemetry.events.clear()

    @telemetry.traceable(name="stream")
    def stream():
        return iter([MARKER, MARKER])

    assert list(stream()) == [MARKER, MARKER]
    assert MARKER not in repr(list(telemetry.events))


def test_export_requires_both_flag_and_key(monkeypatch):
    monkeypatch.setattr(telemetry.config, "TRACING_ENABLED", True)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    assert telemetry.export_enabled() is False
    monkeypatch.setenv("LANGCHAIN_API_KEY", "x")
    assert telemetry.export_enabled() is True


def test_exported_wrapper_is_given_input_output_redactors(monkeypatch):
    """When export IS enabled, langsmith receives processors that drop every payload."""
    captured = {}

    class FakeLangsmith:
        @staticmethod
        def traceable(**kw):
            captured.update(kw)
            return lambda fn: fn

    monkeypatch.setattr(telemetry.config, "TRACING_ENABLED", True)
    monkeypatch.setenv("LANGCHAIN_API_KEY", "x")
    monkeypatch.setitem(__import__("sys").modules, "langsmith", FakeLangsmith)

    @telemetry.traceable(name="exported")
    def f(x):
        return MARKER

    f({"secret": MARKER})
    assert captured["process_inputs"]({"secret": MARKER}) == {"node": "exported"}
    assert captured["process_outputs"]({"out": MARKER}) == {"outcome": "ok"}


def test_http_error_responses_and_logs_do_not_echo_request_content(client, caplog):
    body = client.post("/auth/signup", json={"email": f"t-{uuid.uuid4().hex[:6]}@example.com",
                                             "full_name": "Test User", "password": "Correct-Horse-9"}).json()
    h = {"Authorization": f"Bearer {body['access_token']}"}
    with caplog.at_level(logging.DEBUG):
        r = client.post("/profile", json={"age": 30, "employment_type": "salaried", "monthly_income": MARKER,
                                          "monthly_expenses": 1, "risk_tolerance": "moderate",
                                          "investment_horizon": "long"}, headers=h)
    assert r.status_code == 422
    assert r.headers.get("x-request-id") and r.json()["request_id"] == r.headers["x-request-id"]
    assert MARKER not in caplog.text

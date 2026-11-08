"""T1005 'invalid channel': a client cannot invent a channel, cannot mark its own email verified, and an unverified address gets no mail."""
import pytest
from sqlalchemy.orm import Session
from backend.core.config import config
from backend.models.models import MailMessage, User
from backend.services import notification_service as notices
from tests.test_stage_c_platform import auth


@pytest.mark.parametrize("body", [
    {"categories": ["sms"]},                                   # unknown category
    {"channel": "sms"},                                        # unknown field
    {"verified_email_hash": "a" * 64},                         # server-owned, never client-set
    {"email_verified": True},
    {"quiet_start": 5},                                        # half a quiet-hours pair
    {"quiet_start": 5, "quiet_end": 5},
])
def test_preferences_reject_invented_channels_and_server_owned_fields(client, body):
    a = auth(client, "chan1@example.com")
    assert client.put("/preferences", headers=a, json=body).status_code == 422
    assert client.get("/preferences", headers=a).json()["email_enabled"] is False     # nothing was half-saved


def test_email_switch_alone_never_sends_to_an_unverified_address(client, db_engine, monkeypatch):
    monkeypatch.setattr(config, "NOTIFICATION_EMAIL_ENABLED", True)
    a = auth(client, "chan2@example.com")
    assert client.put("/preferences", headers=a, json={"email_enabled": True}).status_code == 200
    with Session(db_engine) as db:
        owner = db.query(User).filter_by(email="chan2@example.com").one()
        row = notices.deliver(db, owner.id, "evt-1", "report_ready")
        db.commit()
        assert row.state == "delivered"                                   # shown in the app
        assert db.query(MailMessage).count() == 0                         # but never mailed: the address is unverified

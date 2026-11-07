"""Optional user TOTP on the existing auth/session/throttle contracts."""
import base64
import secrets
import time
from datetime import timedelta
from urllib.parse import quote
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import update
from backend.core import auth, throttle
from backend.core.config import config
from backend.core.totp import matching_step
from backend.finance.storage import configured_storage
from backend.models.models import MfaCredential, MfaChallenge, MfaRecoveryCode, User, utcnow

ERROR = 'Invalid or expired credentials. Please sign in again.'


def invalid():
    return HTTPException(401, ERROR)


def _admit(db, bucket):
    if not throttle.consume_attempt(db, bucket):
        raise HTTPException(429, 'Try again later.', headers={'Retry-After': str(config.LOGIN_LOCK_SECONDS)})


def status(db, owner):
    credential = db.get(MfaCredential, owner)
    return {'enrolled': bool(credential and credential.enabled), 'required': config.MFA_REQUIRED}


def start(db, user, password):
    from backend.services.auth_service import AuthService
    AuthService(db).reauthenticate(user, password)
    _admit(db, 'mfa-enroll:' + str(user.id))
    credential = db.get(MfaCredential, user.id)
    if credential and credential.enabled:
        raise HTTPException(409, 'MFA is already enrolled.')
    secret = base64.b32encode(secrets.token_bytes(20)).decode().rstrip('=')
    encrypted = configured_storage().seal(user.id, 'totp', secret)
    generation, expires = str(uuid4()), utcnow() + timedelta(minutes=10)
    if credential:
        count = db.execute(update(MfaCredential).where(MfaCredential.user_id == user.id,
            MfaCredential.enabled.is_(False)).values(encrypted_secret=encrypted,
            generation=generation, expires_at=expires, last_step=-1)).rowcount
        if count != 1:
            db.rollback()
            raise invalid()
    else:
        db.add(MfaCredential(user_id=user.id, encrypted_secret=encrypted,
            generation=generation, expires_at=expires, last_step=-1))
    db.commit()
    # Intentional setup-only disclosure; no rendered QR/email/raw secret field.
    issuer = 'AI Advisory'
    uri = 'otpauth://totp/' + quote(issuer + ':' + str(user.id), safe='')
    uri += '?secret=' + secret + '&issuer=' + quote(issuer) + '&algorithm=SHA1&digits=6&period=30'
    return {'otpauth_uri': uri, 'expires_in': 600}


def _new_codes(db, owner):
    db.query(MfaRecoveryCode).filter_by(user_id=owner).delete(synchronize_session=False)
    codes = [secrets.token_hex(16) for _ in range(10)]
    for code in codes:
        db.add(MfaRecoveryCode(user_id=owner, token_hash=auth.digest_token(code)))
    db.flush()
    return codes


def confirm(db, user, code):
    _admit(db, 'mfa-enroll-confirm:' + str(user.id))
    credential = db.get(MfaCredential, user.id)
    if not credential or credential.enabled or credential.expires_at <= utcnow():
        raise invalid()
    secret = configured_storage().unseal(user.id, 'totp', credential.encrypted_secret)
    step = matching_step(secret, code, time.time())
    if step is None:
        raise invalid()
    count = db.execute(update(MfaCredential).where(MfaCredential.user_id == user.id,
        MfaCredential.enabled.is_(False), MfaCredential.generation == credential.generation,
        MfaCredential.expires_at > utcnow()).values(enabled=True, last_step=step)).rowcount
    if count != 1:
        db.rollback()
        raise invalid()
    codes = _new_codes(db, user.id)
    from backend.services.auth_service import AuthService
    service = AuthService(db)
    service.revoke_user_sessions(user.id, 'mfa_enrolled')
    return {'recovery_codes': codes, 'session': service._issue(user, mfa_verified=True)}


def challenge(db, user, credential):
    _admit(db, 'mfa-challenge-issue:' + str(user.id))
    db.query(MfaChallenge).filter(MfaChallenge.user_id == user.id,
        MfaChallenge.expires_at <= utcnow()).delete(synchronize_session=False)
    token = secrets.token_urlsafe(32)
    db.add(MfaChallenge(user_id=user.id, token_hash=auth.digest_token(token),
        generation=credential.generation, expires_at=utcnow() + timedelta(minutes=5)))
    db.commit()
    return {'mfa_required': True, 'challenge': token, 'expires_in': 300}


def verify(db, token, code):
    digest = auth.digest_token(token)
    challenge_row = db.get(MfaChallenge, digest)
    # Unknown tokens have 256 bounded buckets. Known challenges share owner cap.
    bucket = 'mfa-verify:' + (str(challenge_row.user_id) if challenge_row else 'unknown:' + digest[:2])
    _admit(db, bucket)
    now = utcnow()
    if not challenge_row or challenge_row.used_at is not None or challenge_row.expires_at <= now:
        raise invalid()
    if not secrets.compare_digest(challenge_row.token_hash, digest):
        raise invalid()
    user, credential = db.get(User, challenge_row.user_id), db.get(MfaCredential, challenge_row.user_id)
    if not user or not user.is_active or not credential or not credential.enabled or credential.generation != challenge_row.generation:
        raise invalid()
    if config.SUPPRESSION_JOURNAL:
        from backend.services.privacy.lifecycle import configured_journal
        if configured_journal().contains(user.id):
            raise invalid()
    secret = configured_storage().unseal(user.id, 'totp', credential.encrypted_secret)
    step = matching_step(secret, code, time.time(), credential.last_step)
    recovery = None
    if step is None:
        code_digest = auth.digest_token(code)
        recovery = db.get(MfaRecoveryCode, code_digest)
        if not recovery or recovery.user_id != user.id or recovery.used_at is not None or not secrets.compare_digest(recovery.token_hash, code_digest):
            raise invalid()
    # Credential CAS serializes step claims with recovery/disable/regeneration.
    statement = update(MfaCredential).where(MfaCredential.user_id == user.id,
        MfaCredential.enabled.is_(True), MfaCredential.generation == challenge_row.generation)
    if step is not None:
        statement = statement.where(MfaCredential.last_step < step).values(last_step=step)
    else:
        statement = statement.values(generation=str(uuid4()))
    if db.execute(statement).rowcount != 1:
        db.rollback()
        raise invalid()
    if recovery:
        count = db.execute(update(MfaRecoveryCode).where(MfaRecoveryCode.token_hash == recovery.token_hash,
            MfaRecoveryCode.user_id == user.id, MfaRecoveryCode.used_at.is_(None)).values(used_at=now)).rowcount
        if count != 1:
            db.rollback()
            raise invalid()
    count = db.execute(update(MfaChallenge).where(MfaChallenge.token_hash == digest,
        MfaChallenge.used_at.is_(None), MfaChallenge.expires_at > now).values(used_at=now)).rowcount
    if count != 1:
        db.rollback()
        raise invalid()
    from backend.services.auth_service import AuthService
    service = AuthService(db)
    if recovery:
        service.revoke_user_sessions(user.id, 'mfa_recovery')
    return service._issue(user, mfa_verified=True)


def manage(db, user, password, *, disable=False):
    from backend.services.auth_service import AuthService
    service = AuthService(db)
    service.reauthenticate(user, password)
    if disable and config.MFA_REQUIRED:
        raise HTTPException(409, 'MFA is required by policy.')
    credential = db.get(MfaCredential, user.id)
    if not credential or not credential.enabled:
        raise invalid()
    count = db.execute(update(MfaCredential).where(MfaCredential.user_id == user.id,
        MfaCredential.enabled.is_(True), MfaCredential.generation == credential.generation).values(
        generation=str(uuid4()), enabled=not disable)).rowcount
    if count != 1:
        db.rollback()
        raise invalid()
    db.query(MfaChallenge).filter_by(user_id=user.id).delete(synchronize_session=False)
    service.revoke_user_sessions(user.id, 'mfa_disabled' if disable else 'mfa_codes_regenerated')
    if disable:
        db.query(MfaRecoveryCode).filter_by(user_id=user.id).delete(synchronize_session=False)
        db.query(MfaCredential).filter_by(user_id=user.id).delete(synchronize_session=False)
        db.commit()
        return {'message': 'MFA disabled. Please sign in again.'}
    codes = _new_codes(db, user.id)
    return {'recovery_codes': codes, 'session': service._issue(user, mfa_verified=True)}

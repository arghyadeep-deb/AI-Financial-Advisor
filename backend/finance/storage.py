"""Private encrypted local objects. All keys are random UUIDs scoped by owner.

No public URLs. Auth is enforced by the document service on every read. Rotation
retains old keys for recovery; rotate() rewrites atomically with the active key.
"""
import json
import os
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4
from cryptography.fernet import Fernet, InvalidToken
from backend.core.config import config


class PrivateStorage(Protocol):
    def put(self, owner: int, key: str, content: bytes): ...
    def get(self, owner: int, key: str) -> bytes: ...
    def delete(self, owner: int, key: str): ...


class LocalEncryptedStorage:
    def __init__(self, root, keys, active):
        self.root = Path(root).resolve()
        if active not in keys or not keys or any(not k.isalnum() or len(k) > 40 for k in keys):
            raise ValueError('Valid active storage key required')
        self.keys = {k: Fernet(v.encode() if isinstance(v, str) else v) for k, v in keys.items()}
        self.active = active

    def path(self, owner, key):
        if type(owner) is not int or owner <= 0 or str(UUID(key)) != key:
            raise ValueError('Invalid private object identity')
        path = self.root / str(owner) / key
        if not path.resolve().is_relative_to(self.root):
            raise ValueError('Invalid storage path')
        return path

    def put(self, owner, key, content):
        path = self.path(owner, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(str(uuid4()) + '.tmp')
        try:
            with temporary.open('xb') as stream:
                os.chmod(temporary, 0o600)
                stream.write(self.active.encode() + b'\n' + self.keys[self.active].encrypt(content))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def get(self, owner, key):
        version, token = self.path(owner, key).read_bytes().split(b'\n', 1)
        try:
            return self.keys[version.decode()].decrypt(token)
        except (KeyError, InvalidToken, UnicodeError) as exc:
            raise ValueError('Storage key unavailable or object authentication failed') from exc

    def rotate(self, owner, key):
        self.put(owner, key, self.get(owner, key))

    def seal(self, owner, purpose, content):
        """Encrypt a small DB value with this same managed key ring, bound to owner/purpose."""
        envelope = json.dumps([owner, purpose, content], separators=(',', ':')).encode()
        return self.active + ':' + self.keys[self.active].encrypt(envelope).decode()

    def unseal(self, owner, purpose, value):
        try:
            version, token = value.split(':', 1)
            bound_owner, bound_purpose, content = json.loads(self.keys[version].decrypt(token.encode()))
            if (bound_owner, bound_purpose) != (owner, purpose):
                raise ValueError('Invalid encrypted value binding')
            return content
        except (KeyError, InvalidToken, UnicodeError, TypeError, ValueError) as exc:
            raise ValueError('Encrypted value unavailable') from exc

    def delete(self, owner, key):
        self.path(owner, key).unlink(missing_ok=True)


def configured_storage():
    from fastapi import HTTPException
    if not config.PRIVATE_STORAGE_ROOT or not config.STORAGE_ACTIVE_KEY:
        raise HTTPException(503, 'Private encrypted storage is not configured.')
    try:
        return LocalEncryptedStorage(config.PRIVATE_STORAGE_ROOT, json.loads(config.STORAGE_KEYS_JSON), config.STORAGE_ACTIVE_KEY)
    except (ValueError, TypeError) as exc:
        raise HTTPException(503, 'Private storage key configuration is invalid.') from exc

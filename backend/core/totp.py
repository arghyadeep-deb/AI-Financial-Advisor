"""RFC 6238/4226 primitives. SHA1/6 digits/30 seconds for enrolled credentials."""
import base64
import hashlib
import hmac
import struct


def totp(secret: str, timestamp: int, *, digits=6, algorithm='sha1', period=30) -> str:
    if algorithm not in {'sha1', 'sha256', 'sha512'} or digits not in {6, 8} or period != 30 or timestamp < 0:
        raise ValueError('Unsupported TOTP parameters')
    key = base64.b32decode(secret + '=' * (-len(secret) % 8), casefold=False)
    mac = hmac.new(key, struct.pack('>Q', int(timestamp) // period), getattr(hashlib, algorithm)).digest()
    offset = mac[-1] & 15
    value = struct.unpack('>I', mac[offset:offset + 4])[0] & 0x7fffffff
    return str(value % (10 ** digits)).zfill(digits)


def matching_step(secret, code, timestamp, last_step=-1):
    valid_format = isinstance(code, str) and len(code) == 6 and code.isascii() and code.isdigit()
    candidate = code if valid_format else '------'
    step = int(timestamp) // 30
    matched = None
    for current in (step - 1, step, step + 1):
        if current < 0:
            continue
        equal = hmac.compare_digest(totp(secret, current * 30), candidate)
        if equal and valid_format and current > last_step:
            matched = current
    return matched

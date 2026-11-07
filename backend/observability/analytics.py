"""Privacy-safe product analytics (T1305). Allow-list only: an event name plus enumerated, non-financial properties.

There is no user id, no free text and no number that could be an amount. Anything outside the allow-list is dropped whole,
never "cleaned". No external exporter exists; events stay in a bounded in-memory buffer.
"""
from collections import deque

EVENTS = frozenset({'signup_completed', 'profile_saved', 'statement_uploaded', 'mapping_confirmed', 'report_viewed',
                    'export_requested', 'credit_entry_added'})
PROPERTIES = {
    'surface': frozenset({'web'}),
    'outcome': frozenset({'ok', 'error', 'cancelled'}),
    'step': frozenset({'start', 'preview', 'confirm', 'review', 'done'}),
    'size_bucket': frozenset({'0', '1-10', '11-100', '100+'}),
}
captured = deque(maxlen=500)


def sanitize(name, props=None):
    if name not in EVENTS:
        raise ValueError('event not allowed')
    clean = {}
    for key, value in (props or {}).items():
        if key not in PROPERTIES or value not in PROPERTIES[key]:
            raise ValueError('property not allowed')
        clean[key] = value
    return {'event': name, 'props': clean}


def capture(name, props=None):
    """Never raises into a request. Returns whether the event was kept."""
    try:
        captured.append(sanitize(name, props))
        return True
    except ValueError:
        return False


def bucket(count):
    return '0' if count <= 0 else '1-10' if count <= 10 else '11-100' if count <= 100 else '100+'

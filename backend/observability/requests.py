"""Bounded request metadata for support lookups: id, method, route template, status, duration. No query, body or user data."""
from collections import OrderedDict

MAX = 2000
_recent = OrderedDict()


def record(request_id, method, route, status, duration_ms):
    if not request_id:
        return
    _recent[request_id] = {'request_id': request_id, 'method': method, 'route': route, 'status': status,
                           'duration_ms': round(duration_ms, 1)}
    _recent.move_to_end(request_id)
    while len(_recent) > MAX:
        _recent.popitem(last=False)


def lookup(request_id):
    return _recent.get(request_id)

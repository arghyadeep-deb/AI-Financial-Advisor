"""Private subprocess entrypoint: no credentials, network, shell or dynamic adapters."""
import json
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def denied(*args, **kwargs):
    raise PermissionError('network disabled')


socket.socket = denied
socket.create_connection = denied

if __name__ == '__main__':
    from backend.finance.importers.synthetic import parse, ParseError
    max_bytes, max_rows = map(int, sys.argv[1:3])
    try:
        content = sys.stdin.buffer.read(max_bytes + 1)
        result = {'ok': True, 'parsed': parse(content, max_rows, max_bytes)}
    except ParseError as exc:
        result = {'ok': False, 'error_code': str(exc)}
    except Exception:
        result = {'ok': False, 'error_code': 'parser_failure'}
    sys.stdout.write(json.dumps(result, ensure_ascii=True))

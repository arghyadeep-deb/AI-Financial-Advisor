"""Bounded, credential-free subprocess. OS sandbox remains a real-data release gate."""
import json
import os
from pathlib import Path
import subprocess
import sys
from backend.core.config import config


def extract(content, *, scanner_available=True):
    if not scanner_available:
        return {'ok': False, 'error_code': 'scanner_unavailable'}
    if len(content) > config.STATEMENT_MAX_BYTES:
        return {'ok': False, 'error_code': 'file_too_large'}
    # No inherited provider keys, PYTHONPATH, shell or user-controlled executable.
    env = {k: os.environ[k] for k in ('SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP') if k in os.environ}
    try:
        result = subprocess.run([sys.executable, '-I', str(Path(__file__).with_name('parser_process.py')),
            str(config.STATEMENT_MAX_BYTES), str(config.STATEMENT_MAX_ROWS)], input=content,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env,
            timeout=config.STATEMENT_TIMEOUT_SECONDS, check=True,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        # Output is bounded by the input/row cap and this fixed parser's schema.
        if len(result.stdout) > config.STATEMENT_MAX_BYTES * 10:
            return {'ok': False, 'error_code': 'parser_output_limit'}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error_code': 'parser_timeout'}
    except (OSError, subprocess.CalledProcessError, ValueError):
        return {'ok': False, 'error_code': 'scanner_unavailable'}

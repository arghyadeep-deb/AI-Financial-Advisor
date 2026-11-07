"""Run the offline safety evals against the real API stack with a mocked model. Writes evals/results/latest.json."""
import json
import subprocess
import sys
import uuid
from pathlib import Path


def run(client):
    import agents.summary_agent as sa
    from evals.cases import BASE, CHECKS, FABRICATIONS, PROFILES
    rows = []
    for pname, pdata in PROFILES.items():
        for fname, text in FABRICATIONS.items():
            body = client.post("/auth/signup", json={"email": f"e-{uuid.uuid4().hex[:8]}@example.com",
                                                     "full_name": "Eval User", "password": "Correct-Horse-9"}).json()
            h = {"Authorization": f"Bearer {body['access_token']}"}
            client.post("/profile", json={**BASE, **pdata}, headers=h)
            payload = json.dumps({"executive_summary": text, "top_priorities": [], "quick_wins": [],
                                  "personalized_message": text, "key_numbers": {}})
            orig = sa.call_llm
            sa.call_llm = lambda **kw: payload
            try:
                out = client.post("/analysis", json={"analysis_type": "full"}, headers=h).json()
            finally:
                sa.call_llm = orig
            rows.append({"profile": pname, "fabrication": fname, "passed": bool(CHECKS[fname](out, pname)),
                         "status": out["status"], "narrative_source": out["results"]["summary"].get("narrative_source")})
    return rows


def write(rows):
    rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    res = {"code_revision": rev, "feature": "001", "cases": len(rows), "passed": sum(r["passed"] for r in rows),
           "failed": [r for r in rows if not r["passed"]], "rows": rows, "provider": "mocked",
           "note": "Offline correctness only; says nothing about live-model quality."}
    Path(__file__).with_name("results").mkdir(exist_ok=True)
    Path(__file__).with_name("results").joinpath("latest.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    return res


if __name__ == "__main__":
    print("run via: python -m pytest tests/evals -q", file=sys.stderr)

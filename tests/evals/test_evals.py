"""T111 offline evaluations: every hostile/fabricated narrative is neutralised for every profile class."""
from evals.run_evals import run, write


def test_offline_safety_evals_all_pass(client):
    rows = run(client)
    res = write(rows)
    assert res["cases"] == 20
    assert res["failed"] == [], res["failed"]

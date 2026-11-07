"""Lane L: mapped CSV import, scanned-file message, manual dated credit entry, billing flag. All data fictional."""
import json
from datetime import date, timedelta
import pytest
from cryptography.fernet import Fernet
from backend.core.config import config
from backend.finance.importers import mapped
from backend.integrations.credit_bureau import DisabledAdapter, IntegrationDisabled, get_adapter
from tests.test_stage_c_platform import auth


@pytest.fixture(autouse=True)
def synthetic_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'SYNTHETIC_STATEMENTS_ENABLED', True)
    monkeypatch.setattr(config, 'PRIVATE_STORAGE_ROOT', str(tmp_path / 'private'))
    monkeypatch.setattr(config, 'STORAGE_ACTIVE_KEY', 'v1')
    monkeypatch.setattr(config, 'STORAGE_KEYS_JSON', json.dumps({'v1': Fernet.generate_key().decode()}))


SIGNED = {'date_column': 0, 'date_format': '%d/%m/%Y', 'description_column': 1, 'reference_column': 2,
          'amount_mode': 'signed', 'amount_column': 3}
DC = {'date_column': 0, 'date_format': '%Y-%m-%d', 'description_column': 1, 'amount_mode': 'debit_credit',
      'debit_column': 2, 'credit_column': 3}


def parse(text, mapping=None):
    return mapped.preview(text.encode(), mapped.Mapping(**(mapping or SIGNED)), max_rows=100, max_bytes=100000)


def account(client, headers, token='MAP_A'):
    return client.post('/statement-accounts', headers=headers, json={'label': 'Mapped', 'token': token}).json()


GOOD = 'Date,Narration,Ref,Amount\n01/10/2025,Salary,R1,"1,00,000.50"\n02/10/2025,Groceries,R2,-2500.25\n'


def test_signed_amounts_exact_paise_and_indian_grouping():
    r = parse(GOOD)
    assert r['ok'] and [x['amount_paise'] for x in r['all_rows']] == [10000050, -250025]
    assert r['start_date'] == '2025-10-01' and r['end_date'] == '2025-10-02'


def test_debit_credit_columns():
    r = parse('d,n,debit,credit\n2025-10-01,Rent,15000,\n2025-10-02,Refund,,300.5\n', DC)
    assert r['ok'] and [x['amount_paise'] for x in r['all_rows']] == [-1500000, 30050]
    both = parse('d,n,debit,credit\n2025-10-01,X,5,5\n', DC)
    assert not both['ok'] and both['errors'][0]['code'] == 'invalid_amount'


@pytest.mark.parametrize('amount', ['1.234', '1e3', 'abc', '', '0', '--5', '1,2,3', 'NaN', '₹5'])
def test_bad_amounts_rejected_not_rounded(amount):
    r = parse(f'Date,N,Ref,Amt\n01/10/2025,x,r,"{amount}"\n')
    assert not r['ok'] and r['errors'][0]['code'] == 'invalid_amount'


def test_dates_explicit_format_and_no_future():
    assert parse('h,n,r,a\n2025-10-01,x,r,5\n')['errors'][0]['code'] == 'invalid_date'   # wrong format, not guessed
    tomorrow = (date.today() + timedelta(days=1)).strftime('%d/%m/%Y')
    assert parse(f'h,n,r,a\n{tomorrow},x,r,5\n')['errors'][0]['code'] == 'future_date'


def test_duplicate_reference_error_and_duplicate_row_warning():
    assert parse('h,n,r,a\n01/10/2025,x,R,5\n02/10/2025,y,R,6\n')['errors'][0]['code'] == 'duplicate_reference'
    r = parse('h,n,r,a\n01/10/2025,x,,5\n01/10/2025,x,,5\n')
    assert r['ok'] and r['warnings'][0]['code'] == 'possible_duplicate_of_line'


def test_formula_injection_neutralised():
    r = parse('h,n,r,a\n01/10/2025,=HYPERLINK("http://x"),,5\n02/10/2025,@cmd,,6\n03/10/2025,-2+3,,7\n')
    assert r['ok'] and all(x['description'].startswith("'") for x in r['all_rows'])
    assert {w['code'] for w in r['warnings']} == {'formula_like_text_neutralised'}
    assert "'=HYPERLINK" in mapped.to_canonical('T', r).decode()


def test_mapping_validation():
    with pytest.raises(ValueError):
        mapped.Mapping(date_column=0, date_format='%d/%m/%Y', description_column=1, amount_mode='signed')
    with pytest.raises(ValueError):
        mapped.Mapping(date_column=0, date_format='%d/%m/%Y', description_column=1, amount_mode='debit_credit',
                       debit_column=2, credit_column=2)
    with pytest.raises(ValueError):
        mapped.Mapping(date_column=0, date_format='dd/mm', description_column=1, amount_mode='signed', amount_column=2)


def test_missing_columns_and_limits():
    assert parse('h,n,r,a\n01/10/2025,x\n')['errors'][0]['code'] == 'missing_columns'
    with pytest.raises(mapped.MappingError):
        mapped.preview(b'a\n' * 5, mapped.Mapping(**SIGNED), max_rows=2, max_bytes=100)
    with pytest.raises(mapped.MappingError, match='file_too_large'):
        mapped.preview(b'x' * 11, mapped.Mapping(**SIGNED), max_rows=2, max_bytes=10)


@pytest.mark.parametrize('magic', [b'%PDF-1.7 x', b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff\xe0', b'GIF89a'])
def test_scanned_and_image_files_rejected_with_clear_message(client, magic):
    a = auth(client, 'scan@example.com')
    acct = account(client, a)
    r = client.post(f"/statement-accounts/{acct['id']}/uploads", headers={**a, 'Content-Type': 'text/plain'}, content=magic)
    if magic.startswith(b'%PDF'):
        assert r.status_code == 202   # PDFs are quarantined by the parser with a readable message instead
        job = client.get('/statement-imports/' + r.json()['id'], headers=a).json()
        assert 'error_message' in job
    else:
        assert r.status_code == 422 and 'not supported' in r.json()['detail'] and 'Nothing was sent' in r.json()['detail']
    for kind in ('image/png', 'application/pdf'):
        r = client.post(f"/statement-accounts/{acct['id']}/uploads", headers={**a, 'Content-Type': kind}, content=magic)
        assert r.status_code == 415 and 'not supported' in r.json()['detail']


def body(csv_text=GOOD, **extra):
    return {'csv_text': csv_text, 'mapping': SIGNED, **extra}


def test_preview_then_confirmed_upload_flows_into_review(client):
    a = auth(client, 'map@example.com')
    acct = account(client, a)
    path = f"/statement-accounts/{acct['id']}"
    preview = client.post(path + '/mapped-preview', headers=a, json=body())
    assert preview.status_code == 200 and preview.json()['ok'] and preview.json()['row_count'] == 2
    assert 'all_rows' not in preview.json()
    assert client.get('/statement-imports', headers=a).json() == []           # a preview stores nothing
    assert client.post(path + '/mapped-uploads', headers=a, json=body(confirm=False, expected_rows=2)).status_code == 422
    assert client.post(path + '/mapped-uploads', headers=a, json=body(confirm=True, expected_rows=3)).status_code == 409
    up = client.post(path + '/mapped-uploads', headers=a, json=body(confirm=True, expected_rows=2))
    assert up.status_code == 202, up.text
    assert len(client.get('/statement-imports', headers=a).json()) == 1


def test_invalid_rows_block_upload_and_other_owner_gets_404(client):
    a, b = auth(client, 'own1@example.com'), auth(client, 'own2@example.com')
    acct = account(client, a)
    path = f"/statement-accounts/{acct['id']}"
    bad = body('h,n,r,a\n01/10/2025,x,r,abc\n', confirm=True, expected_rows=1)
    r = client.post(path + '/mapped-uploads', headers=a, json=bad)
    assert r.status_code == 422 and r.json()['detail']['code'] == 'validation_failed'
    assert client.post(path + '/mapped-preview', headers=b, json=body()).status_code == 404
    assert client.post(path + '/mapped-uploads', headers=b, json=body(confirm=True, expected_rows=2)).status_code == 404


def test_mapped_import_disabled_outside_synthetic_gate(client, monkeypatch):
    a = auth(client, 'gate@example.com')
    acct = account(client, a)
    monkeypatch.setattr(config, 'SYNTHETIC_STATEMENTS_ENABLED', False)
    assert client.post(f"/statement-accounts/{acct['id']}/mapped-preview", headers=a, json=body()).status_code == 503


def test_manual_credit_entry_dated_stale_and_unknown(client):
    a, b = auth(client, 'cr1@example.com'), auth(client, 'cr2@example.com')
    empty = client.get('/credit/manual', headers=a).json()
    assert empty['latest']['status'] == 'unknown' and empty['latest']['score'] is None
    assert empty['provider']['status'] == 'disabled'
    today = date.today().isoformat()
    cur = client.post('/credit/manual', headers=a, json={'score': 750, 'bureau_label': 'My app', 'as_of': today})
    assert cur.status_code == 201 and cur.json()['status'] == 'current' and cur.json()['source'] == 'user_reported'
    old = (date.today() - timedelta(days=200)).isoformat()
    stale = client.post('/credit/manual', headers=b, json={'score': 700, 'as_of': old}).json()
    assert stale['status'] == 'stale' and 'update' in stale['note']
    unknown = client.post('/credit/manual', headers=b, json={'as_of': today}).json()
    assert unknown['status'] == 'unknown' and unknown['score'] is None
    assert client.get('/credit/manual', headers=b).json()['latest']['id'] == unknown['id']
    assert client.get('/credit/manual', headers=a).json()['latest']['score'] == 750   # owner-scoped
    for bad in ({'score': 299, 'as_of': today}, {'score': 901, 'as_of': today}, {'score': 700, 'as_of': '2999-01-01'},
                {'score': 700}, {'score': '750', 'as_of': today}):
        assert client.post('/credit/manual', headers=a, json=bad).status_code == 422


def test_credit_adapter_disabled_and_billing_flag(client, monkeypatch):
    with pytest.raises(IntegrationDisabled):
        get_adapter().fetch_summary('consent-ref')
    assert isinstance(get_adapter(), DisabledAdapter)
    a = auth(client, 'bill@example.com')
    e = client.get('/billing/entitlement', headers=a).json()
    assert e['plan'] == 'free_pilot' and e['billing'] == 'disabled' and e['paid_billing'] == 'deferred'
    assert client.get('/billing/entitlement').status_code == 401
    monkeypatch.setattr(config, 'BILLING_MODE', 'stripe')
    with pytest.raises(Exception, match='paid billing is deferred'):
        config.validate()

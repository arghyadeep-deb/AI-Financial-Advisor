"""Structured manual input acceptance only; document parsing PENDING."""
import pytest
from pydantic import ValidationError
from backend.schemas.tax import TaxInputs
from tests.tax.test_h2_independent import case


@pytest.mark.parametrize('field',['salary_paise','withholding_paise','allowances_paise','deductions_paise'])
@pytest.mark.parametrize('bad',[True,-1,1.5,float('nan'),float('inf'),10**14])
def test_manual_money_is_exact_and_bounded(field,bad):
    data=case(120000000).model_dump()
    if field in {'salary_paise','withholding_paise'}: data['sources'][0][field]=bad
    else: data[field]={'taxable_allowances' if field=='allowances_paise' else '80C':bad}
    with pytest.raises(ValidationError): TaxInputs.model_validate(data)


@pytest.mark.parametrize('layout',['Form16','AIS','26AS','pdf','ocr'])
def test_official_document_parsing_is_not_implemented(layout):
    data=case(120000000).model_dump(); data['sources'][0]['layout']=layout
    with pytest.raises(ValidationError): TaxInputs.model_validate(data)


def test_manual_inputs_review_and_evidence(client,monkeypatch):
    from tests.tax.test_stage_h import ready, operation
    inp=case(110000000,deductions_paise={'80C':15000000},allowances_paise={'taxable_allowances':10000000})
    a,cid,_=ready(client,monkeypatch,inp.model_dump(mode='json'))
    got=client.post(f'/tax/cases/{cid}/drafts',headers=a,json=operation(1)).json()['data']
    assert got['regimes']['old']['gross_salary_paise']==120000000
    assert got['regimes']['old']['tax_paise']==11700000
    assert got['regimes']['new']['status']=='unsupported'
    assert got['manual_claim_evidence']['deductions_paise']=={'80C':15000000}
    assert 'not implemented' in got['document_parsing']
    assert got['review_snapshot']['fields']['salary_paise']==110000000

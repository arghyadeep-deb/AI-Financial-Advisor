"""D04 historical pack smoke checks, fictional inputs only."""
from datetime import date
from backend.schemas.tax import TaxInputs
from backend.finance.tax import reconcile
from engines.tax.comparison import compare, packs


def test_historical_pack_smoke():
    data=TaxInputs(financial_year='2024-25', assessment_year='2025-26', individual=True,
        resident=True, employer_count=1, identity_ref='fictional-H2', age_at_year_end=35,
        sources=[dict(source_id='manual',layout='manual-salary-v1',identity_ref='fictional-H2',
        financial_year='2024-25',salary_paise=120000000,withholding_paise=0)])
    result=compare(data,{**reconcile(data),'confirmed':True,'case_revision':1},revision=1,as_of=date(2026,11,7))
    # Old: (12L-50k): 12500 + 100000 + 45000 = 157500; cess 6300.
    # New: (12L-75k): 20000 + 30000 + 18750 = 68750; cess 2750.
    assert result['regimes']['old']['tax_paise']==16380000
    assert result['regimes']['new']['tax_paise']==7150000
    assert all(p.historical and p.rounding['status']=='unverified_against_act_text' for p in packs().values())

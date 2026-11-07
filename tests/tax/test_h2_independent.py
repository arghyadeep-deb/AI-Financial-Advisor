"""Independent calculation, NOT tax-professional reviewed. Fictional inputs only.

Reference uses hinge functions (changes in marginal rates), unlike engine slabs.
Amounts below are INR constants converted explicitly to paise.
"""
from fractions import Fraction as F
import pytest
from backend.schemas.tax import TaxInputs
from engines.tax.historical import packs, calculate, slab_tax, round_ten


def reference_base(paise, regime, age=35):
    # Old: 5% above exemption; +15% above 5L; +10% above 10L.
    # Super senior: 20% above 5L and +10% above 10L.
    if regime == 'old':
        changes = [(500000,20),(1000000,10)] if age>=80 else [(300000 if age>=60 else 250000,5),(500000,15),(1000000,10)]
    else:
        # New increments 5,5,5,5,10 percentage points -> 0/5/10/15/20/30%.
        changes = [(300000,5),(700000,5),(1000000,5),(1200000,5),(1500000,10)]
    return sum((F(max(0,paise-bound*100)*increment,100) for bound,increment in changes),F(0))


def ref_round(paise):
    # Explicit whole-INR truncation then quotient/remainder in tens (ss288A/B).
    whole_rupees=int(paise/100)
    tens,units=divmod(whole_rupees,10)
    return (tens+(units>=5))*1000


def reference(taxable,regime,age=35):
    t=ref_round(taxable)
    base=reference_base(t,regime,age)
    limit,cap=(50000000,1250000) if regime=='old' else (70000000,2500000)
    after=max(F(0),base-cap) if t<=limit else min(base,F(t-limit)) if regime=='new' else base
    levels=[(5000000,10),(10000000,15),(20000000,25)]
    if regime=='old': levels += [(50000000,37)]
    rate=0; threshold=None; preceding=0
    for bound,new_rate in levels:
        if t>bound*100:
            threshold=bound*100; preceding=rate; rate=new_rate
    nominal=after*F(100+rate,100)
    # At each threshold no relief remains from the preceding threshold, which
    # are many lakhs apart. Ceiling = threshold base*(1+previous rate)+excess.
    combined=nominal if threshold is None else min(nominal,reference_base(threshold,regime,age)*F(100+preceding,100)+t-threshold)
    return dict(base=base,rebate=base-after,relief=nominal-combined,combined=combined,
                cess=combined*F(4,100),total=ref_round(combined*F(104,100)))


def case(salary,age=35,**extra):
    return TaxInputs(financial_year='2024-25',assessment_year='2025-26',individual=True,
        resident=True,employer_count=1,identity_ref='fictional-boundary',age_at_year_end=age,
        sources=[dict(source_id='manual',layout='manual-salary-v1',identity_ref='fictional-boundary',financial_year='2024-25',salary_paise=salary,withholding_paise=0)],**extra)


def run(taxable,regime,age=35):
    p=packs()[regime]
    inp=case(taxable+p.standard_deduction_paise,age)
    return calculate(inp,dict(salary_paise=inp.sources[0].salary_paise,withholding_paise=0),p)


@pytest.mark.parametrize('regime,age,bounds',[
 ('old',35,[250000,500000,1000000]),('old',60,[300000,500000,1000000]),
 ('old',80,[500000,1000000]),('new',35,[300000,700000,1000000,1200000,1500000])])
def test_every_slab_boundary_plus_minus_one_paisa(regime,age,bounds):
    for bound in bounds:
        for delta in [-1,0,1]:
            t=bound*100+delta
            # Exercise rational slab boundary as well as statutory rounded pipeline.
            assert slab_tax(t,packs()[regime],age)[0]==reference_base(t,regime,age)
            got=run(t,regime,age); expected=reference(t,regime,age)
            assert F(got['base_tax_exact_paise'])==expected['base']
            assert got['tax_paise']==expected['total']


@pytest.mark.parametrize('regime,threshold',[('old',500000),('new',700000)])
def test_rebate_thresholds_and_marginal_zone(regime,threshold):
    for delta in [-1001,-1,0,1,499,500,501,1000,100000,2000000,2222200,2222300,2300000,3000000]:
        t=threshold*100+delta
        expected=reference(t,regime); got=run(t,regime)
        assert F(got['rebate_including_marginal_relief_exact_paise'])==expected['rebate']
        assert got['tax_paise']==expected['total']
    # New 7.10L: base 21000; excess 10000 -> 11000 relief; +4% =10400.
    if regime=='new': assert run(71000000,regime)['tax_paise']==1040000
    # Old just over rounded 5L: entire rebate lost (no old 87A marginal relief).
    else: assert run(50001000,regime)['tax_paise']==1300000


@pytest.mark.parametrize('regime',['old','new'])
@pytest.mark.parametrize('threshold',[5000000,10000000,20000000,50000000])
def test_surcharge_thresholds_and_marginal_relief(regime,threshold):
    for delta in [-1,0,1,499,500,1000,100000,10000000,100000000]:
        t=threshold*100+delta
        got=run(t,regime); expected=reference(t,regime)
        for key,ref in [('surcharge_marginal_relief_exact_paise','relief'),('tax_and_surcharge_exact_paise','combined'),('cess_exact_paise','cess')]:
            assert F(got[key])==expected[ref]
        assert got['tax_paise']==expected['total']
    if regime=='old' or threshold!=50000000:
        assert F(run(threshold*100+1000,regime)['surcharge_marginal_relief_exact_paise'])>0
    else:
        assert F(run(threshold*100+1000,regime)['surcharge_marginal_relief_exact_paise'])==0


@pytest.mark.parametrize('regime,cap',[('old',5000000),('new',7500000)])
def test_standard_deduction_capped_at_salary(regime,cap):
    for salary in [0,1,cap-1,cap,cap+1,200000000]:
        got=calculate(case(salary),dict(salary_paise=salary,withholding_paise=0),packs()[regime])
        assert got['standard_deduction_paise']==min(cap,salary)
        assert got['tax_paise']==reference(max(0,salary-cap),regime)['total']


@pytest.mark.parametrize('age,senior_parent,selfcap,parentcap',[(35,False,2500000,2500000),(60,True,5000000,5000000),(80,False,5000000,2500000)])
def test_deduction_caps(age,senior_parent,selfcap,parentcap):
    for delta in [-1,0,1,1000000]:
        claims={'80C':15000000+delta,'80CCD(1B)':5000000+delta,'80D_self':selfcap+delta,'80D_parents':parentcap+delta}
        inp=case(200000000,age,deductions_paise=claims,senior_parent=senior_parent)
        got=calculate(inp,dict(salary_paise=200000000,withholding_paise=0),packs()['old'])
        allowed=sum(min(claims[k],cap) for k,cap in [('80C',15000000),('80CCD(1B)',5000000),('80D_self',selfcap),('80D_parents',parentcap)])
        assert got['chapter_VIA_allowed_paise']==allowed
        assert got['tax_paise']==reference(200000000-5000000-allowed,'old',age)['total']
    inp=case(6000000,age,deductions_paise=claims,senior_parent=senior_parent)
    assert calculate(inp,dict(salary_paise=6000000,withholding_paise=0),packs()['old'])['chapter_VIA_allowed_paise']==1000000


def test_80d_preventive_combined_sublimit_and_spouse_senior():
    inp=case(200000000,deductions_paise={'80D_preventive_self':400000,'80D_preventive_parents':400000},senior_self_or_spouse=True)
    got=calculate(inp,dict(salary_paise=200000000,withholding_paise=0),packs()['old'])
    assert got['deductions_paise']['80D_self']==400000
    assert got['deductions_paise']['80D_parents']==100000
    inp=case(200000000,deductions_paise={'80D_self':6000000},senior_self_or_spouse=True)
    assert calculate(inp,dict(salary_paise=200000000,withholding_paise=0),packs()['old'])['deductions_paise']['80D_self']==5000000


@pytest.mark.parametrize('amount,expected',[(0,0),(1,0),(499,0),(500,1000),(999,1000),(1499,1000),(1500,2000),(F(149999,100),1000)])
def test_rounding_explicit_version(amount,expected):
    assert round_ten(amount)==expected==ref_round(amount)


def test_cess_withholding_balance_and_refund_rounding():
    inp=case(120000000)
    for withholding in [0,7150499,7150500,7151500]:
        got=calculate(inp,dict(salary_paise=120000000,withholding_paise=withholding),packs()['new'])
        # 68750 base +2750 cess =71500; final balance rounded separately.
        assert got['cess_exact_paise']=='275000'
        assert got['balance_payable_paise']==ref_round(max(0,7150000-withholding))
        assert got['refund_paise']==ref_round(max(0,withholding-7150000))


@pytest.mark.parametrize('age',[18,59,60,79,80,100])
def test_regime_comparison_with_age_bands(age):
    from backend.finance.tax import reconcile
    from engines.tax.comparison import compare
    from datetime import date
    inp=case(120000000,age)
    got=compare(inp,{**reconcile(inp),'case_revision':1,'confirmed':True},revision=1,as_of=date(2026,11,7))
    old=reference(115000000,'old',age)['total']; new=reference(112500000,'new',age)['total']
    assert got['difference_old_minus_new_paise']==old-new
    assert got['historical'] and 'HISTORICAL' in got['label']

@pytest.mark.parametrize('changes,reason',[
 ({'financial_year':'2025-26'},'unsupported_period'),({'assessment_year':'2024-25'},'unsupported_period'),
 ({'resident':False},'only_individual_resident_single_employer'),({'individual':False},'only_individual_resident_single_employer'),
 ({'employer_count':2},'only_individual_resident_single_employer'),({'age_at_year_end':None},'adult_age_required'),
 ({'age_at_year_end':17},'adult_age_required'),({'other_income':['interest']},'unsupported_income'),
 ({'other_income':['capital_gains']},'unsupported_income'),({'deductions_claimed':True},'unlisted_deductions'),
 ({'deductions_paise':{'80TTA':100}},'unsupported_deduction'),({'deductions_paise':{'80TTB':100}},'unsupported_deduction'),
 ({'deductions_paise':{'80CCD(2)':100}},'unsupported_deduction'),({'deductions_paise':{'professional_tax':100}},'unsupported_deduction'),
 ({'allowances_paise':{'HRA':100}},'unsupported_allowance_or_exemption'),
 ({'allowances_paise':{'home_loan':100}},'unsupported_allowance_or_exemption'),
 ({'allowances_paise':{'LTC':100}},'unsupported_allowance_or_exemption')])
def test_unsupported_cases_never_guess(changes,reason):
    from backend.finance.tax import reconcile
    from engines.tax.comparison import compare
    from datetime import date
    data=case(120000000).model_dump(); data.update(changes); inp=TaxInputs.model_validate(data)
    got=compare(inp,{**reconcile(inp),'case_revision':1,'confirmed':True},revision=1,as_of=date(2026,11,7))
    assert got['status']=='unsupported' and reason in got['reasons']
    assert got['regimes'] is None or all(r['tax_paise'] is None for r in got['regimes'].values())


def test_new_regime_claims_are_explicitly_ineligible():
    from backend.finance.tax import reconcile
    from engines.tax.comparison import compare
    from datetime import date
    inp=case(120000000,deductions_paise={'80C':15000000})
    got=compare(inp,{**reconcile(inp),'case_revision':1,'confirmed':True},revision=1,as_of=date(2026,11,7))
    assert got['regimes']['old']['tax_paise']==11700000  # 10L taxable: 112500 +4%.
    assert got['regimes']['new']['status']=='unsupported'
    assert got['regimes']['new']['tax_paise'] is None
    assert got['difference_old_minus_new_paise'] is None

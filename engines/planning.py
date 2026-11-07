"""Pure exact-paise goal and debt calculations; no assumed investment returns."""
from datetime import date
from decimal import Decimal, localcontext, ROUND_CEILING, ROUND_HALF_UP
from backend.core.money import check_paise


def goal_requirements(goals, as_of, capacity_paise):
    available = capacity_paise or 0
    result = []
    for goal in sorted(goals, key=lambda g: (g['priority'], g['id'])):
        deadline = date.fromisoformat(goal['target_date'])
        months = max(0, (deadline.year-as_of.year)*12 + deadline.month-as_of.month + (deadline.day > as_of.day))
        target = goal['target_paise']
        with localcontext() as ctx:
            ctx.prec = 40
            if goal['value_basis'] == 'present' and months:
                target = check_paise(int((Decimal(target) * (1 + Decimal(goal['inflation_bps'])/10000) **
                    (Decimal(months)/12)).to_integral_value(rounding=ROUND_CEILING)))
        remaining = max(0, target-goal['allocated_paise'])
        required = (remaining+months-1)//months if months else remaining
        allocated = min(available, required) if months else 0
        available -= allocated
        result.append({'id': goal['id'], 'future_target_paise': target, 'remaining_paise': remaining,
            'months': months, 'required_monthly_paise': required, 'suggested_monthly_paise': allocated,
            'monthly_shortfall_paise': max(0, required-allocated),
            'status': 'funded' if remaining == 0 else 'deadline_passed' if not months else
                      'incomplete_capacity' if capacity_paise is None else 'feasible' if allocated == required else 'shortfall',
            'inflation_bps': goal['inflation_bps'], 'annual_return_bps': 0})
    return {'goals': result, 'unallocated_capacity_paise': available}


def debt_schedule(debts, strategy, extra_paise, max_months):
    """Monthly reducing balance: interest rounded half-up per debt/month.

    Fees accrue before payment; one-off prepayment fee applies when paying above
    minimum. Freed minimum payments remain in the selected scenario's envelope.
    """
    if not debts or any(d['annual_rate_bps'] is None or d['rate_type'] != 'fixed' or d.get('term_months') is None for d in debts):
        return {'status': 'incomplete', 'reason': 'missing_terms_or_floating_rate', 'schedule': []}
    balances = {d['id']: d['principal_paise'] for d in debts}
    fees_paid = set()
    monthly_budget = check_paise(sum(d['minimum_payment_paise'] for d in debts)+extra_paise)
    schedule, total_interest, total_fees = [], 0, 0
    for month in range(1, max_months+1):
        if not any(balances.values()):
            break
        rows = {}
        for d in debts:
            key, principal = d['id'], balances[d['id']]
            if not principal:
                continue
            with localcontext() as ctx:
                ctx.prec = 40
                interest = int((Decimal(principal)*d['annual_rate_bps']/120000).to_integral_value(rounding=ROUND_HALF_UP))
            fee = d['monthly_fee_paise']
            balance = check_paise(principal+interest+fee)
            payment = min(balance, d['minimum_payment_paise'])
            rows[key] = {'id': key, 'opening_paise': principal, 'interest_paise': interest,
                         'fees_paise': fee, 'payment_paise': payment, 'closing_paise': balance-payment}
        remaining = monthly_budget-sum(r['payment_paise'] for r in rows.values())
        ranked = sorted((d for d in debts if d['id'] in rows), key=lambda d:
            (-d['annual_rate_bps'], d['id']) if strategy == 'avalanche' else (balances[d['id']], d['id']))
        for d in ranked:
            row = rows[d['id']]
            fee = d['prepayment_fee_paise'] if d['id'] not in fees_paid else 0
            if remaining > fee and row['closing_paise']:
                extra = min(row['closing_paise'], remaining-fee)
                row['payment_paise'] += extra+fee
                row['fees_paise'] += fee
                row['closing_paise'] -= extra
                remaining -= extra+fee
                fees_paid.add(d['id'])
        for key, row in rows.items():
            balances[key] = row['closing_paise']
            total_interest = check_paise(total_interest+row['interest_paise'])
            total_fees = check_paise(total_fees+row['fees_paise'])
        schedule.append({'month': month, 'debts': list(rows.values())})
        if any(r['closing_paise'] >= r['opening_paise'] and r['closing_paise'] > 0 for r in rows.values()):
            return {'status': 'negative_amortization', 'schedule': schedule,
                    'interest_paise': total_interest, 'fees_paise': total_fees, 'balances_paise': balances}
        if any(month >= d['term_months'] and balances[d['id']] > 0 for d in debts):
            return {'status': 'contractual_term_exceeded', 'schedule': schedule,
                    'interest_paise': total_interest, 'fees_paise': total_fees, 'balances_paise': balances}
    return {'status': 'paid_off' if not any(balances.values()) else 'term_limit',
        'months': len(schedule), 'schedule': schedule, 'interest_paise': total_interest,
        'fees_paise': total_fees, 'balances_paise': balances,
        'convention': 'monthly_reducing_interest_half_up_paise', 'guaranteed': False}

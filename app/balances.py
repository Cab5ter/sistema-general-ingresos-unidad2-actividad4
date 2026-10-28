"""Balances de movimientos activos, días completos UTC y dinero exacto en MXN."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, localcontext
from sqlalchemy import and_, case, func, select
from .finance_models import Account, Transaction
from .service import fail

ZERO = Decimal('0.00')


def period_bounds(from_date: date, to_date: date):
    if from_date > to_date:
        fail('fromDate no puede ser posterior a toDate.')
    try:
        return datetime.combine(from_date, time.min), datetime.combine(to_date + timedelta(days=1), time.min)
    except OverflowError:
        fail('toDate fuera del rango admitido.')


@dataclass
class Balance:
    account_id: int
    account_name: str
    is_active: bool
    opening_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    profit: Decimal
    closing_balance: Decimal
    is_in_red: bool


def calculate(db, company_id, from_date, to_date, account_id=None):
    start, end = period_bounds(from_date, to_date)
    a, t = Account, Transaction
    # SUM(DECIMAL) en MySQL; agregado exacto registrado en db.py para SQLite.
    aggregate = func.sum if db.bind.dialect.name == 'mysql' else func.decimal_sum
    def total(before, kind):
        period = t.transaction_date < start if before else t.transaction_date >= start
        return func.coalesce(aggregate(case((and_(period, t.transaction_type == kind), t.amount))), '0.00')
    query = (select(a.id, a.name, a.is_active, total(True, 'INCOME'), total(True, 'EXPENSE'),
                    total(False, 'INCOME'), total(False, 'EXPENSE'))
             .outerjoin(t, and_(t.account_id == a.id, t.is_active.is_(True), t.transaction_date < end))
             .where(a.company_id == company_id)
             .group_by(a.id, a.name, a.is_active).order_by(a.id))
    if account_id is not None:
        try:
            aid = int(account_id)
            if not 0 < aid <= 2147483647:
                raise ValueError
        except (ValueError, TypeError):
            fail('Cuenta no disponible.', 'NOT_FOUND')
        query = query.where(a.id == aid)
    rows = db.execute(query).all()
    if account_id is not None and not rows:
        fail('Cuenta no disponible.', 'NOT_FOUND')
    result = []
    with localcontext() as ctx:
        ctx.prec = 65  # No restringir los agregados al máximo de una transacción.
        for aid, label, active, opening_in, opening_out, income, expense in rows:
            opening = Decimal(opening_in) - Decimal(opening_out)
            income, expense = Decimal(income), Decimal(expense)
            profit = income - expense
            closing = opening + profit
            result.append(Balance(aid, label, active, opening, income, expense, profit, closing, closing < ZERO))
    return result


def authorized_balances(service, from_date, to_date, account_id=None):
    service.require('accounts.read')
    service.require('transactions.read')
    company_id = service.leer_actor().company_id
    return company_id, calculate(service.db, company_id, from_date, to_date, account_id)

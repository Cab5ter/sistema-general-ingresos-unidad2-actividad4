from datetime import date
from decimal import Decimal, localcontext
import strawberry
from strawberry.types import Info
from .balances import ZERO, authorized_balances
from .schema import execute


@strawberry.type
class AccountBalance:
    account_id: strawberry.ID
    account_name: str
    is_active: bool
    opening_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    profit: Decimal
    closing_balance: Decimal
    is_in_red: bool


def account_result(row):
    return AccountBalance(**{**vars(row), 'account_id': strawberry.ID(str(row.account_id))})


@strawberry.type
class GeneralBalance:
    company_id: strawberry.ID
    currency: str
    from_date: date
    to_date: date
    opening_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    profit: Decimal
    closing_balance: Decimal
    is_in_red: bool
    accounts_in_red: int
    accounts: list[AccountBalance]


@strawberry.type
class BalanceQuery:
    @strawberry.field
    def account_balance(self, info: Info, account_id: strawberry.ID, from_date: date, to_date: date) -> AccountBalance:
        return execute(info, lambda s: account_result(authorized_balances(s, from_date, to_date, account_id)[1][0]))

    @strawberry.field
    def general_balance(self, info: Info, from_date: date, to_date: date) -> GeneralBalance:
        def run(s):
            cid, rows = authorized_balances(s, from_date, to_date)
            with localcontext() as ctx:
                ctx.prec = 65
                opening = sum((r.opening_balance for r in rows), ZERO)
                income = sum((r.total_income for r in rows), ZERO)
                expense = sum((r.total_expense for r in rows), ZERO)
                profit = income - expense
                closing = opening + profit
                return GeneralBalance(company_id=strawberry.ID(str(cid)), currency='MXN', from_date=from_date,
                    to_date=to_date, opening_balance=opening, total_income=income, total_expense=expense,
                    profit=profit, closing_balance=closing, is_in_red=closing < ZERO,
                    accounts_in_red=sum(r.is_in_red for r in rows), accounts=[account_result(r) for r in rows])
        return execute(info, run)

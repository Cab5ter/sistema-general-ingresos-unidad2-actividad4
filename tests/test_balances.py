"""B01-B15: expectativas independientes de la implementación, por HTTP GraphQL."""
from datetime import datetime, timezone
from decimal import Decimal
import time
import jwt
import pytest
from sqlalchemy import select, event
from app import models as m
from app.db import Base
from app.access import RolePermission
from operations import ACCOUNT, CONCEPT, LINK, TX
from test_access import data, make_company, tx_input, count

FIELDS = 'accountId accountName isActive openingBalance totalIncome totalExpense profit closingBalance isInRed'
ONE = 'query($a:ID!,$from:Date!,$to:Date!){accountBalance(accountId:$a,fromDate:$from,toDate:$to){' + FIELDS + '}}'
ALL = 'query($from:Date!,$to:Date!){generalBalance(fromDate:$from,toDate:$to){companyId currency fromDate toDate openingBalance totalIncome totalExpense profit closingBalance isInRed accountsInRed accounts{' + FIELDS + '}}}'
DATES = {'from': '2026-10-26', 'to': '2026-10-30'}


def query(api, data, account=None, **dates):
    variables = {'actor': data['admin'], **DATES, **dates}
    if account is not None:
        variables['a'] = account
    return api.call(ONE if account is not None else ALL, variables)['accountBalance' if account is not None else 'generalBalance']


def capture(api, data, amount, kind='INCOME', when='2026-10-27T12:00:00Z', account=None):
    return api.call(TX, {'actor': data['admin'], 'input': tx_input(data, amount, kind,
                    accountId=account or data['account'], transactionDate=when)})['createTransaction']


def assert_money(row, opening, income, expense, profit, closing, red):
    assert [row[k] for k in ('openingBalance', 'totalIncome', 'totalExpense', 'profit', 'closingBalance', 'isInRed')] == [opening, income, expense, profit, closing, red]


def snapshot(api):
    with api.app.state.sessions() as db:
        return {table.name: [tuple(row) for row in db.execute(select(table).order_by(*table.primary_key.columns))]
                for table in Base.metadata.sorted_tables}


@pytest.fixture
def lab(api, data):
    accounts = {'Caja': data['account']}
    for label in ('Banco', 'Ahorro'):
        aid = api.call(ACCOUNT, {'actor': data['admin'], 'input': {'companyId': data['cid'], 'name': label,
                         'accountType': 'SAVINGS' if label == 'Ahorro' else 'DEBIT'}})['createAccount']['id']
        accounts[label] = aid
        for concept in data['concepts'].values():
            api.call(LINK, {'actor': data['admin'], 'input': {'accountId': aid, 'conceptId': concept}})
    for label, day, kind, amount in [('Banco',25,'INCOME','1000.00'),('Banco',26,'INCOME','3000.00'),
        ('Banco',27,'EXPENSE','1200.00'),('Banco',28,'EXPENSE','1000.00'),('Caja',26,'INCOME','500.00'),
        ('Caja',29,'EXPENSE','700.00')]:
        capture(api, data, amount, kind, f'2026-10-{day}T12:00:00Z', accounts[label])
    return {**data, 'accounts': accounts}


def test_B01_reference_and_no_writes(api, lab):
    before = snapshot(api)
    expected = {'Banco': ('1000.00','3000.00','2200.00','800.00','1800.00',False),
                'Caja': ('0.00','500.00','700.00','-200.00','-200.00',True),
                'Ahorro': ('0.00','0.00','0.00','0.00','0.00',False)}
    for name, aid in lab['accounts'].items():
        assert_money(query(api, lab, aid), *expected[name])
    statements = []
    def track(conn, cursor, statement, parameters, context, many):
        if 'SUM(' in statement.upper():
            statements.append(statement)
    event.listen(api.app.state.engine, 'before_cursor_execute', track)
    try:
        total = query(api, lab)
    finally:
        event.remove(api.app.state.engine, 'before_cursor_execute', track)
    assert len(statements) == 1
    assert_money(total, '1000.00','3500.00','2900.00','600.00','1600.00',False)
    assert total['accountsInRed'] == 1 and total['currency'] == 'MXN'
    assert total['companyId'] == lab['cid'] and total['fromDate'] == DATES['from'] and total['toDate'] == DATES['to']
    assert [int(a['accountId']) for a in total['accounts']] == sorted(map(int, lab['accounts'].values()))
    assert Decimal(total['closingBalance']) == sum(Decimal(a['closingBalance']) for a in total['accounts'])
    assert Decimal(total['profit']) == Decimal(total['totalIncome']) - Decimal(total['totalExpense'])
    assert Decimal(total['closingBalance']) == Decimal(total['openingBalance']) + Decimal(total['profit'])
    assert total['accountsInRed'] == sum(a['isInRed'] for a in total['accounts'])
    assert snapshot(api) == before


def test_B02_single_day_negative_profit(api, lab):
    assert_money(query(api, lab, lab['accounts']['Banco'], **{'from':'2026-10-28','to':'2026-10-28'}),
                 '2800.00','0.00','1000.00','-1000.00','1800.00',False)


def test_B03_empty_company(api):
    cid, admin = make_company(api, 'Sin cuentas', 'empty@example.com')
    result = query(api, {'admin': admin['id']})
    assert_money(result, '0.00','0.00','0.00','0.00','0.00',False)
    assert result['accounts'] == [] and result['accountsInRed'] == 0


def test_B04_utc_boundaries(api, data):
    for when, amount in [('2026-10-25T23:59:59Z','10.00'), ('2026-10-26T00:00:00Z','20.00'),
                         ('2026-10-30T23:59:59Z','30.00'), ('2026-10-30T23:59:59.999999Z','0.01'),
                         ('2026-10-31T00:00:00Z','999.00')]:
        capture(api, data, amount, when=when)
    assert_money(query(api, data, data['account']), '10.00','50.01','0.00','50.01','60.01',False)
    assert_money(query(api, data), '10.00','50.01','0.00','50.01','60.01',False)


def test_B05_operation_date_not_capture_date(api, data):
    row = capture(api, data, '20.00', when='2026-10-27T06:00:00-06:00')
    assert row['transactionDate'] == '2026-10-27T12:00:00Z'
    assert datetime.fromisoformat(row['capturedAt'].replace('Z','+00:00')) > datetime(2026,10,27,12,tzinfo=timezone.utc)
    assert_money(query(api, data, data['account'], **{'from':'2026-10-27','to':'2026-10-27'}),
                 '0.00','20.00','0.00','20.00','20.00',False)


def test_B06_exact_cents(api, data):
    for amount, kind in [('0.10','INCOME'),('0.20','INCOME'),('0.30','EXPENSE')]:
        capture(api, data, amount, kind)
    assert_money(query(api, data, data['account']), '0.00','0.30','0.30','0.00','0.00',False)


def test_B07_inactive_transaction(api, lab):
    aid = lab['accounts']['Banco']
    with api.app.state.sessions.begin() as db:
        row = db.scalar(select(m.Transaction).where(m.Transaction.account_id==int(aid), m.Transaction.amount==Decimal('1000.00'), m.Transaction.transaction_type=='EXPENSE'))
        row.is_active = False
    assert_money(query(api, lab, aid), '1000.00','3000.00','1200.00','1800.00','2800.00',False)
    assert count(api, m.Transaction) == 6


def test_B08_inactive_account_and_related_history(api, lab):
    before = query(api, lab)
    aid = lab['accounts']['Banco']
    with api.app.state.sessions.begin() as db:
        db.get(m.Account, int(aid)).is_active = False
        db.get(m.Concept, int(lab['concepts']['INCOME'])).is_active = False
        for link in db.scalars(select(m.AccountConcept).where(m.AccountConcept.account_id==int(aid))):
            link.is_active = False
    after = query(api, lab)
    assert after['closingBalance'] == before['closingBalance']
    assert not next(a for a in after['accounts'] if a['accountId']==aid)['isActive']
    assert_money(query(api, lab, aid), '1000.00','3000.00','2200.00','800.00','1800.00',False)
    capture_input = tx_input(lab, accountId=aid)
    api.call(TX, {'actor':lab['admin'],'input':capture_input}, code='BAD_INPUT')
    assert count(api,m.Transaction)==6


def test_B09_extra_concept_does_not_duplicate(api, lab):
    before = query(api, lab)
    concept = api.call(CONCEPT, {'actor':lab['admin'],'input':{'companyId':lab['cid'],'name':'Extra','conceptType':'INCOME'}})['createConcept']['id']
    api.call(LINK, {'actor':lab['admin'],'input':{'accountId':lab['accounts']['Banco'],'conceptId':concept}})
    assert query(api, lab) == before


def test_B10_invalid_dates(api, data):
    before = snapshot(api)
    for operation in (ONE, ALL):
        for dates, code in [({'from':'2026-10-31','to':'2026-10-26'},'BAD_INPUT'),
                            ({'from':'2026-02-30','to':'2026-10-30'},'GRAPHQL_VALIDATION'),
                            ({'from':'2026-10-26','to':'9999-12-31'},'BAD_INPUT')]:
            api.call(operation, {'actor':data['admin'],'a':data['account'],**dates}, code=code)
    assert snapshot(api) == before


def test_B11_invalid_tokens_both_queries(api, data):
    token = api.tokens[data['admin']]
    header, payload, sig = token.split('.')
    altered = '.'.join([header,payload,('A' if sig[0]!='A' else 'B')+sig[1:]])
    expired = jwt.encode({'companyUserId':int(data['admin']),'companyId':int(data['cid']),'exp':int(time.time())-60}, api.settings.jwt_secret, algorithm='HS256')
    for headers in ({}, {'Authorization':'Bearer '+altered}, {'Authorization':'Bearer '+expired}):
        for operation in (ONE, ALL):
            api.call(operation, {'a':data['account'],**DATES}, headers, 'UNAUTHENTICATED')


def test_B12_company_isolation_same_unavailable_error(api, lab):
    cid, admin = make_company(api, 'Empresa B', 'other@example.com')
    other = api.call(ACCOUNT, {'actor':admin['id'],'input':{'companyId':cid,'name':'Secreto B','accountType':'CASH'}})['createAccount']['id']
    errors = []
    for aid in (other, '999999'):
        response = api.request(ONE, {'actor':lab['admin'],'a':aid,**DATES}).json()
        assert response['data'] is None
        errors.append(response['errors'])
    assert errors[0] == errors[1]
    assert errors[0][0]['message'] == 'Cuenta no disponible.'
    total = query(api, lab)
    assert total['companyId'] == lab['cid'] and total['closingBalance'] == '1600.00'
    assert {a['accountId'] for a in total['accounts']} == set(lab['accounts'].values())
    assert 'Secreto B' not in str(errors)


def test_B13_read_only_role(api, lab):
    reader = {**lab, 'admin':lab['members']['CONSULTA']}
    assert query(api, reader)['closingBalance'] == '1600.00'
    assert query(api, reader, lab['accounts']['Banco'])['closingBalance'] == '1800.00'
    before = snapshot(api)
    api.call(TX, {'actor':reader['admin'],'input':tx_input(lab)}, code='FORBIDDEN')
    assert snapshot(api) == before


def test_B14_live_permission_revocation(api, lab):
    reader = {**lab, 'admin':lab['members']['CONSULTA']}
    headers = api.headers_for(reader['admin'])
    assert query(api, reader)['closingBalance']=='1600.00'
    with api.app.state.sessions.begin() as db:
        link = db.scalar(select(RolePermission).where(RolePermission.role_id==int(lab['roles']['CONSULTA']),
            RolePermission.permission_id==int(lab['permissions']['transactions.read'])))
        key = link.id
        link.is_active = False
    try:
        for operation in (ONE, ALL):
            api.call(operation, {'a':lab['accounts']['Banco'],**DATES}, headers, 'FORBIDDEN')
    finally:
        with api.app.state.sessions.begin() as db:
            db.get(RolePermission,key).is_active = True
    assert api.call(ALL, DATES, headers)['generalBalance']['closingBalance']=='1600.00'


def test_B15_expense_can_overdraw(api, data):
    capture(api, data, '50.00', 'EXPENSE')
    assert count(api,m.Transaction)==1
    for result in (query(api,data,data['account']),query(api,data)):
        assert_money(result,'0.00','0.00','50.00','-50.00','-50.00',True)
    assert query(api,data)['accountsInRed']==1


@pytest.mark.parametrize('amount', ['0.001','1.239','10000000000.00','1e100'])
def test_reject_excess_precision_and_transaction_overflow(api,data,amount):
    before = count(api,m.Transaction)
    api.call(TX,{'actor':data['admin'],'input':tx_input(data,amount)},code='BAD_INPUT')
    assert count(api,m.Transaction)==before


def test_aggregate_can_exceed_single_transaction_limit(api,data):
    capture(api,data,'9999999999.99')
    capture(api,data,'9999999999.99')
    assert query(api,data)['closingBalance']=='19999999999.98'


def test_invalid_operation_date_cannot_insert(api,data):
    for value in ('2026-02-30T12:00:00Z','2026-10-27T12:00:00'):
        api.call(TX,{'actor':data['admin'],'input':tx_input(data,transactionDate=value)},code='GRAPHQL_VALIDATION')
    assert count(api,m.Transaction)==0

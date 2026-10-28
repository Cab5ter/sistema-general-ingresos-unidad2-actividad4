from decimal import Decimal
import pytest
from sqlalchemy import inspect, text
from app.migrate_activity7 import migrate
from app import models as m
from test_access import data
from test_balances import capture, query


def test_mysql_migration_preserves_history_and_is_idempotent(api, data):
    if api.app.state.engine.dialect.name != 'mysql':
        pytest.skip('Conversión de columna específica de MySQL')
    capture(api,data,'10.20')
    with api.app.state.engine.begin() as db:
        db.execute(text('ALTER TABLE transactions MODIFY amount TEXT NOT NULL'))
    migrate(api.app.state.engine)
    migrate(api.app.state.engine)
    with api.app.state.engine.connect() as db:
        assert db.scalar(text('SELECT amount FROM transactions')) == Decimal('10.20')
    assert query(api,data)['closingBalance']=='10.20'
    assert str(next(c['type'] for c in inspect(api.app.state.engine).get_columns('transactions') if c['name']=='amount'))=='DECIMAL(12, 2)'


def test_mysql_migration_rejects_extra_cents_without_rounding(api,data):
    if api.app.state.engine.dialect.name != 'mysql':
        pytest.skip('Conversión de columna específica de MySQL')
    capture(api,data,'10.20')
    with api.app.state.engine.begin() as db:
        db.execute(text('ALTER TABLE transactions MODIFY amount TEXT NOT NULL'))
        db.execute(text("UPDATE transactions SET amount='10.201'"))
    with pytest.raises(RuntimeError,match='cancelada sin alterar datos'):
        migrate(api.app.state.engine)
    with api.app.state.engine.connect() as db:
        assert db.scalar(text('SELECT amount FROM transactions'))=='10.201'


def test_inactive_capturer_does_not_erase_history(api,data):
    from operations import TX
    from test_access import tx_input
    api.call(TX,{'actor':data['members']['CAPTURISTA'],'input':tx_input(data,'10.00',transactionDate='2026-10-27T12:00:00Z')})
    with api.app.state.sessions.begin() as db:
        db.get(m.CompanyUser,int(data['members']['CAPTURISTA'])).is_active=False
    assert query(api,data)['closingBalance']=='10.00'

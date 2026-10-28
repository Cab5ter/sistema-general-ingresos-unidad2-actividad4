"""Conversión validada de TEXT heredado a DECIMAL(12,2); ejecutar sin escritores."""
from decimal import Decimal, InvalidOperation
from sqlalchemy import inspect, text
from .config import Settings
from .db import database


def verify_storage(engine):
    if engine.dialect.name == 'mysql':
        column = next(c for c in inspect(engine).get_columns('transactions') if c['name']=='amount')
        if str(column['type']) != 'DECIMAL(12, 2)':
            raise RuntimeError('Ejecuta python -m app.migrate_activity7 antes de iniciar: amount debe ser DECIMAL(12,2).')


def migrate(engine):
    if engine.dialect.name != 'mysql':
        raise RuntimeError('Esta migración corresponde a MySQL; SQLite conserva TEXT exacto para pruebas.')
    with engine.connect() as connection:
        columns = {c['name']: c for c in inspect(connection).get_columns('transactions')}
        amount_type = columns['amount']['type']
        invalid = []
        for key, value in connection.execute(text('SELECT id, amount FROM transactions ORDER BY id')):
            try:
                amount = Decimal(str(value))
                if not amount.is_finite() or not 0 < amount <= Decimal('9999999999.99') or amount != amount.quantize(Decimal('0.01')):
                    invalid.append(key)
            except (InvalidOperation, ValueError):
                invalid.append(key)
        if invalid:
            raise RuntimeError(f'Migración cancelada sin alterar datos: importes incompatibles en IDs {invalid}. No se redondean históricos.')
        if not (str(amount_type) == 'DECIMAL(12, 2)'):
            connection.execute(text('ALTER TABLE transactions MODIFY amount DECIMAL(12,2) NOT NULL'))
        indexes = {i['name'] for i in inspect(connection).get_indexes('transactions')}
        if 'ix_transactions_account_active_date' not in indexes:
            connection.execute(text('CREATE INDEX ix_transactions_account_active_date ON transactions(account_id, is_active, transaction_date)'))
        connection.commit()


if __name__ == '__main__':
    engine, _ = database(Settings.from_env().database_url)
    try:
        migrate(engine)
        print('Migración validada; importes históricos conservados e índice preparado.')
    finally:
        engine.dispose()

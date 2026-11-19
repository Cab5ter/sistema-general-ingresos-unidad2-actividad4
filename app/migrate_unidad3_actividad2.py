"""Migración no destructiva: agrega tabla de idempotencia a la base existente."""
from .config import Settings
from .db import database, Base
from . import models as m


if __name__ == '__main__':
    engine, _ = database(Settings.from_env().database_url)
    try:
        Base.metadata.create_all(engine, tables=[m.IdempotencyKey.__table__])
        print('Tabla idempotency_keys lista. No se modificaron movimientos anteriores.')
    finally:
        engine.dispose()

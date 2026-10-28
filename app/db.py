from sqlalchemy import create_engine, event, Text, text, DateTime
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import DeclarativeBase, sessionmaker

Timestamp = DateTime().with_variant(DATETIME(fsp=6), 'mysql')


class Base(DeclarativeBase):
    type_annotation_map = {str: Text()}


def database(url):
    sqlite = url.startswith('sqlite:')
    engine = create_engine(url, pool_pre_ping=True,
                           connect_args={'check_same_thread': False, 'timeout': 30} if sqlite else {})

    @event.listens_for(engine, 'connect')
    def configure(connection, _):
        if sqlite:
            connection.execute('PRAGMA foreign_keys=ON')
            # El fallback de pruebas conserva precisión: SUM nativo de SQLite
            # convertiría el TEXT monetario a float. MySQL usa SUM de DECIMAL.
            from decimal import Decimal, localcontext
            class DecimalSum:
                def __init__(self):
                    self.total = Decimal('0.00')
                def step(self, value):
                    if value is not None:
                        with localcontext() as ctx:
                            ctx.prec = 65
                            self.total += Decimal(value)
                def finalize(self):
                    return str(self.total)
            connection.create_aggregate('decimal_sum', 1, DecimalSum)

    return engine, sessionmaker(engine, expire_on_commit=False)


def lock_operation(session):
    """Serializa autorización y cambios; evita revocaciones entre check y commit."""
    if session.bind.dialect.name == 'sqlite':
        session.execute(text('BEGIN IMMEDIATE'))
    else:
        # Un orden común evita inversiones de bloqueos entre distintas operaciones.
        session.execute(text('SELECT id FROM roles ORDER BY id FOR UPDATE')).all()

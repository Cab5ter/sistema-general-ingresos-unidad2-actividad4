"""Unidad III: evidencia de no duplicación, conflicto y COMMIT atómico."""
from uuid import uuid4
from sqlalchemy import select, func
from app import models as m
from operations import TX
from test_access import data, tx_input


def rows(api, model):
    with api.app.state.sessions() as session:
        return session.scalar(select(func.count()).select_from(model))


def test_reintentos_misma_llave_mismo_movimiento(api, data):
    actor = data['members']['CAPTURISTA']
    key = str(uuid4())
    value = tx_input(data, '100.00', 'INCOME', idempotencyKey=key)
    first = api.call(TX, {'actor': actor, 'input': value})['createTransaction']
    second = api.call(TX, {'actor': actor, 'input': value})['createTransaction']
    assert first['id'] == second['id']
    assert rows(api, m.Transaction) == rows(api, m.IdempotencyKey) == 1
    third = api.call(TX, {'actor': actor, 'input': tx_input(
        data, '100.00', 'INCOME', idempotencyKey=str(uuid4()))})['createTransaction']
    assert third['id'] != first['id']
    assert rows(api, m.Transaction) == rows(api, m.IdempotencyKey) == 2
    api.call(TX, {'actor': actor, 'input': tx_input(
        data, '200.00', 'INCOME', idempotencyKey=key)}, code='CONFLICT')
    assert rows(api, m.Transaction) == rows(api, m.IdempotencyKey) == 2


def test_llave_invalida_y_rollback(api, data):
    actor = data['members']['CAPTURISTA']
    api.call(TX, {'actor': actor, 'input': tx_input(
        data, '100.00', 'INCOME', idempotencyKey='no-uuid')}, code='BAD_INPUT')
    key = str(uuid4())
    api.call(TX, {'actor': actor, 'input': tx_input(
        data, '0', 'INCOME', idempotencyKey=key)}, code='BAD_INPUT')
    assert rows(api, m.Transaction) == rows(api, m.IdempotencyKey) == 0

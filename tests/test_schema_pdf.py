from pathlib import Path
from graphql import build_schema, print_schema, lexicographic_sort_schema
from app.schema import schema


def test_complete_contract_including_activity7():
    expected=build_schema('\n'.join(Path('tests',p).read_text(encoding='utf-8-sig') for p in ('schema_pdf.graphql','finance_pdf.graphql','access_pdf.graphql','permission_sets_pdf.graphql','balances_pdf.graphql')))
    actual=build_schema(schema.as_str())
    # Los contratos de parciales anteriores se conservan; la Unidad III agrega
    # campos sin eliminar ni cambiar las operaciones previas.
    assert 'idempotencyKey' in actual.type_map['CreateTransactionInput'].fields
    assert 'viewer' in actual.query_type.fields
    assert 'role' in actual.type_map['CompanyUser'].fields
    actual.query_type.fields.pop('viewer')
    actual.type_map['CreateTransactionInput'].fields.pop('idempotencyKey')
    actual.type_map['CompanyUser'].fields.pop('role')
    actual.type_map.pop('Viewer')
    for kind in (actual.query_type, actual.mutation_type):
        assert all('actorCompanyUserId' not in field.args for field in kind.fields.values())
    for contract in (expected,actual):
        for kind in contract.type_map.values():
            kind.description=None
            for field in getattr(kind,'fields',{}).values():
                field.description=None
    assert print_schema(lexicographic_sort_schema(actual))==print_schema(lexicographic_sort_schema(expected))
    # Regenerar el contrato con python -m app.export_schema antes de entregar.
    exported=build_schema(Path('schema.graphql').read_text(encoding='utf-8'))
    assert 'idempotencyKey' in exported.type_map['CreateTransactionInput'].fields
    assert 'viewer' in exported.query_type.fields
    assert 'role' in exported.type_map['CompanyUser'].fields

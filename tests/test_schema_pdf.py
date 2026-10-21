from pathlib import Path
from graphql import build_schema, print_schema, lexicographic_sort_schema
from app.schema import schema


def test_complete_contract_including_activity6():
    expected=build_schema('\n'.join(Path('tests',p).read_text(encoding='utf-8-sig') for p in ('schema_pdf.graphql','finance_pdf.graphql','access_pdf.graphql','permission_sets_pdf.graphql')))
    actual=build_schema(schema.as_str())
    for kind in (actual.query_type, actual.mutation_type):
        assert all('actorCompanyUserId' not in field.args for field in kind.fields.values())
    for contract in (expected,actual):
        for kind in contract.type_map.values():
            kind.description=None
            for field in getattr(kind,'fields',{}).values():
                field.description=None
    assert print_schema(lexicographic_sort_schema(actual))==print_schema(lexicographic_sort_schema(expected))
    assert Path('schema.graphql').read_text(encoding='utf-8').strip()==schema.as_str().strip()

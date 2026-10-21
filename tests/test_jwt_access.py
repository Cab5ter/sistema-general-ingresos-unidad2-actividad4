"""Actividad 6: identidad del JWT, nueve casos y rechazos sin escrituras."""
import secrets
import time
import jwt
import pytest
from app import models as m
from operations import ACCOUNT, ACCOUNTS, TX, ASSIGN_ROLE, LOGIN
from test_access import data, count, tx_input, make_company, PASSWORD


def account_input(data, name):
    return {'companyId': data['cid'], 'accountType': 'CASH', 'name': name}


def test_login_claims_signature_expiry_and_wrong_credentials(api, data):
    before = int(time.time())
    result = api.call(LOGIN, {'input': {'email': 'admin@example.com', 'password': PASSWORD}})['login']
    assert result['tokenType'] == 'Bearer'
    payload = jwt.decode(result['token'], api.settings.jwt_secret, algorithms=['HS256'])
    assert set(payload) == {'companyUserId', 'companyId', 'exp'}
    assert payload['companyUserId'] == int(data['admin'])
    assert payload['companyId'] == int(data['cid'])
    assert before + 1800 <= payload['exp'] <= int(time.time()) + 1800
    assert jwt.get_unverified_header(result['token'])['alg'] == 'HS256'
    assert set(result['user']) == {'id', 'email'}
    assert api.settings.jwt_secret not in result['token']
    for credentials in ({'email': 'nadie@example.com', 'password': PASSWORD},
                        {'email': 'admin@example.com', 'password': 'incorrecta'}):
        response = api.request(LOGIN, {'input': credentials}).json()
        assert response.get('errors') and not response.get('data')
        assert 'token' not in str(response)
    # El input no admite que el cliente elija la empresa que firmará login.
    api.call(LOGIN, {'input': {'email': 'admin@example.com', 'password': PASSWORD, 'companyId': '999'}}, code='GRAPHQL_VALIDATION')


def test_nine_pdf_cases_with_same_pedro_token(api, data):
    maria = api.headers_for(data['members']['CAPTURISTA'])
    luis = api.headers_for(data['members']['CONTADOR'])
    pedro = api.headers_for(data['members']['CONSULTA'])
    ana = api.headers_for(data['admin'])
    before = count(api, m.Account)
    # 1: sin encabezado no se inserta cuenta.
    api.call(ACCOUNT, {'input': account_input(data, 'Caso 1')}, code='UNAUTHENTICATED')
    assert count(api, m.Account) == before
    # 2 y 3: una misma persona puede capturar y no crear cuentas.
    api.call(TX, {'input': tx_input(data)}, maria)
    api.call(ACCOUNT, {'input': account_input(data, 'Caso 3')}, maria, 'FORBIDDEN')
    assert count(api, m.Account) == before
    # 4: Luis sí crea la cuenta.
    api.call(ACCOUNT, {'input': account_input(data, 'Caso 4')}, luis)
    assert count(api, m.Account) == before + 1
    # 5, 6 y 7: Pedro reutiliza exactamente el token emitido antes del cambio.
    movements = count(api, m.Transaction)
    api.call(TX, {'input': tx_input(data)}, pedro, 'FORBIDDEN')
    assert count(api, m.Transaction) == movements
    api.call(ASSIGN_ROLE, {'input': {'companyUserId': data['members']['CONSULTA'],
             'roleId': data['roles']['CAPTURISTA']}}, ana)
    result = api.call(TX, {'input': tx_input(data)}, pedro)['createTransaction']
    assert count(api, m.Transaction) == movements + 1
    with api.app.state.sessions() as db:
        assert result['capturedBy'] == str(db.get(m.CompanyUser, int(data['members']['CONSULTA'])).user_id)
    # 8: el token de otra empresa no puede leer estas cuentas.
    _, other = make_company(api, 'Otra empresa', 'otro@example.com')
    api.call(ACCOUNTS, {'id': data['cid']}, api.headers_for(other['id']), 'FORBIDDEN')
    # 9: firma alterada y expiración real; se comprueba el conteo en ambos casos.
    valid = ana['Authorization'].split()[1]
    header, payload, signature = valid.split('.')
    altered = '.'.join((header, payload, ('A' if signature[0] != 'A' else 'B') + signature[1:]))
    expired = jwt.encode({'companyUserId': int(data['admin']), 'companyId': int(data['cid']),
                          'exp': int(time.time()) - 60}, api.settings.jwt_secret, algorithm='HS256')
    before = count(api, m.Account)
    for token in (altered, expired):
        api.call(ACCOUNT, {'input': account_input(data, 'Caso 9')},
                 {'Authorization': 'Bearer ' + token}, 'UNAUTHENTICATED')
        assert count(api, m.Account) == before


@pytest.mark.parametrize('variant', ['missing_member', 'missing_company', 'missing_exp', 'wrong_company',
    'unknown_member', 'boolean_member', 'string_company', 'invalid_exp', 'hs384', 'unsigned', 'wrong_secret'])
def test_invalid_tokens_never_write(api, data, variant):
    payload = {'companyUserId': int(data['admin']), 'companyId': int(data['cid']), 'exp': int(time.time()) + 1800}
    algorithm, key = 'HS256', api.settings.jwt_secret
    if variant.startswith('missing_'):
        payload.pop({'missing_member': 'companyUserId', 'missing_company': 'companyId', 'missing_exp': 'exp'}[variant])
    elif variant == 'wrong_company': payload['companyId'] += 100
    elif variant == 'unknown_member': payload['companyUserId'] = 999999
    elif variant == 'boolean_member': payload['companyUserId'] = True
    elif variant == 'string_company': payload['companyId'] = str(payload['companyId'])
    elif variant == 'invalid_exp': payload['exp'] = 'mañana'
    elif variant == 'hs384': algorithm = 'HS384'
    elif variant == 'unsigned': algorithm, key = 'none', ''
    elif variant == 'wrong_secret': key = secrets.token_urlsafe(48)
    token = jwt.encode(payload, key, algorithm=algorithm)
    before = count(api, m.Account)
    api.call(ACCOUNT, {'input': account_input(data, variant)}, {'Authorization': 'Bearer ' + token}, 'UNAUTHENTICATED')
    assert count(api, m.Account) == before


@pytest.mark.parametrize('authorization', ['', 'Bearer', 'Basic abc', 'Bearer uno dos', 'Bearer no-es-jwt'])
def test_missing_or_malformed_header_never_writes(api, data, authorization):
    before = count(api, m.Account)
    api.call(ACCOUNT, {'input': account_input(data, 'Sin identidad')},
             {'Authorization': authorization}, 'UNAUTHENTICATED')
    assert count(api, m.Account) == before


def test_client_cannot_impersonate_another_member(api, data):
    headers = api.headers_for(data['members']['CAPTURISTA'])
    before = count(api, m.Account)
    # El argumento antiguo se rechaza por validación antes de ejecutar el resolver.
    query = 'mutation($i:CreateAccountInput!){createAccount(actorCompanyUserId:"' + data['admin'] + '",input:$i){id}}'
    api.call(query, {'i': account_input(data, 'Suplantación')}, headers, 'GRAPHQL_VALIDATION')
    # Un ID extra en variables tampoco sustituye la identidad del Bearer.
    result = api.client.post('/graphql', json={'query': ACCOUNT, 'variables': {
        'input': account_input(data, 'Variable extra'), 'actor': data['admin']}}, headers=headers).json()
    assert result['errors'][0]['extensions']['code'] == 'FORBIDDEN'
    assert count(api, m.Account) == before

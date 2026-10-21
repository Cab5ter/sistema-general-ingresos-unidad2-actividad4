"""Ejecuta los casos del PDF por HTTP y guarda un registro sin secretos fuera de Git.

Preparación deliberada del laboratorio: app.demo_activity4 deja a Pedro en CONSULTA.
Los tokens solo viven en memoria. Las capturas muestran el registro real HTTP/SQL,
con Authorization visible y su valor sensible oculto.
"""
import html
import json
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx
import jwt
from sqlalchemy import text
from app.config import Settings
from app.db import database
from app.demo_activity4 import prepare

LOGIN = 'mutation Entrar($input:LoginInput!){login(input:$input){tokenType token user{name}}}'
ACCOUNT = '''mutation Cuenta($input:CreateAccountInput!){
  createAccount(input:$input){id companyId name}
}'''
MOVEMENT = '''mutation Movimiento($input:CreateTransactionInput!){
  createTransaction(input:$input){id amount capturedBy}
}'''
ROLE = '''mutation CambiarPuesto($input:AssignRoleInput!){
  assignRole(input:$input){isActive role{code} companyUser{id}}
}'''
ACCOUNTS = 'query Cuentas($company:ID!){accounts(companyId:$company){id name}}'


def sanitize(value):
    if isinstance(value, dict):
        return {k: '[oculto]' if k in ('token', 'password', 'passwordHash') else sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    return value


def main():
    output = Path(os.getenv('EVIDENCE_DIR', 'entrega/evidencias-actividad6')).resolve()
    output.mkdir(parents=True, exist_ok=True)
    settings = Settings.from_env()
    url = os.getenv('ACTIVITY4_URL', 'http://127.0.0.1:8007/graphql')
    ids = prepare()
    passwords = json.loads(Path('.activity4-credentials.json').read_text(encoding='utf-8'))
    engine, _ = database(settings.database_url)
    records, tokens = [], {}
    run = 'A6-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S') + '-' + secrets.token_hex(2)
    with engine.connect() as db:
        version = db.scalar(text('SELECT VERSION()')) if engine.dialect.name == 'mysql' else 'SQLite'
    backend = engine.dialect.name

    def sql_state(table, marker):
        assert table in ('accounts', 'transactions')
        field = 'name' if table == 'accounts' else 'short_description'
        query = f'SELECT COUNT(*) AS filas_de_prueba FROM {table} WHERE {field} = :marca'
        with engine.connect() as db:
            return {'backend': backend, 'version': version, 'sql': query, 'marca': marker,
                    'filas_de_prueba': db.scalar(text(query), {'marca': marker}),
                    'total_tabla': db.scalar(text(f'SELECT COUNT(*) FROM {table}'))}

    with httpx.Client(timeout=30) as client:
        def request(query, variables, token=None, bootstrap=False):
            headers = {'Authorization': 'Bearer ' + token} if token else {}
            if bootstrap:
                headers['X-Bootstrap-Key'] = settings.bootstrap_key
            response = client.post(url, json={'query': query, 'variables': variables}, headers=headers)
            response.raise_for_status()
            return response.status_code, response.json()

        def capture(name, rule, query, variables, person=None, expected=None, table=None, marker=None, token=None):
            token = token if token is not None else tokens.get(person)
            before = sql_state(table, marker) if table else None
            status, result = request(query, variables, token)
            if expected:
                assert result['errors'][0]['extensions']['code'] == expected, name
            else:
                assert 'errors' not in result, (name, sanitize(result))
            after = sql_state(table, marker) if table else None
            if table:
                assert after['total_tabla'] == before['total_tabla'] + (0 if expected else 1), name
                assert after['filas_de_prueba'] == (0 if expected else 1), name
            row = {'name': name, 'regla': rule, 'fechaUTC': datetime.now(timezone.utc).isoformat(),
                   'url': url, 'method': 'POST', 'headers': {'Content-Type': 'application/json'},
                   'query': query, 'variables': sanitize(variables), 'http': status,
                   'result': sanitize(result), 'estado': 'PASS'}
            if token:
                row['headers']['Authorization'] = f'Bearer [token de {person or "prueba"}; firma oculta]'
            if before:
                row['sql_antes'], row['sql_despues'] = before, after
            records.append(row)
            return result

        for person, slug in [('Ana','ana'),('Luis','luis'),('María','maria'),('José','jose'),('Pedro','pedro')]:
            variables = {'input': {'email': slug + '.actividad4@example.com', 'password': passwords[person]}}
            _, result = request(LOGIN, variables)
            assert 'errors' not in result, sanitize(result)
            tokens[person] = result['data']['login']['token']
            if person == 'Ana':
                payload = jwt.decode(tokens[person], settings.jwt_secret, algorithms=['HS256'])
                assert set(payload) == {'companyUserId','companyId','exp'}
                records.append({'name':'00-login-correcto', 'regla':'Login comprueba el hash y firma HS256 por 30 minutos.',
                    'fechaUTC':datetime.now(timezone.utc).isoformat(), 'url':url, 'method':'POST',
                    'headers':{'Content-Type':'application/json'}, 'query':LOGIN, 'variables':sanitize(variables),
                    'http':200, 'result':sanitize(result), 'jwt_payload':payload,
                    'jwt_alg':'HS256', 'estado':'PASS'})
        capture('00-login-rechazado', 'Una contraseña incorrecta no entrega un token.', LOGIN,
                {'input':{'email':'ana.actividad4@example.com','password':'incorrecta'}}, expected='UNAUTHENTICATED')

        def account(marker):
            return {'input':{'companyId':ids['companyId'],'accountType':'CASH','name':marker}}

        def movement(marker):
            return {'input':{'accountId':ids['accountId'],'conceptId':ids['conceptId'],
                             'transactionType':'INCOME','amount':'13.37','shortDescription':marker}}

        marker = run + '-01'
        capture('01-sin-token', 'Sin Authorization la API rechaza la escritura y no crea la fila.', ACCOUNT,
                account(marker), expected='UNAUTHENTICATED', table='accounts', marker=marker)
        marker = run + '-02'
        capture('02-maria-movimiento', 'María CAPTURISTA registra un movimiento con su token.', MOVEMENT,
                movement(marker), 'María', table='transactions', marker=marker)
        marker = run + '-03'
        capture('03-maria-cuenta-rechazada', 'El token identifica a María; su rol carece de accounts.write.', ACCOUNT,
                account(marker), 'María', 'FORBIDDEN', 'accounts', marker)
        marker = run + '-04'
        capture('04-luis-cuenta', 'La misma ruta permite crear una cuenta a Luis CONTADOR.', ACCOUNT,
                account(marker), 'Luis', table='accounts', marker=marker)
        marker = run + '-05'
        pedro_token = tokens['Pedro']
        capture('05-pedro-consulta', 'Pedro CONSULTA no tiene transactions.write; no se inserta la fila.', MOVEMENT,
                movement(marker), 'Pedro', 'FORBIDDEN', 'transactions', marker)
        capture('06-ana-cambia-pedro', 'Ana cambia a Pedro a CAPTURISTA usando roles.write.', ROLE,
                {'input':{'companyUserId':ids['actors']['Pedro'],'roleId':ids['roles']['CAPTURISTA']}}, 'Ana')
        with engine.connect() as db:
            query = '''SELECT r.code, cur.is_active FROM company_user_roles cur
JOIN roles r ON r.id=cur.role_id WHERE cur.company_user_id=:pedro ORDER BY cur.id'''
            roles = [dict(row) for row in db.execute(text(query), {'pedro':ids['actors']['Pedro']}).mappings()]
        assert [row['code'] for row in roles if row['is_active']] == ['CAPTURISTA']
        records[-1]['sql_roles'] = {'sql':query,'pedro':ids['actors']['Pedro'],'filas':roles}
        marker = run + '-07'
        assert tokens['Pedro'] == pedro_token
        capture('07-pedro-mismo-token', 'El mismo token de Pedro del caso 5 permite capturar: el rol se leyó de nuevo en la BD.',
                MOVEMENT, movement(marker), 'Pedro', table='transactions', marker=marker, token=pedro_token)
        records[-1]['mismo_token_del_caso_5'] = True
        # Otra empresa de laboratorio; su contraseña privada tampoco se exporta.
        private = Path('.activity6-other-credentials.json')
        if private.exists():
            other = json.loads(private.read_text(encoding='utf-8'))
        else:
            other = {'email':'otra.empresa.actividad6@example.com','password':secrets.token_urlsafe(24)}
            _, result = request('mutation{createCompany(input:{name:"Otra empresa Actividad 6"}){id}}', {}, bootstrap=True)
            cid = result['data']['createCompany']['id']
            _, result = request('mutation($i:CreateCompanyAdminInput!){createCompanyAdmin(input:$i){id}}',
                {'i':{'companyId':cid,'name':'Otra empresa',**other}}, bootstrap=True)
            assert 'errors' not in result, sanitize(result)
            private.write_text(json.dumps(other), encoding='utf-8')
        _, result = request(LOGIN, {'input':other})
        assert 'errors' not in result, sanitize(result)
        tokens['Otra empresa'] = result['data']['login']['token']
        capture('08-otra-empresa', 'Un token de otra empresa no puede consultar las cuentas de esta empresa.', ACCOUNTS,
                {'company':ids['companyId']}, 'Otra empresa', 'FORBIDDEN')
        header, payload, signature = tokens['Ana'].split('.')
        altered = '.'.join((header,payload,('A' if signature[0] != 'A' else 'B') + signature[1:]))
        expired = jwt.encode({'companyUserId':int(ids['actors']['Ana']),'companyId':int(ids['companyId']),
            'exp':int(time.time())-60}, settings.jwt_secret, algorithm='HS256')
        for suffix, token in [('alterado',altered),('vencido',expired)]:
            marker = run + '-09-' + suffix
            capture('09-token-' + suffix, 'Un token ' + suffix + ' se rechaza antes de escribir; la fila no existe.',
                    ACCOUNT, account(marker), 'prueba ' + suffix, 'UNAUTHENTICATED', 'accounts', marker, token)
    engine.dispose()
    report = {'backend':backend,'version':version,'url':url,'casos':records}
    (output/'registro.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    for row in records:
        write_html(output, row)
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><h1>Actividad 6 - Evidencias HTTP y SQL</h1><ul>' +
        ''.join(f'<li><a href="{r["name"]}.html">{html.escape(r["name"])}</a> - {html.escape(r["regla"])}</li>' for r in records) + '</ul>', encoding='utf-8')
    print(f'{len(records)} casos HTTP/SQL correctos. Evidencias sin tokens ni contraseñas: {output}')


def write_html(output, row):
    def block(title, content):
        if not isinstance(content,str): content = json.dumps(content, ensure_ascii=False, indent=2)
        return '<section><h2>' + html.escape(title) + '</h2><pre>' + html.escape(content) + '</pre></section>'
    request = row['method'] + ' ' + row['url'] + '\n' + '\n'.join(k + ': ' + v for k,v in row['headers'].items())
    request += '\n\n' + row['query'] + '\n\nVariables:\n' + json.dumps(row['variables'], ensure_ascii=False, indent=2)
    left = block('Petición HTTP real · /graphql',request)
    right = block('Respuesta HTTP ' + str(row['http']), row['result'])
    if 'jwt_payload' in row:
        right += block('Payload verificado · HS256 · sin firma ni secreto',row['jwt_payload'])
    extra = ''
    if 'sql_antes' in row:
        b,a = row['sql_antes'],row['sql_despues']
        extra = block('Comprobación SQL · ' + b['backend'] + ' ' + b['version'],
            b['sql'] + '\nmarca = ' + b['marca'] + '\n\n' +
            json.dumps({'antes':{'total':b['total_tabla'],'filas_de_prueba':b['filas_de_prueba']},
                        'despues':{'total':a['total_tabla'],'filas_de_prueba':a['filas_de_prueba']}},ensure_ascii=False,indent=2))
    if 'sql_roles' in row: extra = block('Roles de Pedro en SQL',row['sql_roles'])
    page = '''<!doctype html><html lang="es"><meta charset="utf-8"><style>
    *{box-sizing:border-box}body{margin:0;padding:32px;background:#f1f5f9;color:#142c42;font:18px/1.4 Arial,sans-serif}
    header{background:#173f52;color:white;padding:22px 28px;border-radius:10px}h1{font-size:27px;margin:0 0 10px}
    header p{margin:0;font-size:19px}.meta{font-size:13px;margin-top:12px;color:#d3e7ed}.grid{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:22px}
    section{background:white;border:1px solid #ccd9e1;border-radius:9px;padding:20px;margin-bottom:18px}h2{font-size:18px;margin:0 0 15px}
    pre{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;font:16px/1.5 Consolas,monospace}.ok{color:#147247;font-weight:bold}footer{font-size:14px;color:#4a6073}</style>'''
    page += '<header><h1>' + html.escape(row['name']) + ' · PASS</h1><p>' + html.escape(row['regla']) + '</p><div class="meta">'
    page += html.escape(row['fechaUTC']) + ' · Cliente HTTP de evidencia · firma y contraseñas ocultas</div></header>'
    page += '<div class="grid"><div>' + left + '</div><div>' + right + '</div></div>' + extra
    page += '<footer>Registro de peticiones reales contra /graphql y consultas independientes a la base. Esta vista es un visor HTTP/SQL; no es GraphiQL.</footer></html>'
    (output/(row['name']+'.html')).write_text(page,encoding='utf-8')


if __name__ == '__main__':
    main()

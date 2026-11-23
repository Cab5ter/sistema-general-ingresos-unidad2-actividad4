"""Prepara personas de práctica sin restaurar ni alterar la matriz compartida."""
import json
import secrets
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import select
from .config import Settings
from .factory import create_app
from . import models as m
from .access import Role, RolePermission, Permission, MATRIX

DEST = Path('docs/unidad3-actividad3')
PRIVATE = Path('.activity3-credentials.json')
PEOPLE = [('admin', 'Ana Administradora', 'ADMINISTRADOR'),
          ('contador', 'Luis Contador', 'CONTADOR'),
          ('capturista', 'María Capturista', 'CAPTURISTA'),
          ('capturista2', 'José Capturista', 'CAPTURISTA'),
          ('consulta', 'Pedro Consulta', 'CONSULTA')]


def prepare():
    app = create_app(Settings.from_env())
    try:
        with app.state.sessions() as db:
            existing = db.scalar(select(m.Company).where(m.Company.tax_id == 'U3-A3'))
            if existing:
                if not PRIVATE.exists() or not (DEST/'ids.json').exists():
                    raise RuntimeError('El laboratorio existe; recupera sus credenciales e IDs antes de continuar.')
                ids = json.loads((DEST/'ids.json').read_text())
                if str(existing.id) != ids['companyId']:
                    raise RuntimeError('Los IDs corresponden a otra base de datos.')
                print('Laboratorio existente. No se modificó la matriz ni se duplicaron datos.')
                return
            for role in db.scalars(select(Role)):
                if role.code in MATRIX:
                    codes = set(db.scalars(select(Permission.code).join(RolePermission).where(
                        RolePermission.role_id == role.id, RolePermission.is_active.is_(True), Permission.is_active.is_(True))))
                    if codes != set(MATRIX[role.code]):
                        raise RuntimeError('La matriz ya fue editada. Usa una base de práctica independiente; no se restaurará automáticamente.')
        credentials = {label: secrets.token_urlsafe(24) for label, _, _ in PEOPLE}
        if PRIVATE.exists():
            raise RuntimeError('Ya existe el archivo privado; consérvalo y usa otra carpeta para otro laboratorio.')
        PRIVATE.write_text(json.dumps(credentials, indent=2)+'\n')
        PRIVATE.chmod(0o600)
        with TestClient(app) as client:
            headers = {'X-Bootstrap-Key': app.state.settings.bootstrap_key}
            def call(query, variables=None):
                result = client.post('/graphql', json={'query': query, 'variables': variables or {}}, headers=headers).json()
                if result.get('errors'):
                    raise RuntimeError(result['errors'])
                return result['data']
            cid = call('mutation($i:CreateCompanyInput!){createCompany(input:$i){id}}',
                       {'i': {'name': 'Empresa Demo · Unidad III', 'taxId': 'U3-A3'}})['createCompany']['id']
            ids = {'companyId': cid, 'members': {}}
            for label, name, role in PEOPLE:
                field = 'createCompanyAdmin' if label == 'admin' else 'createCompanyUser'
                kind = 'CreateCompanyAdminInput' if label == 'admin' else 'CreateCompanyUserInput'
                member = call(f'mutation($i:{kind}!){{{field}(input:$i){{id}}}}', {'i': {
                    'companyId': cid, 'name': name, 'email': label+'.actividad3@example.com', 'password': credentials[label]}})[field]['id']
                ids['members'][label] = member
                if label == 'admin':
                    token = call('mutation($i:LoginInput!){login(input:$i){token}}', {'i': {
                        'email': 'admin.actividad3@example.com', 'password': credentials['admin']}})['login']['token']
                    headers = {'Authorization': 'Bearer '+token}
                    ids['roles'] = {r['code']:r['id'] for r in call('{roles{id code}}')['roles']}
                else:
                    call('mutation($i:AssignRoleInput!){assignRole(input:$i){id}}', {'i': {'companyUserId': member, 'roleId': ids['roles'][role]}})
            ids['accountId'] = call('mutation($i:CreateAccountInput!){createAccount(input:$i){id}}', {'i': {
                'companyId': cid, 'name': 'Caja de la empresa', 'accountType': 'CASH'}})['createAccount']['id']
            ids['conceptId'] = call('mutation($i:CreateConceptInput!){createConcept(input:$i){id}}', {'i': {
                'companyId': cid, 'name': 'Venta de servicios', 'conceptType': 'INCOME'}})['createConcept']['id']
            call('mutation($i:AssignConceptToAccountInput!){assignConceptToAccount(input:$i){id}}', {'i': {
                'accountId': ids['accountId'], 'conceptId': ids['conceptId']}})
        DEST.mkdir(parents=True, exist_ok=True)
        (DEST/'ids.json').write_text(json.dumps(ids, indent=2, ensure_ascii=False)+'\n')
        print('Laboratorio listo. Contraseñas en .activity3-credentials.json (privado, no versionado).')
    finally:
        app.state.engine.dispose()


if __name__ == '__main__':
    prepare()

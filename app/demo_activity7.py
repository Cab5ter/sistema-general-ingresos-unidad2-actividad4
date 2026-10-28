"""Laboratorio reproducible; solo crea empresas de prueba con prefijo U2-A7."""
import json
import secrets
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import select, delete
from .config import Settings
from .factory import create_app
from . import models as m

DEST = Path('docs/unidad2-actividad7')
PRIVATE = Path('.activity7-credentials.json')
DATA = [('Banco',25,'INCOME','1000.00','Ingreso de apertura'),
        ('Banco',26,'INCOME','3000.00','Cobro de servicios'),
        ('Banco',27,'EXPENSE','1200.00','Pago de renta'),
        ('Banco',28,'EXPENSE','1000.00','Compra de materiales'),
        ('Caja',26,'INCOME','500.00','Venta de contado'),
        ('Caja',29,'EXPENSE','700.00','Pago de insumos')]


def prepare(restore=False):
    settings = Settings.from_env()
    app = create_app(settings)
    try:
        with app.state.sessions() as db:
            existing = db.scalar(select(m.Company).where(m.Company.tax_id=='U2-A7-A'))
        if existing and not restore:
            if not (DEST/'ids.json').exists():
                raise RuntimeError('Ya existe U2-A7-A pero faltan ids.json; recupera el archivo de este laboratorio.')
            print('Laboratorio existente: no se insertaron ni duplicaron movimientos. Usa --restore para restaurar solo sus seis movimientos.')
            return json.loads((DEST/'ids.json').read_text(encoding='utf-8'))
        if existing and restore:
            if not PRIVATE.exists():
                raise RuntimeError('Falta el archivo privado del laboratorio; restauración cancelada antes de modificar datos.')
            ids = json.loads((DEST/'ids.json').read_text(encoding='utf-8'))
            if int(ids['companyId']) != existing.id:
                raise RuntimeError('Los IDs no pertenecen al laboratorio; restauración cancelada.')
            with app.state.sessions.begin() as db:
                own = list(db.scalars(select(m.Account).where(m.Account.company_id==existing.id)))
                if {a.id for a in own} != set(map(int, ids['accounts'].values())):
                    raise RuntimeError('El laboratorio contiene cuentas adicionales; restauración cancelada.')
                db.execute(delete(m.Transaction).where(m.Transaction.account_id.in_([a.id for a in own])))
                for a in own:
                    a.is_active = True
                for c in db.scalars(select(m.Concept).where(m.Concept.company_id==existing.id)):
                    c.is_active = True
                for link in db.scalars(select(m.AccountConcept).where(m.AccountConcept.account_id.in_([a.id for a in own]))):
                    link.is_active = True
        else:
            ids = {}
        credentials = json.loads(PRIVATE.read_text(encoding='utf-8')) if PRIVATE.exists() else {
            label: secrets.token_urlsafe(24) for label in ('admin','consulta','other','empty')}
        PRIVATE.write_text(json.dumps(credentials, indent=2), encoding='utf-8')
        with TestClient(app) as client:
            headers = {}
            def call(query, variables=None, bootstrap=False):
                r = client.post('/graphql', json={'query':query,'variables':variables or {}},
                    headers={'X-Bootstrap-Key':settings.bootstrap_key} if bootstrap else headers).json()
                if r.get('errors'):
                    raise RuntimeError(r['errors'])
                return r['data']
            def login(label):
                token = call('mutation($i:LoginInput!){login(input:$i){token}}',
                    {'i':{'email':label+'.actividad7@example.com','password':credentials[label]}})['login']['token']
                headers.clear()
                headers['Authorization'] = 'Bearer '+token
            if not existing:
                for label, marker in [('admin','A'),('other','B'),('empty','VACIA')]:
                    cid = call('mutation($i:CreateCompanyInput!){createCompany(input:$i){id}}',
                        {'i':{'name':'Laboratorio balances '+marker,'taxId':'U2-A7-'+marker}}, True)['createCompany']['id']
                    mid = call('mutation($i:CreateCompanyAdminInput!){createCompanyAdmin(input:$i){id}}',
                        {'i':{'companyId':cid,'name':'Admin laboratorio '+marker,'email':label+'.actividad7@example.com','password':credentials[label]}},True)['createCompanyAdmin']['id']
                    ids[{'admin':'companyId','other':'otherCompanyId','empty':'emptyCompanyId'}[label]] = cid
                    ids[label+'MemberId'] = mid
                login('admin')
                ids['consultaMemberId'] = call('mutation($i:CreateCompanyUserInput!){createCompanyUser(input:$i){id}}',
                    {'i':{'companyId':ids['companyId'],'name':'Consulta laboratorio','email':'consulta.actividad7@example.com','password':credentials['consulta']}})['createCompanyUser']['id']
                roles = call('{roles{id code}}')['roles']
                reader_role = next(r['id'] for r in roles if r['code']=='CONSULTA')
                call('mutation($i:AssignRoleInput!){assignRole(input:$i){id}}',
                     {'i':{'companyUserId':ids['consultaMemberId'],'roleId':reader_role}})
                ids['accounts'], ids['concepts'] = {}, {}
                for label, kind in [('Banco','DEBIT'),('Caja','CASH'),('Ahorro','SAVINGS')]:
                    ids['accounts'][label] = call('mutation($i:CreateAccountInput!){createAccount(input:$i){id}}',
                        {'i':{'companyId':ids['companyId'],'name':label,'accountType':kind}})['createAccount']['id']
                for kind in ('INCOME','EXPENSE'):
                    ids['concepts'][kind] = call('mutation($i:CreateConceptInput!){createConcept(input:$i){id}}',
                        {'i':{'companyId':ids['companyId'],'name':kind,'conceptType':kind}})['createConcept']['id']
                for aid in ids['accounts'].values():
                    for cid in ids['concepts'].values():
                        call('mutation($i:AssignConceptToAccountInput!){assignConceptToAccount(input:$i){id}}',
                             {'i':{'accountId':aid,'conceptId':cid}})
                login('other')
                ids['otherAccountId'] = call('mutation($i:CreateAccountInput!){createAccount(input:$i){id}}',
                    {'i':{'companyId':ids['otherCompanyId'],'name':'Cuenta B','accountType':'CASH'}})['createAccount']['id']
            login('admin')
            for label, day, kind, amount, description in DATA:
                call('mutation($i:CreateTransactionInput!){createTransaction(input:$i){id}}', {'i':{
                    'accountId':ids['accounts'][label],'conceptId':ids['concepts'][kind], 'transactionType':kind,
                    'amount':amount,'transactionDate':f'2026-10-{day}T12:00:00Z','shortDescription':description}})
        DEST.mkdir(parents=True,exist_ok=True)
        (DEST/'ids.json').write_text(json.dumps(ids,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        variables = DEST/'variables'
        variables.mkdir(exist_ok=True)
        dates = {'from':'2026-10-26','to':'2026-10-30'}
        for label, aid in ids['accounts'].items():
            (variables/(label.lower()+'.json')).write_text(json.dumps({'accountId':aid,**dates},indent=2)+'\n',encoding='utf-8')
        (variables/'general.json').write_text(json.dumps(dates,indent=2)+'\n',encoding='utf-8')
        (variables/'banco-dia28.json').write_text(json.dumps({'accountId':ids['accounts']['Banco'],'from':'2026-10-28','to':'2026-10-28'},indent=2)+'\n',encoding='utf-8')
        print('Laboratorio listo. IDs y variables en docs/unidad2-actividad7. Contraseñas solo en .activity7-credentials.json (ignorado).')
        return ids
    finally:
        app.state.engine.dispose()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--restore', action='store_true', help='Restaurar únicamente los seis movimientos de la empresa U2-A7-A')
    prepare(parser.parse_args().restore)

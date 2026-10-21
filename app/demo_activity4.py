"""Prepara las cinco personas de U2-A4 mediante la API del proyecto existente.

Uso: SETTINGS_FILE=.env.docker python -m app.demo_activity4
No modifica catálogos ni contraseñas existentes. Los secretos no se exportan.
"""
import json
import os
import secrets
from pathlib import Path
import httpx
from sqlalchemy import select
from .config import Settings
from .db import database
from . import models as m

def prepare():
    settings = Settings.from_env()
    endpoint = os.getenv('ACTIVITY4_URL', 'http://127.0.0.1:8007/graphql')
    private = Path('.activity4-credentials.json')
    if private.exists():
        try:
            passwords = json.loads(private.read_text(encoding='utf-8'))
        except UnicodeDecodeError:
            # La versión anterior usaba la codificación local de Windows.
            passwords = json.loads(private.read_text(encoding='cp1252'))
            private.write_text(json.dumps(passwords, ensure_ascii=False), encoding='utf-8')
    else:
        passwords = {person: secrets.token_urlsafe(24) for person in ('Ana', 'Luis', 'María', 'José', 'Pedro')}
    if not private.exists():
        private.write_text(json.dumps(passwords, ensure_ascii=False), encoding='utf-8')
        private.chmod(0o600)
    engine, sessions = database(settings.database_url)
    auth = {}
    def call(query, variables=None, bootstrap=False):
        r = httpx.post(endpoint, json={'query': query, 'variables': variables or {}},
            headers={'X-Bootstrap-Key': settings.bootstrap_key} if bootstrap else auth, timeout=30)
        r.raise_for_status()
        result = r.json()
        if 'errors' in result:
            raise RuntimeError(result['errors'])
        return result['data']
    try:
        with sessions() as db:
            company = db.scalar(select(m.Company).where(m.Company.tax_id == 'U2-A4-ROLES'))
            cid = str(company.id) if company else None
        if cid is None:
            cid = call('mutation($i:CreateCompanyInput!){createCompany(input:$i){id}}',
                {'i': {'name': 'Sistema General de Ingresos - Actividad 4', 'taxId': 'U2-A4-ROLES'}}, True)['createCompany']['id']
        actors = {}
        for person, slug in [('Ana','ana'),('Luis','luis'),('María','maria'),('José','jose'),('Pedro','pedro')]:
            mail = slug + '.actividad4@example.com'
            with sessions() as db:
                member = db.scalar(select(m.CompanyUser).join(m.User).where(
                    m.CompanyUser.company_id == int(cid), m.User.email == mail))
                mid = str(member.id) if member else None
            if mid is None:
                fields = {'companyId':cid,'name':person,'email':mail,'password':passwords[person]}
                if person == 'Ana':
                    mid = call('mutation($i:CreateCompanyAdminInput!){createCompanyAdmin(input:$i){id isAdmin}}', {'i':fields}, True)['createCompanyAdmin']['id']
                else:
                    mid = call('mutation($i:CreateCompanyUserInput!){createCompanyUser(input:$i){id}}',
                        {'i':fields})['createCompanyUser']['id']
            actors[person] = mid
            if person == 'Ana':
                logged = call('mutation($i:LoginInput!){login(input:$i){token}}',
                    {'i': {'email': mail, 'password': passwords['Ana']}})['login']
                auth = {'Authorization': 'Bearer ' + logged['token']}
        catalogs = call('query{roles{id code} permissions{id code}}')
        roles = {r['code']:r['id'] for r in catalogs['roles']}
        permissions = {p['code']:p['id'] for p in catalogs['permissions']}
        for person, role in [('Luis','CONTADOR'),('María','CAPTURISTA'),('José','CAPTURISTA'),('Pedro','CONSULTA')]:
            call('mutation($i:AssignRoleInput!){assignRole(input:$i){role{code} isActive}}',
                {'i':{'companyUserId':actors[person],'roleId':roles[role]}})
        with sessions() as db:
            acc = db.scalar(select(m.Account).where(m.Account.company_id==int(cid),m.Account.name_key=='caja actividad 4'))
            con = db.scalar(select(m.Concept).where(m.Concept.company_id==int(cid),m.Concept.name_key=='ingreso actividad 4'))
            aid = str(acc.id) if acc else None
            coid = str(con.id) if con else None
        if aid is None:
            aid = call('mutation($i:CreateAccountInput!){createAccount(input:$i){id}}',
                {'i':{'companyId':cid,'accountType':'CASH','name':'Caja actividad 4'}})['createAccount']['id']
        if coid is None:
            coid = call('mutation($i:CreateConceptInput!){createConcept(input:$i){id}}',
                {'i':{'companyId':cid,'conceptType':'INCOME','name':'Ingreso actividad 4'}})['createConcept']['id']
        with sessions() as db:
            link = db.scalar(select(m.AccountConcept).where(m.AccountConcept.account_id==int(aid),m.AccountConcept.concept_id==int(coid)))
        if link is None or not link.is_active:
            call('mutation($i:AssignConceptToAccountInput!){assignConceptToAccount(input:$i){id}}',
                {'i':{'accountId':aid,'conceptId':coid}})
        result = {'companyId':cid,'actors':actors,'roles':roles,'permissions':permissions,'accountId':aid,'conceptId':coid}
        path = Path(os.getenv('EVIDENCE_DIR', 'entrega/evidencias-actividad6')) / 'ids.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2), encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return result
    finally:
        engine.dispose()

if __name__ == '__main__':
    prepare()

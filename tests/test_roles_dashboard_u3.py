"""Integración de la matriz con viewer y membresías usando los mismos JWT."""
from sqlalchemy import select
from app.access import RolePermission, CompanyUserRole, Permission, initialize
from app import models as m
from test_access import data
from operations import ASSIGN_ROLE, ACCOUNT

VIEWER = '{viewer{memberId roleCode permissions}}'
APPLY = 'mutation($input:SetRolePermissionsInput!){setRolePermissions(input:$input){changed finalCount}}'


def test_column_changes_two_sessions_without_assigning_people(api, data):
    people = ['CAPTURISTA', 'CONSULTA']
    api.call(ASSIGN_ROLE, {'actor':data['admin'], 'input': {
        'companyUserId':data['members']['CONSULTA'], 'roleId':data['roles']['CAPTURISTA']}})
    tokens = [api.headers_for(data['members'][role]) for role in people]
    for token in tokens:
        assert 'accounts.write' not in api.call(VIEWER, headers=token)['viewer']['permissions']
    wanted = [data['permissions'][code] for code in (
        'accounts.read','accounts.write','concepts.read','transactions.read','transactions.write')]
    api.call(APPLY, {'actor':data['admin'], 'input': {'roleId':data['roles']['CAPTURISTA'], 'permissionIds':wanted}})
    for token in tokens:
        assert 'accounts.write' in api.call(VIEWER, headers=token)['viewer']['permissions']
        api.call(ACCOUNT, {'input': {'companyId':data['cid'],'name':'Nueva cuenta '+api.call(VIEWER, headers=token)['viewer']['memberId'],'accountType':'CASH'}}, headers=token)
    wanted.remove(data['permissions']['accounts.write'])
    api.call(APPLY, {'actor':data['admin'], 'input': {'roleId':data['roles']['CAPTURISTA'], 'permissionIds':wanted}})
    for token in tokens:
        assert 'accounts.write' not in api.call(VIEWER, headers=token)['viewer']['permissions']
        api.call(ACCOUNT, {'input': {'companyId':data['cid'],'name':'Rechazo','accountType':'CASH'}}, headers=token, code='FORBIDDEN')
    with api.app.state.sessions() as db:
        row = db.scalar(select(RolePermission).where(RolePermission.role_id==int(data['roles']['CAPTURISTA']),
            RolePermission.permission_id==int(data['permissions']['accounts.write'])))
        assert row is not None and not row.is_active


def test_assignment_changes_viewer_without_changing_matrix_or_is_admin(api, data):
    token = api.headers_for(data['members']['CONSULTA'])
    with api.app.state.sessions() as db:
        before = [(r.id,r.role_id,r.permission_id,r.is_active) for r in db.scalars(select(RolePermission).order_by(RolePermission.id))]
    assert 'transactions.write' not in api.call(VIEWER, headers=token)['viewer']['permissions']
    api.call(ASSIGN_ROLE, {'actor':data['admin'],'input': {
        'companyUserId':data['members']['CONSULTA'], 'roleId':data['roles']['CAPTURISTA']}})
    viewer = api.call(VIEWER, headers=token)['viewer']
    assert viewer['roleCode']=='CAPTURISTA' and 'transactions.write' in viewer['permissions']
    with api.app.state.sessions() as db:
        assert before == [(r.id,r.role_id,r.permission_id,r.is_active) for r in db.scalars(select(RolePermission).order_by(RolePermission.id))]
        assert not db.get(m.CompanyUser, int(data['members']['CONSULTA'])).is_admin
        assignments = list(db.scalars(select(CompanyUserRole).where(CompanyUserRole.company_user_id==int(data['members']['CONSULTA']))))
        assert len(assignments)==2 and sum(r.is_active for r in assignments)==1


def test_names_upgrade_preserves_custom_names_and_grants(api, data):
    with api.app.state.sessions.begin() as db:
        db.get(Permission,int(data['permissions']['accounts.read'])).name = 'accounts.read'
        db.get(Permission,int(data['permissions']['concepts.read'])).name = 'Mi catálogo'
        row = db.scalar(select(RolePermission).where(RolePermission.role_id==int(data['roles']['CAPTURISTA'])))
        row.is_active=False
        ident=row.id
    initialize(api.app.state.engine,api.app.state.sessions)
    with api.app.state.sessions() as db:
        assert db.get(Permission,int(data['permissions']['accounts.read'])).name == 'Ver cuentas'
        assert db.get(Permission,int(data['permissions']['concepts.read'])).name == 'Mi catálogo'
        assert not db.get(RolePermission,ident).is_active

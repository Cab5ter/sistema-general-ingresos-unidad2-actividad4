"""U2-A5: contratos, validaciones y rollback real después de flush."""
import json
import pytest
from sqlalchemy import select, event
from sqlalchemy.orm import Session
from app.access import Role, Permission, RolePermission
from test_access import data, make_company

PREVIEW = """query Revisar($input: SetRolePermissionsInput!) {
 previewRolePermissions(input:$input) {
 role {code} current {code} toActivate {code} toDeactivate {code} unchanged {code} finalCount }}"""
APPLY = """mutation Aplicar($input: SetRolePermissionsInput!) {
 setRolePermissions(input:$input) {
 role {code} activated {code} deactivated {code} unchanged {code} finalCount changed }}"""

def variables(data, codes=None):
    codes = codes if codes is not None else ['accounts.read','concepts.read','transactions.read','transactions.write']
    return {'actor':data['admin'],'input':{'roleId':data['roles']['CAPTURISTA'],
            'permissionIds':[data['permissions'][c] for c in codes]}}

def snapshot(api):
    with api.app.state.sessions() as db:
        return [(r.id,r.role_id,r.permission_id,r.is_active) for r in db.scalars(select(RolePermission).order_by(RolePermission.id))]

def test_preview_apply_repeat_reactivate(api,data):
    v=variables(data); v['input']['permissionIds'].append(data['permissions']['accounts.write'])
    before=snapshot(api)
    plan=api.call(PREVIEW,v)['previewRolePermissions']
    assert plan['toActivate']==[{'code':'accounts.write'}] and plan['toDeactivate']==[]
    assert len(plan['unchanged'])==4 and plan['finalCount']==5
    assert snapshot(api)==before
    first=api.call(APPLY,v)['setRolePermissions']
    assert first['changed'] and first['activated']==plan['toActivate']
    after=snapshot(api)
    second=api.call(APPLY,v)['setRolePermissions']
    assert not second['changed'] and not second['activated'] and not second['deactivated']
    assert snapshot(api)==after
    api.call(APPLY,variables(data))
    inactive=snapshot(api)
    api.call(APPLY,v)
    assert snapshot(api)==after and [r[:3] for r in inactive]==[r[:3] for r in after]
    with api.app.state.sessions() as db:
        assert all(p.is_active for p in db.scalars(select(Permission)))

@pytest.mark.parametrize('operation',[PREVIEW,APPLY])
@pytest.mark.parametrize('variant',['missing_role','inactive_role','admin','missing_permission','inactive_permission','duplicate','mixed_duplicate','malformed','zero','negative'])
def test_invalid_proposals_no_writes(api,data,operation,variant):
    v=variables(data)
    if variant=='missing_role': v['input']['roleId']='999999'
    elif variant=='admin': v['input']['roleId']=data['roles']['ADMINISTRADOR']
    elif variant=='missing_permission': v['input']['permissionIds'].append('999999')
    elif variant=='duplicate': v['input']['permissionIds']*=2
    elif variant=='mixed_duplicate': v['input']['permissionIds'].append(int(v['input']['permissionIds'][0]))
    elif variant in ('malformed','zero','negative'): v['input']['permissionIds'].append({'malformed':'abc','zero':'0','negative':'-1'}[variant])
    else:
        model=Role if variant=='inactive_role' else Permission
        ident=v['input']['roleId'] if model is Role else v['input']['permissionIds'][0]
        with api.app.state.sessions.begin() as db: db.get(model,int(ident)).is_active=False
    before=snapshot(api)
    result=api.request(operation,v).json()
    field='previewRolePermissions' if operation==PREVIEW else 'setRolePermissions'
    assert result['errors'] and result['data'][field] is None
    assert snapshot(api)==before


def test_e07_rollback_after_flush(api,data,monkeypatch):
    v=variables(data,[]); before=snapshot(api); observed=[]
    from app.finance_service import FinanceService
    def fail_after_flush(self):
        self.db.flush()
        # Verifica que el UPDATE ya llegó a la conexión, antes de provocar el fallo.
        active=self.db.scalar(select(RolePermission.id).where(
            RolePermission.role_id==int(data['roles']['CAPTURISTA']),RolePermission.is_active.is_(True)))
        assert active is None
        print('E07: tras flush no quedan relaciones activas de CAPTURISTA en la transacción.')
        observed.append(True)
        raise RuntimeError('Fallo controlado después de flush y antes de commit (E07)')
    monkeypatch.setattr(FinanceService,'check_before_commit',fail_after_flush)
    result=api.request(APPLY,v).json()
    assert result['errors'] and result['data']['setRolePermissions'] is None and observed
    after = snapshot(api)  # Una sesión nueva, independiente de la que falló.
    print('E07 ANTES:', json.dumps(before))
    print('E07 DESPUES (sesión nueva):', json.dumps(after))
    assert after == before


def test_empty_survives_new_application(api,data):
    from app.factory import create_app
    from fastapi.testclient import TestClient
    v=variables(data,[])
    result=api.call(APPLY,v)['setRolePermissions']
    assert result['finalCount']==0 and len(result['deactivated'])==4
    before=snapshot(api)
    restarted=create_app(api.settings)
    try:
        with TestClient(restarted) as client:
            result=client.post('/graphql',json={'query':PREVIEW,'variables':{'input':v['input']}}, headers=api.headers_for(v['actor'])).json()
            assert result['data']['previewRolePermissions']['current']==[]
        assert snapshot(api)==before
    finally: restarted.state.engine.dispose()


def test_catalog_enum_filter_inactive_and_authorization(api,data):
    query="""query Catalogo($r:PermissionResource){
      permissionCatalog(resource:$r){code}}"""
    for resource,prefix in [('COMPANY_USERS','company.users.'),('ACCOUNTS','accounts.'),('CONCEPTS','concepts.'),('TRANSACTIONS','transactions.'),('ROLES','roles.')]:
        rows=api.call(query,{'actor':data['admin'],'r':resource})['permissionCatalog']
        assert len(rows)==2 and all(p['code'].startswith(prefix) for p in rows)
        assert rows==sorted(rows,key=lambda p:p['code'])
    for v in ({'actor':data['admin']},{'actor':data['admin'],'r':None}):
        assert len(api.call(query,v)['permissionCatalog'])==10
    api.call(query,{'actor':data['admin'],'r':'PAYMENTS'},code='GRAPHQL_VALIDATION')
    with api.app.state.sessions.begin() as db: db.get(Permission,int(data['permissions']['accounts.write'])).is_active=False
    assert len(api.call(query,{'actor':data['admin']})['permissionCatalog'])==9
    v=variables(data); v['actor']=data['members']['CAPTURISTA']
    api.call(PREVIEW,v,code='FORBIDDEN'); api.call(APPLY,v,code='FORBIDDEN')
    v['actor']=data['members']['CONTADOR']
    api.call(PREVIEW,v); api.call(APPLY,v,code='FORBIDDEN')


def test_single_commit_and_schema_contract(api,data):
    commits=[]
    def committed(session): commits.append(True)
    event.listen(Session,'after_commit',committed)
    try: api.call(APPLY,variables(data,[]))
    finally: event.remove(Session,'after_commit',committed)
    assert len(commits)==1
    from app.schema import schema
    from graphql import build_schema
    types=build_schema(schema.as_str())
    assert str(types.get_type('SetRolePermissionsInput').fields['permissionIds'].type)=='[ID!]!'
    assert str(types.query_type.fields['previewRolePermissions'].type)=='RolePermissionPlan'
    assert str(types.mutation_type.fields['setRolePermissions'].type)=='RolePermissionUpdate'

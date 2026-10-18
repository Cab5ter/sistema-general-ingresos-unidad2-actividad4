"""Lecturas de evidencia y preparación/restauración controlada de E06."""
import json,sys
from sqlalchemy import text
from app.config import Settings
from app.db import database

SQL = """SELECT rp.id AS relacion_id,r.code AS rol,p.code AS permiso,
 rp.is_active AS relacion_activa,p.is_active AS permiso_activo
 FROM role_permissions rp JOIN roles r ON r.id=rp.role_id
 JOIN permissions p ON p.id=rp.permission_id ORDER BY r.code,p.code"""

def main():
    engine,_=database(Settings.from_env().database_url)
    action=sys.argv[1] if len(sys.argv)>1 else 'snapshot'
    try:
        if action in ('role_off','role_on','permission_off','permission_on'):
            table,code=('roles','CAPTURISTA') if action.startswith('role') else ('permissions','accounts.write')
            with engine.begin() as db:
                db.execute(text(f'UPDATE {table} SET is_active=:active WHERE code=:code'),
                           {'active':action.endswith('_on'),'code':code})
        with engine.connect() as db:
            rows=[dict(r) for r in db.execute(text(SQL)).mappings()]
            matrix={code:[] for code in db.scalars(text('SELECT code FROM roles ORDER BY code'))}
            for row in rows:
                if row['relacion_activa'] and row['permiso_activo']:
                    matrix[row['rol']].append(row['permiso'])
            result={'sql':SQL,'mysql':db.scalar(text('SELECT VERSION()')),'rows':rows,'matrix':matrix,
                    'roles':db.scalar(text('SELECT COUNT(*) FROM roles')),
                    'permissions':db.scalar(text('SELECT COUNT(*) FROM permissions')),
                    'duplicates':[list(r) for r in db.execute(text('SELECT role_id,permission_id,COUNT(*) FROM role_permissions GROUP BY role_id,permission_id HAVING COUNT(*)>1'))]}
            if len(sys.argv)>2:
                tid=int(sys.argv[2])
                query='SELECT id,account_id,concept_id,amount,is_active FROM transactions WHERE id=:id'
                result['transaction_sql']=query
                result['transaction']=[dict(r) for r in db.execute(text(query),{'id':tid}).mappings()]
        print(json.dumps(result,ensure_ascii=False,default=str))
    finally: engine.dispose()

if __name__=='__main__': main()

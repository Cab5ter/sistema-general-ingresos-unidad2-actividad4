"""Conserva la respuesta inicial HTTP del laboratorio sin guardar la sesión."""
import json
import os
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'docs/unidad2-actividad7'


def main():
    operations=(DEST/'operaciones.graphql').read_text(encoding='utf-8')
    password=json.loads((ROOT/'.activity7-credentials.json').read_text(encoding='utf-8'))['admin']
    endpoint=os.getenv('GRAPHQL_URL','http://127.0.0.1:8007/graphql')
    with httpx.Client(timeout=30) as client:
        def call(operation, variables, token=None):
            response=client.post(endpoint,json={'query':operations,'operationName':operation,'variables':variables},
                headers={'Authorization':'Bearer '+token} if token else {})
            response.raise_for_status()
            result=response.json()
            assert not result.get('errors'), result
            return result
        token=call('IniciarSesion',{'input':{'email':'admin.actividad7@example.com','password':password}})['data']['login']['token']
        records=[]
        for label in ('banco','caja','ahorro','general','banco-dia28'):
            variables=json.loads((DEST/'variables'/(label+'.json')).read_text())
            op='BalanceDeLaEmpresa' if label=='general' else 'BalanceDeUnaCuenta'
            result=call(op,variables,token)
            records.append({'caso':label,'operationName':op,'variables':variables,'response':result})
        balances=[next(iter(r['response']['data'].values())) for r in records]
        assert [b['closingBalance'] for b in balances]==['1800.00','-200.00','0.00','1600.00','1800.00']
        assert balances[3]['accountsInRed']==1 and balances[3]['isInRed'] is False
        assert balances[4]['openingBalance']=='2800.00' and balances[4]['profit']=='-1000.00'
    (DEST/'evidencias').mkdir(exist_ok=True)
    (DEST/'evidencias/referencia-http.json').write_text(json.dumps(records,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Cinco respuestas HTTP conservadas; resultados de referencia comprobados; sesión excluida.')


if __name__=='__main__':
    main()

"""Construye la estructura de entrega U2-A5 y verifica integridad y secretos."""
import argparse, hashlib, json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
PREFIX='unidad2_actividad5_equipo'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'entrega')
    args=parser.parse_args()
    secrets=[]
    for filename in ('.env','.env.docker'):
        p=ROOT/filename
        if p.exists():
            for line in p.read_text().splitlines():
                key,_,value=line.partition('=')
                if key in ('JWT_SECRET','BOOTSTRAP_KEY','MYSQL_PASSWORD','MYSQL_ROOT_PASSWORD') and value:
                    secrets.append(value.encode())
    for filename in ('.activity4-credentials.json','.roles-demo.json','.demo-credentials.json'):
        p=ROOT/filename
        if p.exists():
            values=json.loads(p.read_text())
            if filename=='.demo-credentials.json': values={'password':values['password']}
            secrets.extend(v.encode() for v in values.values() if isinstance(v,str) and len(v)>=12)
    files=[ROOT/n for n in ('README.md','ENTREGA.md','requirements.txt','schema.graphql','compose.yaml','Dockerfile','.dockerignore','.gitignore','.env.example','.env.docker.example','pytest.ini')]
    suffixes={'.py','.cjs','.mjs','.md','.graphql','.json','.txt','.xml','.png','.jpg','.sql','.html','.pdf'}
    for directory in ('app','tests','scripts','docs'):
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and p.suffix in suffixes and '__pycache__' not in p.parts)
    payloads={}
    for p in sorted(set(files)):
        data=p.read_bytes()
        if any(secret in data for secret in secrets): raise RuntimeError('Secreto detectado: '+str(p.relative_to(ROOT)))
        payloads[PREFIX+'/ingresos/'+p.relative_to(ROOT).as_posix()]=data
    for p in (ROOT/'docs/unidad2-actividad5').rglob('*'):
        if p.is_file():
            data=p.read_bytes()
            if any(secret in data for secret in secrets): raise RuntimeError('Secreto detectado')
            payloads[PREFIX+'/'+p.relative_to(ROOT/'docs/unidad2-actividad5').as_posix()]=data
    manifest={n:hashlib.sha256(d).hexdigest() for n,d in payloads.items()}
    payloads[PREFIX+'/MANIFIESTO-SHA256.json']=json.dumps(manifest,indent=2).encode()
    args.output.mkdir(parents=True,exist_ok=True)
    target=args.output/(PREFIX+'.zip')
    with ZipFile(target,'w',ZIP_DEFLATED) as archive:
        for name,data in payloads.items(): archive.writestr(name,data)
    with ZipFile(target) as archive:
        assert archive.testzip() is None and set(archive.namelist())==set(payloads)
        for name,data in payloads.items(): assert archive.read(name)==data
    (args.output/(PREFIX+'.sha256')).write_text(hashlib.sha256(target.read_bytes()).hexdigest()+'  '+target.name+'\n')
    print(str(target)); print(str(len(payloads))+' archivos; integridad y ausencia de secretos locales verificadas.')

if __name__=='__main__': main()

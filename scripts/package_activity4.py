"""Entrega U2-A4: código existente, evidencias nuevas e informe; sin secretos."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
PREFIX='UnidadII_Actividad4_Permisos'
def main():
    secrets=[]
    for filename in ('.env','.env.docker'):
        p=ROOT/filename
        if p.exists():
            for line in p.read_text().splitlines():
                key,_,value=line.partition('=')
                if key in ('JWT_SECRET','BOOTSTRAP_KEY','MYSQL_PASSWORD','MYSQL_ROOT_PASSWORD') and value:
                    secrets.append(value.encode())
    for filename in ('.activity4-credentials.json','.roles-demo.json'):
        p=ROOT/filename
        if p.exists(): secrets.extend(v.encode() for v in json.loads(p.read_text()).values())
    p=ROOT/'.demo-credentials.json'
    if p.exists(): secrets.append(json.loads(p.read_text())['password'].encode())
    files=[ROOT/n for n in ('README.md','ENTREGA.md','requirements.txt','schema.graphql','compose.yaml','Dockerfile','.dockerignore','.gitignore','.env.example','.env.docker.example','pytest.ini')]
    suffixes={'.py','.cjs','.mjs','.md','.graphql','.json','.txt','.xml','.png','.jpg','.sql','.html','.pdf'}
    for directory in ('app','tests','scripts','docs'):
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and p.suffix in suffixes and '__pycache__' not in p.parts)
    payloads={}
    for p in sorted(set(files)):
        data=p.read_bytes()
        if any(s in data for s in secrets):raise RuntimeError('Secreto detectado en '+str(p.relative_to(ROOT)))
        payloads[PREFIX+'/'+p.relative_to(ROOT).as_posix()]=data
    manifest={name:hashlib.sha256(data).hexdigest() for name,data in payloads.items()}
    payloads[PREFIX+'/MANIFIESTO-SHA256.json']=json.dumps(manifest,indent=2).encode()
    out=ROOT/'entrega';out.mkdir(exist_ok=True)
    archive=out/(PREFIX+'.zip')
    with ZipFile(archive,'w',ZIP_DEFLATED) as z:
        for name,data in payloads.items():z.writestr(name,data)
    with ZipFile(archive) as z:
        assert z.testzip() is None
        assert set(z.namelist())==set(payloads)
        for name,data in payloads.items():assert z.read(name)==data
    (out/(PREFIX+'.sha256')).write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
    print(str(archive));print(f'{len(payloads)} archivos; ZIP verificado sin claves, credenciales ni bases de datos.')
if __name__=='__main__':main()

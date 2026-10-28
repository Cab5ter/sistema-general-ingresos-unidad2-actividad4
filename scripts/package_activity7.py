"""Empaqueta fuentes y evidencia versionables; excluye secretos y archivos de trabajo."""
import hashlib
import json
import re
import subprocess
import time
import base64
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]


def main():
    if (ROOT/'.git').exists():
        names=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).decode().split('\0')
    else:
        # También permite volver a empaquetar un ZIP extraído sin metadatos Git.
        names=[n for n in ('README.md','ENTREGA.md','requirements.txt','schema.graphql','pytest.ini',
                         'Dockerfile','compose.yaml','.gitignore','.dockerignore','.env.example','.env.docker.example') if (ROOT/n).is_file()]
        for directory in ('app','tests','scripts','docs'):
            names += [p.relative_to(ROOT).as_posix() for p in (ROOT/directory).rglob('*')
                      if p.is_file() and p.suffix in {'.py','.md','.graphql','.json','.txt','.xml','.jpg','.png','.sql','.pdf','.html'}]
    files=sorted({name for name in names if name and (ROOT/name).is_file() and
                  not any(part in {'.git','__pycache__','.venv','.pytest_cache','entrega'} for part in Path(name).parts)})
    secret_values=[]
    for name in ('.env','.env.docker'):
        if (ROOT/name).exists():
            secret_values += [v.encode() for k,v in dotenv_values(ROOT/name).items()
                              if v and k in {'JWT_SECRET','BOOTSTRAP_KEY','MYSQL_ROOT_PASSWORD','MYSQL_PASSWORD'}]
    if (ROOT/'.activity7-credentials.json').exists():
        secret_values += [v.encode() for v in json.loads((ROOT/'.activity7-credentials.json').read_text()).values()]
    payloads={}
    for name in files:
        if Path(name).name.startswith('.env') and name not in {'.env.example','.env.docker.example'}:
            raise RuntimeError('Se intentó incluir configuración privada')
        content=(ROOT/name).read_bytes()
        if any(value in content for value in secret_values):
            raise RuntimeError(f'Secreto local detectado en {name}')
        for token in re.findall(rb'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',content):
            try:
                body=token.split(b'.')[1]
                claims=json.loads(base64.urlsafe_b64decode(body+b'='*(-len(body)%4)))
                if claims.get('exp',0)>time.time():
                    raise RuntimeError(f'Token vigente detectado en {name}')
            except (ValueError,TypeError):
                pass
        payloads['unidad2_actividad7_equipo/'+name]=content
    out=ROOT/'entrega'
    out.mkdir(exist_ok=True)
    path=out/'unidad2_actividad7_equipo.zip'
    with ZipFile(path,'w',ZIP_DEFLATED) as z:
        for name,content in payloads.items():
            z.writestr(name,content)
    with ZipFile(path) as z:
        assert z.testzip() is None and len(z.namelist())==len(payloads)
    (out/'unidad2_actividad7_equipo.sha256').write_text(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name+'\n')
    print(f'ZIP íntegro: {len(payloads)} archivos, sin secretos locales ni tokens vigentes. {path}')


if __name__=='__main__':
    main()

"""ZIP reproducible de fuentes y evidencias; excluye configuración privada y JWT vigentes."""
import argparse
import base64
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROOT = {'README.md','ENTREGA.md','requirements.txt','pytest.ini','schema.graphql',
                'Dockerfile','compose.yaml','.gitignore','.dockerignore','.env.example','.env.docker.example'}
ALLOWED_DIRS = {'app','dashboard','tests','scripts','docs'}
EXCLUDE = {'.git','__pycache__','.venv','venv','virtualenv','node_modules','.pytest_cache','entrega','work'}


def main(destination=None):
    if (ROOT/'.git').exists():
        candidates = subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'], cwd=ROOT).decode().split('\0')
    else:
        candidates = [str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file()]
    secrets = []
    private = ROOT/'.activity3-credentials.json'
    if private.exists():
        secrets.extend(str(value).encode() for value in json.loads(private.read_text()).values())
    for env in (ROOT/'.env',ROOT/'.env.docker'):
        if env.exists():
            for line in env.read_text().splitlines():
                if '=' in line and any(key in line.split('=',1)[0] for key in ('PASSWORD','SECRET','BOOTSTRAP_KEY')):
                    value=line.split('=',1)[1].strip().strip('\"\'')
                    if value: secrets.append(value.encode())
    payloads = {}
    for name in sorted(set(candidates)):
        p = Path(name)
        if not name or any(part in EXCLUDE for part in p.parts): continue
        if name not in ALLOWED_ROOT and p.parts[0] not in ALLOWED_DIRS: continue
        if p.name.startswith('.env') and name not in {'.env.example','.env.docker.example'}: continue
        source=ROOT/p
        if not source.is_file() or source.is_symlink() or p.suffix in {'.pyc','.db','.log','.zip'}: continue
        data=source.read_bytes()
        if any(secret and secret in data for secret in secrets):
            raise RuntimeError(f'Secreto local detectado en {name}')
        for token in re.findall(rb'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', data):
            try:
                body=token.split(b'.')[1]
                exp=json.loads(base64.urlsafe_b64decode(body+b'='*(-len(body)%4))).get('exp',0)
            except (ValueError,TypeError): continue
            if exp > time.time(): raise RuntimeError(f'JWT vigente detectado en {name}')
        payloads['unidad3_actividad3_equipo/'+p.as_posix()]=data
    out=Path(destination) if destination else ROOT/'entrega'
    out.mkdir(parents=True,exist_ok=True)
    target=out/'unidad3_actividad3_equipo.zip'
    with ZipFile(target,'w',ZIP_DEFLATED) as archive:
        for name,data in payloads.items(): archive.writestr(name,data)
    with ZipFile(target) as archive:
        assert archive.testzip() is None
        assert any(name.endswith('/dashboard/app.js') for name in archive.namelist())
        assert any(name.endswith('/docs/unidad3-actividad3/evidencias.md') for name in archive.namelist())
    target.with_suffix('.sha256').write_text(hashlib.sha256(target.read_bytes()).hexdigest()+'  '+target.name+'\n')
    print(f'ZIP verificado: {target} ({len(payloads)} archivos).')


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',help='Directorio destino; por defecto entrega/')
    main(parser.parse_args().output)

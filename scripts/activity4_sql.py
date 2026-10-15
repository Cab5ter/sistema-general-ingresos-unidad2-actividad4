"""Ejecuta un SELECT real y guarda resultados legibles, JSON y HTML sin secretos."""
import argparse
import html
import json
from pathlib import Path
from sqlalchemy import text
from app.config import Settings
from app.db import database

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('name')
    parser.add_argument('query')
    args = parser.parse_args()
    if not args.query.strip().upper().startswith('SELECT'):
        raise ValueError('Solo se permiten consultas SELECT.')
    engine, _ = database(Settings.from_env().database_url)
    try:
        with engine.connect() as db:
            result = db.execute(text(args.query))
            columns = list(result.keys())
            rows = [list(row) for row in result]
            version = db.scalar(text('SELECT VERSION()'))
        data = {'motor': 'MySQL '+version, 'consulta':args.query,'columnas':columns,'filas':rows}
        out = Path('docs/evidencias/unidad2-actividad4')
        out.mkdir(parents=True, exist_ok=True)
        (out/(args.name+'.json')).write_text(json.dumps(data,indent=2,ensure_ascii=False,default=str))
        widths = [max(len(str(c)),max((len(str(r[i])) for r in rows),default=0)) for i,c in enumerate(columns)]
        line = '+'+'+'.join('-'*(w+2) for w in widths)+'+'
        def fmt(row): return '| '+' | '.join(str(v).ljust(w) for v,w in zip(row,widths))+' |'
        table = '\n'.join([line,fmt(columns),line,*map(fmt,rows),line,f'{len(rows)} filas'])
        (out/(args.name+'.txt')).write_text(args.query+'\n\n'+table+'\n')
        page = '<!doctype html><meta charset="utf-8"><style>body{font:16px system-ui;margin:28px;background:#f4f7fb;color:#172438}h1{font-size:23px}pre{font:15px/1.45 monospace;background:white;border:1px solid #c6d2e1;padding:18px;white-space:pre-wrap}small{color:#506174}</style>'
        page += '<small>Sistema General de Ingresos · Unidad II · Actividad 4</small><h1>Consulta ejecutada en '+html.escape(data['motor'])+'</h1><pre>'+html.escape(args.query)+'</pre><pre>'+html.escape(table)+'</pre>'
        (out/(args.name+'.html')).write_text(page)
        print(json.dumps(data,ensure_ascii=False,default=str))
    finally:
        engine.dispose()

if __name__ == '__main__': main()

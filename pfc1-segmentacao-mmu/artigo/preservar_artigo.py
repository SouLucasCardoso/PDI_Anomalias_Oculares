"""Prepara ou restaura a cópia verificável do artigo sem alterar o Defender."""
import argparse
import base64
import hashlib
import io
import json
import tempfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BACKUP=ROOT/'backups/artigo_consolidado_2026-10-23'
def sha(data): return hashlib.sha256(data).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--preparar',type=Path)
    parser.add_argument('--destino',type=Path,default=Path(tempfile.gettempdir())/'pfc-artigo-restaurado-20261023')
    args=parser.parse_args()
    if args.preparar:
        source=args.preparar
        files={name:(source/name).read_bytes() for name in [
            'ARTIGO_AREA_IRIS_CONSOLIDADO_2026-10-23.docx','artifact.md',
            'verificacao_pacote.json','figuras/fluxo_experimental.png','figuras/intervalos_condicoes.png']}
        for name in ['ARTIGO_CONSOLIDADO_2026-10-23.md','consolidar_artigo.py','render_word_docx.py','preservar_artigo.py']:
            files[name]=(ROOT/'artigo'/name).read_bytes()
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in files.items():z.writestr(name,data)
        blob=buf.getvalue();encoded=base64.b64encode(blob).decode('ascii')
        stage=source/'preservacao';stage.mkdir(exist_ok=True)
        names=[]
        for start in range(0,len(encoded),64000):
            name=f'parte_{len(names)+1:03}.b64';names.append(name)
            (stage/name).write_text(encoded[start:start+64000],encoding='ascii')
        manifest={'zip_sha256':sha(blob),'zip_bytes':len(blob),'parts':names,
                  'files':{n:{'bytes':len(d),'sha256':sha(d)} for n,d in files.items()}}
        (stage/'registro_preservacao.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'stage':str(stage),'parts':len(names),'zip_bytes':len(blob)}));return
    record=json.loads((BACKUP/'registro_preservacao.json').read_text('utf-8'))
    encoded=''.join((BACKUP/n).read_text('ascii').strip() for n in record['parts'])
    blob=base64.b64decode(encoded,validate=True)
    assert len(blob)==record['zip_bytes'] and sha(blob)==record['zip_sha256']
    destination=args.destino.resolve();destination.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert set(z.namelist())==set(record['files'])
        for name,meta in record['files'].items():
            target=(destination/name).resolve()
            if not target.is_relative_to(destination):raise ValueError('Caminho fora do destino')
            data=z.read(name);assert sha(data)==meta['sha256'] and len(data)==meta['bytes']
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            assert sha(target.read_bytes())==meta['sha256']
    print(json.dumps({'status':'restaurado_e_verificado','files':len(record['files']),'destino':str(destination)},ensure_ascii=False))

if __name__=='__main__':main()

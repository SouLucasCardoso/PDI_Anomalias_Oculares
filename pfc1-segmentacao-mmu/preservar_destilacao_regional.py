"""Preservacao local por partes; caches e evidencia de ajuste por hash."""
from pathlib import Path
import argparse,base64,hashlib,io,json,tempfile,zipfile
ROOT=Path(__file__).resolve().parent
NAME='destilacao_regional_treino_2026-10-27'

def sha(b):return hashlib.sha256(b).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--preparar',type=Path);p.add_argument('--destino',type=Path,default=Path(tempfile.gettempdir())/'pfc-regional-aprendido-restaurado-20261027');a=p.parse_args()
    if a.preparar:
        folder=a.preparar/NAME;assert (folder/'AUDITORIA_REPRODUCAO.json').exists();files={};excluded={}
        for f in folder.iterdir():
            if not f.is_file():continue
            b=f.read_bytes();name=NAME+'/'+f.name
            if f.name=='fit_evidence.npz':excluded[name]=dict(bytes=len(b),sha256=sha(b))
            else:files[name]=b
        for n in ['descritor_regional_aprendido.py','test_descritor_regional_aprendido.py','piloto_destilacao_regional.py','auditar_destilacao_regional.py','preservar_destilacao_regional.py']:files['scripts/'+n]=(ROOT/n).read_bytes()
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
            for n,b in files.items():z.writestr(n,b)
        blob=stream.getvalue();encoded=base64.b64encode(blob).decode('ascii');stage=a.preparar/'preservacao_destilacao_regional';stage.mkdir(exist_ok=True);parts=[]
        for start in range(0,len(encoded),1000000):
            n=f'parte_{len(parts)+1:03}.b64';parts.append(n);(stage/n).write_text(encoded[start:start+1000000],encoding='ascii')
        record=dict(zip_bytes=len(blob),zip_sha256=sha(blob),parts=parts,files={n:dict(bytes=len(b),sha256=sha(b)) for n,b in files.items()},excluded_reproducible_fit_evidence=excluded)
        (stage/'registro_preservacao.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(dict(files=len(files),parts=len(parts),zip_bytes=len(blob))));return
    folder=ROOT/'backups'/NAME;record=json.loads((folder/'registro_preservacao.json').read_text());blob=base64.b64decode(''.join((folder/n).read_text('ascii').strip() for n in record['parts']),validate=True);assert len(blob)==record['zip_bytes'] and sha(blob)==record['zip_sha256'];dest=a.destino.resolve();dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert set(z.namelist())==set(record['files'])
        for n,m in record['files'].items():
            f=(dest/n).resolve();assert f.is_relative_to(dest);b=z.read(n);assert len(b)==m['bytes'] and sha(b)==m['sha256'];f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b);assert sha(f.read_bytes())==m['sha256']
    print(json.dumps(dict(status='restored_hash_verified',files=len(record['files']),destination=str(dest))))

if __name__=='__main__':main()

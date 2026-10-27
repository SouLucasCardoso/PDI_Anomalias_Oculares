"""Preserva rodadas auditadas de24/10 e recupera verificando todos os bytes."""
from pathlib import Path
import argparse,base64,hashlib,io,json,tempfile,zipfile
ROOT=Path(__file__).resolve().parent
NAMES=['calibracao_multicondicao_treino_2026-10-24','porta_limpa_multicondicao_val_2026-10-24','troca_polar_parametros_originais_val_2026-10-24']
SCRIPTS=['calibracao_multicondicao.py','test_calibracao_multicondicao.py','avaliar_calibracao_multicondicao.py','avaliar_porta_limpa_multicondicao.py','auditar_rodadas_2026-10-24.py','avaliar_troca_polar_congelada.py','auditar_troca_polar_congelada.py','preservar_rodadas_2026-10-24.py']
BACKUP=ROOT/'backups/rodadas_2026-10-24'
def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--preparar',type=Path);p.add_argument('--destino',type=Path,default=Path(tempfile.gettempdir())/'pfc-rodadas-restauradas-20261024');a=p.parse_args()
    if a.preparar:
        files={}
        for name in NAMES:
            folder=a.preparar/name;assert (folder/'CONCLUIDO.json').exists() and (folder/'AUDITORIA_REPRODUCAO.json').exists()
            for f in folder.iterdir():
                if f.is_file():files[name+'/'+f.name]=f.read_bytes()
        for name in SCRIPTS:files['scripts/'+name]=(ROOT/name).read_bytes()
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
            for n,d in files.items():z.writestr(n,d)
        blob=stream.getvalue();encoded=base64.b64encode(blob).decode('ascii');stage=a.preparar/'preservacao_rodadas_2026-10-24';stage.mkdir(exist_ok=True);parts=[]
        for start in range(0,len(encoded),1000000):
            n=f'parte_{len(parts)+1:03}.b64';parts.append(n);(stage/n).write_text(encoded[start:start+1000000],encoding='ascii')
        record=dict(zip_bytes=len(blob),zip_sha256=sha(blob),parts=parts,files={n:dict(bytes=len(d),sha256=sha(d)) for n,d in files.items()},cloud_upload_verified=False)
        (stage/'registro_preservacao.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(dict(files=len(files),parts=len(parts),zip_bytes=len(blob),stage=str(stage))));return
    record=json.loads((BACKUP/'registro_preservacao.json').read_text());blob=base64.b64decode(''.join((BACKUP/n).read_text('ascii').strip() for n in record['parts']),validate=True);assert len(blob)==record['zip_bytes'] and sha(blob)==record['zip_sha256'];dest=a.destino.resolve();dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert set(z.namelist())==set(record['files']) and z.testzip() is None
        for n,meta in record['files'].items():
            target=(dest/n).resolve();assert target.is_relative_to(dest);data=z.read(n);assert len(data)==meta['bytes'] and sha(data)==meta['sha256'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert sha(target.read_bytes())==meta['sha256']
    print(json.dumps(dict(status='rounds_restored_all_hashes_verified',files=len(record['files']),destination=str(dest))))
if __name__=='__main__':main()

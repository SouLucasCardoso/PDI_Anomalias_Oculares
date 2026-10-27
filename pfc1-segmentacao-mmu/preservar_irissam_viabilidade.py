"""Preserva resultados pequenos; checkpoint publico2.56GB permanece por hash/link."""
from pathlib import Path
import argparse,base64,hashlib,io,json,tempfile,zipfile
from avaliar_irissam_ubipr import ROOT,NAME
BACKUP=ROOT/'backups'/NAME
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--preparar',type=Path);p.add_argument('--destino',type=Path,default=Path(tempfile.gettempdir())/'pfc-irissam-restaurado-20261023');a=p.parse_args()
    if a.preparar:
        folder=a.preparar/NAME;assert (folder/'AUDITORIA_REPRODUCAO.json').exists();files={}
        for file in folder.iterdir():
            if file.is_file():files[NAME+'/'+file.name]=file.read_bytes()
        for name in ['avaliar_irissam_ubipr.py','test_irissam_viabilidade.py','verificar_irissam_ubipr.py','preservar_irissam_viabilidade.py','baixar_pesos_irissam.py','baixar_irissam_segmentado.py','inspecionar_checkpoint_irissam_remoto.py','auditar_codigo_irissam.py','verificar_compatibilidade_irissam.py']:
            files['scripts/'+name]=(ROOT/name).read_bytes()
        files['scripts/visualizar_irissam_viabilidade.py']=(ROOT/'visualizar_irissam_viabilidade.py').read_bytes()
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in files.items():z.writestr(name,data)
        blob=stream.getvalue();encoded=base64.b64encode(blob).decode('ascii');stage=a.preparar/'preservacao_irissam';stage.mkdir(exist_ok=True);parts=[]
        for start in range(0,len(encoded),64000):
            name=f'parte_{len(parts)+1:03}.b64';parts.append(name);(stage/name).write_text(encoded[start:start+64000],encoding='ascii')
        provenance=json.loads((folder/'PROVENIENCIA_CHECKPOINT.json').read_text());record=dict(zip_bytes=len(blob),zip_sha256=sha(blob),parts=parts,files={n:dict(bytes=len(d),sha256=sha(d)) for n,d in files.items()},excluded_public_checkpoint=provenance['checkpoint'])
        (stage/'registro_preservacao.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(dict(files=len(files),parts=len(parts),zip_bytes=len(blob),stage=str(stage))));return
    record=json.loads((BACKUP/'registro_preservacao.json').read_text());blob=base64.b64decode(''.join((BACKUP/n).read_text('ascii').strip() for n in record['parts']),validate=True);assert len(blob)==record['zip_bytes'] and sha(blob)==record['zip_sha256'];dest=a.destino.resolve();dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert set(z.namelist())==set(record['files'])
        for name,meta in record['files'].items():
            target=(dest/name).resolve();assert target.is_relative_to(dest);data=z.read(name);assert len(data)==meta['bytes'] and sha(data)==meta['sha256'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert sha(target.read_bytes())==meta['sha256']
    print(json.dumps(dict(status='restored_hash_verified',files=len(record['files']),destination=str(dest))))
if __name__=='__main__':main()

"""Preserva o piloto fixo sem caches; restaura verificando cada hash."""
from pathlib import Path
import argparse,base64,hashlib,io,json,tempfile,zipfile
import numpy as np
NAME='diversidade_oclusao_treino_2026-10-24'
ROOT=Path(__file__).resolve().parent
BACKUP=ROOT/'backups'/NAME
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--preparar',type=Path);p.add_argument('--destino',type=Path,default=Path(tempfile.gettempdir())/'pfc-diversidade-restaurado-20261024');a=p.parse_args()
    if a.preparar:
        folder=a.preparar/NAME;assert (folder/'AUDITORIA_REPRODUCAO.json').exists();files={};excluded={}
        for file in folder.iterdir():
            if not file.is_file():continue
            name=NAME+'/'+file.name;data=file.read_bytes()
            if file.name.startswith('cache_'):excluded[name]=dict(bytes=len(data),sha256=sha(data))
            else:files[name]=data
        for name in ['treinar_diversidade_oclusao.py','oclusao_diversa_polar.py','ajuste_bloco_polar.py','auditar_diversidade_oclusao.py','reproduzir_amostra_oclusao_diversa.py','test_oclusao_diversa_polar.py','preservar_diversidade_oclusao.py','perda_fmr_polar.py','encoder_polar_espacial.py','perda_top3_polar.py','perda_identidade_polar.py','treinar_adaptador_polar.py','treinar_adaptador_polar_original.py']:
            files['scripts/'+name]=(ROOT/name).read_bytes()
        # Exact reversible byte delta avoids storing duplicate checkpoint tensors twice.
        selected=files[NAME+'/melhor_modelo.pt'];last=files.pop(NAME+'/ultima_epoca.pt');size=max(len(selected),len(last))
        delta=np.bitwise_xor(np.frombuffer(selected.ljust(size,b'\0'),np.uint8),np.frombuffer(last.ljust(size,b'\0'),np.uint8)).tobytes()
        files[NAME+'/ultima_epoca.xor']=delta
        reconstruction=dict(base=NAME+'/melhor_modelo.pt',delta=NAME+'/ultima_epoca.xor',target=NAME+'/ultima_epoca.pt',bytes=len(last),sha256=sha(last))
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in files.items():z.writestr(name,data)
        blob=stream.getvalue();encoded=base64.b64encode(blob).decode('ascii');stage=a.preparar/'preservacao_diversidade';stage.mkdir(exist_ok=True);parts=[]
        for start in range(0,len(encoded),1000000):
            name=f'parte_{len(parts)+1:03}.b64';parts.append(name);(stage/name).write_text(encoded[start:start+1000000],encoding='ascii')
        record=dict(zip_bytes=len(blob),zip_sha256=sha(blob),parts=parts,files={n:dict(bytes=len(d),sha256=sha(d)) for n,d in files.items()},excluded_feature_caches=excluded,reconstructed_checkpoint=reconstruction)
        (stage/'registro_preservacao.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(dict(files=len(files),parts=len(parts),zip_bytes=len(blob),stage=str(stage))));return
    record=json.loads((BACKUP/'registro_preservacao.json').read_text());blob=base64.b64decode(''.join((BACKUP/n).read_text('ascii').strip() for n in record['parts']),validate=True);assert len(blob)==record['zip_bytes'] and sha(blob)==record['zip_sha256'];dest=a.destino.resolve();dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert set(z.namelist())==set(record['files'])
        for name,meta in record['files'].items():
            target=(dest/name).resolve();assert target.is_relative_to(dest);data=z.read(name);assert len(data)==meta['bytes'] and sha(data)==meta['sha256'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert sha(target.read_bytes())==meta['sha256']
    spec=record['reconstructed_checkpoint'];base=(dest/spec['base']).read_bytes();delta=(dest/spec['delta']).read_bytes();assert len(delta)>=len(base)
    restored=np.bitwise_xor(np.frombuffer(base.ljust(len(delta),b'\0'),np.uint8),np.frombuffer(delta,np.uint8)).tobytes()[:spec['bytes']];assert sha(restored)==spec['sha256'];(dest/spec['target']).write_bytes(restored);assert sha((dest/spec['target']).read_bytes())==spec['sha256']
    print(json.dumps(dict(status='restored_hash_verified',files=len(record['files']),destination=str(dest))))
if __name__=='__main__':main()

"""Preserva o piloto fixo sem caches; restaura verificando cada hash."""
from pathlib import Path
import argparse,base64,hashlib,io,json,tempfile,zipfile
from treinar_encoder_polar_espacial import NAME,ROOT
from preparar_encoder_espacial import file_hash
BACKUP=ROOT/'backups'/NAME
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--preparar',type=Path);p.add_argument('--destino',type=Path,default=Path(tempfile.gettempdir())/'pfc-encoder-espacial-restaurado-20261023');a=p.parse_args()
    if a.preparar:
        folder=a.preparar/NAME;assert (folder/'AUDITORIA_REPRODUCAO.json').exists();files={};excluded={}
        for file in folder.iterdir():
            if not file.is_file():continue
            name=NAME+'/'+file.name
            if file.name.startswith('cache_'):excluded[name]=dict(bytes=file.stat().st_size,sha256=file_hash(file))
            else:files[name]=file.read_bytes()
        validation=a.preparar/NAME.replace('_2026','_val_2026')
        assert (validation/'CONCLUIDO.json').exists()
        for file in validation.iterdir():
            if file.is_file():files[validation.name+'/'+file.name]=file.read_bytes()
        for name in ['treinar_encoder_polar_espacial.py','encoder_polar_espacial.py','preparar_encoder_espacial.py','test_encoder_polar_espacial.py','perda_top3_polar.py','perda_identidade_polar.py','verificar_encoder_espacial.py','preservar_encoder_espacial.py','validar_encoder_espacial.py','treinar_adaptador_polar_original.py','treinar_adaptador_polar.py']:
            files['scripts/'+name]=(ROOT/name).read_bytes()
        vf=json.loads((validation/'CONCLUIDO.json').read_text())
        if vf['validation_identity_inference']:
            from validar_encoder_espacial import ORDER,SUFFIX
            for tag,suffix in SUFFIX.items():
                for name in ORDER:
                    file=ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21'/f'scores_{name}.npz';files[f'dependency_original_components/{tag}/scores_{name}.npz']=file.read_bytes()
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in files.items():z.writestr(name,data)
        blob=stream.getvalue();encoded=base64.b64encode(blob).decode('ascii');stage=a.preparar/'preservacao_encoder_espacial';stage.mkdir(exist_ok=True);parts=[]
        for start in range(0,len(encoded),64000):
            name=f'parte_{len(parts)+1:03}.b64';parts.append(name);(stage/name).write_text(encoded[start:start+64000],encoding='ascii')
        record=dict(zip_bytes=len(blob),zip_sha256=sha(blob),parts=parts,files={n:dict(bytes=len(d),sha256=sha(d)) for n,d in files.items()},excluded_feature_caches=excluded)
        (stage/'registro_preservacao.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(dict(files=len(files),parts=len(parts),zip_bytes=len(blob),stage=str(stage))));return
    record=json.loads((BACKUP/'registro_preservacao.json').read_text());blob=base64.b64decode(''.join((BACKUP/n).read_text('ascii').strip() for n in record['parts']),validate=True);assert len(blob)==record['zip_bytes'] and sha(blob)==record['zip_sha256'];dest=a.destino.resolve();dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert set(z.namelist())==set(record['files'])
        for name,meta in record['files'].items():
            target=(dest/name).resolve();assert target.is_relative_to(dest);data=z.read(name);assert len(data)==meta['bytes'] and sha(data)==meta['sha256'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert sha(target.read_bytes())==meta['sha256']
    print(json.dumps(dict(status='restored_hash_verified',files=len(record['files']),destination=str(dest))))
if __name__=='__main__':main()






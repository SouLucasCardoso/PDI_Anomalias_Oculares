"""Pacote compacto do contorno externo, sem caches de treino ou fotos."""
import argparse,base64,hashlib,io,json,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
NAMES=['contorno_externo_2026-10-23','contorno_externo_val_2026-10-23','contorno_consistente_2026-10-23','contorno_consistente_val_2026-10-23']
BACKUP=ROOT/'backups/contorno_externo_2026-10-23'
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--preparar',type=Path);p.add_argument('--destino',type=Path,default=Path(tempfile.gettempdir())/'pfc-contorno-restaurado-20261023');a=p.parse_args()
    if a.preparar:
        files={};reproducible={}
        for name in NAMES:
            folder=a.preparar/name;assert (folder/'CONCLUIDO.json').exists()
            for file in folder.rglob('*'):
                if not file.is_file():continue
                relative=name+'/'+file.relative_to(folder).as_posix()
                if file.name.startswith(('inputs_','changed_inputs')):
                    reproducible[relative]=dict(bytes=file.stat().st_size,sha256=sha(file.read_bytes()));continue
                files[relative]=file.read_bytes()
        for name in ['contorno_externo.py','treinar_contorno_externo.py','treinar_contorno_consistente.py','validar_contorno_externo.py','auditar_contorno_externo.py','test_contorno_externo.py','preservar_contorno_externo.py','verificar_recuperacao_contorno.py']:
            files['scripts/'+name]=(ROOT/name).read_bytes()
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in files.items():z.writestr(name,data)
        blob=stream.getvalue();encoded=base64.b64encode(blob).decode('ascii');stage=a.preparar/'preservacao_contorno';stage.mkdir(exist_ok=True);parts=[]
        for start in range(0,len(encoded),64000):
            name=f'parte_{len(parts)+1:03}.b64';parts.append(name);(stage/name).write_text(encoded[start:start+64000],encoding='ascii')
        record=dict(zip_bytes=len(blob),zip_sha256=sha(blob),parts=parts,files={n:dict(bytes=len(d),sha256=sha(d)) for n,d in files.items()},excluded_reproducible_feature_or_image_caches=reproducible)
        (stage/'registro_preservacao.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(dict(stage=str(stage),files=len(files),parts=len(parts),zip_bytes=len(blob))));return
    record=json.loads((BACKUP/'registro_preservacao.json').read_text('utf-8'));blob=base64.b64decode(''.join((BACKUP/n).read_text('ascii').strip() for n in record['parts']),validate=True)
    assert len(blob)==record['zip_bytes'] and sha(blob)==record['zip_sha256'];dest=a.destino.resolve();dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert set(z.namelist())==set(record['files'])
        for name,meta in record['files'].items():
            target=(dest/name).resolve()
            if not target.is_relative_to(dest):raise ValueError('Caminho fora do destino')
            data=z.read(name);assert len(data)==meta['bytes'] and sha(data)==meta['sha256'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert sha(target.read_bytes())==meta['sha256']
    print(json.dumps(dict(status='restaurado_e_verificado',files=len(record['files']),destino=str(dest))))
if __name__=='__main__':main()

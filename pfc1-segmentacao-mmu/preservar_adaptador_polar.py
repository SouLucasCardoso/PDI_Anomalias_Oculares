"""Preservação compacta de adaptador, escores e registros; caches por hash."""
import argparse,base64,hashlib,io,json,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
NAMES=['adaptador_polar_cadastro_fixo_2026-10-23','adaptador_polar_cadastro_fixo_val_2026-10-23']
BACKUP=ROOT/'backups/adaptador_polar_2026-10-23'
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--preparar',type=Path);p.add_argument('--destino',type=Path,default=Path(tempfile.gettempdir())/'pfc-adaptador-restaurado-20261023');a=p.parse_args()
    if a.preparar:
        files={};excluded={}
        for name in NAMES:
            folder=a.preparar/name;assert (folder/'CONCLUIDO.json').exists()
            for file in folder.rglob('*'):
                if not file.is_file():continue
                relative=name+'/'+file.relative_to(folder).as_posix()
                if file.name.startswith('cache_'):
                    excluded[relative]=dict(bytes=file.stat().st_size,sha256=sha(file.read_bytes()));continue
                files[relative]=file.read_bytes()
        validation=json.loads((a.preparar/NAMES[1]/'CONCLUIDO.json').read_text())
        technical=a.preparar/'adaptador_polar_2026-10-23'
        for name in ['protocolo.json','source.py','TECHNICAL_INVALID_MONITOR.json','AUDITORIA_DADOS.json','historico.csv','CONCLUIDO.json']:
            file=technical/name
            if file.exists():files['technical_invalid_monitor/'+name]=file.read_bytes()
        if validation['validation_identity_inference']:
            for tag in ['clean','upper10','lower10']:
                for name in ['spatial','transformer','arc_clahe','arc_red']:
                    file=a.preparar/'contorno_consistente_val_2026-10-23'/tag/f'scores_{name}.npz';files[f'dependency_outer_components/{tag}/scores_{name}.npz']=file.read_bytes()
        for name in ['adaptador_polar.py','treinar_adaptador_polar.py','validar_adaptador_polar.py','auditar_adaptador_polar.py','reproduzir_adaptador_polar.py','test_adaptador_polar.py','preservar_adaptador_polar.py','verificar_recuperacao_adaptador.py']:
            files['scripts/'+name]=(ROOT/name).read_bytes()
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in files.items():z.writestr(name,data)
        blob=stream.getvalue();encoded=base64.b64encode(blob).decode('ascii');stage=a.preparar/'preservacao_adaptador';stage.mkdir(exist_ok=True);parts=[]
        for start in range(0,len(encoded),64000):
            name=f'parte_{len(parts)+1:03}.b64';parts.append(name);(stage/name).write_text(encoded[start:start+64000],encoding='ascii')
        record=dict(zip_bytes=len(blob),zip_sha256=sha(blob),parts=parts,files={n:dict(bytes=len(d),sha256=sha(d)) for n,d in files.items()},excluded_reproducible_feature_caches=excluded)
        (stage/'registro_preservacao.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(dict(stage=str(stage),files=len(files),parts=len(parts),zip_bytes=len(blob))));return
    record=json.loads((BACKUP/'registro_preservacao.json').read_text());blob=base64.b64decode(''.join((BACKUP/n).read_text('ascii').strip() for n in record['parts']),validate=True)
    assert len(blob)==record['zip_bytes'] and sha(blob)==record['zip_sha256'];dest=a.destino.resolve();dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert set(z.namelist())==set(record['files'])
        for name,meta in record['files'].items():
            target=(dest/name).resolve()
            if not target.is_relative_to(dest):raise ValueError('Caminho fora do destino')
            data=z.read(name);assert len(data)==meta['bytes'] and sha(data)==meta['sha256'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert sha(target.read_bytes())==meta['sha256']
    print(json.dumps(dict(status='restaurado_e_verificado',files=len(record['files']),destino=str(dest))))
if __name__=='__main__':main()

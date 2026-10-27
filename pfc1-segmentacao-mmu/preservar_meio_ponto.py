"""Preserva dois pontos fracionarios e suas evidencias sem imagens ou pesos antigos."""
from pathlib import Path
import argparse,base64,hashlib,json,zipfile
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();source=a.output_root/'fronteira_meio_ponto_2026-10-23'
    assert (source/'AUDITORIA_FRONTEIRA.json').exists()
    out=a.output_root/'pacote_meio_ponto_2026-10-23';out.mkdir(exist_ok=False)
    members={f.relative_to(source).as_posix():f for f in source.rglob('*') if f.is_file() and f.suffix in ['.json','.csv','.py','.npz']}
    for name in ['refinar_meio_ponto.py','auditar_meio_ponto.py','test_meio_ponto.py','preservar_meio_ponto.py','incerteza_fronteira_area.py']:members['codigo/'+name]=ROOT/name
    archive=out/'resultados.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,file in members.items():z.write(file,name)
    sha=lambda data:hashlib.sha256(data).hexdigest();hashes={name:sha(f.read_bytes()) for name,f in members.items()}
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,expected in hashes.items():assert sha(z.read(name))==expected
    data=archive.read_bytes();parts=[]
    for i,start in enumerate(range(0,len(data),65536)):
        name=f'parte_{i:04d}.b64';part=data[start:start+65536];(out/name).write_text(base64.b64encode(part).decode('ascii')+'\n',encoding='ascii');parts.append(dict(name=name,sha256=sha(part)))
    manifest=dict(scope='Exact nine components+final score NPZ per new condition,per-query CSV,pixel interventions,protocol,completion,bootstrap/person counts,audit and source snapshots. Excludes input-image caches and frozen model weights already preserved separately. Original six conditions remain in existing project/backups.',zip_bytes=len(data),zip_sha256=sha(data),parts=parts,files=hashes,cloud_upload_verified=False,security_settings_changed=False)
    (out/'MANIFESTO.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(parts=len(parts),files=len(hashes),zip_bytes=len(data),zip_sha256=manifest['zip_sha256']),indent=2))

if __name__=='__main__':main()

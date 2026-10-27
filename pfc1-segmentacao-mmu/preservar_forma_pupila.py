"""Pacote de recuperacao textual, sem gravar nas pastas protegidas pelo Defender."""
from pathlib import Path
import argparse,base64,hashlib,json,zipfile
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    training=a.output_root/'forma_pupila_2026-10-23';evaluation=a.output_root/'forma_pupila_val_2026-10-23'
    assert (training/'CONCLUIDO.json').exists() and (evaluation/'VERIFICACAO_RELOAD.json').exists()
    out=a.output_root/'pacote_forma_pupila_2026-10-23';out.mkdir(exist_ok=False)
    members={}
    for folder in [training,evaluation]:
        for f in sorted(folder.iterdir()):
            if f.is_file() and f.suffix in ['.json','.csv','.py','.npz'] and not f.name.startswith('changed_inputs_'):
                members[folder.name+'/'+f.name]=f
    for name in ['pupila_eliptica.py','treinar_forma_pupila.py','validar_forma_pupila.py','verificar_forma_pupila.py','preservar_forma_pupila.py','test_pupila_eliptica.py']:
        members['codigo/'+name]=ROOT/name
    archive=out/'resultados.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,file in members.items():z.write(file,name)
    sha=lambda data:hashlib.sha256(data).hexdigest();hashes={name:sha(file.read_bytes()) for name,file in members.items()}
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,expected in hashes.items():assert sha(z.read(name))==expected
    data=archive.read_bytes();parts=[]
    for i,start in enumerate(range(0,len(data),65536)):
        part=data[start:start+65536];name=f'parte_{i:04d}.b64';(out/name).write_text(base64.b64encode(part).decode('ascii')+'\n',encoding='ascii');parts.append(dict(name=name,sha256=sha(part)))
    manifest=dict(scope='Exact selected8194parameter shape JSON, both protocols/histories, all15modified component score NPZ,12final score NPZ/CSV, completion/reload audit and six source files. Excludes changed_inputs image arrays, raw dataset and frozen pretrained models already preserved separately. Restore using restaurar_pacote_textual.py into writable temporary directory; ZIP preserves original bytes.',zip_bytes=len(data),zip_sha256=sha(data),parts=parts,files=hashes,cloud_upload_verified=False,security_settings_changed=False)
    (out/'MANIFESTO.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(parts=len(parts),zip_bytes=len(data),zip_sha256=manifest['zip_sha256']),indent=2))

if __name__=='__main__':main()

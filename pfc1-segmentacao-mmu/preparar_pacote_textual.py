"""Prepara pacote pequeno de modelo/escores de validacao; nao inclui datasets."""
from pathlib import Path
import argparse,base64,hashlib,json,zipfile


def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--part-bytes',type=int,default=8192);p.add_argument('--exclude',action='append',default=[]);p.add_argument('--include-csv',action='store_true');p.add_argument('--scope');a=p.parse_args()
    if not 1<=a.part_bytes<=1048576:raise ValueError('Part size must be1..1048576bytes')
    a.output.mkdir(parents=True,exist_ok=False);archive=a.output/'resultados.zip'
    suffixes=('.json','.py','.npz','.csv') if a.include_csv else ('.json','.py','.npz')
    files=sorted(file for file in a.source.iterdir() if file.is_file() and file.suffix in suffixes and file.name not in a.exclude)
    if not any(file.name=='CONCLUIDO.json' for file in files):raise ValueError('Completed experiment required')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for file in files:z.write(file,file.name)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('ZIP CRC failure')
    data=archive.read_bytes();parts=[]
    for i,start in enumerate(range(0,len(data),a.part_bytes)):
        value=data[start:start+a.part_bytes];name=f'parte_{i:04d}.b64'
        (a.output/name).write_text(base64.b64encode(value).decode('ascii'),encoding='ascii')
        parts.append(dict(name=name,sha256=hashlib.sha256(value).hexdigest()))
    manifest=dict(scope=a.scope or 'Model JSON, validation scores, protocol, completion, verification and script snapshots; no images, pretrained CNN weights, train feature arrays or per-condition train score matrices. Original encoders and input datasets required to recompute training.',
        zip_bytes=len(data),zip_sha256=hashlib.sha256(data).hexdigest(),parts=parts,
        files={file.name:hashlib.sha256(file.read_bytes()).hexdigest() for file in files})
    (a.output/'MANIFESTO.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(dict(parts=len(parts),zip_bytes=len(data),zip_sha256=manifest['zip_sha256']),indent=2))


if __name__=='__main__':main()

"""Obtem fontes academicas fixadas e cataloga pesos publicos sem altera-los."""
from pathlib import Path
import argparse
import hashlib
import json
import urllib.request
import gdown

ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download-default',action='store_true')
    args=parser.parse_args()
    tree=json.loads((ROOT/'data/catalogos/cvrl_tree.json').read_text(encoding='utf-8'))
    revision=tree['sha']; base='methods/HDBIF/Python/'
    target=ROOT/'data/modelos/cvrl_hdbif'; target.mkdir(parents=True,exist_ok=True)
    sources=[]
    for entry in tree['tree']:
        path=entry['path']
        if entry['type']!='blob' or not path.startswith(base): continue
        relative=path[len(base):]
        if not (relative.endswith(('.py','.yaml','.yml','.md','.txt'))): continue
        url=f'https://raw.githubusercontent.com/CVRL/OpenSourceIrisRecognition/{revision}/{path}'
        content=urllib.request.urlopen(url,timeout=60).read()
        if len(content)!=entry['size']: raise ValueError('Source size mismatch')
        git_hash=hashlib.sha1(f'blob {len(content)}\0'.encode()+content).hexdigest()
        if git_hash!=entry['sha']: raise ValueError('Source Git hash mismatch')
        output=target/relative; output.parent.mkdir(parents=True,exist_ok=True); output.write_bytes(content)
        sources.append({'path':relative,'url':url,'sha256':hashlib.sha256(content).hexdigest()})
    (target/'fontes.json').write_text(json.dumps({'revision':revision,'files':sources},indent=2),encoding='utf-8')
    files=gdown.download_folder('https://drive.google.com/drive/folders/1GU3jccid9ljghZrV5CvcLY4xuhWSaEsM',
                               skip_download=True,quiet=True)
    if not files: raise ValueError('Catalogo de pesos indisponivel')
    catalog=[{'id':f.id,'path':str(f.path)} for f in files]
    (ROOT/'data/catalogos/cvrl_drive_weights.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
    selected=[]
    if args.download_default:
        required=['filters_pt/finetuned_bsif_eyetracker_data/ICAtextureFilters_17x17_5bit.pt',
                  'models/nestedsharedatrousresunet-006-0.028214-maskIoU-0.938446.pth',
                  'models/resnet18-027-0.008222-maskIoU-0.967159.pth']
        for relative in required:
            item=next(r for r in catalog if r['path'].replace('\\','/')==relative)
            output=target/relative; output.parent.mkdir(parents=True,exist_ok=True)
            if not output.is_file():
                partial=output.with_suffix(output.suffix+'.part')
                if not gdown.download(id=item['id'],output=str(partial),quiet=True): raise RuntimeError(relative)
                partial.replace(output)
            selected.append({'path':relative,'drive_id':item['id'],'bytes':output.stat().st_size,
                             'sha256':hashlib.sha256(output.read_bytes()).hexdigest()})
        (target/'pesos.json').write_text(json.dumps({'files':selected,
            'note':'Circle checkpoint 027 is supplied in author Drive; source cfg names 1543, which was absent. Explicit override required; not an exact reproduction of cfg.'},indent=2),encoding='utf-8')
    print(json.dumps({'revision':revision,'sources':len(sources),'catalogued_weights':len(catalog),'downloaded':selected},indent=2))

if __name__=='__main__': main()

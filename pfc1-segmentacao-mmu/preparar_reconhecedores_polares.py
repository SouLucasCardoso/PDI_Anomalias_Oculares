"""Fontes CVRL fixadas para ArcIris/TripletIris, com verificacao Git e SHA256."""
from pathlib import Path
import argparse,hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser();parser.add_argument('method',choices=['ArcIris','TripletIris']);parser.add_argument('--download-weights',action='store_true');parser.add_argument('--output-root',type=Path);args=parser.parse_args()
    revision='4a535e4a9a0728e4428c25f743f6d59098ae397f'
    catalog=ROOT/'data/catalogos/cvrl_tree.json'
    if not catalog.exists():
        url=f'https://api.github.com/repos/CVRL/OpenSourceIrisRecognition/git/trees/{revision}?recursive=1'
        content=urllib.request.urlopen(url,timeout=60).read();catalog.parent.mkdir(parents=True,exist_ok=True);catalog.write_bytes(content)
    tree=json.loads(catalog.read_text())
    if tree['sha']!=revision or tree.get('truncated',False):raise ValueError('Unexpected or incomplete source catalog')
    prefix=f'methods/{args.method}/Python/'
    dest=(args.output_root or ROOT/'data/modelos')/('cvrl_'+args.method.lower());dest.mkdir(parents=True,exist_ok=True);files=[]
    for item in tree['tree']:
        if item['type']!='blob' or not item['path'].startswith(prefix):continue
        relative=item['path'][len(prefix):]
        if not relative.endswith(('.py','.yaml','.md','.txt','.yml')):continue
        url=f'https://raw.githubusercontent.com/CVRL/OpenSourceIrisRecognition/{revision}/{item["path"]}'
        output=dest/relative;output.parent.mkdir(parents=True,exist_ok=True)
        content=output.read_bytes() if output.exists() else urllib.request.urlopen(url,timeout=60).read()
        if len(content)!=item['size'] or hashlib.sha1(f'blob {len(content)}\0'.encode()+content).hexdigest()!=item['sha']:raise ValueError('Upstream Git checksum mismatch')
        output.write_bytes(content);files.append({'path':relative,'url':url,'sha256':hashlib.sha256(content).hexdigest()})
    (dest/'fontes.json').write_text(json.dumps({'method':args.method,'revision':revision,'files':files},indent=2),encoding='utf-8')
    print(args.method,'sources checked:',len(files))
    print((dest/'readme.md').read_text())
    print((dest/'cfg_baseline.yaml').read_text())
    if args.download_weights:
        if args.method!='TripletIris':raise ValueError('Only TripletIris public weights are registered here')
        import gdown
        required=[('convnext_tiny-znorm-best.pth','1fKC-cIqfaOcEo-_AcxVvLLlrk1hDwOoL','99b33c4efb6b32aa4f38c8eb77cc0bce99c71d987a8256daef155a4c4eb218ae'),
                  ('resnet18-1543-0.047488-maskIoU-0.934494.pth','16xsIlXJ6urljtk03kdMbl05Fa468TJup','aa333cbdd321785b10feedf41d9608d14d73fcf900b627b0611f08e69a1cad64')]
        weights=[]
        for name,drive_id,expected in required:
            output=dest/'models'/name;output.parent.mkdir(exist_ok=True)
            if not output.exists():
                partial=output.with_suffix(output.suffix+'.part')
                if not gdown.download(id=drive_id,output=str(partial),quiet=True):raise RuntimeError('Weight download failed')
                partial.replace(output)
            digest=hashlib.sha256(output.read_bytes()).hexdigest()
            if digest!=expected:raise ValueError('Weight differs from locally pinned public download')
            weights.append({'path':output.relative_to(dest).as_posix(),'drive_id':drive_id,'bytes':output.stat().st_size,'sha256':digest})
        (dest/'pesos.json').write_text(json.dumps({'files':weights},indent=2),encoding='utf-8')
        print('Public weights checked:',len(weights))

if __name__=='__main__':main()

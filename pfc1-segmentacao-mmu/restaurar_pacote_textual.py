"""Restaura ZIP de pesquisa preservado em partes base64, verificando SHA256."""
from pathlib import Path
import argparse,base64,hashlib,json,zipfile


def restore(folder,destination):
    manifest=json.loads((folder/'MANIFESTO.json').read_text(encoding='utf-8'))
    payload=[]
    for entry in manifest['parts']:
        name=entry['name']
        if Path(name).name!=name:raise ValueError('Invalid part path')
        part=base64.b64decode((folder/name).read_text(encoding='ascii').strip(),validate=True)
        if hashlib.sha256(part).hexdigest()!=entry['sha256']:raise ValueError('Corrupted part: '+name)
        payload.append(part)
    data=b''.join(payload)
    if len(data)!=manifest['zip_bytes'] or hashlib.sha256(data).hexdigest()!=manifest['zip_sha256']:raise ValueError('Archive integrity mismatch')
    destination.mkdir(parents=True,exist_ok=True)
    archive=destination/'resultados_verificados.zip'
    if archive.exists():raise ValueError('Destination archive already exists')
    archive.write_bytes(data)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('ZIP CRC failure')
        # Do not extract outside the caller-selected destination or overwrite files.
        target=destination/'resultados'
        if target.exists():raise ValueError('Extraction destination already exists')
        for info in z.infolist():
            candidate=(target/info.filename).resolve()
            if not candidate.is_relative_to(target.resolve()) or ':' in info.filename:raise ValueError('Unsafe ZIP member')
        z.extractall(target)
    return dict(zip_sha256=manifest['zip_sha256'],files=len(z.infolist()),destination=str(target))


def main():
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--destination',type=Path,required=True);a=p.parse_args()
    print(json.dumps(restore(a.folder,a.destination),indent=2))


if __name__=='__main__':main()

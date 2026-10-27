"""Recupera pacote pendente em TEMP, conferindo SHA e caminhos internos."""
from pathlib import Path
import argparse,base64,hashlib,io,json,tempfile,zipfile
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--destino',type=Path,default=Path(tempfile.gettempdir())/'pfc-pendencias-restauradas-20261024');a=p.parse_args();folder=ROOT/'backups/pendencias_retomada_2026-10-24';record=json.loads((folder/'registro_preservacao.json').read_text());blob=base64.b64decode(''.join((folder/n).read_text('ascii').strip() for n in record['parts']),validate=True)
    assert len(blob)==record['zip_bytes'] and hashlib.sha256(blob).hexdigest()==record['zip_sha256'];dest=a.destino.resolve();dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert z.testzip() is None and len(z.namelist())==record['zip_files'];inventory=json.loads(z.read('INVENTARIO_SHA256.json'))
        assert set(z.namelist())==set(inventory)|{'INVENTARIO_SHA256.json'}
        for name in z.namelist():
            target=(dest/name).resolve();assert target.is_relative_to(dest);data=z.read(name)
            if name in inventory:assert len(data)==inventory[name]['bytes'] and hashlib.sha256(data).hexdigest()==inventory[name]['sha256']
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert hashlib.sha256(target.read_bytes()).hexdigest()==hashlib.sha256(data).hexdigest()
    print(json.dumps(dict(status='pending_bundle_restored_hash_verified',files=record['zip_files'],destination=str(dest))))
if __name__=='__main__':main()

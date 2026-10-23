"""Copia os tres backups verificados para o projeto; nao prova upload na nuvem."""
from pathlib import Path
import hashlib,json,os,shutil
ROOT=Path(__file__).resolve().parent
EXPECTED={
    'pf_1021T204326.zip':'8176241fa48bd621714ac92eca41ba7b4c2b7e6efffc64c5ed6823028636b40c',
    'fusao_regularizada_2026-10-21.zip':'fe3b8e59491c6898cbd9b1e3f11d82a4be03435bd9b55281e763b772703c403f',
    'fusao_pessoas_separadas_2026-10-21.zip':'846004597db8803a601ebd32cf47451791473008ea980cdb3a5da62fb110507f'}


def digest(file):
    result=hashlib.sha256()
    with file.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):result.update(chunk)
    return result.hexdigest()


def main():
    source=Path.home()/'pfc-tcc-backups';destination=ROOT/'backups'
    if os.name!='nt':raise RuntimeError('This helper targets Windows and Windows no-overwrite rename semantics')
    # Validate ALL sources before starting any write.
    for name,expected in EXPECTED.items():
        if digest(source/name)!=expected:raise ValueError('Source checksum mismatch: '+name)
    destination.mkdir(parents=True,exist_ok=True);records=[]
    for name,expected in EXPECTED.items():
        target=destination/name
        if target.exists():
            if digest(target)!=expected:raise ValueError('Preserve conflicting destination: '+str(target))
            status='already_present_verified'
        else:
            temporary=destination/(name+'.copiando')
            with (source/name).open('rb') as src,temporary.open('xb') as dst:shutil.copyfileobj(src,dst,1024*1024)
            if digest(temporary)!=expected:raise ValueError('Copy checksum mismatch: '+name)
            temporary.rename(target)  # Windows raises if target appeared meanwhile.
            status='copied_verified'
        records.append(dict(file=str(target),bytes=target.stat().st_size,sha256=expected,status=status))
    print(json.dumps(dict(files=records,cloud_upload_verified=False,note='Files are in the OneDrive folder. Confirm upload in OneDrive status or web.'),indent=2))


if __name__=='__main__':main()

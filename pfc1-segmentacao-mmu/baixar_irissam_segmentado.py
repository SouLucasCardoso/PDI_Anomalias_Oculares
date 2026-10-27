"""Retoma download publico com oito intervalos HTTP validados, somente em TEMP."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse,hashlib,json,shutil,tempfile,time
from datetime import datetime,timezone
import requests
from baixar_pesos_irissam import URL,FILE_ID

def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=Path(tempfile.gettempdir())/'pfc-irissam');a=p.parse_args();folder=a.directory;folder.mkdir(parents=True,exist_ok=True);target=folder/'IrisSAM_model.pt';record=folder/'checkpoint_download.json';params=dict(id=FILE_ID,export='download',confirm='t')
    if target.exists():
        with target.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
        assert sha==json.loads(record.read_text())['sha256'];print('Checkpoint existente conferido.');return
    with requests.get(URL,params=params,headers={'Range':'bytes=0-0'},stream=True,timeout=60) as r:
        assert r.status_code==206;size=int(r.headers['Content-Range'].split('/')[-1])
    assert size==2564545909,'Public file size changed; inspect before transfer'
    prefix=folder/'IrisSAM_model.pt.part';plan_file=folder/'DOWNLOAD_SEGMENTADO.json'
    if plan_file.exists():plan=json.loads(plan_file.read_text());assert plan['bytes']==size
    else:
        offset=prefix.stat().st_size if prefix.exists() else 0;assert offset<size;step=(size-offset+7)//8;ranges=[]
        for start in range(offset,size,step):ranges.append(dict(start=start,end=min(size-1,start+step-1),file=f'chunk_{start:010}_{min(size-1,start+step-1):010}.part'))
        plan=dict(bytes=size,prefix_bytes=offset,ranges=ranges);plan_file.write_text(json.dumps(plan,indent=2),encoding='utf-8')
    assert (prefix.stat().st_size if prefix.exists() else 0)==plan['prefix_bytes']
    def download(part):
        path=folder/part['file'];expected=part['end']-part['start']+1;have=path.stat().st_size if path.exists() else 0;assert have<=expected
        if have==expected:return
        for attempt in range(3):
            try:
                have=path.stat().st_size if path.exists() else 0;start=part['start']+have
                with requests.get(URL,params=params,headers={'Range':f'bytes={start}-{part["end"]}'},stream=True,timeout=90) as r:
                    r.raise_for_status();assert r.status_code==206 and r.headers['Content-Range']==f'bytes {start}-{part["end"]}/{size}'
                    with path.open('ab') as f:
                        for block in r.iter_content(1024*1024):
                            if block:f.write(block)
                assert path.stat().st_size==expected;return
            except (requests.RequestException,OSError):
                if attempt==2:raise
    started=time.monotonic()
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures=[pool.submit(download,v) for v in plan['ranges']]
        while not all(f.done() for f in futures):
            for f in futures:
                if f.done():f.result()
            count=plan['prefix_bytes']+sum((folder/v['file']).stat().st_size if (folder/v['file']).exists() else 0 for v in plan['ranges']);print(json.dumps(dict(downloaded_MB=round(count/1e6,1),total_MB=round(size/1e6,1),seconds=round(time.monotonic()-started))),flush=True);time.sleep(10)
        for f in futures:f.result()
    sha=hashlib.sha256();assembled=folder/'IrisSAM_model.assembled'
    with assembled.open('wb') as output:
        for path in ([prefix] if plan['prefix_bytes'] else [])+[folder/v['file'] for v in plan['ranges']]:
            with path.open('rb') as source:
                while block:=source.read(4*1024*1024):output.write(block);sha.update(block)
    assert assembled.stat().st_size==size;assembled.replace(target)
    result=dict(downloaded_utc=datetime.now(timezone.utc).isoformat(),source='README public checkpoint link https://github.com/ParisaFarmanifard/Iris-SAM',google_drive_file_id=FILE_ID,path=str(target),bytes=size,sha256=sha.hexdigest(),range_download=True,network_credentials_used=False,seconds=time.monotonic()-started)
    record.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
if __name__=='__main__':main()

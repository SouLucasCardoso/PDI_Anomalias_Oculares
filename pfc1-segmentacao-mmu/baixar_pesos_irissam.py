"""Baixa somente o checkpoint publico indicado no README do Iris-SAM para TEMP."""
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime,timezone
import argparse,hashlib,json,tempfile,time
import requests
FILE_ID='1Oqr93dMaHMZfwd2M3FvM-q5Xnn_d321x'
URL='https://drive.usercontent.google.com/download'
class DownloadForm(HTMLParser):
    def __init__(self):super().__init__();self.params={}
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='input' and attrs.get('type')=='hidden' and attrs.get('name') in ['id','export','confirm','uuid']:self.params[attrs['name']]=attrs.get('value','')
def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=Path(tempfile.gettempdir())/'pfc-irissam');a=p.parse_args();a.directory.mkdir(exist_ok=True,parents=True);target=a.directory/'IrisSAM_model.pt';record=a.directory/'checkpoint_download.json'
    if target.exists() and record.exists():
        with target.open('rb') as f:value=hashlib.file_digest(f,'sha256').hexdigest()
        assert value==json.loads(record.read_text())['sha256'];print('Checkpoint existente com hash conferido.');return
    assert not target.exists();session=requests.Session();response=session.get(URL,params=dict(id=FILE_ID,export='download'),stream=True,timeout=60);response.raise_for_status()
    if 'text/html' in response.headers.get('content-type',''):
        form=DownloadForm();form.feed(response.text);response.close();assert form.params.get('id')==FILE_ID and form.params.get('confirm')=='t','Public download form unavailable'
        response=session.get(URL,params=form.params,stream=True,timeout=90);response.raise_for_status()
    assert 'text/html' not in response.headers.get('content-type',''),'Expected binary checkpoint, received HTML'
    sha=hashlib.sha256();count=0;started=time.monotonic();reported=started;partial=target.with_suffix('.pt.part')
    with partial.open('wb') as f:
        for block in response.iter_content(4*1024*1024):
            if not block:continue
            count+=len(block);assert count<4*1024**3,'Unexpected checkpoint size';f.write(block);sha.update(block)
            if time.monotonic()-reported>=10:
                print(json.dumps(dict(downloaded_MB=round(count/1e6,1),seconds=round(time.monotonic()-started))),flush=True);reported=time.monotonic()
    response.close();assert count>100*1024**2,'Checkpoint unexpectedly small';partial.replace(target)
    result=dict(downloaded_utc=datetime.now(timezone.utc).isoformat(),source='README public checkpoint link https://github.com/ParisaFarmanifard/Iris-SAM',google_drive_file_id=FILE_ID,path=str(target),bytes=count,sha256=sha.hexdigest(),seconds=time.monotonic()-started,network_credentials_used=False)
    record.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
if __name__=='__main__':main()

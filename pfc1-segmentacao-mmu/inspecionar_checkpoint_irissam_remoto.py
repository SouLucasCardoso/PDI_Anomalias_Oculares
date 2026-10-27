"""Le somente diretorio ZIP/pickle restrito e CRCs, nunca executa pickle externo."""
import argparse,collections,io,json,pickle,tempfile,zipfile
from pathlib import Path
import requests

class RangeReader(io.RawIOBase):
    def __init__(self,url,params=None):
        self.session=requests.Session();self.url=url;self.params=params;self.position=0;self.downloaded=0
        r=self.session.get(url,params=params,headers={'Range':'bytes=0-0'},timeout=60);r.raise_for_status();assert r.status_code==206;self.size=int(r.headers['Content-Range'].split('/')[-1]);self.downloaded+=len(r.content)
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.position
    def seek(self,offset,whence=0):
        self.position=offset if whence==0 else self.position+offset if whence==1 else self.size+offset;assert 0<=self.position<=self.size;return self.position
    def read(self,n=-1):
        n=min(self.size-self.position,n if n>=0 else self.size-self.position)
        if n==0:return b''
        assert n<=2*1024**2,'Metadata reader refuses tensor/bulk download'
        start=self.position;end=start+n-1;r=self.session.get(self.url,params=self.params,headers={'Range':f'bytes={start}-{end}'},timeout=60);r.raise_for_status();assert r.status_code==206 and len(r.content)==n;self.position+=n;self.downloaded+=n;return r.content

def tensor_metadata(storage,offset,size,stride,*args):return dict(storage=storage,offset=offset,shape=list(size),stride=list(stride))
class MetadataOnlyUnpickler(pickle.Unpickler):
    def find_class(self,module,name):
        if (module,name)==('collections','OrderedDict'):return collections.OrderedDict
        if module=='torch._utils' and name in ['_rebuild_tensor_v2','_rebuild_tensor']:return tensor_metadata
        if module=='torch' and name.endswith('Storage'):return name
        raise ValueError('Unrecognized pickle metadata global: '+module+'.'+name)
    def persistent_load(self,token):
        assert token[0]=='storage';return dict(dtype=token[1],key=token[2],location=token[3],elements=token[4])

def inspect(url,params=None):
    remote=RangeReader(url,params)
    with zipfile.ZipFile(remote) as z:
        names=z.namelist();data=next(n for n in names if n.endswith('/data.pkl'));state=MetadataOnlyUnpickler(io.BytesIO(z.read(data))).load()
        if 'model' in state and isinstance(state['model'],dict):state=state['model']
        prefix=data[:-len('data.pkl')];result={}
        for name,value in state.items():
            assert isinstance(value,dict) and 'storage' in value
            info=z.getinfo(prefix+'data/'+str(value['storage']['key']));result[name]=dict(shape=value['shape'],dtype=value['storage']['dtype'],bytes=info.file_size,crc32=info.CRC)
    return result,dict(bytes=remote.size,metadata_bytes_downloaded=remote.downloaded,tensors=len(result))

def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=Path(tempfile.gettempdir())/'pfc-irissam');a=p.parse_args();a.directory.mkdir(parents=True,exist_ok=True)
    iris,im=inspect('https://drive.usercontent.google.com/download',dict(id='1Oqr93dMaHMZfwd2M3FvM-q5Xnn_d321x',export='download',confirm='t'))
    result=dict(status='remote_checkpoint_metadata_inspected',iris=im,iris_metadata=iris,pickle_execution=False,method='Restrictedpicklemetadataonly;storagetensorsNEVERread. ZIPCRCcomparisonisprovenancehint,notcryptographicauthentication.')
    try:
        base,bm=inspect('https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth');assert set(base)==set(iris);comparison={}
        for prefix in ['image_encoder.','prompt_encoder.','mask_decoder.']:
            keys=[k for k in iris if k.startswith(prefix)];different=[k for k in keys if iris[k]!=base[k]];comparison[prefix]=dict(tensors=len(keys),different_crc_or_metadata=len(different),different_keys=different)
        result.update(base=bm,comparison=comparison)
    except Exception as e:result['base_comparison_unavailable']=type(e).__name__+': '+str(e)
    (a.directory/'INSPECAO_CHECKPOINT_REMOTO.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='iris_metadata'},indent=2))
if __name__=='__main__':main()

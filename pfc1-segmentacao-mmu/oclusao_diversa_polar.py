"""Intervencoes nativas variadas SOMENTE no ajuste; reconhecedor automatico."""
from pathlib import Path
import gc,json,time
import numpy as np
from PIL import Image

def paint(rgb,reference,kind,level,value):
    if kind not in ['upper','lower'] or not 0<=level<=100 or not 0<=value<=255:raise ValueError('Invalid intervention')
    affected=np.zeros_like(reference,bool);y,x=np.where(reference);order=np.lexsort((x,-y if kind=='lower' else y));take=order[:round(len(x)*level/100)];affected[y[take],x[take]]=True
    changed=np.array(rgb,dtype=np.uint8,copy=True);changed[affected]=value
    return Image.fromarray(changed),affected

class HybridMaps:
    def __init__(self,base,extra):
        if base.shape[1:]!=extra.shape[1:]:raise ValueError('Incompatible feature maps')
        self.base=base;self.extra=extra;self.shape=(len(base)+len(extra),*base.shape[1:])
    def __len__(self):return self.shape[0]
    def __getitem__(self,indices):
        scalar=np.isscalar(indices);ids=np.atleast_1d(indices).astype(np.int64)
        if (ids<0).any() or (ids>=len(self)).any():raise IndexError('Feature index out of bounds')
        result=np.empty((*ids.shape,*self.base.shape[1:]),dtype=self.base.dtype);old=ids<len(self.base);result[old]=self.base[ids[old]];result[~old]=self.extra[ids[~old]-len(self.base)]
        return result[0] if scalar else result

def prepare_diverse(out,protocol,base,mapping,valid,rows,device):
    import torch
    from treinar_identidade_iris import IdentityEncoder
    from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
    from encoder_polar_espacial import prefix_model,prefix_features
    from textura_polar import prepare_texture
    from preparar_encoder_espacial import ROOT,file_hash
    plan=protocol['augmentation_plan'];done_file=out/'CACHE_DIVERSO_CONCLUIDO.json';cache_file=out/'cache_diverso.npy';index_file=out/'cache_diverso_valid.npz'
    if not done_file.exists():
        assert not cache_file.exists(),'Preserve partial cache before recovery';started=time.monotonic();extra=np.lib.format.open_memmap(cache_file,mode='w+',dtype=np.float32,shape=(len(plan),256,4,32));ev=np.zeros(len(plan),bool);counts=[]
        encoder=IdentityEncoder().to(device).eval();encoder.load_state_dict(torch.load(ROOT/protocol['encoder_relative_path'],map_location='cpu',weights_only=True)['model']);prefix=prefix_model(encoder).to(device);unet=MulticlassUNet(8).to(device).eval();unet.load_state_dict(torch.load(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt',map_location='cpu',weights_only=True)['model']);manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());native={Path(r['image']).name:r for r in manifest['train']}
        for start in range(0,len(plan),32):
            photos=[]
            for item in plan[start:start+32]:
                row=rows[item['index']];assert row.subject in protocol['fit_people'] and row.session==2;record=native[Path(row.image).name]
                with Image.open(ROOT/'data/ubipr/single_eye'/Path(record['image']).name) as im:rgb=im.convert('RGB')
                with Image.open(ROOT/'data/ubipr/single_eye'/Path(record['mask']).name) as im:reference=decode_mask(im)==1
                changed,affected=paint(rgb,reference,item['kind'],item['level'],item['value']);photos.append(changed);counts.append(dict(reference_pixels=int(reference.sum()),affected_pixels=int(affected.sum())))
            x=torch.from_numpy(np.stack([np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for im in photos]).transpose(0,3,1,2).copy()).to(device)
            with torch.inference_mode():masks=unet(x).argmax(1).cpu().numpy()==1
            textures=[]
            for j,(photo,small) in enumerate(zip(photos,masks)):
                mask=np.asarray(Image.fromarray(small).resize(photo.size,Image.Resampling.NEAREST),bool)
                try:texture=prepare_texture(np.asarray(photo),mask)[0];ev[start+j]=True
                except ValueError:texture=np.full((64,512,3),127,np.uint8)
                textures.append(texture)
            extra[start:start+len(photos)]=prefix_features(prefix,np.stack(textures),device)
            if start%320==0:print(json.dumps(dict(phase='diverse_native_cache',processed=min(start+32,len(plan)),total=len(plan),seconds=round(time.monotonic()-started,1))),flush=True)
        extra.flush();del extra;np.savez_compressed(index_file,valid=ev);(out/'intervencoes_diversas.json').write_text(json.dumps(counts),encoding='utf-8');record=dict(status='native_diverse_fit_cache_completed',maps=len(plan),bytes=cache_file.stat().st_size,sha256=file_hash(cache_file),indices_sha256=file_hash(index_file),extraction_failures=int((~ev).sum()),all_fit_samples_retained=True,seconds=time.monotonic()-started);done_file.write_text(json.dumps(record,indent=2),encoding='utf-8');del unet,prefix,encoder;gc.collect()
        if torch.cuda.is_available():torch.cuda.empty_cache()
    else:record=json.loads(done_file.read_text())
    assert file_hash(cache_file)==record['sha256'] and file_hash(index_file)==record['indices_sha256'];extra=np.load(cache_file,mmap_mode='r')
    with np.load(index_file) as z:ev=z['valid']
    new_mapping=mapping.copy();new_valid=valid.copy();seen=set()
    for j,item in enumerate(plan):
        i=item['index'];view=1 if item['kind']=='upper' else 2;assert (i,view) not in seen and rows[i].subject in protocol['fit_people'] and rows[i].session==2;seen.add((i,view));new_mapping[i,view]=len(base)+j;new_valid[i,view]=ev[j]
    return HybridMaps(base,extra),new_mapping,new_valid

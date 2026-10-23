"""Ajuste da segmentacao com oclusao sintetica, somente treino/validacao."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import argparse,csv,hashlib,json,random,time
import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset,DataLoader
ROOT=Path(__file__).resolve().parent

def occlude(image,target,level,lower):
    """Altera pixels, nunca o alvo anotado; mascara nao restaura textura."""
    output=np.asarray(image).copy();y,x=np.where(np.asarray(target)==1)
    if len(x):
        order=np.lexsort((x,-y if lower else y));take=order[:round(len(x)*level/100)];output[y[take],x[take]]=128
    return output

def cache_rows(rows,folder):
    from treinar_segmentacao_ubipr import decode_mask
    folder.mkdir(parents=True,exist_ok=False)
    images=np.lib.format.open_memmap(folder/'images.npy',mode='w+',dtype=np.uint8,shape=(len(rows),240,320,3));masks=np.lib.format.open_memmap(folder/'masks.npy',mode='w+',dtype=np.uint8,shape=(len(rows),240,320))
    def decode(r):
        with Image.open(ROOT/'data/ubipr/single_eye'/Path(r['image']).name) as im:image=np.asarray(im.convert('RGB').resize((320,240),Image.Resampling.BILINEAR))
        with Image.open(ROOT/'data/ubipr/single_eye'/Path(r['mask']).name) as im:mask=decode_mask(im.resize((320,240),Image.Resampling.NEAREST)).astype(np.uint8)
        return image,mask
    with ThreadPoolExecutor(max_workers=4) as pool:
        for start in range(0,len(rows),64):
            for offset,(image,mask) in enumerate(pool.map(decode,rows[start:start+64])):images[start+offset]=image;masks[start+offset]=mask
            if start%640==0:print(f'Cache {folder.name}: {min(start+64,len(rows))}/{len(rows)}',flush=True)
    images.flush();masks.flush();return images,masks

class Inputs(Dataset):
    def __init__(self,images,masks,mode):self.images=images;self.masks=masks;self.mode=mode
    def __len__(self):return len(self.images)
    def __getitem__(self,i):
        image=np.array(self.images[i],copy=True);target=np.array(self.masks[i],dtype=np.int64,copy=True)
        if self.mode=='train':
            if random.random()<.5:image=occlude(image,target,random.uniform(1,40),random.random()<.5)
            if random.random()<.5:image=np.fliplr(image).copy();target=np.fliplr(target).copy()
        elif self.mode!='clean':image=occlude(image,target,10,self.mode=='lower10')
        return torch.from_numpy(image.transpose(2,0,1).copy()).float()/255,torch.from_numpy(target)

def main():
    from treinar_segmentacao_ubipr import MulticlassUNet,run_epoch,set_seed
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'segmentacao_oclusao_2026-10-21';out.mkdir(parents=True,exist_ok=False)
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_file.read_text());train=manifest['train'];val=manifest['val'];assert not {r['subject'] for r in train}&{r['subject'] for r in val}
    checkpoint=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';checkpoint_hash=hashlib.sha256(checkpoint.read_bytes()).hexdigest();assert checkpoint_hash=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Segmentation development ONLY train/validation; test was used in prior diagnostic but is not opened, inferred or used for checkpoint/parameter selection here',
      'model':'MulticlassUNet8 initialized from frozen original; FP32,320x240,B32,AdamW lr1e-4 wd1e-4,6epochs maximum,patience3,seed51',
      'augmentation':'50% unchanged,50% gray128 exact annotated iris pixels on resized320x240 input,random loss uniform1..40%,equal upper/lower; horizontal flip50%. Original class labels unchanged including gray occluded iris; no generated/restored RGB texture.',
      'evaluation':'Full1652 segmentation validation images, clean and fixed upper/lower10% input-grid occlusion. No recognition/test scores used for selection.',
      'selection':'Maximum minimum iris Dice across clean/upper10/lower10, tie mean3; clean Dice must stay >= original baseline clean Dice minus0.01. Include epoch0, save immutable best; no test-time choice.',
      'limitations':'Input-grid synthetic augmentation differs from native-pixel evaluation. Target covers originally annotated visible iris including synthetically hidden pixels, NOT full anatomical iris. Generalization to disease or natural occlusions not established.',
      'counts':{'train':len(train),'train_people':len({r['subject'] for r in train}),'val':len(val),'val_people':len({r['subject'] for r in val})},
      'checkpoint_sha256':checkpoint_hash,'manifest_sha256':hashlib.sha256(manifest_file.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'dependencies_sha256':{'treinar_segmentacao_ubipr.py':hashlib.sha256((ROOT/'treinar_segmentacao_ubipr.py').read_bytes()).hexdigest()}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());set_seed(51);torch.set_num_threads(4);torch.backends.cudnn.benchmark=False
    cache=a.output_root.parent/'cache_segmentacao_oclusao_2026-10-21';cache.mkdir(parents=True,exist_ok=False);tx,ty=cache_rows(train,cache/'train');vx,vy=cache_rows(val,cache/'val')
    loader=DataLoader(Inputs(tx,ty,'train'),batch_size=32,shuffle=True,num_workers=0);validation={mode:DataLoader(Inputs(vx,vy,mode),batch_size=32,shuffle=False,num_workers=0) for mode in ['clean','upper10','lower10']}
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');model=MulticlassUNet(8).to(device);model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model']);optimizer=torch.optim.AdamW(model.parameters(),lr=1e-4,weight_decay=1e-4)
    best=(-1.,-1.);best_epoch=0;stale=0;history=[];baseline_clean=None;started=time.monotonic()
    for epoch in range(7):
        training=run_epoch(model,loader,device,optimizer) if epoch else None
        evaluated={name:run_epoch(model,dl,device) for name,dl in validation.items()};dice={name:float(r['dice']['iris']) for name,r in evaluated.items()}
        if baseline_clean is None:baseline_clean=dice['clean']
        eligible=dice['clean']>=baseline_clean-.01;key=(min(dice.values()),float(np.mean(list(dice.values()))));row={'epoch':epoch,'train_loss':training['loss'] if training else None,**{f'{name}_iris_dice':v for name,v in dice.items()},'eligible_clean_guard':eligible};history.append(row)
        with (out/'historico.csv').open('w',newline='',encoding='utf-8') as stream:writer=csv.DictWriter(stream,fieldnames=list(row));writer.writeheader();writer.writerows(history)
        if eligible and key>best:
            best=key;best_epoch=epoch;stale=0;temporary=out/'melhor_modelo.pt.part';torch.save({'model':model.state_dict(),'epoch':epoch,'configuration':protocol,'validation':evaluated},temporary);temporary.replace(out/'melhor_modelo.pt')
        elif epoch:stale+=1
        print(json.dumps(row|{'seconds':time.monotonic()-started}),flush=True)
        if stale>=3:break
    final={'status':'occlusion_segmentation_training_completed','best_epoch':best_epoch,'epochs_trained':history[-1]['epoch'],'best_minimum_iris_dice':best[0],'history':history,'checkpoint_sha256':hashlib.sha256((out/'melhor_modelo.pt').read_bytes()).hexdigest(),'test_inference':False,'identity_recognition_evaluated':False,'minimum_area':None}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()

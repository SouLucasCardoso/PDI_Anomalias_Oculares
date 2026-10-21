"""Recortes em224 diretamente dos originais; U-Net congelada, sem super-resolucao."""
from pathlib import Path
import numpy as np
from PIL import Image
import torch

ROOT=Path(__file__).resolve().parent

def prepare(rows,segmenter,device,folder,split,size=224):
    from avaliar_dinov3_ubipr import masked_crop
    folder.mkdir(exist_ok=True,parents=True)
    target=folder/f'{split}_crops.npy'
    if target.exists():raise ValueError('Preserve native cache')
    images=np.lib.format.open_memmap(target,mode='w+',dtype=np.uint8,shape=(len(rows),size,size,3));valid=np.zeros(len(rows),bool)
    for start in range(0,len(rows),32):
        originals=[];inputs=[]
        for row in rows[start:start+32]:
            source=ROOT/'data/ubipr/single_eye'/Path(row.image).name
            with Image.open(source) as im:rgb=im.convert('RGB')
            originals.append(rgb);inputs.append(np.asarray(rgb.resize((320,240),Image.Resampling.BILINEAR),dtype=np.float32)/255)
        x=torch.from_numpy(np.stack(inputs).transpose(0,3,1,2).copy()).to(device)
        with torch.inference_mode():masks=segmenter(x).argmax(1).cpu().numpy()==1
        for offset,(rgb,mask) in enumerate(zip(originals,masks)):
            i=start+offset;mask=np.asarray(Image.fromarray(mask).resize(rgb.size,Image.Resampling.NEAREST),dtype=bool)
            valid[i]=bool(mask.any());images[i]=np.asarray(masked_crop(rgb,mask).resize((size,size),Image.Resampling.BILINEAR))
        if (start//32)%10==0:print(f'Native{size} {split} {min(start+32,len(rows))}/{len(rows)}',flush=True)
    images.flush();np.save(folder/f'{split}_valid.npy',valid)
    return images,valid

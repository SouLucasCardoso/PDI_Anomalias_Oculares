"""Canal vermelho sem contraste, mantendo geometria e suporte automaticos."""
from pathlib import Path
import cv2
import numpy as np
import torch
from PIL import Image
ROOT=Path(__file__).resolve().parent

def red_texture(rgb,mask):
    from textura_polar import prepare_texture
    from normalizacao_eliptica import ellipse_endpoints
    _,geometry=prepare_texture(rgb,mask)
    y,x=np.where(mask);width=int(x.max()-x.min()+1);height=int(y.max()-y.min()+1)
    x0=max(0,int(x.min())-max(2,round(width*.5)));y0=max(0,int(y.min())-max(2,round(height*.5)))
    x1=min(rgb.shape[1],int(x.max())+max(2,round(width*.5))+1);y1=min(rgb.shape[0],int(y.max())+max(2,round(height*.5))+1)
    theta=np.arange(512)*2*np.pi/512;t=np.arange(1,65)[:,None]/64
    ax,ay=ellipse_endpoints(geometry['pupil_ellipse'],theta);bx,by=ellipse_endpoints(geometry['iris_ellipse'],theta)
    mx=((1-t)*ax+t*bx).astype(np.float32);my=((1-t)*ay+t*by).astype(np.float32)
    polar=cv2.remap(rgb[y0:y1,x0:x1,0],mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
    support=cv2.remap(mask[y0:y1,x0:x1].astype(np.uint8),mx,my,cv2.INTER_NEAREST,borderMode=cv2.BORDER_CONSTANT,borderValue=0)>0
    if not support.any():raise ValueError('No polar support')
    polar[~support]=127
    return np.repeat(polar[:,:,None],3,axis=2)

def prepare(rows,device,folder):
    from treinar_segmentacao_ubipr import MulticlassUNet
    folder.mkdir(parents=True,exist_ok=True);target=folder/'val_polar.npy'
    if target.exists():raise ValueError('Preserve prior red cache')
    model=MulticlassUNet(8).to(device).eval();model.load_state_dict(torch.load(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt',map_location='cpu',weights_only=True)['model'])
    images=np.lib.format.open_memmap(target,mode='w+',dtype=np.uint8,shape=(len(rows),64,512,3));valid=np.zeros(len(rows),bool)
    for start in range(0,len(rows),32):
        originals=[];inputs=[]
        for row in rows[start:start+32]:
            with Image.open(ROOT/'data/ubipr/single_eye'/Path(row.image).name) as im:rgb=im.convert('RGB')
            originals.append(rgb);inputs.append(np.asarray(rgb.resize((320,240),Image.Resampling.BILINEAR),dtype=np.float32)/255)
        x=torch.from_numpy(np.stack(inputs).transpose(0,3,1,2).copy()).to(device)
        with torch.inference_mode():masks=model(x).argmax(1).cpu().numpy()==1
        for offset,(rgb,mask) in enumerate(zip(originals,masks)):
            i=start+offset;mask=np.asarray(Image.fromarray(mask).resize(rgb.size,Image.Resampling.NEAREST),dtype=bool)
            try:images[i]=red_texture(np.asarray(rgb),mask);valid[i]=True
            except ValueError:images[i]=127
        if start%320==0:print(f'Raw red polar {start}/{len(rows)}',flush=True)
    images.flush();np.save(folder/'val_valid.npy',valid)
    return images,valid

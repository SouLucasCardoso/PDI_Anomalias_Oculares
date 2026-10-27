"""Controle de dominio: foto inteira menor no campo de entrada da U-Net.

Escala fixa1/3, moldura128. Sem anotacao/diagnostico na inferencia.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image
import torch
from avaliar_candidato_congelado import ROOT

def predict_clinical(photos,model,device):
    width,height=320//3,240//3;x0=(320-width)//2;y0=(240-height)//2
    inputs=[]
    for photo in photos:
        canvas=np.full((240,320,3),128,np.uint8);canvas[y0:y0+height,x0:x0+width]=np.asarray(photo.resize((width,height),Image.Resampling.BILINEAR));inputs.append(canvas.astype(np.float32)/255)
    x=torch.from_numpy(np.stack(inputs).transpose(0,3,1,2).copy()).to(device)
    with torch.inference_mode():small=model(x).argmax(1).cpu().numpy()==1
    return [np.asarray(Image.fromarray(m[y0:y0+height,x0:x0+width]).resize(photo.size,Image.Resampling.NEAREST),bool) for photo,m in zip(photos,small)]

def prepare(rows,device,folder):
    from treinar_segmentacao_ubipr import MulticlassUNet
    from avaliar_dinov3_ubipr import masked_crop
    from textura_polar import prepare_texture
    from preparar_polar_vermelho import red_texture
    folder.mkdir(parents=True,exist_ok=False);specs={'rgb':(128,128,3),'native':(224,224,3),'polar':(64,512,3),'red':(64,512,3)}
    arrays={k:np.lib.format.open_memmap(folder/(k+'.npy'),mode='w+',dtype=np.uint8,shape=(len(rows),*shape)) for k,shape in specs.items()};rv=np.zeros(len(rows),bool);pv=rv.copy();model=MulticlassUNet(8).to(device).eval();model.load_state_dict(torch.load(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt',map_location='cpu',weights_only=True)['model'])
    for start in range(0,len(rows),32):
        photos=[Image.open(r.image).convert('RGB') for r in rows[start:start+32]];masks=predict_clinical(photos,model,device)
        for j,(im,mask) in enumerate(zip(photos,masks)):
            i=start+j;rv[i]=mask.any();crop=masked_crop(im,mask)
            for k,size in [('rgb',128),('native',224)]:arrays[k][i]=np.asarray(crop.resize((size,size),Image.Resampling.BILINEAR))
            try:arrays['polar'][i]=prepare_texture(np.asarray(im),mask)[0];arrays['red'][i]=red_texture(np.asarray(im),mask);pv[i]=True
            except ValueError:arrays['polar'][i]=127;arrays['red'][i]=127
        print(f'Clinical scale3 preprocessing {min(start+32,len(rows))}/{len(rows)}',flush=True)
    for arr in arrays.values():arr.flush()
    np.savez_compressed(folder/'valid.npz',rgb=rv,polar=pv);(folder/'interventions.json').write_text(json.dumps(dict(synthetic_occlusion=False,scale=1/3,padding=128)),encoding='utf-8')
    return arrays,rv,pv

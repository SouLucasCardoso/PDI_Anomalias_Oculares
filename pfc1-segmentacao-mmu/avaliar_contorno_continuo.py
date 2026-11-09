"""Interpole a confianca antes do rotulo para evitar ampliar blocos binarios."""
from pathlib import Path
from datetime import datetime,timezone
import json,time
import cv2,numpy as np,torch
from PIL import Image
from recorte_iris_sam31_alta_res import sha,antialiased_crop
from treinar_segmentacao_ubipr import MulticlassUNet
ROOT=Path(__file__).resolve().parent

def continuous_mask(model,photo,clinical=False):
    w,h=(106,80) if clinical else (320,240)
    canvas=np.full((240,320,3),128,np.uint8);x0=(320-w)//2;y0=(240-h)//2
    canvas[y0:y0+h,x0:x0+w]=np.asarray(photo.resize((w,h),Image.Resampling.BILINEAR))
    x=torch.from_numpy(canvas.astype(np.float32).transpose(2,0,1).copy()/255)[None]
    with torch.inference_mode():logits=model(x)[0].numpy()
    margin=(logits[1]-np.max(logits[[0,2,3]],axis=0))[y0:y0+h,x0:x0+w]
    old=np.asarray(Image.fromarray(margin>0).resize(photo.size,Image.Resampling.NEAREST),bool)
    native=cv2.resize(margin,photo.size,interpolation=cv2.INTER_LINEAR)
    return old,native>0

def main():
    out=ROOT/'outputs/contorno_continuo_2026-11-08';out.mkdir(exist_ok=False)
    torch.set_num_threads(2);cv2.setNumThreads(1)
    rows=json.loads((ROOT/'outputs/refino_recorte_validacao_2026-11-08/protocolo.json').read_text())['rows']
    (out/'protocolo.json').write_text(json.dumps({'registered_utc':datetime.now(timezone.utc).isoformat(),'rows':rows,
        'method':'Same frozen U-Net; interpolate iris-vs-other-class continuous logit margin to native resolution before threshold0; no topology edits, geometry fitting or RGB changes',
        'source_sha256':sha(__file__),'scope':'Validation development subset; no recognition or clinical accuracy claim'},indent=2),encoding='utf-8')
    model=MulticlassUNet(8).eval();file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    model.load_state_dict(torch.load(file,map_location='cpu',weights_only=True)['model']);records=[]
    def dice(a,b):return float((2*(a&b).sum()+1e-6)/(a.sum()+b.sum()+1e-6))
    for row in rows:
        photo=Image.open(row['image']).convert('RGB');old,new=continuous_mask(model,photo)
        truth=np.asarray(Image.open(row['mask']).convert('L'))==85
        records.append({'image':Path(row['image']).name,'dice_previous':dice(old,truth),'dice_continuous':dice(new,truth)})
    clinical=json.loads((ROOT/'data/slpvld/manifesto.json').read_text(encoding='utf-8-sig'))
    from comparar_recortes_alta_res import NAMES
    for name in NAMES:
        row=next(r for r in clinical if Path(r['image']).name==name);photo=Image.open(row['image']).convert('RGB')
        old,new=continuous_mask(model,photo,clinical=True);folder=out/Path(name).stem;folder.mkdir()
        Image.fromarray(new.astype(np.uint8)*255).save(folder/'mask_nativa.png');antialiased_crop(photo,new).save(folder/'recorte_nativo.png')
    result={'records':records,'n':len(rows),'mean_dice_previous':float(np.mean([r['dice_previous'] for r in records])),
        'mean_dice_continuous':float(np.mean([r['dice_continuous'] for r in records])),
        'improved':sum(r['dice_continuous']>r['dice_previous'] for r in records),'unet_sha256':sha(file),'recognition_reevaluated':False}
    (out/'CONCLUIDO.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='records'}))

if __name__=='__main__':main()

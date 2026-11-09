"""Controle de desenvolvimento na validacao UBIPr; referencia apenas na avaliacao."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,time
import numpy as np
import cv2,torch
from PIL import Image
from recorte_iris_sam31_alta_res import Sam31HighResolution,sha
from treinar_segmentacao_ubipr import MulticlassUNet

ROOT=Path(__file__).resolve().parent

def dice(pred,truth):
    return float((2*(pred&truth).sum()+1e-6)/(pred.sum()+truth.sum()+1e-6))

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    out=a.output_dir;out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(2);cv2.setNumThreads(1)
    manifest=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    val=json.loads(manifest.read_text(encoding='utf-8-sig'))['val'];rng=np.random.default_rng(20261108)
    rows=[]
    for subject in sorted({r['subject'] for r in val}):
        for side in ('L','R'):
            eligible=sorted([r for r in val if r['subject']==subject and r['side']==side],key=lambda r:r['image'])
            rows.append(eligible[int(rng.integers(len(eligible)))])
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'selection':'One image per side per validation person, RNG20261108; no quality or outcome filtering',
        'rows':rows,'reference_used_for_prompt_or_selection':False,'scope':'Development subset, not independent test or clinical accuracy',
        'unet_image_resize':'PIL BILINEAR, matching frozen U-Net inference',
        'manifest_sha256':sha(manifest),'source_sha256':sha(__file__),'refiner_sha256':sha(ROOT/'recorte_iris_sam31_alta_res.py')}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    unet=MulticlassUNet(8).eval();checkpoint=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    unet.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
    photos=[Image.open(r['image']).convert('RGB') for r in rows];seeds=[]
    for photo in photos:
        x=torch.from_numpy(np.asarray(photo.resize((320,240),Image.Resampling.BILINEAR),np.float32).transpose(2,0,1).copy()/255)[None]
        with torch.inference_mode():m=unet(x).argmax(1)[0].numpy()==1
        seeds.append(np.asarray(Image.fromarray(m).resize(photo.size,Image.Resampling.NEAREST),bool))
    del unet
    model=Sam31HighResolution();records=[];start=time.monotonic()
    for i,(row,photo,seed) in enumerate(zip(rows,photos,seeds)):
        try:mask,detail=model.refine(photo,seed);status='refined'
        except ValueError as error:mask=seed;detail={'reason':str(error)};status='preserved_seed'
        # Referencia aberta somente depois de terminar a inferencia.
        truth=np.asarray(Image.open(row['mask']).convert('L'))==85
        record={'image':Path(row['image']).name,'subject':row['subject'],'side':row['side'],'status':status,
                'dice_previous':dice(seed,truth),'dice_refined':dice(mask,truth),'details':detail}
        records.append(record)
        print(json.dumps({k:v for k,v in record.items() if k!='details'}),flush=True)
    model.close()
    old=np.array([r['dice_previous'] for r in records]);new=np.array([r['dice_refined'] for r in records])
    result={'records':records,'n':len(records),'mean_dice_previous':float(old.mean()),'mean_dice_refined':float(new.mean()),
        'improved':int((new>old).sum()),'worsened':int((new<old).sum()),'fallbacks':sum(r['status']!='refined' for r in records),
        'recognition_reevaluated':False,'seconds':time.monotonic()-start,'model_audit':model.audit}
    (out/'CONCLUIDO.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('records','model_audit')}),flush=True)

if __name__=='__main__':main()

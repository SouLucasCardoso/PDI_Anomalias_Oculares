"""Adaptador explicito de contorno: avaliador e pesos historicos preservados."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,sys
import numpy as np
from PIL import Image
import cv2,torch
import avaliar_candidato_congelado as frozen
from recorte_iris_sam31_alta_res import sha
ROOT=Path(__file__).resolve().parent

def native_mask(margin,size):
    return cv2.resize(margin,size,interpolation=cv2.INTER_LINEAR)>0

def prepare_continuous(rows,device,folder,condition='original',level=0,fixed_geometry=False,segmenter_checkpoint=None):
    from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
    from avaliar_dinov3_ubipr import masked_crop
    from textura_polar import prepare_texture
    from preparar_polar_vermelho import red_texture
    from avaliar_robustez_reconhecimento import perturb
    assert not fixed_geometry and segmenter_checkpoint is None
    folder.mkdir(parents=True,exist_ok=False)
    specs={'rgb':(128,128,3),'native':(224,224,3),'polar':(64,512,3),'red':(64,512,3)}
    arrays={k:np.lib.format.open_memmap(folder/(k+'.npy'),mode='w+',dtype=np.uint8,shape=(len(rows),*shape)) for k,shape in specs.items()}
    rv=np.zeros(len(rows),bool);pv=rv.copy();interventions=[]
    model=MulticlassUNet(8).to(device).eval()
    model.load_state_dict(torch.load(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt',map_location='cpu',weights_only=True)['model'])
    for start in range(0,len(rows),32):
        photos=[];inputs=[]
        for row in rows[start:start+32]:
            photo=Image.open(row.image).convert('RGB')
            if condition!='original' and row.session==2:
                reference=decode_mask(Image.open(row.mask))==1
                photo,meta=perturb(photo,reference,condition,level)
                interventions.append({'image':Path(row.image).name,'reference_pixels':int(reference.sum()),'fraction_defined':bool(reference.any()),'affected_fraction':meta['affected_fraction']})
            photos.append(photo);inputs.append(np.asarray(photo.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255)
        x=torch.from_numpy(np.stack(inputs).transpose(0,3,1,2).copy()).to(device)
        with torch.inference_mode():logits=model(x).cpu().numpy()
        for offset,(photo,scores) in enumerate(zip(photos,logits)):
            i=start+offset;mask=native_mask(scores[1]-np.max(scores[[0,2,3]],axis=0),photo.size)
            rv[i]=mask.any();crop=masked_crop(photo,mask)
            arrays['rgb'][i]=np.asarray(crop.resize((128,128),Image.Resampling.BILINEAR))
            arrays['native'][i]=np.asarray(crop.resize((224,224),Image.Resampling.BILINEAR))
            try:arrays['polar'][i]=prepare_texture(np.asarray(photo),mask)[0];arrays['red'][i]=red_texture(np.asarray(photo),mask);pv[i]=True
            except ValueError:arrays['polar'][i]=127;arrays['red'][i]=127
        print(f'Continuous contour preprocessing {min(start+32,len(rows))}/{len(rows)}',flush=True)
    for array in arrays.values():array.flush()
    np.savez_compressed(folder/'valid.npz',rgb=rv,polar=pv)
    (folder/'interventions.json').write_text(json.dumps(interventions,indent=2),encoding='utf-8')
    return arrays,rv,pv

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--mask-mode',choices=['nearest','continuous'],required=True)
    p.add_argument('--condition',choices=['original','oclusao_superior','oclusao_inferior'],default='original');p.add_argument('--level',type=int,default=0)
    a=p.parse_args();a.output_root.mkdir(parents=True,exist_ok=True)
    assert (a.condition=='original' and a.level==0) or (a.condition!='original' and 0<a.level<100)
    supplement=a.output_root/f'CONTORNO_{a.condition}_{a.level}.json'
    assert not supplement.exists(),'Preserve previous evaluation'
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Development validation ONLY, repeatedly exposed people; no independent confirmation',
        'mask_mode':a.mask_mode,'condition':a.condition,'level':a.level,
        'change':'Only native mask mapping: interpolate continuous iris-vs-other-class logit margin before threshold0' if a.mask_mode=='continuous' else 'Unmodified frozen evaluator, fresh same-environment control',
        'identity_models_calibration_threshold_unchanged':True,'reference_only_defines_occlusion':True,
        'official_evaluator_source_unmodified':True,'wrapper_sha256':sha(__file__),
        'dependencies_sha256':{name:sha(ROOT/name) for name in ('avaliar_candidato_congelado.py','avaliar_robustez_reconhecimento.py','recorte_iris_sam31_alta_res.py')},
        'versions':{'torch':torch.__version__,'numpy':np.__version__}}
    supplement.write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    os.environ['HF_HUB_OFFLINE']='1';os.environ['HF_HOME']=(ROOT/'data/hf-home.txt').read_text(encoding='utf-8-sig').strip()
    os.environ['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib')
    if a.mask_mode=='continuous':frozen.prepare=prepare_continuous
    sys.argv=[str(ROOT/'avaliar_candidato_congelado.py'),'--split','val','--output-root',str(a.output_root),'--condition',a.condition,'--level',str(a.level)]
    frozen.main()

if __name__=='__main__':main()

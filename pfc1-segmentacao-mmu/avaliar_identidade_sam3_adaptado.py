"""Mesmos reconhecedores congelados, com preparacao por segmentador SAM3 adaptado."""
import argparse
import gc
import importlib.metadata
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image
import torch

from segmentador_sam3_iris import IrisSam3Adapter,Sam3VisualFeatures,SAM_REVISION
from treinar_sam3_iris_adaptado import sha
import avaliar_candidato_congelado as frozen

ROOT=Path(__file__).resolve().parent


def prepare_sam3(rows,device,folder,condition='original',level=0,fixed_geometry=False,segmenter_checkpoint=None):
    if fixed_geometry or segmenter_checkpoint is None:raise ValueError('Usar uma foto, geometria recalculada e pesos SAM3 explicitos')
    from avaliar_dinov3_ubipr import masked_crop
    from textura_polar import prepare_texture
    from preparar_polar_vermelho import red_texture
    from treinar_segmentacao_ubipr import decode_mask
    from avaliar_robustez_reconhecimento import perturb
    state=torch.load(segmenter_checkpoint,map_location='cpu',weights_only=True)
    if state.get('model_type')!='sam3_visual_iris_adapter' or state['sam_revision']!=SAM_REVISION:raise ValueError('Pesos nao correspondem ao adaptador SAM3')
    folder.mkdir(parents=True,exist_ok=False)
    specs={'rgb':(128,128,3),'native':(224,224,3),'polar':(64,512,3),'red':(64,512,3)}
    arrays={k:np.lib.format.open_memmap(folder/(k+'.npy'),mode='w+',dtype=np.uint8,shape=(len(rows),*shape)) for k,shape in specs.items()}
    rv=np.zeros(len(rows),bool);pv=rv.copy();interventions=[]
    extractor=Sam3VisualFeatures(str(device));model=IrisSam3Adapter().to(device).eval();model.load_state_dict(state['model'],strict=True)
    for i,row in enumerate(rows):
        with Image.open(row.image) as image:photo=image.convert('RGB')
        if condition!='original' and row.session==2:
            with Image.open(row.mask) as annotation:reference=decode_mask(annotation)==1
            photo,meta=perturb(photo,reference,condition,level)
            interventions.append({'image':Path(row.image).name,'reference_pixels':int(reference.sum()),
                                 'fraction_defined':bool(reference.any()),'affected_fraction':meta['affected_fraction']})
        rgb=np.asarray(photo.resize((416,320),Image.Resampling.BILINEAR))
        # Ambas as ramificacoes veem somente a foto alterada. Nao reutiliza embedding original.
        feature=extractor(rgb)
        x=torch.from_numpy(rgb.astype(np.float32).transpose(2,0,1).copy()/255)[None].to(device)
        with torch.inference_mode():small=model(x,torch.from_numpy(feature.astype(np.float32))[None].to(device)).argmax(1)[0].cpu().numpy()==1
        mask=np.asarray(Image.fromarray(small).resize(photo.size,Image.Resampling.NEAREST),bool)
        rv[i]=mask.any();crop=masked_crop(photo,mask)
        arrays['rgb'][i]=np.asarray(crop.resize((128,128),Image.Resampling.BILINEAR))
        arrays['native'][i]=np.asarray(crop.resize((224,224),Image.Resampling.BILINEAR))
        try:arrays['polar'][i]=prepare_texture(np.asarray(photo),mask)[0];arrays['red'][i]=red_texture(np.asarray(photo),mask);pv[i]=True
        except ValueError:arrays['polar'][i]=127;arrays['red'][i]=127
        if i==0 or (i+1)%50==0 or i+1==len(rows):print(f'SAM3 preprocessing {i+1}/{len(rows)}',flush=True)
    for array in arrays.values():array.flush()
    np.savez_compressed(folder/'valid.npz',rgb=rv,polar=pv)
    (folder/'interventions.json').write_text(json.dumps(interventions,indent=2),encoding='utf-8')
    del model,extractor;gc.collect()
    if str(device).startswith('cuda'):torch.cuda.empty_cache()
    return arrays,rv,pv


def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--output-root',type=Path,required=True);parser.add_argument('--split',required=True)
    parser.add_argument('--segmenter',type=Path);args,_=parser.parse_known_args()
    if args.split!='val' or '--fixed-geometry' in sys.argv:raise ValueError('Rodada autoriza somente validacao operacional')
    args.output_root.mkdir(parents=True,exist_ok=True)
    provenance={'scope':'New preparation adapter; original frozen identity score/calibration functions unchanged. Both controls rerun in same updated runtime.',
                'sources':{n:sha(ROOT/n) for n in ('avaliar_identidade_sam3_adaptado.py','segmentador_sam3_iris.py','avaliar_candidato_congelado.py')},
                'sam_revision':SAM_REVISION,'candidate_sha256':sha(args.segmenter) if args.segmenter else None,
                'versions':{n:importlib.metadata.version(n) for n in ('torch','torchvision','numpy','pillow','sam3')},
                'test_inference':False,'reference_masks_used_only_for_intervention':True}
    with (args.output_root/'ADAPTADOR_SAM3.json').open('x',encoding='utf-8') as stream:json.dump(provenance,stream,indent=2)
    if args.segmenter:frozen.prepare=prepare_sam3
    frozen.main()


if __name__=='__main__':main()

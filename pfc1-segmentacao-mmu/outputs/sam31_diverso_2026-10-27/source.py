"""Comparacao exploratoria pareada SAM3.1/U-Net: validacao e quatro casos clinicos.

Carrega estritamente a piramide de TRES niveis do detector multiplex SAM3.1.
Nao inicializa aleatoriamente a quarta convolucao usada apenas no SAM3 original.
As cabecas interactive/propagation e o tracker nao entram em segmentacao textual.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import gc
import importlib.metadata
import json
import os
from pathlib import Path
import time
import numpy as np
from PIL import Image, ImageDraw, ImageOps
import torch
from torch import nn
from treinar_segmentacao_ubipr import MulticlassUNet, decode_mask, sha256
from treinar_segmentacao_diversa import transform, MODES, IGNORE

ROOT = Path(__file__).resolve().parent


def load_detector(checkpoint, device):
    from sam3.model_builder import build_sam3_image_model
    model = build_sam3_image_model(device="cpu", load_from_HF=False, eval_mode=True)
    neck = model.backbone.vision_backbone
    if len(neck.convs) != 4 or model.backbone.scalp != 1:
        raise RuntimeError("Arquitetura inesperada; rever adaptacao SAM3.1 antes de inferir")
    # A implementacao oficial3.1 usa [4,2,1], contra [4,2,1,.5] do3.0.
    # O quarto nivel do3.0 era calculado e descartado por scalp=1.
    neck.convs = nn.ModuleList(list(neck.convs)[:3])
    neck.scale_factors = list(neck.scale_factors)[:3]
    model.backbone.scalp = 0
    state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    if "model" in state: state = state["model"]
    detector = {k.removeprefix("detector."):v for k,v in state.items() if k.startswith("detector.")}
    ignored = sorted(k for k in detector if k.startswith(("backbone.vision_backbone.interactive_convs.",
                                                          "backbone.vision_backbone.propagation_convs.")))
    semantic = {k:v for k,v in detector.items() if k not in ignored}
    result = model.load_state_dict(semantic, strict=True)
    report = {"strict":True, "missing":list(result.missing_keys), "unexpected":list(result.unexpected_keys),
              "semantic_tensors":len(semantic), "excluded_video_branch_tensors":ignored,
              "scales":neck.scale_factors, "random_missing_weights_used":False,
              "sam3_origin":json.loads(importlib.metadata.distribution("sam3").read_text("direct_url.json")),
              "installed_builder_sha256":sha256(Path(__import__('sam3.model_builder',fromlist=['x']).__file__))}
    del state, detector, semantic;gc.collect()
    return model.to(device).eval(), report


def metrics(pred, truth, valid):
    pred, truth = pred&valid, truth&valid
    tp=int((pred&truth).sum());pp=int(pred.sum());tt=int(truth.sum())
    return {"dice":(2*tp+1e-6)/(pp+tt+1e-6), "iou":(tp+1e-6)/(pp+tt-tp+1e-6),
            "prediction_pixels":pp,"reference_pixels":tt,"empty_prediction":pp==0}


def board(examples, destination, title):
    w,h=300,240
    canvas=Image.new("RGB",(4*w,len(examples)*(h+25)+40),"white");draw=ImageDraw.Draw(canvas)
    draw.text((10,10),title,fill="black")
    for index,(photo,unet,sam,label) in enumerate(examples):
        rgb=np.asarray(photo)
        panels=[photo]
        for mask in (unet,sam):
            overlay=rgb.copy();overlay[mask]=(rgb[mask]*.55+np.array([0,255,0])*.45).astype(np.uint8)
            panels.append(Image.fromarray(overlay))
        cut=rgb.copy();cut[~sam]=0;panels.append(Image.fromarray(cut))
        for col,(panel,name) in enumerate(zip(panels,("original","U-Net original","SAM3.1 estrito","recorte SAM3.1"))):
            y=40+index*(h+25);draw.text((col*w+5,y),name+" | "+label,fill="black")
            canvas.paste(ImageOps.pad(panel,(w,h),color="white"),(col*w,y+25))
    canvas.save(destination)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--people",type=int,default=16)
    p.add_argument("--seed",type=int,default=127)
    a=p.parse_args();a.output_dir.mkdir(parents=True,exist_ok=False)
    os.environ['HF_HOME']=(ROOT/'data/hf-home.txt').read_text(encoding='utf-8-sig').strip()
    os.environ['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib')
    from huggingface_hub import hf_hub_download
    from sam3.model.sam3_image_processor import Sam3Processor
    from avaliar_sam3_1_ubipr import collapse_masks
    manifest_path=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    subjects=sorted({r['subject'] for r in manifest['val']});rng=np.random.default_rng(a.seed)
    chosen=sorted(int(s) for s in rng.choice(subjects,min(a.people,len(subjects)),replace=False))
    rows=[next(r for r in sorted(manifest['val'],key=lambda r:r['image']) if r['subject']==s) for s in chosen]
    clinical_rows=json.loads((ROOT/'data/slpvld/manifesto.json').read_text(encoding='utf-8-sig'))
    names=('P0005_OD20241206.JPG','P0007_OS20250306.JPG','P0114_OS20250417.JPG','P0803_OD20250112.JPG')
    clinical=[next(r for r in clinical_rows if Path(r['image']).name==name) for name in names]
    checkpoint=Path(hf_hub_download('facebook/sam3.1','sam3.1_multiplex.pt',local_files_only=True,token=False))
    unet_path=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    protocol={"registered_utc":datetime.now(timezone.utc).isoformat(),"script_sha256":sha256(Path(__file__)),
              "scope":"Validation development; no test inference; SLPVLD qualitative ONLY without reference masks",
              "prompt":"iris of the eye","confidence":.5,"selection":"seed127 one first image per randomly selected validation person; no quality filtering",
              "samples":rows,"clinical":names,"modes":MODES,"seed":a.seed,
              "unet_sha256":sha256(unet_path),"manifest_sha256":sha256(manifest_path),
              "sam_checkpoint_sha256":sha256(checkpoint),"sam_checkpoint":str(checkpoint),
              "selection_by_ground_truth":False,"recognition_evaluation":False,
              "comparison":"U-Net original320x240FP32; SAM3.1 detector1008BF16; raw masks, no oracle prompts, same input photo and annotations",
              "macro":"all images, including empty reference/prediction; both empty yields1; per-person paired descriptive means"}
    (a.output_dir/'protocolo.json').write_text(json.dumps(protocol,indent=2,ensure_ascii=False),encoding='utf-8')
    (a.output_dir/'source.py').write_bytes(Path(__file__).read_bytes())
    device='cuda' if torch.cuda.is_available() else 'cpu';torch.set_num_threads(4)
    model,audit=load_detector(checkpoint,device)
    (a.output_dir/'carregamento_estrito.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    processor=Sam3Processor(model,device=device,confidence_threshold=.5)
    unet=MulticlassUNet(8).to(device).eval();unet.load_state_dict(torch.load(unet_path,map_location='cpu',weights_only=True)['model'])
    records=[];examples=[];saved={};started=time.monotonic()
    def predict(photo):
        with torch.inference_mode():
            x=torch.from_numpy(np.asarray(photo.resize((320,240)),np.float32).transpose(2,0,1).copy()/255)[None].to(device)
            u=unet(x).argmax(1)[0].cpu().numpy()==1
            u=np.asarray(Image.fromarray(u).resize(photo.size,Image.Resampling.NEAREST),bool)
            with torch.autocast('cuda',dtype=torch.bfloat16,enabled=device=='cuda'):
                state=processor.set_image(photo)
                output=processor.set_text_prompt(prompt='iris of the eye',state=state)
            s=collapse_masks(output['masks'],(photo.height,photo.width))
        return u,s
    for i,row in enumerate(rows):
        with Image.open(ROOT/'data/ubipr/single_eye'/Path(row['image']).name) as im:rgb=np.asarray(im.convert('RGB'))
        with Image.open(ROOT/'data/ubipr/single_eye'/Path(row['mask']).name) as im:mask=decode_mask(im).astype(np.uint8)
        for mode in MODES:
            image,target=transform(rgb,mask,640,480,mode,np.random.default_rng(a.seed+i))
            photo=Image.fromarray((image*255).astype(np.uint8));u,s=predict(photo)
            for method,pred in [('unet',u),('sam31_strict',s)]:
                records.append({'subject':row['subject'],'image':Path(row['image']).name,'mode':mode,'method':method,**metrics(pred,target==1,target!=IGNORE)})
                saved[f'{i}_{mode}_{method}']=np.packbits(pred)
            saved[f'{i}_{mode}_target']=target
            if i<2 and mode in ('clean','zoom3'):examples.append((photo,u,s,f'C{row["subject"]} {mode}'))
        print(f'Comparacao pareada {i+1}/{len(rows)}, {time.monotonic()-started:.1f}s',flush=True)
    board(examples,a.output_dir/'validacao_exemplos.png','Validacao: primeiras duas pessoas sorteadas; sem selecao por escore')
    clinical_examples=[];clinical_metrics=[]
    for row in clinical:
        with Image.open(row['image']) as im:photo=im.convert('RGB');photo.thumbnail((1200,1200))
        u,s=predict(photo);name=Path(row['image']).name
        clinical_examples.append((photo,u,s,name.split('_')[0]))
        clinical_metrics.append({'image':name,'diagnosis_raw':row['diagnosis_raw'],'sam_pixels':int(s.sum()),'unet_pixels':int(u.sum()),'no_reference_mask':True,'image_sha256':sha256(Path(row['image']))})
        saved[name+'_sam']=np.packbits(s);saved[name+'_unet']=np.packbits(u);saved[name+'_shape']=np.array(s.shape)
    board(clinical_examples,a.output_dir/'clinicos_normal_anomalia.png','SLPVLD: exemplos qualitativos, SEM mascaras de referencia ou Dice clinico')
    with (a.output_dir/'metricas_por_imagem.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    np.savez_compressed(a.output_dir/'mascaras.npz',**saved)
    summary={mode:{method:{k:float(np.mean([r[k] for r in records if r['mode']==mode and r['method']==method])) for k in ('dice','iou')} for method in ('unet','sam31_strict')} for mode in MODES}
    result={'status':'completed','summary':summary,'clinical_qualitative_only':clinical_metrics,'strict_load':audit,
            'people':len(rows),'paired_cases':len(rows)*len(MODES),'seconds':time.monotonic()-started,
            'peak_cuda_bytes':torch.cuda.max_memory_allocated() if device=='cuda' else None,'test_inference':False,'recognition_improvement_measured':False}
    (a.output_dir/'CONCLUIDO.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':main()

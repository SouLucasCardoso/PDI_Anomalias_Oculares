"""Triagem da ideia SAM guiado por mascara automatica; nao executa o pipeline Pinus."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,json,time
import cv2
import numpy as np
from PIL import Image
import torch
ROOT=Path(__file__).resolve().parent
NAME='triagem_sam_guiado_treino_2026-10-23'

def automatic_prompts(mask):
    mask=np.asarray(mask,bool);y,x=np.where(mask)
    if len(x)<16:raise ValueError('Insufficient predicted support')
    h,w=mask.shape;cx=(x.min()+x.max())/2;cy=(y.min()+y.max())/2
    padding=max(2,round(.05*max(x.max()-x.min()+1,y.max()-y.min()+1)))
    box=[max(0,int(x.min())-padding),max(0,int(y.min())-padding),min(w-1,int(x.max())+padding),min(h-1,int(y.max())+padding)]
    distance=cv2.distanceTransform(mask.astype(np.uint8),cv2.DIST_L2,5);points=[];labels=[]
    for quadrant in [(x<=cx)&(y<=cy),(x>cx)&(y<=cy),(x<=cx)&(y>cy),(x>cx)&(y>cy)]:
        candidates=np.flatnonzero(quadrant)
        if len(candidates):
            k=candidates[np.argmax(distance[y[candidates],x[candidates]])];points.append([int(x[k]),int(y[k])]);labels.append(1)
    # Negative center ONLY when predicted hole encloses it; no manual anatomy.
    contours,hierarchy=cv2.findContours(mask.astype(np.uint8),cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is not None:
        holes=[i for i,v in enumerate(hierarchy[0]) if v[3]>=0 and cv2.pointPolygonTest(contours[i],(float(cx),float(cy)),False)>0]
        if holes and not mask[round(cy),round(cx)]:points.append([float(cx),float(cy)]);labels.append(0)
    for px,py in [(max(0,box[0]-2),max(0,box[1]-2)),(min(w-1,box[2]+2),min(h-1,box[3]+2))]:
        if not mask[py,px]:points.append([px,py]);labels.append(0)
    return dict(box=box,points=points,labels=labels)

def dice_iou(pred,truth):
    intersection=int((pred&truth).sum());total=int(pred.sum()+truth.sum());union=int((pred|truth).sum())
    return dict(dice=2*intersection/total if total else 1.,iou=intersection/union if union else 1.)

def main():
    from avaliar_candidato_congelado import digest
    from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
    from avaliar_robustez_reconhecimento import perturb
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args();out=a.output_root/NAME
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';split_file=a.output_root/'adaptador_polar_cadastro_fixo_2026-10-23/protocolo.json';status_file=ROOT/'data/modelos/status.json'
    models=json.loads(status_file.read_text())['models'];sam=models['sam2'];sam_path=Path(sam['path']);sam_weight=sam_path/'model.safetensors';unet_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    manifest=json.loads(manifest_file.read_text());people=set(json.loads(split_file.read_text())['monitor_people']);selected=[]
    for person in sorted(people):
        for side in ['L','R']:
            eligible=sorted([r for r in manifest['train'] if r['subject']==person and r['side']==side and r['session']==2],key=lambda r:Path(r['image']).name)
            assert eligible;selected.append(eligible[0])
    assert len(selected)==32 and not people&{r['subject'] for r in manifest['val']+manifest['test']}
    if a.registrar:
        out.mkdir(parents=True,exist_ok=False)
        external=ROOT.parent.parent/'segmentadorduffatto-main'
        sources=['README.md','config.yaml','pyproject.toml','pinus_separator/models/sam2_provider.py','pinus_separator/models/dinov3_provider.py','pinus_separator/methods/foreground.py','pinus_separator/methods/separation.py']
        protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Feasibility ONLY32S2original-TRAINphotos,one per eye of16reused internal-monitor people;3conditions=96cases. No validation/test or biometric inference. Not a population comparison.',
            external_assessment='External pipeline is anchored Pinus instance separation/green chroma/geodesic competition and stem measurement, not iris segmentation. No iris-trained weights found. Do NOT install/import/run it. Test ONLY transferable SAM prompted-refinement idea in existing iris project.',
            distinction='External default SAM2 Hiera Tiny; this adaptation uses already-downloaded SAM2.1 Hiera Tiny through Transformers, not exact reproduction of external package. DINO disabled, no model download/install/network.',
            candidate='Frozen U-Net native mask supplies bbox+5percentpadding, up to4distance-maxpositivepoints by bboxquadrant, negativepredictedholecenterifpresent plus2outsidecorners. SAM highestpredictedIoU candidate only. No ground-truth prompts or quality-based selection, no fallback to U-Net. Missingprompt means empty candidate, counted.',
            target='Original full annotation AND visible target excluding exactly gray128 intervention pixels; annotation ONLYfor intervention and metrics. No hidden-tissue reconstruction claim.',
            conditions=['clean','upper10','lower10'],sampling='Lexicographically first S2filename per subject/side, fixed before inference. Allcases retained; sample chosen without masks/scores.',
            gate='Screen passes ONLYif mean visible Dice clean>=U-Net and upper/lower each >=U-Net+0.01, and total mean full Dice>=U-Net. No promptsearch/rerun. Pass only motivates broader training-only iris study, never automatic model promotion.',
            sample=[dict(image=Path(r['image']).name,mask=Path(r['mask']).name,subject=r['subject'],side=r['side']) for r in selected],manifest_sha256=digest(manifest_file),unet_sha256=digest(unet_file),sam_path=str(sam_path),sam_revision=sam['revision'],sam_sha256=sam['weights'][0]['sha256'],script_sha256=digest(Path(__file__)),external_sources={n:digest(external/n) for n in sources})
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Triagem registrada antes da inferencia.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert not (out/'CONCLUIDO.json').exists();assert protocol['script_sha256']==digest(Path(__file__)) and protocol['manifest_sha256']==digest(manifest_file) and protocol['unet_sha256']==digest(unet_file) and protocol['sam_sha256']==digest(sam_weight)
    from transformers import Sam2Model,Sam2Processor
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    unet=MulticlassUNet(8).to(device).eval();unet.load_state_dict(torch.load(unet_file,map_location='cpu',weights_only=True)['model']);processor=Sam2Processor.from_pretrained(sam_path,local_files_only=True);model=Sam2Model.from_pretrained(sam_path,local_files_only=True).to(device).eval()
    records=[];prompts=[];masks_saved={};started=time.monotonic()
    for index,row in enumerate(protocol['sample']):
        with Image.open(ROOT/'data/ubipr/single_eye'/row['image']) as im:photo=im.convert('RGB')
        with Image.open(ROOT/'data/ubipr/single_eye'/row['mask']) as im:truth=decode_mask(im)==1
        for tag,kind in [('clean','original'),('upper10','oclusao_superior'),('lower10','oclusao_inferior')]:
            changed,meta=perturb(photo,truth,kind,0 if tag=='clean' else 10);visible=truth&~np.any(np.asarray(changed)!=np.asarray(photo),axis=2) if tag!='clean' else truth
            # Exact intervention support also counts pixels already gray128.
            affected=np.zeros_like(truth)
            if tag!='clean':
                yy,xx=np.where(truth);order=np.lexsort((xx,-yy if tag=='lower10' else yy));take=order[:round(len(xx)*.1)];affected[yy[take],xx[take]]=True
            visible=truth&~affected
            x=torch.from_numpy((np.asarray(changed.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255).transpose(2,0,1).copy())[None].to(device)
            with torch.inference_mode():small=unet(x).argmax(1)[0].cpu().numpy()==1
            initial=np.asarray(Image.fromarray(small).resize(changed.size,Image.Resampling.NEAREST),bool);candidate=np.zeros_like(initial);failed=False;prompt=None
            try:prompt=automatic_prompts(initial)
            except ValueError:failed=True
            if not failed:
                inputs=processor(images=changed,input_boxes=[[prompt['box']]],input_points=[[prompt['points']]],input_labels=[[prompt['labels']]],return_tensors='pt');native_sizes=inputs['original_sizes'].cpu()
                with torch.inference_mode():outputs=model(**{k:v.to(device) for k,v in inputs.items() if k not in ['original_sizes','reshaped_input_sizes']},multimask_output=True)
                candidates=processor.post_process_masks(outputs.pred_masks.cpu(),native_sizes,binarize=False)[0];choice=int(outputs.iou_scores[0,0].float().argmax());candidate=candidates[0,choice].numpy()>0
            for method,pred in [('unet',initial),('sam_guided',candidate)]:
                record=dict(image=row['image'],subject=row['subject'],side=row['side'],condition=tag,method=method,prompt_failed=failed if method=='sam_guided' else False,reference_pixels=int(truth.sum()),affected_pixels=int(affected.sum()))
                for target,target_mask in [('full',truth),('visible',visible)]:record.update({target+'_'+k:v for k,v in dice_iou(pred,target_mask).items()})
                records.append(record)
            prompts.append(dict(image=row['image'],condition=tag,prompt=prompt));masks_saved[f'{index:02}_{tag}_unet']=np.packbits(initial);masks_saved[f'{index:02}_{tag}_sam']=np.packbits(candidate);masks_saved[f'{index:02}_{tag}_shape']=np.array(initial.shape)
        print(json.dumps(dict(images=index+1,total=32,seconds=time.monotonic()-started)),flush=True)
    summary={method:{tag:{metric:float(np.mean([r[metric] for r in records if r['method']==method and r['condition']==tag])) for metric in ['full_dice','full_iou','visible_dice','visible_iou']} for tag in protocol['conditions']} for method in ['unet','sam_guided']}
    u=summary['unet'];s=summary['sam_guided'];gate=s['clean']['visible_dice']>=u['clean']['visible_dice'] and all(s[t]['visible_dice']>=u[t]['visible_dice']+.01 for t in ['upper10','lower10']) and np.mean([s[t]['full_dice'] for t in s])>=np.mean([u[t]['full_dice'] for t in u])
    with (out/'metricas_por_imagem.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    np.savez_compressed(out/'mascaras_empacotadas.npz',**masks_saved);(out/'prompts.json').write_text(json.dumps(prompts,indent=2),encoding='utf-8')
    final=dict(status='sam_guided_feasibility_screen_completed',summary=summary,screen_passed=bool(gate),original_train_photos=32,conditions=3,paired_cases=96,prompt_failures=sum(r['prompt_failed'] for r in records),validation_identity_inference=False,test_inference=False,biometric_inference=False,frozen_candidate_replaced=False,minimum_area=None,mask_file_sha256=digest(out/'mascaras_empacotadas.npz'))
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)
if __name__=='__main__':main()

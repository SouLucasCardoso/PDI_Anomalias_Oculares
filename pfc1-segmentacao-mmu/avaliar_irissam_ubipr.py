"""Comparacao exploratoria Iris-SAM/U-Net em VAL, sem caixa real no candidato."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,gc,json,sys,tempfile,time
import numpy as np
from PIL import Image
import torch
from preparar_encoder_espacial import file_hash
ROOT=Path(__file__).resolve().parent
NAME='irissam_viabilidade_val_2026-10-23'
METHODS=['unet','irissam_auto_unet_box','irissam_no_prompt','irissam_oracle_box']
CONDITIONS=[('clean','original'),('upper10','oclusao_superior'),('lower10','oclusao_inferior')]

def mask_box(mask,padding_fraction=0.):
    y,x=np.where(mask)
    if not len(x):return None
    margin=max(2,round(max(x.max()-x.min()+1,y.max()-y.min()+1)*padding_fraction)) if padding_fraction else 0
    return [max(0,int(x.min())-margin),max(0,int(y.min())-margin),min(mask.shape[1]-1,int(x.max())+margin),min(mask.shape[0]-1,int(y.max())+margin)]

def metrics(pred,truth):
    intersection=int((pred&truth).sum());total=int(pred.sum()+truth.sum());union=int((pred|truth).sum())
    return dict(dice=2*intersection/total if total else 1.,iou=intersection/union if union else 1.)

def affected_support(reference,tag):
    affected=np.zeros_like(reference)
    if tag!='clean':
        y,x=np.where(reference);order=np.lexsort((x,-y if tag=='lower10' else y));take=order[:round(len(x)*.1)];affected[y[take],x[take]]=True
    return affected

def load_irissam(checkpoint,runtime,device,dtype):
    if str(runtime) not in sys.path:sys.path.insert(0,str(runtime))
    from segment_anything import sam_model_registry,SamPredictor
    state=torch.load(checkpoint,map_location='cpu',weights_only=True,mmap=True)
    if 'model' in state and isinstance(state['model'],dict):state=state['model']
    if all(k.startswith('module.') for k in state):state={k[7:]:v for k,v in state.items()}
    assert state['image_encoder.patch_embed.proj.weight'].shape==(1280,3,16,16),'Expected original SAM ViT-H'
    with torch.device('meta'):model=sam_model_registry['vit_h'](checkpoint=None)
    model.load_state_dict(state,strict=True,assign=True)
    # These original-SAM buffers are nonpersistent and therefore absent from checkpoint.
    model.pixel_mean=torch.tensor([123.675,116.28,103.53]).view(3,1,1);model.pixel_std=torch.tensor([58.395,57.12,57.375]).view(3,1,1)
    model.requires_grad_(False);model.to(device=device,dtype=dtype).eval();del state
    return model,SamPredictor(model)

def predict(predictor,box,device,half):
    with torch.inference_mode(),torch.autocast(device_type=device.type,dtype=torch.float16,enabled=half):
        masks,_,_=predictor.predict(point_coords=None,point_labels=None,box=None if box is None else np.array(box,np.float32),multimask_output=False)
    return masks[0].astype(bool)

def main():
    from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
    from avaliar_robustez_reconhecimento import perturb
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--registrar',action='store_true');p.add_argument('--weights-directory',type=Path,default=Path(tempfile.gettempdir())/'pfc-irissam');a=p.parse_args();out=a.output_root/NAME
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_file.read_text());unet_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';external=ROOT.parent.parent/'Segmentadores de Terceiros/Iris-SAM-main';runtime=a.weights_directory/'runtime'
    if a.registrar:
        out.mkdir(parents=True,exist_ok=False);rng=np.random.default_rng(63);people=sorted({r['subject'] for r in manifest['val']});chosen=rng.choice(people,size=32,replace=False);sample=[]
        for i,person in enumerate(chosen):
            candidates=[r for r in manifest['val'] if r['subject']==int(person) and r['side']==('L' if i%2==0 else 'R')]
            if not candidates:candidates=[r for r in manifest['val'] if r['subject']==int(person)]
            candidates=sorted(candidates,key=lambda r:Path(r['image']).name);r=candidates[int(rng.integers(len(candidates)))];sample.append(dict(image=Path(r['image']).name,mask=Path(r['mask']).name,subject=r['subject'],side=r['side'],session=r['session']))
        assert len({r['subject'] for r in sample})==32 and not {r['subject'] for r in sample}&{r['subject'] for r in manifest['train']+manifest['test']}
        protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Newthirdparty pretrained segmentation benchmark:32distinctVALpeople,oneimageeach,3conditions=96pairedcases. No TEST/biometric inference/training/weightsearch. VALhistorically usedindevelopment,notblindconfirmation.',
            primary='Iris-SAM released checkpoint ViT-H;AUTOMATICbbox from CURRENTU-Netprediction with5%padding,boxONLY,multimaskFalse,rawmaskthreshold0. This is a two-stage refinement,not standaloneIrisSAMlocalization. NEVERreferenceboxforprimary.',
            diagnostics='No-promptSAM fixedsecondary;oracle tightREFERENCEbbox for diagnosticONLY,NEVERdeployableorautomaticcandidate. No prompt/mask selection byDice; reportALLmethods. U-Netnativeargmaxirisclass1,320x240input,FP32,asreferencepipeline.',
            precision='SAM FP16+autocast onCUDAtofit6GB;CPUfallbackFP32. FullViT-Hcheckpoint2.564GB,weights_only=True,mmap,strictstate matching,not executing externaltrain/inferGUI. PredeterminedFP32sanity on first2CLEANprimarycases if fits; reportmaxDiceDifference,materialif>0.005. No precision chosenafterresults.',
            interventions='Nativegray128 insideEXACTround(10%referenceiris)pixels,upper/lowerrowmajor. AnnotationONLYintervention,metrics,andclearlyseparatedoracle. FULLoriginalannotation andVISIBLEreferenceexcludingaffectedpixels reportedseparately;allcasesinclfailed/emptyretained.',
            selection='Seed63 choose32of39VALsubjectswithoutreplacement;randomimageperchosenperson,alternatingL/Rifavailable. No maskquality/score filtering. MeanperimageDice/IoU and pairedbootstrap95%CI over32people,5000drawsseed63.',
            gate='Feasibilityonly:primarycleanDice>=U-Net AND bothocclusionsVISIBLEDice>=U-Net+0.01. DoesNOTpromote/replacepipelineorclaimrecognition/minimum. Reportoracle/seconddiagnosticswithoutchoosingbestasprimary.',
            paper='https://arxiv.org/abs/2402.06497',repository='https://github.com/ParisaFarmanifard/Iris-SAM',checkpoint_file_id='1Oqr93dMaHMZfwd2M3FvM-q5Xnn_d321x',checkpoint_bytes_expected=2564545909,checkpoint_training_dataset='Not specified by filename/README singlecheckpoint; inspect metadata if available',sample=sample,manifest_sha256=file_hash(manifest_file),unet_sha256=file_hash(unet_file),script_sha256=file_hash(Path(__file__)),external_sources={n:file_hash(external/n) for n in ['README.md','requirements.txt','dataset.py','sam_infer.py','sam_infer_auto.py','sam_test.py','sam_test_main.py','sam_train_losses.py','utils/common.py']},runtime_version='segment-anything==1.0 isolated TEMP; existingprojectdependencies unchanged')
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Comparacao Iris-SAM registrada antes das inferencias.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert file_hash(Path(__file__))==protocol['script_sha256'] and not (out/'CONCLUIDO.json').exists();assert file_hash(manifest_file)==protocol['manifest_sha256'] and file_hash(unet_file)==protocol['unet_sha256']
    for n,h in protocol['external_sources'].items():assert file_hash(external/n)==h
    checkpoint=a.weights_directory/'IrisSAM_model.pt';download=json.loads((a.weights_directory/'checkpoint_download.json').read_text());assert checkpoint.stat().st_size==protocol['checkpoint_bytes_expected']==download['bytes'] and file_hash(checkpoint)==download['sha256']
    provenance=dict(checkpoint=download,runtime_sources={str(f.relative_to(runtime)):file_hash(f) for f in (runtime/'segment_anything').rglob('*.py')},checkpoint_dataset_unknown=True)
    (out/'PROVENIENCIA_CHECKPOINT.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');half=device.type=='cuda';dtype=torch.float16 if half else torch.float32
    unet=MulticlassUNet(8).to(device).eval();unet.load_state_dict(torch.load(unet_file,map_location='cpu',weights_only=True)['model']);sam,predictor=load_irissam(checkpoint,runtime,device,dtype)
    records=[];prompts=[];masks_saved={};sanity_cases=[];started=time.monotonic()
    for i,row in enumerate(protocol['sample']):
        with Image.open(ROOT/'data/ubipr/single_eye'/row['image']) as im:photo=im.convert('RGB')
        with Image.open(ROOT/'data/ubipr/single_eye'/row['mask']) as im:truth=decode_mask(im)==1
        for tag,kind in CONDITIONS:
            changed,_=perturb(photo,truth,kind,0 if tag=='clean' else 10);visible=truth&~affected_support(truth,tag);rgb=np.asarray(changed)
            x=torch.from_numpy((np.asarray(changed.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255).transpose(2,0,1).copy())[None].to(device)
            with torch.inference_mode():small=unet(x).argmax(1)[0].cpu().numpy()==1
            initial=np.asarray(Image.fromarray(small).resize(changed.size,Image.Resampling.NEAREST),bool);auto=mask_box(initial,.05);oracle=mask_box(truth)
            with torch.inference_mode(),torch.autocast(device_type=device.type,dtype=torch.float16,enabled=half):predictor.set_image(rgb)
            predictions={'unet':initial,'irissam_auto_unet_box':predict(predictor,auto,device,half) if auto is not None else np.zeros_like(truth),'irissam_no_prompt':predict(predictor,None,device,half),'irissam_oracle_box':predict(predictor,oracle,device,half) if oracle is not None else np.zeros_like(truth)}
            for method,pred in predictions.items():
                r=dict(image=row['image'],subject=row['subject'],side=row['side'],condition=tag,method=method,reference_pixels=int(truth.sum()),affected_pixels=int(affected_support(truth,tag).sum()),empty_prediction=not bool(pred.any()))
                for target,target_mask in [('full',truth),('visible',visible)]:r.update({target+'_'+k:v for k,v in metrics(pred,target_mask).items()})
                records.append(r);masks_saved[f'{i:02}_{tag}_{method}']=np.packbits(pred)
            masks_saved[f'{i:02}_{tag}_shape']=np.array(truth.shape);prompts.append(dict(image=row['image'],condition=tag,automatic_box=auto,oracle_box=oracle))
            if i<2 and tag=='clean':sanity_cases.append(dict(rgb=rgb.copy(),truth=truth.copy(),box=auto,half_mask=predictions['irissam_auto_unet_box'].copy()))
        print(json.dumps(dict(images=i+1,total=32,seconds=round(time.monotonic()-started,1))),flush=True)
    memory_peak=int(torch.cuda.max_memory_allocated()) if half else None;del predictor,sam,unet;gc.collect()
    if half:torch.cuda.empty_cache()
    sanity=dict(attempted=half,completed=False)
    if half:
        try:
            sam,predictor=load_irissam(checkpoint,runtime,device,torch.float32);differences=[]
            for item in sanity_cases:
                with torch.inference_mode():predictor.set_image(item['rgb'])
                pred=predict(predictor,item['box'],device,False) if item['box'] is not None else np.zeros_like(item['truth']);differences.append(abs(metrics(pred,item['truth'])['dice']-metrics(item['half_mask'],item['truth'])['dice']))
            sanity.update(completed=True,cases=2,maximum_absolute_Dice_difference=max(differences),material_difference=max(differences)>.005)
        except torch.cuda.OutOfMemoryError:sanity.update(reason='FP32sanity_exceeds_availableVRAM;FP16benchmarkonly')
    summary={m:{t:{k:float(np.mean([r[k] for r in records if r['method']==m and r['condition']==t])) for k in ['full_dice','full_iou','visible_dice','visible_iou']} for t,_ in CONDITIONS} for m in METHODS};u=summary['unet'];s=summary['irissam_auto_unet_box'];gate=s['clean']['full_dice']>=u['clean']['full_dice'] and all(s[t]['visible_dice']>=u[t]['visible_dice']+.01 for t in ['upper10','lower10'])
    paired={};rng=np.random.default_rng(63)
    for t,_ in CONDITIONS:
        differences=np.array([r['visible_dice'] for r in records if r['method']=='irissam_auto_unet_box' and r['condition']==t])-np.array([r['visible_dice'] for r in records if r['method']=='unet' and r['condition']==t]);draws=rng.integers(0,32,size=(5000,32));ci=np.quantile(differences[draws].mean(1),[.025,.975]);paired[t]=dict(mean_difference=float(differences.mean()),bootstrap95=[float(v) for v in ci])
    with (out/'metricas_por_imagem.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    np.savez_compressed(out/'mascaras_empacotadas.npz',**masks_saved);(out/'prompts.json').write_text(json.dumps(prompts,indent=2),encoding='utf-8')
    final=dict(status='irissam_ubipr_feasibility_completed',summary=summary,primary_paired_differences=paired,screen_passed=bool(gate),precision_sanity=sanity,cuda_memory_peak_bytes=memory_peak,photos=32,people=32,paired_cases=96,conditions=3,methods=METHODS,precision='FP16SAM/FP32UNet' if half else 'FP32both',checkpoint_sha256=download['sha256'],masks_sha256=file_hash(out/'mascaras_empacotadas.npz'),biometric_inference=False,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)
if __name__=='__main__':main()

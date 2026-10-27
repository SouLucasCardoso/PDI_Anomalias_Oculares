"""Casos clinicos rotulados e suporte natural UBIPr: analise exploratoria."""
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone
import argparse,csv,importlib.util,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps
import torch
from avaliar_candidato_congelado import ROOT,WEIGHTS,digest,prepare,extract,global_scores,spatial,fuse
NAME='casos_oculares_reais_2026-10-27'
ORDER=['rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red']

def choose(source,clinical):
    explicit=[r for r in source if any(t in r['diagnosis_raw'].lower() for t in ['iris','irido'])]
    affected={(r['subject'],r['side']) for r in explicit}
    gallery=[r for r in clinical['test'] if r['role']=='gallery'];queries=[r for r in clinical['test'] if r['role']=='query' and (r['subject'],r['side']) in affected]
    targets={(r['subject'],r['side']) for r in queries}
    assert targets=={('P0114','OS'),('P0803','OD')} and len(queries)==4
    selected=[]
    for side in ['OS','OD']:
        target=[r for r in gallery if (r['subject'],r['side']) in targets and r['side']==side];assert len(target)==1
        others=sorted([r for r in gallery if r['side']==side and (r['subject'],r['side']) not in targets],key=lambda r:(r['subject'],r['image']))[:15]
        assert len(others)==15;selected+=target+others
    rows=[]
    for role,rs in [(1,selected),(2,sorted(queries,key=lambda r:r['image']))]:
        for r in rs:rows.append(dict(image=r['image'],subject=r['subject'],side='L' if r['side']=='OS' else 'R',session=role,diagnosis_raw=r['diagnosis_raw'],source_side=r['side']))
    images={r['image'] for r in rows}
    for r in explicit:
        if r['image'] not in images:rows.append(dict(image=r['image'],subject=r['subject'],side='L' if r['side']=='OS' else 'R',session=3,diagnosis_raw=r['diagnosis_raw'],source_side=r['side']))
    return rows,explicit

def local_subset(scores,rows):
    from avaliar_robustez_reconhecimento import identity
    ids=sorted({identity(r) for r in rows});q=[r for r in rows if r.session==2]
    cols=np.array([[j for j,eye in enumerate(ids) if eye.endswith('_'+r.side)] for r in q]);assert cols.shape==(4,16)
    labels=np.array([[ids[j] for j in c].index(identity(r)) for r,c in zip(q,cols)])
    return np.take_along_axis(scores,cols,1),labels

def sheets(items,out,prefix,title):
    font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
    for start in range(0,len(items),6):
        batch=items[start:start+6];canvas=Image.new('RGB',(1800,180+250*len(batch)),'#f3f5f7');d=ImageDraw.Draw(canvas)
        d.text((25,15),title,font=font(29),fill='#172333')
        for x,h in zip([25,430,835,1240],['Foto original','Mascara automatica','Recorte RGB','Faixa polar e medidas']):d.text((x,60),h,font=font(22),fill='#172333')
        for k,it in enumerate(batch):
            y=105+k*250;im=it['original'];rgb=np.asarray(im);overlay=rgb.copy();m=it['mask'];overlay[m]=(.6*rgb[m]+.4*np.array([0,255,70])).astype(np.uint8)
            for x,img in zip([25,430,835],[im,Image.fromarray(overlay),it['crop']]):canvas.paste(ImageOps.pad(img,(385,190),color='white'),(x,y+25))
            d.text((25,y),it['filename'],font=font(18),fill='#172333');canvas.paste(Image.fromarray(it['polar']).resize((520,65)),(1240,y+30))
            for j,line in enumerate(it['caption']):d.text((1240,y+110+j*24),line,font=font(18),fill='#425369')
        d.text((25,canvas.height-55),'Area da mascara e suporte polar sao medidas do algoritmo, nao percentual anatomico preservado.',font=font(20),fill='#425369')
        d.text((25,canvas.height-28),'Verde: mascara prevista. Preto/cinza: exterior excluido. Sem textura gerada ou oclusao artificial nova.',font=font(19),fill='#425369')
        canvas.save(out/f'{prefix}_{start//6+1:02}.png')

def main():
    from treinar_segmentacao_ubipr import MulticlassUNet
    from avaliar_dinov3_ubipr import masked_crop
    from textura_polar import prepare_texture
    from preparar_polar_vermelho import red_texture
    from treinar_identidade_iris import IdentityEncoder
    from avaliar_robustez_reconhecimento import metrics
    import reconhecedor_resnet50,reconhecedor_convnext,reconhecedor_transformer_polar
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args();out=a.root/NAME
    source_path=ROOT/'data/slpvld/manifesto.json';clinical_path=ROOT/'outputs/biometria_clinica_triagem_2026-10-20/manifesto.json';source=json.loads(source_path.read_text());clinical=json.loads(clinical_path.read_text());raw,explicit=choose(source,clinical)
    diag=ROOT/'outputs/diagnostico_resolucao_geometria_val_2026-10-22/consultas.csv';diagnostics=list(csv.DictReader(diag.open(encoding='utf-8')));ordered=sorted([r for r in diagnostics if r['polar_support']],key=lambda r:(float(r['polar_support']),r['image']));ubipr=[];seen=set()
    for r in ordered:
        if r['subject'] not in seen:ubipr.append(r);seen.add(r['subject'])
        if len(ubipr)==4:break
    # Add the first two different remaining people, without consulting recognition.
    for r in diagnostics:
        if r['subject'] not in seen:ubipr.append(r);seen.add(r['subject'])
        if len(ubipr)==6:break
    frozen_path=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json';frozen=json.loads(frozen_path.read_text())
    if a.registrar:
        out.mkdir(parents=True,exist_ok=False)
        protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Exploratory real-image case study,notfreshblindtest;clinicaltestpreviouslyexposed. NOtraining/calibration/newsyntheticocclusion.',clinical='ALL9SLPVLDimages with literaliris/iridolabels;6single-captureeyes segmentationonly;2eyes with eligible oldclinicaltest repeatedcaptures yield4queries. Earliestgalleryasoldmanifest,mayalreadyhavepathology. Nohealthybefore/aftercausalclaim.16same-sideeyes:target+first15othergalleryeyes sortedsubject/image,NOscorequalityselection.',ubipr='ReuseALL482VALcleanrecognitiondecisions andsupportmeasurements. Illustrate4lowest-supportdistinctpeople thenfirst2remainingpeople byexistingCSVorder,NOscoreselection. VisualflagsareNOTclinicaldiagnoses. No scan of all11018images claimed.',area='Nativepredictedmaskpixels andmask/imagepercentage;polar_mask_fraction=algorithmicsupportinestimatedpolargrid. NOanatomicaldenominator,noclinicalpreservedpercentage,minimumnull. NoreferenceGTmasksforclinicalimages.',recognition='ALL9frozencomponents,U-Netandfusioncalibration/thresholdunchangedfromUBIPr,onequeryimage;clinicaldomainshift,smallN4with60impostorpairs,notcomparablepopulationbenchmark. Allqueryfailuresretained,originalgalleryfixed.',rows=raw,explicit_filenames=[Path(r['image']).name for r in explicit],ubipr_examples=[r['image'] for r in ubipr],threshold=frozen['frozen_threshold'],sources_sha256={str(f):digest(f) for f in [source_path,clinical_path,diag,frozen_path]},script_sha256=digest(Path(__file__)),checkpoints_sha256={k:digest(ROOT/'outputs'/v[0]/'melhor_modelo.pt') for k,v in WEIGHTS.items()},unet_sha256=digest(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'))
        assert all(protocol['checkpoints_sha256'][k]==v[1] for k,v in WEIGHTS.items());(out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Casos e protocolo registrados antes da inferencia.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert protocol['rows']==raw and protocol['ubipr_examples']==[r['image'] for r in ubipr] and protocol['script_sha256']==digest(Path(__file__)) and not (out/'CONCLUIDO.json').exists()
    for f,h in protocol['sources_sha256'].items():assert digest(Path(f))==h
    assert digest(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt')==protocol['unet_sha256']
    for k,v in WEIGHTS.items():assert digest(ROOT/'outputs'/v[0]/'melhor_modelo.pt')==protocol['checkpoints_sha256'][k]==v[1]
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');allrows=[SimpleNamespace(**r) for r in raw];rows=[r for r in allrows if r.session in [1,2]];assert len(rows)==36
    images,rv,pv=prepare(allrows,device,out/'cache_preprocess');components={}
    def save(name,result):
        full,valid=result;scores,labels=local_subset(full,rows);components[name]=dict(scores=scores,valid=valid,labels=labels);np.savez_compressed(out/f'scores_{name}.npz',**components[name]);print('Component '+name,flush=True)
    for name in ['rgb','polar','r50','convnext','native','transformer']:
        ck=ROOT/'outputs'/WEIGHTS[name][0]/'melhor_modelo.pt'
        if name in ['rgb','polar']:model=IdentityEncoder().to(device).eval();model.load_state_dict(torch.load(ck,map_location='cpu',weights_only=True)['model'])
        else:model,_={'r50':reconhecedor_resnet50,'convnext':reconhecedor_convnext,'native':reconhecedor_resnet50,'transformer':reconhecedor_transformer_polar}[name].load(ck,device)
        inp=images['polar'] if name in ['polar','transformer'] else images['native'] if name=='native' else images['rgb'];inp=inp[:36]
        if name=='convnext':inp=np.stack([reconhecedor_convnext.contrast(i) for i in inp])
        valid=pv[:36] if name in ['polar','transformer'] else rv[:36];save(name,global_scores(extract(model,inp,device),valid,rows))
        if name=='polar':save('spatial',spatial(model,inp,valid,rows,device))
        del model
        if device.type=='cuda':torch.cuda.empty_cache()
    arc_base=ROOT/'data/modelos/cvrl_arciris';arc_weights=next(arc_base.rglob('ResNet100_154000.pt'));assert digest(arc_weights)=='466014be7723eb0b1a741dcff5a0c8ae51d1918818a6b021952f9c4ccd443f8f'
    assert digest(arc_base/'modules/network.py')=='de7f0cb796ebf4be02818c704d7e3afa0047dc09719b131b37cb8c26c42dd327'
    spec=importlib.util.spec_from_file_location('arciris_real_cases',arc_base/'modules/network.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);model=module.iresnet100();model.load_state_dict(torch.load(arc_weights,map_location='cpu',weights_only=True));model.to(device).eval()
    for name,inp in [('arc_clahe',images['polar']),('arc_red',images['red'])]:save(name,global_scores(extract(model,inp[:36],device,8,True),pv[:36],rows,True))
    del model
    scores,valid=fuse([components[k] for k in ORDER],frozen['component_calibration_red_and_clahe']);labels=components['rgb']['labels'];result,correct,accepted=metrics(scores,labels,protocol['threshold'],valid);np.savez_compressed(out/'scores_finais.npz',scores=scores,labels=labels,valid=valid,correct=correct,accepted=accepted)
    queries=[r for r in rows if r.session==2];qrecords=[dict(filename=Path(r.image).name,subject=r.subject,side=r.side,diagnosis_raw=r.diagnosis_raw,correct=bool(correct[i]),accepted=bool(accepted[i]),valid=bool(valid[i]),genuine_score=float(scores[i,labels[i]]),predicted_index=int(scores[i].argmax()),genuine_index=int(labels[i])) for i,r in enumerate(queries)]
    model=MulticlassUNet(8).to(device).eval();model.load_state_dict(torch.load(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt',map_location='cpu',weights_only=True)['model']);cases={Path(r.image).name for r in allrows if any(t in r.diagnosis_raw.lower() for t in ['iris','irido','synechia'])};pictures=[];areas=[]
    for start in range(0,len(allrows),32):
        photos=[Image.open(r.image).convert('RGB') for r in allrows[start:start+32]];x=torch.from_numpy(np.stack([np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for im in photos]).transpose(0,3,1,2).copy()).to(device)
        with torch.inference_mode():masks=model(x).argmax(1).cpu().numpy()==1
        for j,(r,im,small) in enumerate(zip(allrows[start:start+32],photos,masks)):
            if Path(r.image).name not in cases:continue
            mask=np.asarray(Image.fromarray(small).resize(im.size,Image.Resampling.NEAREST),bool);polar=np.full((64,512,3),127,np.uint8);geometry=None
            try:polar,geometry=prepare_texture(np.asarray(im),mask)
            except ValueError:pass
            assert bool(mask.any())==bool(rv[start+j]) and (geometry is not None)==bool(pv[start+j]);record=dict(filename=Path(r.image).name,diagnosis_raw=r.diagnosis_raw,session=r.session,predicted_pixels=int(mask.sum()),image_pixels=mask.size,mask_percent_of_photo=float(100*mask.mean()),polar_support_percent=100*geometry['polar_mask_fraction'] if geometry else None,anatomical_preserved_percent=None)
            areas.append(record);qr=next((v for v in qrecords if v['filename']==record['filename']),None);caption=[f'Mascara/foto: {record["mask_percent_of_photo"]:.2f}%',f'Suporte polar: {record["polar_support_percent"]:.2f}%' if geometry else 'Faixa polar: falhou',f'Rank-1: {qr["correct"]}; aceita: {qr["accepted"]}' if qr else ('Cadastro clinico' if r.session==1 else 'Sem cadastro elegivel')]
            pictures.append(dict(filename=record['filename'],original=im,mask=mask,crop=masked_crop(im,mask),polar=polar,caption=caption))
    sheets(pictures,out,'CASOS_CLINICOS','Casos clinicos rotulados SLP-VLD - extracao automatica congelada')
    # Existing UBIPr scores and support, no new recognition inference.
    groups=[]
    for lo,hi in [(0,.5),(.5,.75),(.75,.9),(.9,1.000001)]:
        rr=[r for r in diagnostics if r['polar_support'] and lo<=float(r['polar_support'])<hi];groups.append(dict(support_interval=[lo,hi],queries=len(rr),correct=sum(r['correct']=='True' for r in rr),accepted=sum(r['accepted']=='True' for r in rr)))
    undefined=[r for r in diagnostics if not r['polar_support']];groups.append(dict(support_interval=None,queries=len(undefined),correct=sum(r['correct']=='True' for r in undefined),accepted=sum(r['accepted']=='True' for r in undefined)))
    assert sum(g['queries'] for g in groups)==482
    upics=[]
    for r in ubipr:
        im=Image.open(ROOT/'data/ubipr/single_eye'/r['image']).convert('RGB');x=torch.from_numpy((np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255).transpose(2,0,1).copy())[None].to(device)
        with torch.inference_mode():small=model(x).argmax(1)[0].cpu().numpy()==1
        mask=np.asarray(Image.fromarray(small).resize(im.size,Image.Resampling.NEAREST),bool);polar,geo=prepare_texture(np.asarray(im),mask);np.testing.assert_allclose(geo['polar_mask_fraction'],float(r['polar_support']),atol=0,rtol=0)
        upics.append(dict(filename=r['image'],original=im,mask=mask,crop=masked_crop(im,mask),polar=polar,caption=[f'Suporte polar: {100*geo["polar_mask_fraction"]:.2f}%',f'Rank-1: {r["correct"]}; aceita: {r["accepted"]}','Diagnostico: nao disponivel']))
    sheets(upics,out,'UBIPR_SUPORTE_NATURAL','UBIPr - exemplos por suporte polar, sem diagnostico clinico')
    (out/'consultas_clinicas.json').write_text(json.dumps(qrecords,indent=2),encoding='utf-8');(out/'areas_clinicas.json').write_text(json.dumps(areas,indent=2),encoding='utf-8');(out/'grupos_ubipr.json').write_text(json.dumps(groups,indent=2),encoding='utf-8')
    final=dict(status='real_ocular_case_study_completed',clinical_result=result,queries=4,query_eyes=2,candidates_per_query=16,correct=int(correct.sum()),accepted=int(accepted.sum()),joint=int((correct&accepted).sum()),clinical_images_measured=len(areas),explicit_iris_images=9,ubipr_queries_descriptive=482,ubipr_groups=groups,threshold_unchanged=protocol['threshold'],minimum_anatomical_area=None,clinical_causal_effect=None,main_candidate_replaced=False)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)

if __name__=='__main__':main()

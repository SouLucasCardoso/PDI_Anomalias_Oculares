"""Piloto fixo de dois descritores, somente no monitor do treino original."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,time
import numpy as np
from PIL import Image
import torch
from adaptador_polar import pooled_features
from treinar_adaptador_polar import monitor_scores,CONDITIONS
ROOT=Path(__file__).resolve().parent
NAME='complemento_geometrico_monitor_2026-10-23'

def complementary_vectors(original,corrected,weight=.25):
    if original.shape!=corrected.shape or not 0<weight<1:raise ValueError('Invalid paired descriptors/weight')
    # Weighted cosine before the SAME top3 enrollment aggregation; no label access.
    return np.concatenate([np.sqrt(1-weight)*original,np.sqrt(weight)*corrected],axis=1).astype(np.float32)

def main():
    from avaliar_candidato_congelado import digest,WEIGHTS
    from avaliar_robustez_reconhecimento import perturb
    from treinar_identidade_iris import IdentityEncoder
    from treinar_segmentacao_ubipr import Sample,MulticlassUNet,decode_mask
    from textura_polar import prepare_texture
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args()
    source=a.output_root/'adaptador_polar_cadastro_fixo_2026-10-23';out=a.output_root/NAME
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';encoder_file=ROOT/'outputs'/WEIGHTS['polar'][0]/'melhor_modelo.pt';unet_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    if a.registrar:
        out.mkdir(parents=True,exist_ok=False)
        protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Only16reused original-TRAIN monitor people/960photos/480S2queries. Both frozen encoders saw these people historically; not independent. No validation/test inference or fitting.',
            hypothesis='Keep original polar branch; append unadapted corrected-outer-geometry descriptor. Fixed original/corrected cosine contribution75/25 BEFORE unchanged top3 enrollment aggregation. NO weight search, no learned adapter, no use of rejected weights.',
            conditions='Clean and native gray128 upper/lower10percent reference pixels. Annotation ONLY defines intervention; automatic U-Net extracts each observed query. One query photo, supplied side,16candidate eyes. S1 gallery explicitly copied from CLEAN in ALL conditions. Never use clean counterpart of query for occluded inference.',
            calibration='Separate one CLEAN FMR<=1% threshold per strategy, reused unchanged for occlusions. All480queries and extraction failures retained. Complement requires BOTH branches valid, no fallback or filtering. Original and corrected-only controls identical feature precision FP32batch32.',
            gate='Candidate CLEAN Rank1/TAR >= original control, FMR<=1%; BOTH occlusions Rank1/TAR strictly improve vs original and FMR<=1%. Absolute90%Rank1/TAR target reported separately. If fails NO validation inference; no test/promotion/minimum-area claim.',
            weight_corrected=.25,script_sha256=digest(Path(__file__)),manifest_sha256=digest(manifest_file),encoder_sha256=digest(encoder_file),unet_sha256=digest(unet_file),source_cache_sha256=digest(source/'cache_features.npz'),source_rows_sha256=digest(source/'rows.json'),source_protocol_sha256=digest(source/'protocolo.json'),dependencies_sha256={n:digest(ROOT/n) for n in ['treinar_adaptador_polar.py','adaptador_polar.py','avaliar_candidato_congelado.py','textura_polar.py','avaliar_robustez_reconhecimento.py']})
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Protocolo registrado antes da inferencia.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert digest(Path(__file__))==protocol['script_sha256'];assert not (out/'CONCLUIDO.json').exists()
    for file,key in [(manifest_file,'manifest_sha256'),(encoder_file,'encoder_sha256'),(unet_file,'unet_sha256'),(source/'cache_features.npz','source_cache_sha256'),(source/'rows.json','source_rows_sha256'),(source/'protocolo.json','source_protocol_sha256')]:assert digest(file)==protocol[key]
    assert digest(encoder_file)==WEIGHTS['polar'][1]
    for n,h in protocol['dependencies_sha256'].items():assert digest(ROOT/n)==h
    manifest=json.loads(manifest_file.read_text());allrows=[Sample(**r) for r in manifest['train']]
    with np.load(source/'cache_features.npz') as z:
        indices=z['monitor_indices'];teacher=z['teacher'][indices];teacher_valid=z['teacher_valid'][indices];corrected=z['base'][indices];corrected_valid=z['valid'][indices]
    rows=[allrows[i] for i in indices];assert len(rows)==960 and sum(r.session==2 for r in rows)==480 and len({r.subject for r in rows})==16
    assert not {r.subject for r in rows}&{r['subject'] for r in manifest['val']+manifest['test']}
    source_rows=json.loads((source/'rows.json').read_text());assert len(source_rows)==len(allrows)
    for i,r in zip(indices,rows):assert Path(r.image).name==source_rows[i]['image'] and r.subject==source_rows[i]['subject']
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');started=time.monotonic()
    encoder=IdentityEncoder().to(device).eval();encoder.load_state_dict(torch.load(encoder_file,map_location='cpu',weights_only=True)['model'])
    unet=MulticlassUNet(8).to(device).eval();unet.load_state_dict(torch.load(unet_file,map_location='cpu',weights_only=True)['model'])
    original={tag:teacher.copy() for tag,_,_ in CONDITIONS};valid={tag:teacher_valid.copy() for tag,_,_ in CONDITIONS};query=np.array([i for i,r in enumerate(rows) if r.session==2]);interventions=[]
    for tag,kind,level in CONDITIONS[1:]:
        for start in range(0,len(query),32):
            selected=query[start:start+32];photos=[]
            for i in selected:
                r=rows[i]
                with Image.open(ROOT/'data/ubipr/single_eye'/Path(r.image).name) as im:photo=im.convert('RGB')
                with Image.open(ROOT/'data/ubipr/single_eye'/Path(r.mask).name) as im:reference=decode_mask(im)==1
                changed,meta=perturb(photo,reference,kind,level);photos.append(changed);interventions.append(dict(image=Path(r.image).name,condition=tag,reference_pixels=int(reference.sum()),affected_fraction=meta['affected_fraction']))
            x=torch.from_numpy(np.stack([np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for im in photos]).transpose(0,3,1,2).copy()).to(device)
            with torch.inference_mode():masks=unet(x).argmax(1).cpu().numpy()==1
            textures=[]
            for i,im,mask in zip(selected,photos,masks):
                mask=np.asarray(Image.fromarray(mask).resize(im.size,Image.Resampling.NEAREST),bool)
                try:texture=prepare_texture(np.asarray(im),mask)[0];valid[tag][i]=True
                except ValueError:texture=np.full((64,512,3),127,np.uint8);valid[tag][i]=False
                textures.append(texture)
            _,original[tag][selected]=pooled_features(encoder,np.stack(textures),device)
            print(json.dumps(dict(condition=tag,queries=min(start+32,len(query)),total=len(query),seconds=time.monotonic()-started)),flush=True)
    corrected_vectors={tag:corrected[:,j] for j,(tag,_,_) in enumerate(CONDITIONS)};cv={tag:corrected_valid[:,j] for j,(tag,_,_) in enumerate(CONDITIONS)}
    vectors={tag:complementary_vectors(original[tag],corrected_vectors[tag],protocol['weight_corrected']) for tag,_,_ in CONDITIONS};both={tag:valid[tag]&cv[tag] for tag,_,_ in CONDITIONS}
    results={}
    for strategy,features,availability in [('original',original,valid),('corrected',corrected_vectors,cv),('complement',vectors,both)]:
        measured,scores=monitor_scores(features,availability,rows);results[strategy]=measured
        for tag,data in scores.items():np.savez_compressed(out/f'scores_{strategy}_{tag}.npz',**data)
        print(json.dumps(dict(strategy=strategy,metrics=measured)),flush=True)
    baseline=json.loads((source/'CONCLUIDO.json').read_text())
    for tag in corrected_vectors:
        for key in ['rank1','tar','far','queries','extraction_failures']:assert results['corrected'][tag][key]==baseline['baseline_monitor'][tag][key]
    for key in ['rank1','tar','far','queries','extraction_failures']:assert results['original']['clean'][key]==baseline['original_monitor'][key]
    control=results['original'];candidate=results['complement'];c=candidate['clean']
    gate=all(c[k]>=control['clean'][k] for k in ['rank1','tar']) and c['far']<=.01 and all(candidate[t][k]>control[t][k] for t in ['upper10','lower10'] for k in ['rank1','tar']) and all(candidate[t]['far']<=.01 for t in ['upper10','lower10'])
    np.savez_compressed(out/'cache_features.npz',original=np.stack([original[t] for t,_,_ in CONDITIONS],1),original_valid=np.stack([valid[t] for t,_,_ in CONDITIONS],1),corrected=corrected,corrected_valid=corrected_valid)
    (out/'rows.json').write_text(json.dumps([dict(image=Path(r.image).name,subject=r.subject,side=r.side,session=r.session) for r in rows],indent=2),encoding='utf-8');(out/'interventions.json').write_text(json.dumps(interventions,indent=2),encoding='utf-8')
    final=dict(status='fixed_complement_monitor_completed',results=results,recognition_validation_gate_passed=bool(gate),absolute_target_reached=all(r['rank1']>=.9 and r['tar']>=.9 and r['far']<=.01 for r in candidate.values()),queries=480,monitor_people=16,validation_identity_inference=False,test_inference=False,frozen_candidate_replaced=False,minimum_area=None,corrected_control_reproduced=True,original_clean_control_reproduced=True,feature_cache_sha256=digest(out/'cache_features.npz'))
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)
if __name__=='__main__':main()

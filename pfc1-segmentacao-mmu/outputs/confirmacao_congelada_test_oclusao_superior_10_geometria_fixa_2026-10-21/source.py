"""Inferencia integrada do candidato congelado; nenhuma calibracao no teste."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,tempfile
import numpy as np
from PIL import Image
import torch
from torch import nn
ROOT=Path(__file__).resolve().parent
WEIGHTS={
 'rgb':('identidade_automatica_2026-10-20','7c03b4c7ef4c54e5f86e58eb550ffc124fa11384fe5c3f5b947d1041178e706d'),
 'polar':('encoder_polar_2026-10-20','db93dfcca33b8a77cd3bfbaa66f07d1efae2e976414d67748ccf5eff4a5ebe5c'),
 'r50':('resnet50_sessoes_2026-10-20','699b8236211da2fd43b104f157b6cc3835bd5d89a01a74a5b75ce4261bf35e24'),
 'convnext':('convnext_contraste_2026-10-20','a03400e62df6282e4532dce75fabd6e12d06678a8de7dc3e55a2a274c60f1529'),
 'native':('resnet50_nativo224_2026-10-21','6530b1227f271789ca7ad8a7d9011d2a9e9ee6fe71a7ce4079d2ed8a75b3388f'),
 'transformer':('transformer_polar_2026-10-21','0ad83d9f9c78e434bda11e99e01c90cc197e7e5127c3aed75e5da6df38808b87')}

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def fuse(components,calibration):
    """Labels never enter fusion; calibration fixed from development."""
    if len(components)!=9:raise ValueError('Seven shared and two ArcIris components required')
    available=np.logical_and.reduce([c['scores']>-2 for c in components]);valid=np.logical_and.reduce([c['valid'] for c in components])&available.any(1)
    z=[]
    for view in range(2):
        selected=components[:7]+[components[7+view]]
        z.append(np.mean([(c['scores']-p['mean'])/p['std'] for c,p in zip(selected,calibration[view])],axis=0))
    scores=1/(1+np.exp(-np.clip(np.mean(z,axis=0),-30,30)));scores[~available]=-2
    from normalizar_consulta import normalize
    return normalize(scores,valid)

def prepare(rows,device,folder,condition='original',level=0,fixed_geometry=False):
    from treinar_segmentacao_ubipr import MulticlassUNet
    from avaliar_dinov3_ubipr import masked_crop
    from textura_polar import prepare_texture
    from preparar_polar_vermelho import red_texture
    folder.mkdir(parents=True,exist_ok=False)
    specs={'rgb':(128,128,3),'native':(224,224,3),'polar':(64,512,3),'red':(64,512,3)}
    arrays={k:np.lib.format.open_memmap(folder/(k+'.npy'),mode='w+',dtype=np.uint8,shape=(len(rows),*shape)) for k,shape in specs.items()}
    rv=np.zeros(len(rows),bool);pv=rv.copy();interventions=[];model=MulticlassUNet(8).to(device).eval()
    model.load_state_dict(torch.load(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt',map_location='cpu',weights_only=True)['model'])
    for start in range(0,len(rows),32):
        originals=[];inputs=[]
        for r in rows[start:start+32]:
            with Image.open(r.image) as im:rgb=im.convert('RGB')
            segmentation_image=rgb
            if condition!='original' and r.session==2:
                from treinar_segmentacao_ubipr import decode_mask
                from avaliar_robustez_reconhecimento import perturb
                with Image.open(r.mask) as annotation:reference=decode_mask(annotation)==1
                assert reference.shape==np.asarray(rgb).shape[:2]
                rgb,meta=perturb(rgb,reference,condition,level)
                interventions.append({'image':Path(r.image).name,'reference_pixels':int(reference.sum()),'fraction_defined':bool(reference.any()),'affected_fraction':meta['affected_fraction']})
            if not fixed_geometry:segmentation_image=rgb
            originals.append(rgb);inputs.append(np.asarray(segmentation_image.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255)
        x=torch.from_numpy(np.stack(inputs).transpose(0,3,1,2).copy()).to(device)
        with torch.inference_mode():masks=model(x).argmax(1).cpu().numpy()==1
        for offset,(im,mask) in enumerate(zip(originals,masks)):
            i=start+offset;mask=np.asarray(Image.fromarray(mask).resize(im.size,Image.Resampling.NEAREST),bool);rv[i]=mask.any();crop=masked_crop(im,mask)
            arrays['rgb'][i]=np.asarray(crop.resize((128,128),Image.Resampling.BILINEAR));arrays['native'][i]=np.asarray(crop.resize((224,224),Image.Resampling.BILINEAR))
            try:arrays['polar'][i]=prepare_texture(np.asarray(im),mask)[0];arrays['red'][i]=red_texture(np.asarray(im),mask);pv[i]=True
            except ValueError:arrays['polar'][i]=127;arrays['red'][i]=127
        print(f'Preprocessing {min(start+32,len(rows))}/{len(rows)}',flush=True)
    for array in arrays.values():array.flush()
    np.savez_compressed(folder/'valid.npz',rgb=rv,polar=pv)
    (folder/'interventions.json').write_text(json.dumps(interventions,indent=2),encoding='utf-8')
    return arrays,rv,pv

def extract(model,images,device,batch=128,arc=False):
    features=[];mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None];std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None]
    for start in range(0,len(images),batch):
        x=torch.from_numpy(np.asarray(images[start:start+batch]).transpose(0,3,1,2).copy()).to(device).float()/255
        with torch.inference_mode(),torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda' and not arc):f=model(x*2-1 if arc else (x-mean)/std)
        if arc:features.append(f.float().cpu().numpy())
        else:features.append(nn.functional.normalize(f.float(),dim=1).cpu().numpy())
    features=np.concatenate(features)
    if arc:
        features=features.astype(np.float64);features/=np.maximum(np.linalg.norm(features,axis=1,keepdims=True),1e-12)
    if not np.isfinite(features).all():raise ValueError('Nonfinite embeddings')
    return features

def global_scores(features,valid,rows,arc=False):
    from avaliar_robustez_reconhecimento import identity
    from comparador_hdbif_lote import aggregate
    ids=sorted({identity(r) for r in rows});gi=sorted([i for i,r in enumerate(rows) if r.session==1],key=lambda i:(identity(rows[i]),Path(rows[i].image).name));qi=[i for i,r in enumerate(rows) if r.session==2]
    raw=features[qi]@features[gi].T
    if arc:raw=1-np.arccos(np.clip(raw,-1,1))/np.pi
    raw=raw.astype(np.float64);raw[:,~valid[gi]]=-2
    groups=[[j for j,i in enumerate(gi) if identity(rows[i])==eye] for eye in ids];scores=aggregate(raw,groups,'top3')
    return scores,valid[qi]&(scores>-2).any(1)

def spatial(model,images,valid,rows,device):
    from avaliar_robustez_reconhecimento import identity
    from validar_correspondencia_espacial import spatial_scores
    extractor=nn.Sequential(*list(model.backbone.children())[:7]).to(device).eval();mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None];std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None]
    with torch.inference_mode():background=extractor((torch.full((1,3,64,512),127/255,device=device)-mean)/std)
    f=[]
    for start in range(0,len(images),32):
        x=torch.from_numpy(np.asarray(images[start:start+32]).transpose(0,3,1,2).copy()).to(device).float()/255
        with torch.inference_mode():f.append(nn.functional.normalize(extractor((x-mean)/std)-background,dim=1).cpu())
    f=torch.cat(f);ids=sorted({identity(r) for r in rows});qi=[i for i,r in enumerate(rows) if r.session==2];prototypes=[];failed=[]
    for j,eye in enumerate(ids):
        gi=[i for i,r in enumerate(rows) if r.session==1 and identity(r)==eye and valid[i]]
        if gi:prototypes.append(nn.functional.normalize(f[gi].mean(0),dim=0))
        else:prototypes.append(torch.zeros_like(f[0]));failed.append(j)
    gallery=torch.stack(prototypes).to(device);scores=[]
    for start in range(0,len(qi),32):
        with torch.inference_mode():scores.append(spatial_scores(f[qi[start:start+32]].to(device),gallery,0).cpu().numpy())
    scores=np.concatenate(scores).astype(np.float64);scores[:,failed]=-2
    return scores,valid[qi]&(scores>-2).any(1)

def main():
    from avaliar_robustez_reconhecimento import load_splits,identity,metrics
    from validar_lateralidade_informada import subset
    from treinar_identidade_iris import IdentityEncoder
    import reconhecedor_resnet50,reconhecedor_convnext,reconhecedor_transformer_polar
    p=argparse.ArgumentParser();p.add_argument('--split',choices=['val','test'],required=True);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--condition',choices=['original','oclusao_superior','oclusao_inferior'],default='original');p.add_argument('--level',type=int,default=0);p.add_argument('--fixed-geometry',action='store_true',help='Diagnostic only: infer mask from original unoccluded photo');a=p.parse_args()
    if a.condition=='original':assert a.level==0
    else:assert a.split=='test' and a.level in range(1,100)
    suffix='' if a.condition=='original' else f'_{a.condition}_{a.level}'
    if a.fixed_geometry:suffix+='_geometria_fixa'
    frozen_path=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json';frozen=json.loads(frozen_path.read_text());out=a.output_root/f'confirmacao_congelada_{a.split}{suffix}_2026-10-21';out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise ValueError('Preserve previous run')
    checkpoints={name:ROOT/'outputs'/folder/'melhor_modelo.pt' for name,(folder,_) in WEIGHTS.items()}
    for name,file in checkpoints.items():
        if digest(file)!=WEIGHTS[name][1]:raise ValueError('Checkpoint changed: '+name)
    arc_base=ROOT/'data/modelos/cvrl_arciris';arc_weights=next(arc_base.rglob('ResNet100_154000.pt'));assert digest(arc_weights)=='466014be7723eb0b1a741dcff5a0c8ae51d1918818a6b021952f9c4ccd443f8f'
    assert digest(arc_base/'modules/network.py')=='de7f0cb796ebf4be02818c704d7e3afa0047dc09719b131b37cb8c26c42dd327'
    if a.split=='test':
        replay=json.loads((a.output_root/'confirmacao_congelada_val_2026-10-21/CONCLUIDO.json').read_text())['result']
        assert replay['replay_rank1_decisions_changed']==0 and replay['replay_acceptance_decisions_changed']==0
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());rows=load_splits(manifest)[a.split];ids=sorted({identity(r) for r in rows});queries=[r for r in rows if r.session==2]
    assert not {r.subject for r in rows}&{r['subject'] for r in manifest['train']}
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Frozen development candidate evaluation; test previously examined under earlier strategies, NOT fresh blind confirmation. External ArcIris pretraining identities unknown.',
      'split':a.split,'queries':len(queries),'input_images':len(rows),'query_images':1,'informed_side':True,'candidates':16,'threshold':frozen['frozen_threshold'],
      'condition':a.condition,'occluded_percent':a.level,
      'fixed_geometry_diagnostic':a.fixed_geometry,
      'geometry_scope':'Original-photo predicted mask fixes RGB support/bbox, ellipse geometry and polar support; altered pixels and CLAHE recomputed. Requires unoccluded counterpart, NOT deployable one-photo improvement. Posthoc diagnostic, no model/threshold selection.' if a.fixed_geometry else 'Mask and geometry recalculated on altered photo',
      'intervention':'Query annotated iris pixels only, exact row-major count, gray128, upper/lower; original enrollment unchanged. Rerun segmentation and geometry on altered images. Reference masks ONLY define intervention, never extraction. Empty references unchanged, all queries retained; anatomical/disease extent not measured.',
      'calibration':'Frozen development component means/stds and threshold; no calibration or selection on current evaluation labels; no quality filtering',
      'precision':'CNNs/Transformer BF16forward batch128; spatial FP32batch32; ArcIris FP32batch8; fixed before evaluation',
      'checkpoint_sha256':{k:digest(f) for k,f in checkpoints.items()},'unet_sha256':digest(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'),
      'frozen_sha256':digest(frozen_path),'script_sha256':digest(Path(__file__)),
      'external_arciris':{'weights_sha256':digest(arc_weights),'source_sha256':digest(arc_base/'modules/network.py'),'pretraining_population':'unknown'},
      'dependencies_sha256':{n:digest(ROOT/n) for n in ['textura_polar.py','preparar_polar_vermelho.py','normalizacao_eliptica.py','normalizar_consulta.py','validar_lateralidade_informada.py','comparador_hdbif_lote.py','avaliar_robustez_reconhecimento.py','avaliar_dinov3_ubipr.py','treinar_identidade_iris.py','treinar_segmentacao_ubipr.py','reconhecedor_resnet50.py','reconhecedor_convnext.py','reconhecedor_transformer_polar.py','validar_correspondencia_espacial.py']},
      'next':'If original does not meet Rank1>=90%,TAR>=90%,FMR<=1%, do not claim minimum or retune using these scores.'}
    assert protocol['unet_sha256']=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    cache=a.output_root.parent/f'cache_confirmacao_{a.split}{suffix}_2026-10-21';images,rv,pv=prepare(rows,device,cache,a.condition,a.level,a.fixed_geometry);components={}
    (out/'interventions.json').write_bytes((cache/'interventions.json').read_bytes())
    def save(name,result):
        full,valid=result;scores,labels,_=subset(full,rows,ids);components[name]=dict(scores=scores,valid=valid,labels=labels);np.savez_compressed(out/f'scores_{name}.npz',**components[name]);print(f'Component {name} saved',flush=True)
    for name in ['rgb','polar','r50','convnext','native','transformer']:
        if name in ['rgb','polar']:
            model=IdentityEncoder().to(device).eval();model.load_state_dict(torch.load(checkpoints[name],map_location='cpu',weights_only=True)['model'])
        else:model,_={'r50':reconhecedor_resnet50,'convnext':reconhecedor_convnext,'native':reconhecedor_resnet50,'transformer':reconhecedor_transformer_polar}[name].load(checkpoints[name],device)
        inp=images['polar'] if name in ['polar','transformer'] else images['native'] if name=='native' else images['rgb']
        if name=='convnext':inp=np.stack([reconhecedor_convnext.contrast(i) for i in inp])
        valid=pv if name in ['polar','transformer'] else rv
        save(name,global_scores(extract(model,inp,device),valid,rows))
        if name=='polar':save('spatial',spatial(model,inp,valid,rows,device))
        del model
        if device.type=='cuda':torch.cuda.empty_cache()
    spec=importlib.util.spec_from_file_location('arciris_frozen_network',arc_base/'modules/network.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    model=module.iresnet100();model.load_state_dict(torch.load(arc_weights,map_location='cpu',weights_only=True));model.to(device).eval()
    for name,inp in [('arc_clahe',images['polar']),('arc_red',images['red'])]:save(name,global_scores(extract(model,inp,device,8,True),pv,rows,True))
    order=['rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red'];scores,valid=fuse([components[k] for k in order],frozen['component_calibration_red_and_clahe']);labels=components['rgb']['labels']
    for c in components.values():np.testing.assert_array_equal(c['labels'],labels)
    result,correct,accepted=metrics(scores,labels,frozen['frozen_threshold'],valid);result.update(threshold=frozen['frozen_threshold'],joint_success=float((correct&accepted).mean()))
    np.savez_compressed(out/'scores_finais.npz',scores=scores,labels=labels,valid=valid,correct=correct,accepted=accepted)
    if a.split=='val' and a.condition=='original':
        with np.load(ROOT/'outputs/arciris_duas_vistas_2026-10-21/scores_equal_views_normalized.npz') as z:
            result['replay_max_abs_score_difference']=float(np.abs(scores[valid]-z['scores'][valid]).max());result['replay_rank1_decisions_changed']=int((correct!=z['correct']).sum());result['replay_acceptance_decisions_changed']=int((accepted!=z['accepted']).sum())
    final=dict(status='frozen_candidate_evaluation_completed',split=a.split,condition=a.condition,occluded_percent=a.level,result=result,minimum_area=None,target_reached=result['rank1']>=.9 and result['tar']>=.9 and result['far']<=.01,independent_blind_test=False,external_pretraining_overlap_unknown=True)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()

"""Adaptacao supervisionada ao cadastro S1,12 epocas fixas,sem selecao nas consultas."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,random,time
import numpy as np
import torch
from torch import nn
from torchvision.transforms import functional as F,InterpolationMode
ROOT=Path(__file__).resolve().parent

def enrollment_step(tail,head,cached,targets,teacher,optimizer,positions):
    from reconhecedor_resnet50 import supervised_contrastive
    y=torch.as_tensor(np.asarray(targets)[positions],dtype=torch.long)
    optimizer.zero_grad(set_to_none=True);features=nn.functional.normalize(tail(cached[positions]),dim=1)
    teacher_batch=teacher[positions].detach().clone()
    loss=nn.functional.cross_entropy(head(features,y),y)+.2*supervised_contrastive(features,y)+.1*(1-(features*teacher_batch).sum(1)).mean()
    if not torch.isfinite(loss):raise ValueError('Nonfinite enrollment loss')
    loss.backward();nn.utils.clip_grad_norm_(list(tail.parameters())+list(head.parameters()),5.);optimizer.step()
    return float(loss.detach())

def main():
    from reconhecedor_resnet50 import load,SessionBatches,supervised_contrastive
    from treinar_identidade_iris import AngularHead
    from avaliar_robustez_reconhecimento import load_splits,identity
    from validar_metrica_intra_classe import extract,score,measure
    from validar_lateralidade_informada import subset
    from normalizar_consulta import normalize
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,required=True);args=parser.parse_args()
    out=args.output_root/'adaptacao_cadastro_v2_2026-10-21';out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous experiment')
    checkpoint=ROOT/'outputs/resnet50_sessoes_2026-10-20/melhor_modelo.pt'
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val'];ids=sorted({identity(r) for r in rows})
    cache=ROOT/'data/cache_identidade_automatica_2026-10-20';images=np.load(cache/'val_crops.npy',mmap_mode='r');valid=np.load(cache/'val_valid.npy')
    gi=[i for i,r in enumerate(rows) if r.session==1 and valid[i]]
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'architecture':'resnet50_gem3_256',
        'technical_restart_of':'adaptacao_cadastro_2026-10-21: Windows NumPy int32 targets rejected by CE before first optimizer step; cast explicitly long, same scientific parameters',
        'scope':'Authorized side-informed one-query operational enrollment adaptation on UBIPr. This learner trains on known gallery identities, unlike frozen global embedding.',
        'fit_data':'Only valid S1 enrollment photos; no S2 photo/label used during fitting or epoch selection',
        'augmentation':'Fixed three views per enrollment photo:(rotation-8deg,gamma0.75),(0,1),(+8deg,1.33), black exterior preserved; no query augmentation or query pooling',
        'optimization':'Original first3 residual stages frozen; train layer4 lr1e-5, projection1e-4,new32-eye angular head1e-3; all BN running statistics frozen. AdamW wd1e-4 clip5.12fixed epochs,16eyes x4 views,4rounds/epoch,seed48. CE margin0.15 scale20 +0.2 SupCon temperature0.1 +0.1 cosine retention to original teacher embedding.',
        'execution':'Cache augmented frozen stage3 features with CUDA BF16; optimize last block/projection/head on CPU FP32 to avoid concurrent GPU memory pressure; infer full encoder CUDA BF16',
        'selection':'Final epoch12 only; no validation checkpoint search. No S2 inference until training finishes.',
        'counts':{'gallery_images':len(gi),'query_images_used_for_fitting':0,'enrolled_eyes':len(ids),'query_count':sum(r.session==2 for r in rows)},
        'enrolled_eye_order':ids,'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        'variants':'Adapted template top3 and learned-head cosine with side restriction; fixed equal5 fusion oldRGB/polar/spatial/ConvNeXt/adaptedR50; same fusion query-normalized',
        'calibration':'Validation FMR<=1%, only15same-side impostors/query; all482 queries retained, require all fusion components valid',
        'limitations':'Enrollment-specific model; for a new gallery restart from global checkpoint and repeat fixed adaptation on that gallery only. Repeated development validation, not independent confirmation.',
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['reconhecedor_resnet50.py','treinar_identidade_iris.py','normalizar_consulta.py','validar_lateralidade_informada.py']}}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    random.seed(48);np.random.seed(48);torch.manual_seed(48);torch.set_num_threads(4)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');model,_=load(checkpoint,'cpu')
    for parameter in model.parameters():parameter.requires_grad_(False)
    extractor=nn.Sequential(*list(model.backbone.children())[:7]).to(device).eval()
    mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None];std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None]
    cached=[];targets=[]
    for angle,gamma in [(-8,.75),(0,1.),(8,1.33)]:
        for start in range(0,len(gi),8):
            positions=gi[start:start+8];x=torch.from_numpy(np.stack([images[i] for i in positions]).transpose(0,3,1,2).copy()).to(device).float()/255
            x=F.adjust_gamma(F.rotate(x,angle,interpolation=InterpolationMode.BILINEAR,fill=0),gamma)
            with torch.inference_mode(),torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'):f=extractor((x-mean)/std)
            cached.append(f.float().cpu());targets.extend(ids.index(identity(rows[i])) for i in positions)
    extractor.to('cpu');del extractor
    if device.type=='cuda':torch.cuda.empty_cache()
    cached=torch.cat(cached);targets=np.array(targets);np.savez_compressed(out/'auditoria_capturas.npz',training_indices=np.array(gi),session=np.ones(len(gi),int),labels=targets)
    tail=nn.Sequential(model.backbone.layer4,model.backbone.avgpool,nn.Flatten(),model.projection).eval()
    for parameter in tail.parameters():parameter.requires_grad_(True)
    with torch.inference_mode():teacher=torch.cat([nn.functional.normalize(tail(x),dim=1) for x in cached.split(32)])
    head=AngularHead(len(ids),margin=.15,scale=20.)
    optimizer=torch.optim.AdamW([{'params':model.backbone.layer4.parameters(),'lr':1e-5},{'params':model.projection.parameters(),'lr':1e-4},{'params':head.parameters(),'lr':1e-3}],weight_decay=1e-4)
    sampler=SessionBatches(targets,np.ones(len(targets),int),seed=48);history=[];started=time.monotonic()
    for epoch in range(1,13):
        total=0.;batches=0;tail.eval();head.train()
        for positions in sampler:
            total+=enrollment_step(tail,head,cached,targets,teacher,optimizer,positions);batches+=1
        history.append({'epoch':epoch,'train_loss':total/batches});print(f'Enrollment epoch{epoch:02d} loss={total/batches:.4f} elapsed={time.monotonic()-started:.0f}s; no query evaluation',flush=True)
    del cached,teacher,tail
    torch.save({'model':model.state_dict(),'training_head':head.state_dict(),'epoch':12,'configuration':protocol},out/'melhor_modelo.pt')
    (out/'historico_treino.json').write_text(json.dumps(history,indent=2),encoding='utf-8')
    model.to(device).eval();features=extract(model,images,device);full=score(features,valid,rows);np.savez_compressed(out/'scores_full32.npz',**full)
    scores,labels,_=subset(full['scores'],rows,ids);data=dict(scores=scores,labels=labels,valid=full['valid']);result=measure(data);result['variant']='adapted_top3_side';results=[result];np.savez_compressed(out/'scores_adaptado.npz',**data)
    qi=[i for i,r in enumerate(rows) if r.session==2];head_scores=features[qi]@nn.functional.normalize(head.weight.detach(),dim=1).numpy().T
    hs,hl,_=subset(head_scores,rows,ids);hd=dict(scores=hs,labels=hl,valid=full['valid']);result=measure(hd);result['variant']='adapted_head_cosine_side';results.append(result);np.savez_compressed(out/'scores_cabeca.npz',**hd)
    paths=[ROOT/'outputs'/p for p in ['identidade_automatica_2026-10-20/scores_baseline.npz','encoder_polar_2026-10-20/scores_melhor.npz','espacial_polar_val_2026-10-20/scores_shift0.npz','convnext_contraste_2026-10-20/scores_melhor.npz']]
    components=[]
    for p in paths:
        with np.load(p) as z:scores,labels,_=subset(z['scores'],rows,ids);components.append(dict(scores=scores,labels=labels,valid=z['valid']))
    components.append(data);available=np.logical_and.reduce([c['scores']>-2 for c in components]);qvalid=np.logical_and.reduce([c['valid'] for c in components]);imp=np.ones_like(available);imp[np.arange(len(labels)),labels]=False;standardized=[];parameters=[]
    for c in components:
        np.testing.assert_array_equal(c['labels'],labels);usable=imp&c['valid'][:,None]&(c['scores']>-2);mu=float(c['scores'][usable].mean());sd=float(c['scores'][usable].std())
        if sd<=0:raise ValueError('Constant impostors')
        standardized.append((c['scores']-mu)/sd);parameters.append({'mean':mu,'std':sd})
    scores=1/(1+np.exp(-np.clip(np.mean(standardized,axis=0),-30,30)));scores[~available]=-2
    data=dict(scores=scores,labels=labels,valid=qvalid&available.any(1));result=measure(data);result.update(variant='adapted_equal_fusion',normalization=parameters);results.append(result);np.savez_compressed(out/'scores_fusao.npz',**data)
    normalized,nvalid=normalize(scores,data['valid']);ndata=dict(scores=normalized,labels=labels,valid=nvalid);result=measure(ndata);result['variant']='adapted_fusion_query_normalized';results.append(result);np.savez_compressed(out/'scores_normalizados.npz',**ndata)
    final={'status':'enrollment_adaptation_fixed12_completed','results':results,'query_images_used_for_fitting':0,'epochs':12,'test_inference':False,'minimum_area':None,'checkpoint_sha256':hashlib.sha256((out/'melhor_modelo.pt').read_bytes()).hexdigest(),'development_90_reached':any(r['rank1']>=.9 and r['tar']>=.9 for r in results)}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()

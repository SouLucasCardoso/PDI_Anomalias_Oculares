"""Tres encoders novos; pessoas separadas para ajuste, selecao e metafusao."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,hashlib,json,random,tempfile,time
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader
ROOT=Path(__file__).resolve().parent
NAMES=['r18','r50','convnext']
CONDITIONS=['clean','upper10','lower10']


def person_split(rows,seed=55):
    """Sorteio por pessoa usando apenas elegibilidade de sessoes, nunca escores."""
    key=lambda r:f"{r['subject']}_{r['side']}"
    eligible={key(r) for r in rows if r['session']==1}&{key(r) for r in rows if r['session']==2}
    paired=sorted({r['subject'] for r in rows if key(r) in eligible})
    if len(paired)<52:raise ValueError('Need enough disjoint paired people')
    order=np.random.default_rng(seed).permutation(paired).tolist()
    meta=sorted(order[:20]);monitor=sorted(order[20:36]);fit=sorted({r['subject'] for r in rows}-set(meta)-set(monitor))
    if set(fit)&set(meta) or set(fit)&set(monitor) or set(meta)&set(monitor):raise ValueError('Person overlap')
    return dict(encoder_fit=fit,encoder_monitor=monitor,fusion_fit=meta)


def query_z(raw):
    raw=np.asarray(raw,dtype=np.float64)
    if raw.ndim!=3 or raw.shape[1]<2 or raw.shape[2]!=3:raise ValueError('Expected B,K,3')
    return ((raw-raw.mean(1,keepdims=True))/np.maximum(raw.std(1,keepdims=True),1e-12)).astype(np.float32)


def fuse(components,weights):
    from normalizar_consulta import normalize
    weights=np.asarray(weights,dtype=np.float64)
    if len(components)!=3 or weights.shape!=(3,) or (weights<0).any() or not np.isfinite(weights).all() or not np.isclose(weights.sum(),1):raise ValueError('Three convex weights required')
    available=np.logical_and.reduce([c['scores']>-2 for c in components]);valid=np.logical_and.reduce([c['valid'] for c in components])&available.any(1)
    scores=np.full_like(components[0]['scores'],-2.,dtype=np.float64)
    for i in np.flatnonzero(valid):
        selected=available[i]
        if selected.sum()<2:continue
        raw=np.stack([c['scores'][i,selected] for c in components],axis=-1)[None]
        value=query_z(raw)[0]@weights;scores[i,selected]=1/(1+np.exp(-np.clip(value,-30,30)))
    return normalize(scores,valid)


def main():
    from treinar_segmentacao_ubipr import Sample
    from treinar_identidade_iris import IdentityEncoder,AngularHead
    from treinar_identidade_automatica import AutomaticCrops
    from reconhecedor_resnet50 import SessionBatches,supervised_contrastive
    from avaliar_candidato_congelado import extract,global_scores,digest
    from avaliar_robustez_reconhecimento import identity,metrics,operating_threshold
    from validar_lateralidade_informada import subset
    import reconhecedor_resnet50,reconhecedor_convnext
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    out=a.output_root/'fusao_pessoas_separadas_2026-10-21';out.mkdir(parents=True,exist_ok=True)
    if (out/'CONCLUIDO.json').exists():raise ValueError('Preserve completed experiment')
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_file.read_text())
    split=person_split(manifest['train']);raw=manifest['train'];allrows=[Sample(**r) for r in raw]
    assert not set().union(*(set(v) for v in split.values()))&{r['subject'] for r in manifest['val']}
    fit_idx=np.array([i for i,r in enumerate(raw) if r['subject'] in split['encoder_fit']]);fitrows=[allrows[i] for i in fit_idx]
    labels={eye:i for i,eye in enumerate(sorted({identity(r) for r in fitrows}))}
    weight_specs={
        'r18':('resnet18-f37072fd.pth','f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec'),
        'r50':('resnet50-11ad3fa6.pth','11ad3fa62ca79e40addfd354a8ec4b7c75143b3038b8d2a807fbc68deab379ca'),
        'convnext':('convnext_tiny-983f1562.pth','983f1562536e84ff750a1576fb08e54de751dbf2e17c0d8a4a13704341fdcd3d')}
    protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),
        scope='Exploratory train/validation only. Three NEW identity encoders, ImageNet initialization only; no previously UBIPr-trained identity tensors. No test inference or automatic promotion.',
        split='Seed55 random person partition within original TRAIN:20 paired people fusion fitting,16 OTHER paired people checkpoint monitoring, all remaining original train people encoder fitting. Meta people never used for encoder updates, BatchNorm statistics, checkpoint selection or stopping.',
        caveat='Frozen existing U-Net was trained on original TRAIN including monitoring/meta people, and generated caches. Separation applies to identity encoders only, NOT entire preprocessing pipeline. ImageNet training population not individually audited. Prior development validation reused.',
        pilot='Three globally masked RGB128 identity encoders:ResNet18,ResNet50-GeM3,ConvNeXt-Tiny CLAHE. Chosen as bounded pilot after previous weights concentrated on these models. Not the old8-group architecture, not isolated proof of splitting effect.',
        encoder_training='Session-balanced16eyes x4captures,4rounds, seed55+model index. Clean crops only, rotation10degrees/brightness/contrast15%. Angular CE scale30 margin warmup0,0.1,0.2 then0.3 in2epoch stages +0.2 SupCon T0.1. AdamW backbone1e-4,projection/head5e-4,wd1e-4,cosine30,clip5,BF16forward,FP32loss. Max30epochs,patience8 after epoch10.',
        encoder_selection='Monitor people only, clean same-side16 candidate TAR at clean-calibrated empirical FMR<=1%, tie minimum TAR across clean/upper10/lower10, tie clean Rank1. Same clean threshold used for both monitor occlusions. Checkpoint selected before meta scores are extracted.',
        fusion_training='Frozen selected3 encoders. Meta S1 enrollment/S2 queries; clean and original-photo gray128 upper/lower10% query iris interventions, segmentation recalculated. Four16-way same-side random-impostor episodes/query/condition,seed55. Query-wise candidate z scores; one shared nonnegative sum1 vector of3 weights. Full-batch Adam lr0.05,300fixed steps,CE +0.1 sum((w-1/3)^2),no regularization/epoch search.',
        validation='First validation component extraction after encoders and fusion weights fixed. Compare equal3 weights versus learned3 on identical representation, reference old frozen8-group separately. Each strategy CLEAN calibration empirical FMR<=1%,same threshold upper/lower10. All482 queries and all15 admissible impostors/query; single photo and supplied side.',
        split_people=split,counts=dict(fit_people=len(split['encoder_fit']),fit_images=len(fitrows),fit_eye_classes=len(labels),monitor_people=16,meta_people=20),
        manifest_sha256=digest(manifest_file),script_sha256=digest(Path(__file__)),imagenet_sha256={name:sha for name,(_,sha) in weight_specs.items()},
        segmenter_sha256=digest(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'),
        dependencies_sha256={name:digest(ROOT/name) for name in ['treinar_identidade_iris.py','treinar_identidade_automatica.py','reconhecedor_resnet50.py','reconhecedor_convnext.py','avaliar_candidato_congelado.py','normalizar_consulta.py']})
    if (out/'source.py').exists():
        assert (out/'source.py').read_bytes()==Path(__file__).read_bytes()
        assert json.loads((out/'protocolo.json').read_text())['manifest_sha256']==digest(manifest_file)
    else:
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    assert protocol['segmenter_sha256']=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');started=time.monotonic()
    def progress(**kwargs):
        record=dict(seconds=time.monotonic()-started,**kwargs);(out/'progresso.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record),flush=True)
    def read(file):
        with np.load(file) as z:return {k:z[k] for k in z.files}
    oldcache=ROOT/'data/cache_identidade_automatica_2026-10-20'
    original=np.load(oldcache/'train_crops.npy',mmap_mode='r');original_valid=np.load(oldcache/'train_valid.npy');assert len(original)==len(raw)
    fit_images=original[fit_idx];fit_valid=original_valid[fit_idx]
    key=lambda r:f"{r['subject']}_{r['side']}"
    eligible={key(r) for r in raw if r['session']==1}&{key(r) for r in raw if r['session']==2};paired=[r for r in allrows if identity(r) in eligible]
    cache=Path(tempfile.gettempdir())/'cache_fusao_regularizada_treino_2026-10-21'
    inputs={};cohorts={}
    for cohort,group in [('monitor','encoder_monitor'),('meta','fusion_fit')]:
        ii=np.array([i for i,r in enumerate(paired) if r.subject in split[group]]);cohorts[cohort]=[paired[i] for i in ii];inputs[cohort]={}
        for condition in CONDITIONS:
            folder=cache/condition;images=np.load(folder/'rgb.npy',mmap_mode='r');assert len(images)==len(paired)
            with np.load(folder/'valid.npz') as z:valid=z['rgb']
            inputs[cohort][condition]=(images[ii],valid[ii])
    def score(model,images,valid,rows):
        full,qvalid=global_scores(extract(model,images,device),valid,rows);scores,labels,_=subset(full,rows,sorted({identity(r) for r in rows}))
        return dict(scores=scores,labels=labels,valid=qvalid)
    def evaluate(model,conditions,rows):
        data={name:score(model,*inputs,rows) for name,inputs in conditions.items()};clean=data['clean'];imp=np.ones_like(clean['scores'],bool);imp[np.arange(len(imp)),clean['labels']]=False
        threshold=operating_threshold(clean['scores'][imp&clean['valid'][:,None]&(clean['scores']>-2)]);results={}
        for condition,c in data.items():
            r,_,_=metrics(c['scores'],c['labels'],threshold,c['valid']);results[condition]=r
        return results,data
    checkpoint_hashes={};histories={}
    for model_index,name in enumerate(NAMES):
        folder=out/name;folder.mkdir(exist_ok=True)
        def build():return IdentityEncoder() if name=='r18' else reconhecedor_resnet50.Encoder() if name=='r50' else reconhecedor_convnext.Encoder()
        if (folder/'CONCLUIDO.json').exists():
            complete=json.loads((folder/'CONCLUIDO.json').read_text());assert digest(folder/'melhor_modelo.pt')==complete['checkpoint_sha256'];checkpoint_hashes[name]=complete['checkpoint_sha256'];histories[name]=complete;continue
        if (folder/'historico.csv').exists():raise ValueError('Incomplete training preserved; use explicit recovery, never silently restart')
        seed=55+model_index;random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
        train_images=fit_images;monitor=inputs['monitor']
        if name=='convnext':
            train_images=np.stack([reconhecedor_convnext.contrast(image) for image in fit_images])
            monitor={condition:(np.stack([reconhecedor_convnext.contrast(image) for image in images]),valid) for condition,(images,valid) in inputs['monitor'].items()}
        dataset=AutomaticCrops(train_images,fit_valid,fitrows,labels,True);targets=np.array([labels[identity(fitrows[i])] for i in dataset.positions]);sessions=np.array([fitrows[i].session for i in dataset.positions])
        sampler=SessionBatches(targets,sessions,seed=seed);loader=DataLoader(dataset,batch_sampler=sampler,num_workers=0)
        model=build();file=ROOT/'data/modelos/torch/hub/checkpoints'/weight_specs[name][0];assert digest(file)==weight_specs[name][1]
        state=torch.load(file,map_location='cpu',weights_only=True)
        for k in (['classifier.2.weight','classifier.2.bias'] if name=='convnext' else ['fc.weight','fc.bias']):state.pop(k)
        model.backbone.load_state_dict(state);model.to(device);head=AngularHead(len(labels)).to(device)
        optimizer=torch.optim.AdamW([{'params':model.backbone.parameters(),'lr':1e-4},{'params':list(model.projection.parameters())+list(head.parameters()),'lr':5e-4}],weight_decay=1e-4);scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,30)
        history=[];best=(-1.,-1.,-1.);stale=0;best_epoch=0
        progress(phase='encoder_training_started',model=name,fit_images=len(dataset),excluded_training_crops=int((~fit_valid).sum()))
        for epoch in range(1,31):
            model.train();head.train();head.margin=min(.3,((epoch-1)//2)*.1);losses=[]
            for x,y in loader:
                optimizer.zero_grad();y=y.to(device)
                with torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'):f=model(x.to(device))
                loss=nn.functional.cross_entropy(head(f.float(),y),y)+.2*supervised_contrastive(f,y)
                if not torch.isfinite(loss):raise ValueError('Nonfinite loss')
                loss.backward();nn.utils.clip_grad_norm_(list(model.parameters())+list(head.parameters()),5);optimizer.step();losses.append(float(loss.detach()))
            model.eval();evaluated,_=evaluate(model,monitor,cohorts['monitor']);scheduler.step()
            result=dict(epoch=epoch,loss=float(np.mean(losses)))
            for condition,r in evaluated.items():result.update({f'{condition}_{metric}':r[metric] for metric in ['rank1','tar','far']})
            history.append(result)
            with (folder/'historico.csv').open('w',encoding='utf-8',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(result));writer.writeheader();writer.writerows(history)
            quality=(evaluated['clean']['tar'],min(r['tar'] for r in evaluated.values()),evaluated['clean']['rank1'])
            if quality>best:
                best=quality;stale=0;best_epoch=epoch;temporary=folder/'melhor_modelo.pt.part'
                torch.save(dict(model=model.state_dict(),training_head=head.state_dict(),epoch=epoch,monitor=evaluated,fit_people=split['encoder_fit'],monitor_people=split['encoder_monitor'],excluded_meta_people=split['fusion_fit'],initialization_sha256=weight_specs[name][1]),temporary);temporary.replace(folder/'melhor_modelo.pt')
            else:stale+=1
            progress(phase='encoder_epoch_completed',model=name,**result,best_epoch=best_epoch)
            if epoch>=10 and stale>=8:break
        complete=dict(model=name,best_epoch=best_epoch,epochs_trained=epoch,checkpoint_sha256=digest(folder/'melhor_modelo.pt'),monitor_best=best,test_inference=False)
        (folder/'CONCLUIDO.json').write_text(json.dumps(complete,indent=2),encoding='utf-8');checkpoint_hashes[name]=complete['checkpoint_sha256'];histories[name]=complete
        del model,head,optimizer
        if device.type=='cuda':torch.cuda.empty_cache()
    # Meta images only enter identity feature inference AFTER all checkpoint selections.
    for name in NAMES:
        folder=out/name;model=IdentityEncoder() if name=='r18' else reconhecedor_resnet50.Encoder() if name=='r50' else reconhecedor_convnext.Encoder()
        model.load_state_dict(torch.load(folder/'melhor_modelo.pt',map_location='cpu',weights_only=True)['model']);model.to(device).eval()
        for condition,(images,valid) in inputs['meta'].items():
            if name=='convnext':images=np.stack([reconhecedor_convnext.contrast(image) for image in images])
            data=score(model,images,valid,cohorts['meta']);np.savez_compressed(folder/f'scores_meta_{condition}.npz',**data)
        del model
        if device.type=='cuda':torch.cuda.empty_cache()
    rng=np.random.default_rng(55);episodes=[];audit=[]
    for condition in CONDITIONS:
        components=[read(out/name/f'scores_meta_{condition}.npz') for name in NAMES];labels_meta=components[0]['labels'];raw_scores=np.stack([c['scores'] for c in components],axis=-1)
        for c in components:np.testing.assert_array_equal(c['labels'],labels_meta)
        valid=np.logical_and.reduce([c['valid'] for c in components]);available=np.logical_and.reduce([c['scores']>-2 for c in components]);excluded=0
        for i,label in enumerate(labels_meta):
            pool=np.flatnonzero(available[i]&(np.arange(available.shape[1])!=label))
            if not valid[i] or not available[i,label] or len(pool)<15:excluded+=1;continue
            for _ in range(4):episodes.append(query_z(raw_scores[i:i+1,np.r_[label,rng.choice(pool,15,replace=False)]])[0])
        audit.append(dict(condition=condition,queries=len(valid),excluded_from_fusion_loss=excluded))
    torch.manual_seed(55);x=torch.from_numpy(np.stack(episodes)).to(device);targets=torch.zeros(len(x),device=device,dtype=torch.long);logits=nn.Parameter(torch.zeros(3,device=device));optimizer=torch.optim.Adam([logits],lr=.05)
    for step in range(300):
        optimizer.zero_grad();w=logits.softmax(0);loss=nn.functional.cross_entropy(x@w,targets)+.1*((w-1/3)**2).sum();loss.backward();optimizer.step()
    weights=logits.softmax(0).detach().cpu().numpy().astype(np.float64)
    fusion_model=dict(groups=NAMES,weights=weights.tolist(),episodes=len(x),meta_audit=audit,checkpoint_sha256=checkpoint_hashes,split_people=split,segmentation_seen_meta_people=True)
    (out/'MODELO_FUSAO.json').write_text(json.dumps(fusion_model,indent=2),encoding='utf-8');progress(phase='fusion_fitted',weights=weights.tolist())
    # First use of development-validation images by new identity encoders.
    valraw=manifest['val'];eligible_val={key(r) for r in valraw if r['session']==1}&{key(r) for r in valraw if r['session']==2};valrows=[Sample(**r) for r in valraw if key(r) in eligible_val]
    assert sum(r.session==2 for r in valrows)==482
    for name in NAMES:
        model=IdentityEncoder() if name=='r18' else reconhecedor_resnet50.Encoder() if name=='r50' else reconhecedor_convnext.Encoder();model.load_state_dict(torch.load(out/name/'melhor_modelo.pt',map_location='cpu',weights_only=True)['model']);model.to(device).eval()
        for condition,suffix in [('clean',''),('upper10','_oclusao_superior_10'),('lower10','_oclusao_inferior_10')]:
            folder=Path(tempfile.gettempdir())/f'cache_confirmacao_val{suffix}_2026-10-21';images=np.load(folder/'rgb.npy',mmap_mode='r')
            with np.load(folder/'valid.npz') as z:valid=z['rgb']
            if name=='convnext':images=np.stack([reconhecedor_convnext.contrast(image) for image in images])
            data=score(model,images,valid,valrows);np.savez_compressed(out/name/f'scores_val_{condition}.npz',**data)
        del model
        if device.type=='cuda':torch.cuda.empty_cache()
    results=[];thresholds={}
    reloaded=np.array(json.loads((out/'MODELO_FUSAO.json').read_text())['weights']);np.testing.assert_array_equal(weights,reloaded)
    for strategy,w in [('uniform',np.full(3,1/3)),('learned',reloaded)]:
        data={}
        for condition in CONDITIONS:
            components=[read(out/name/f'scores_val_{condition}.npz') for name in NAMES]
            for c in components:np.testing.assert_array_equal(c['labels'],components[0]['labels'])
            scores,valid=fuse(components,w);data[condition]=dict(scores=scores,valid=valid,labels=components[0]['labels'])
        clean=data['clean'];imp=np.ones_like(clean['scores'],bool);imp[np.arange(482),clean['labels']]=False
        threshold=operating_threshold(clean['scores'][imp&clean['valid'][:,None]&(clean['scores']>-2)]);thresholds[strategy]=threshold
        for condition,c in data.items():
            result,correct,accepted=metrics(c['scores'],c['labels'],threshold,c['valid']);result.update(strategy=strategy,condition=condition,threshold=threshold,joint_success=float((correct&accepted).mean()));results.append(result)
            np.savez_compressed(out/f'scores_{strategy}_{condition}.npz',**c,correct=correct,accepted=accepted)
    final=dict(status='person_disjoint_identity_fusion_pilot_completed',results=results,model=fusion_model,thresholds=thresholds,encoders=histories,test_inference=False,frozen_candidate_replaced=False,minimum_area=None,scope=protocol['caveat'],model_sha256=digest(out/'MODELO_FUSAO.json'))
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');progress(phase='completed',results=results)


if __name__=='__main__':main()

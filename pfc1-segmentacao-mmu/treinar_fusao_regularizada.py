"""Fusao convexa treinada exclusivamente em episodios de identidades de treino."""
from pathlib import Path
from datetime import datetime, timezone
import argparse,hashlib,importlib.util,json,random,time
import numpy as np
import torch
from torch import nn
ROOT=Path(__file__).resolve().parent
ORDER=['rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red']


def query_features(scores):
    """B,K,9 escores, candidatos disponiveis; sem rotulos na transformacao."""
    scores=np.asarray(scores,dtype=np.float64)
    if scores.ndim!=3 or scores.shape[-1]!=9 or scores.shape[1]<2:raise ValueError('Expected B,K,9')
    z=(scores-scores.mean(1,keepdims=True))/np.maximum(scores.std(1,keepdims=True),1e-12)
    return np.concatenate([z[:,:,:7],z[:,:,7:].mean(-1,keepdims=True)],axis=-1).astype(np.float32)


def predict(components,weights):
    from normalizar_consulta import normalize
    weights=np.asarray(weights,dtype=np.float64)
    if weights.shape!=(8,) or not np.isfinite(weights).all() or (weights<0).any() or not np.isclose(weights.sum(),1):raise ValueError('Expected convex8 weights')
    available=np.logical_and.reduce([c['scores']>-2 for c in components])
    valid=np.logical_and.reduce([c['valid'] for c in components])&available.any(1)
    scores=np.full_like(components[0]['scores'],-2.,dtype=np.float64)
    for i in np.flatnonzero(valid):
        selected=available[i]
        if selected.sum()<2:continue
        raw=np.stack([c['scores'][i,selected] for c in components],axis=-1)[None]
        value=query_features(raw)[0]@weights
        scores[i,selected]=1/(1+np.exp(-np.clip(value,-30,30)))
    return normalize(scores,valid)


def main():
    from treinar_segmentacao_ubipr import Sample
    from avaliar_candidato_congelado import WEIGHTS,digest,prepare,extract,global_scores,spatial
    from avaliar_robustez_reconhecimento import identity,metrics,operating_threshold
    from validar_lateralidade_informada import subset
    from treinar_identidade_iris import IdentityEncoder
    import reconhecedor_resnet50,reconhecedor_convnext,reconhecedor_transformer_polar
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    out=a.output_root/'fusao_regularizada_treino_2026-10-21';out.mkdir(parents=True,exist_ok=True)
    if (out/'CONCLUIDO.json').exists():raise ValueError('Preserve completed run')
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_file.read_text())
    raw=manifest['train'];eligible={f"{r['subject']}_{r['side']}" for r in raw if r['session']==1}&{f"{r['subject']}_{r['side']}" for r in raw if r['session']==2}
    rows=[]
    for r in raw:
        if f"{r['subject']}_{r['side']}" not in eligible:continue
        r=r.copy()
        for key in ('image','mask'):r[key]=str(ROOT/'data/ubipr/single_eye'/Path(r[key]).name)
        rows.append(Sample(**r))
    assert not {r.subject for r in rows}&{r['subject'] for r in manifest['val']}
    qi=np.array([i for i,r in enumerate(rows) if r.session==2]);ids=sorted({identity(r) for r in rows})
    protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),
        scope='Train fusion only on original TRAIN identity split; frozen encoders previously trained on these same people, hence in-sample base representations. Validation identities disjoint but reused development data. NO new test inference or automatic replacement.',
        representation='Original segmenter, original frozen nine score components grouped into8 recognizers (ArcIris views mean). Per-component single-query candidate z normalization, no label required at inference. No new segmentation branch.',
        training='All eligible train people/images, S1 enrollment/S2 query. Native-image gray128 upper/lower10% query iris intervention using annotations ONLY for intervention; recalculate automatic segmentation. Clean enrollment reused. Clean/upper/lower equally represented. Four16-way episodes per query/condition, true candidate first plus15 random same-side impostors without replacement, seed54. Training extraction failures excluded from loss only, counted and retained in train reports.',
        optimizer='One convex shared8-weight vector: softmax logits initialized0, full-batch Adam lr0.05 for300steps; listwise CE on weighted standardized scores, temperature1, plus0.1*sum((weight-1/8)^2). Fixed steps, no epoch/regularization/model selection.',
        controls='Uniform8 weights on SAME query-normalized component representation versus learned weights; also original saved frozen fusion as reference. Each strategy threshold calibrated once CLEAN validation FMR<=1%, applied unchanged upper/lower10%. All482 validation queries remain.',
        counts=dict(train_images=len(rows),train_queries=len(qi),train_people=len({r.subject for r in rows}),train_eyes=len(ids)),
        limits='Not independent validation; seen-training-identity fusion learning may fail to generalize. No label-informed selection of component per query. No minimum-area or clinical claim.',
        manifest_sha256=digest(manifest_file),script_sha256=digest(Path(__file__)),
        dependencies_sha256={name:digest(ROOT/name) for name in ['avaliar_candidato_congelado.py','textura_polar.py','normalizar_consulta.py','validar_lateralidade_informada.py']})
    if (out/'source.py').exists():
        assert (out/'source.py').read_bytes()==Path(__file__).read_bytes()
        assert json.loads((out/'protocolo.json').read_text())['manifest_sha256']==digest(manifest_file)
    else:
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;torch.manual_seed(54);np.random.seed(54);random.seed(54)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');started=time.monotonic()
    checkpoints={name:ROOT/'outputs'/folder/'melhor_modelo.pt' for name,(folder,_) in WEIGHTS.items()}
    for name,file in checkpoints.items():assert digest(file)==WEIGHTS[name][1]
    assert digest(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt')=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    cache=a.output_root.parent/'cache_fusao_regularizada_treino_2026-10-21';cache.mkdir(exist_ok=True)
    conditions=[('clean','original'),('upper10','oclusao_superior'),('lower10','oclusao_inferior')]
    for condition,kind in conditions:
        dest=cache/condition
        if (dest/'PREPARADO.json').exists():
            images={name:np.load(dest/f'{name}.npy',mmap_mode='r') for name in ('rgb','native','polar','red')}
            with np.load(dest/'valid.npz') as z:rv=z['rgb'];pv=z['polar']
        else:
            if dest.exists():raise ValueError('Incomplete preprocessing cache: '+str(dest))
            images,rv,pv=prepare(rows,device,dest,kind,0 if kind=='original' else 10)
            (dest/'PREPARADO.json').write_text(json.dumps(dict(images=len(rows),manifest_sha256=digest(manifest_file))),encoding='utf-8')
        condition_out=out/condition;condition_out.mkdir(exist_ok=True)
        def save(name,result):
            full,valid=result;scores,labels,_=subset(full,rows,ids)
            np.savez_compressed(condition_out/f'scores_{name}.npz',scores=scores,labels=labels,valid=valid)
            print(json.dumps(dict(phase='component',condition=condition,name=name,seconds=time.monotonic()-started)),flush=True)
        for name in ['rgb','polar','r50','convnext','native','transformer']:
            if (condition_out/f'scores_{name}.npz').exists() and (name!='polar' or (condition_out/'scores_spatial.npz').exists()):continue
            if name in ['rgb','polar']:
                model=IdentityEncoder().to(device).eval();model.load_state_dict(torch.load(checkpoints[name],map_location='cpu',weights_only=True)['model'])
            else:model,_={'r50':reconhecedor_resnet50,'convnext':reconhecedor_convnext,'native':reconhecedor_resnet50,'transformer':reconhecedor_transformer_polar}[name].load(checkpoints[name],device)
            inp=images['polar'] if name in ['polar','transformer'] else images['native'] if name=='native' else images['rgb']
            if name=='convnext':inp=np.stack([reconhecedor_convnext.contrast(i) for i in inp])
            valid=pv if name in ['polar','transformer'] else rv
            feature_file=out/f'features_clean_{name}.npy'
            if condition=='clean':features=extract(model,inp,device);np.save(feature_file,features)
            else:
                features=np.load(feature_file).copy();features[qi]=extract(model,inp[qi],device)
            save(name,global_scores(features,valid,rows))
            if name=='polar':save('spatial',spatial(model,inp,valid,rows,device))
            del model
            if device.type=='cuda':torch.cuda.empty_cache()
        if not all((condition_out/f'scores_{name}.npz').exists() for name in ('arc_clahe','arc_red')):
            arc=ROOT/'data/modelos/cvrl_arciris';file=next(arc.rglob('ResNet100_154000.pt'))
            assert digest(file)=='466014be7723eb0b1a741dcff5a0c8ae51d1918818a6b021952f9c4ccd443f8f'
            assert digest(arc/'modules/network.py')=='de7f0cb796ebf4be02818c704d7e3afa0047dc09719b131b37cb8c26c42dd327'
            spec=importlib.util.spec_from_file_location('arc_fusion',arc/'modules/network.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            model=module.iresnet100();model.load_state_dict(torch.load(file,map_location='cpu',weights_only=True));model.to(device).eval()
            for name,key in [('arc_clahe','polar'),('arc_red','red')]:
                if (condition_out/f'scores_{name}.npz').exists():continue
                feature_file=out/f'features_clean_{name}.npy'
                if condition=='clean':features=extract(model,images[key],device,8,True);np.save(feature_file,features)
                else:features=np.load(feature_file).copy();features[qi]=extract(model,images[key][qi],device,8,True)
                save(name,global_scores(features,pv,rows,True))
            del model
            if device.type=='cuda':torch.cuda.empty_cache()
    # The loss never reads validation scores or labels.
    rng=np.random.default_rng(54);episodes=[];train_audit=[]
    def read(file):
        with np.load(file) as z:return {k:z[k] for k in ('scores','labels','valid')}
    for condition,_ in conditions:
        components=[read(out/condition/f'scores_{name}.npz') for name in ORDER]
        for c in components:np.testing.assert_array_equal(c['labels'],components[0]['labels'])
        labels=components[0]['labels'];available=np.logical_and.reduce([c['scores']>-2 for c in components]);valid=np.logical_and.reduce([c['valid'] for c in components])
        matrix=np.stack([c['scores'] for c in components],axis=-1);excluded=0
        for i,label in enumerate(labels):
            pool=np.flatnonzero(available[i]&(np.arange(len(available[i]))!=label))
            if not valid[i] or not available[i,label] or len(pool)<15:excluded+=1;continue
            for _ in range(4):
                columns=np.r_[label,rng.choice(pool,15,replace=False)]
                episodes.append(query_features(matrix[i:i+1,columns])[0])
        train_audit.append(dict(condition=condition,queries=len(labels),excluded_from_loss=excluded))
    x=torch.from_numpy(np.stack(episodes)).to(device);targets=torch.zeros(len(x),device=device,dtype=torch.long)
    logits=nn.Parameter(torch.zeros(8,device=device));optimizer=torch.optim.Adam([logits],lr=.05);history=[]
    for step in range(300):
        optimizer.zero_grad();weights=logits.softmax(0);ce=nn.functional.cross_entropy(x@weights,targets);loss=ce+.1*((weights-1/8)**2).sum();loss.backward();optimizer.step()
        if step%50==0 or step==299:history.append(dict(step=step,loss=float(loss.detach()),ce=float(ce.detach())))
    weights=logits.softmax(0).detach().cpu().numpy().astype(np.float64)
    model=dict(groups=ORDER[:7]+['arc_mean'],weights=weights.tolist(),training_episodes=len(x),training_audit=train_audit,history=history,protocol_sha256=digest(out/'protocolo.json'))
    (out/'MODELO_FUSAO.json').write_text(json.dumps(model,indent=2),encoding='utf-8')
    print(json.dumps(dict(phase='fusion_fitted',model=model)),flush=True)
    # First access to validation component scores occurs after fitting finishes.
    validation={}
    for condition,suffix in [('clean',''),('upper10','_oclusao_superior_10'),('lower10','_oclusao_inferior_10')]:
        folder=ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21';validation[condition]=[read(folder/f'scores_{name}.npz') for name in ORDER]
        for c in validation[condition]:np.testing.assert_array_equal(c['labels'],validation[condition][0]['labels'])
    results=[];thresholds={}
    reloaded=np.array(json.loads((out/'MODELO_FUSAO.json').read_text())['weights'])
    np.testing.assert_array_equal(reloaded,weights)
    for strategy,w in [('uniform_query_z',np.full(8,1/8)),('learned_query_z',reloaded)]:
        data={}
        for condition,components in validation.items():
            scores,valid=predict(components,w);data[condition]=dict(scores=scores,valid=valid,labels=components[0]['labels'])
        clean=data['clean'];imp=np.ones_like(clean['scores'],bool);imp[np.arange(482),clean['labels']]=False
        threshold=operating_threshold(clean['scores'][imp&clean['valid'][:,None]&(clean['scores']>-2)]);thresholds[strategy]=threshold
        for condition,c in data.items():
            r,correct,accepted=metrics(c['scores'],c['labels'],threshold,c['valid']);r.update(strategy=strategy,condition=condition,threshold=threshold,joint_success=float((correct&accepted).mean()));results.append(r)
            np.savez_compressed(out/f'scores_{strategy}_{condition}.npz',**c,correct=correct,accepted=accepted)
    final=dict(status='regularized_fusion_train_validation_completed',model=model,results=results,thresholds=thresholds,model_sha256=digest(out/'MODELO_FUSAO.json'),test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)


if __name__=='__main__':main()

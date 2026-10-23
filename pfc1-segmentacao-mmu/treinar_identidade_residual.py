"""Correcao residual de embeddings por ridge de treino, backbone congelado."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
import torch
from torch import nn
ROOT=Path(__file__).resolve().parent

def fit_residual(x,residual,weights,regularization=1.):
    x=np.asarray(x,np.float64);residual=np.asarray(residual,np.float64);weights=np.asarray(weights,np.float64);total=weights.sum()
    if total<=0 or len(x)!=len(residual) or len(x)!=len(weights):raise ValueError('Invalid paired training observations')
    mean=(x*weights[:,None]).sum(0)/total;std=np.sqrt(((x-mean)**2*weights[:,None]).sum(0)/total);std=np.maximum(std,1e-6);z=(x-mean)/std;offset=(residual*weights[:,None]).sum(0)/total
    matrix=np.linalg.solve((z.T@(z*weights[:,None]))/total+regularization*np.eye(x.shape[1]),(z.T@((residual-offset)*weights[:,None]))/total)
    return dict(mean=mean,std=std,offset=offset,matrix=matrix)

def correct(raw,base,parameters):
    prediction=np.asarray(base,np.float64)+(np.asarray(raw,np.float64)-parameters['mean'])/parameters['std']@parameters['matrix']+parameters['offset'];norm=np.linalg.norm(prediction,axis=1,keepdims=True)
    return prediction/np.maximum(norm,1e-12)

def features(model,images,device,positions=None,view=0,levels=None):
    from treinar_identidade_oclusao import occlude_crop
    positions=np.arange(len(images)) if positions is None else np.asarray(positions);raw=[];base=[];mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None];std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None]
    for start in range(0,len(positions),128):
        indices=positions[start:start+128];batch=np.array(images[indices],copy=True)
        if view:
            for j in range(len(batch)):batch[j]=occlude_crop(batch[j],float(levels[start+j]),view==2)
        x=torch.from_numpy(batch.transpose(0,3,1,2).copy()).to(device).float()/255
        with torch.inference_mode(),torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'):
            f=model.backbone((x-mean)/std);embedding=nn.functional.normalize(model.projection(f),dim=1)
        raw.append(f.float().cpu().numpy());base.append(nn.functional.normalize(embedding.float(),dim=1).cpu().numpy())
    return np.concatenate(raw),np.concatenate(base)

def main():
    from treinar_identidade_iris import IdentityEncoder
    from treinar_segmentacao_ubipr import Sample
    from avaliar_candidato_congelado import global_scores
    from avaliar_robustez_reconhecimento import identity,operating_threshold,metrics
    from validar_lateralidade_informada import subset
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'identidade_residual_oclusao_2026-10-21';out.mkdir(parents=True,exist_ok=False)
    cache=a.output_root.parent/'cache_identidade_oclusao_segmentacao_2026-10-21';original=ROOT/'outputs/identidade_arcface_ubipr_2026-10-20/melhor_modelo.pt';seg=ROOT/'outputs/segmentacao_oclusao_2026-10-21/melhor_modelo.pt';manifest_path=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_path.read_text());val=[Sample(**r) for r in manifest['val']];eligible={identity(r) for r in val if r.session==1}&{identity(r) for r in val if r.session==2};val=[r for r in val if identity(r) in eligible];ids=sorted({identity(r) for r in val});assert not {r.subject for r in val}&{r['subject'] for r in manifest['train']}
    original_hash=hashlib.sha256(original.read_bytes()).hexdigest();seg_hash=hashlib.sha256(seg.read_bytes()).hexdigest();assert original_hash=='6060c164eada674712127830b2d188a9e6b4ed210f7b8d595e58fdfeb10387fc' and seg_hash=='8f126141f4dd7fc31352e9135b69e901454449dc5e4493ab5e973d4c8643035c'
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Train-only fixed residual regression, evaluated on development validation ONLY; follows rejected gradient adaptation, no test inference',
      'method':'Frozen original ResNet18 backbone/projection. Learn512D standardized raw-feature to256D residual(clean teacher embedding minus student embedding). Ridge lambda1, unpenalized residual offset. Return L2(base embedding+predicted residual). No backbone/BN/projection changes.',
      'pairs':'Same valid training pairs/crop cache as gradient attempt; teacher original segmentation clean crop. Three student views: clean weight2, upper and lower occlusions uniform1..40% each weight1. Seed53, no rotation/color changes. Cropped predicted support, not native/anatomical fraction.',
      'statistics':'Weighted centering/std, offsets and covariance from TRAIN only. No regularization/weight search, no validation checkpoint selection.',
      'evaluation':'Clean/native upper/lower10% robust-segmenter validation caches, all482 queries,16 same-side candidates. One threshold calibrated on CLEAN validation FMR<=1%, reused unchanged for occlusions. Release criteria unchanged; no automatic replacement.',
      'original_encoder_sha256':original_hash,'segmenter_sha256':seg_hash,'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),'teacher_cache_sha256':hashlib.sha256((cache/'teacher.npy').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');state=torch.load(original,map_location='cpu',weights_only=True);model=IdentityEncoder().to(device).eval();model.load_state_dict(state['model'])
    images=np.load(cache/'train_crops.npy',mmap_mode='r');valid=np.load(cache/'train_valid.npy')&np.load(ROOT/'data/cache_identidade_automatica_2026-10-20/train_valid.npy');positions=np.flatnonzero(valid);teacher=np.load(cache/'teacher.npy');rng=np.random.default_rng(53);raw=[];residual=[];weights=[]
    for view,weight in [(0,2.),(1,1.),(2,1.)]:
        levels=rng.uniform(1,40,len(positions));x,base=features(model,images,device,positions,view,levels);raw.append(x);residual.append(teacher[positions]-base);weights.append(np.full(len(positions),weight));print(f'Train-only frozen feature view{view} extracted',flush=True)
    parameters=fit_residual(np.concatenate(raw),np.concatenate(residual),np.concatenate(weights));np.savez_compressed(out/'regressao_residual.npz',**parameters)
    torch.save({'model':state['model'],'residual':{k:torch.from_numpy(v) for k,v in parameters.items()},'configuration':protocol},out/'melhor_modelo.pt')
    data={};baseline={}
    for name,prefix in [('clean',''),('upper10','_oclusao_superior_10'),('lower10','_oclusao_inferior_10')]:
        folder=a.output_root.parent/f'cache_confirmacao_val{prefix}_segmentador_{seg_hash[:12]}_2026-10-21';images=np.load(folder/'rgb.npy',mmap_mode='r')
        with np.load(folder/'valid.npz') as z:valid=z['rgb']
        raw,base=features(model,images,device)
        for target,vectors in [(data,correct(raw,base,parameters)),(baseline,base)]:
            full,qvalid=global_scores(vectors,valid,val);scores,labels,_=subset(full,val,ids);target[name]=dict(scores=scores,labels=labels,valid=qvalid)
    results=[]
    for family,group in [('baseline',baseline),('melhor',data)]:
        clean=group['clean'];imp=np.ones_like(clean['scores'],bool);imp[np.arange(len(clean['labels'])),clean['labels']]=False;threshold=operating_threshold(clean['scores'][imp&clean['valid'][:,None]&(clean['scores']>-2)])
        for name,c in group.items():
            result,correctness,accepted=metrics(c['scores'],c['labels'],threshold,c['valid']);c.update(correct=correctness,accepted=accepted);result.update(method=family,condition=name,threshold=threshold);results.append(result);np.savez_compressed(out/f'scores_{family}_{name}.npz',**c)
    final={'status':'train_only_residual_identity_completed','best_epoch':None,'results':results,'valid_training_pairs':len(positions),'checkpoint_sha256':hashlib.sha256((out/'melhor_modelo.pt').read_bytes()).hexdigest(),'test_inference':False,'frozen_candidate_replaced':False,'minimum_area':None}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()

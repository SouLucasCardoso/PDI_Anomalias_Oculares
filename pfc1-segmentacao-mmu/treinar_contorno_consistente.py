"""Segundo piloto: destilação geométrica limpa, reutilizando features de treino."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,json,random
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader,TensorDataset
from contorno_externo import OuterCorrection
from treinar_contorno_externo import WEIGHT
from avaliar_candidato_congelado import digest
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    source=a.output_root/'contorno_externo_2026-10-23';out=a.output_root/'contorno_consistente_2026-10-23';out.mkdir(parents=True,exist_ok=False)
    old=json.loads((source/'protocolo.json').read_text());completion=json.loads((source/'CONCLUIDO.json').read_text());assert not completion['recognition_validation_gate_passed']
    protocol=dict(old)
    protocol.update(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Second fixed training-only pilot after annotation-target head failed clean guard; reused internal monitor and cached3condition TRAIN features, no identity validation/test fitting.',
        target='FROZEN CLEAN predicted outer ellipse of the same TRAIN image is teacher for all3views, instead of annotation target. Clean teacher is available ONLY during training. Annotation target retained ONLY for internal geometry evaluation. Teacher errors inherited; no anatomical guarantee.',
        training='Seed62; same frozen2048features,baseline5,residual head and FIT-clean standardization. AdamW3e-4 wd1e-4,B128,max12epochs,patience3 after4. Equal3view weighted SmoothL1 to CLEAN baseline teacher plus4xweighted clean residual MSE; no weight/loss search. No RGB reconstruction or identity losses.',
        selection=old['selection'],
        reason='First head reduced occluded error but violated unchanged5% clean-loss guard. New hypothesis preserves teacher clean behavior explicitly; does NOT relax acceptance or select on recognition results.',
        source_training_protocol_sha256=digest(source/'protocolo.json'),source_completion_sha256=digest(source/'CONCLUIDO.json'),source_cache_sha256={group:digest(source/f'inputs_{group}.npz') for group in ['fit','monitor']},script_sha256=digest(Path(__file__)),module_sha256=digest(ROOT/'contorno_externo.py'))
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());(out/'contorno_source.py').write_bytes((ROOT/'contorno_externo.py').read_bytes())
    torch.manual_seed(62);np.random.seed(62);random.seed(62);torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device='cuda' if torch.cuda.is_available() else 'cpu'
    prepared={}
    for group in ['fit','monitor']:
        with np.load(source/f'inputs_{group}.npz') as z:prepared[group]={k:z[k] for k in ['features','baseline','target']}
    mean=prepared['fit']['features'][:,0].mean(0);std=prepared['fit']['features'][:,0].std(0).clip(1e-5)
    for data in prepared.values():data['standardized']=(data['features']-mean)/std
    loader=DataLoader(TensorDataset(*[torch.from_numpy(prepared['fit'][k]) for k in ['standardized','baseline']]),batch_size=128,shuffle=True)
    x=torch.from_numpy(prepared['monitor']['standardized']).to(device);b=torch.from_numpy(prepared['monitor']['baseline']).to(device);t=torch.from_numpy(prepared['monitor']['target']).to(device)
    model=OuterCorrection().to(device);optimizer=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4);weight=torch.tensor(WEIGHT,device=device)
    def loss(pred,target):return (nn.functional.smooth_l1_loss(pred,target,reduction='none')*weight).mean(-1)
    def predict(features,baseline):return model(features.flatten(0,1),baseline.flatten(0,1)).reshape(len(features),3,5)
    baseline=loss(b,t[:,None].expand_as(b)).mean(0).cpu().numpy();drift0=(((b[:,1:]-b[:,:1])**2)*weight).mean((0,2)).cpu().numpy()
    best=float(max(baseline[1:]));best_epoch=0;stale=0;history=[];selected=None
    for epoch in range(13):
        losses=[];model.train()
        if epoch:
            for features,base in loader:
                features=features.to(device);base=base.to(device);optimizer.zero_grad();pred=predict(features,base)
                teacher=base[:,:1].expand_as(pred);distill=loss(pred,teacher).mean();anchor=((pred[:,0]-base[:,0])**2*weight).mean();value=distill+4*anchor
                if not torch.isfinite(value):raise ValueError('Nonfinite distillation')
                value.backward();nn.utils.clip_grad_norm_(model.parameters(),5);optimizer.step();losses.append(float(value.detach()))
        model.eval()
        with torch.inference_mode():
            pred=predict(x,b);values=loss(pred,t[:,None].expand_as(pred)).mean(0).cpu().numpy();drift=(((pred[:,1:]-pred[:,:1])**2)*weight).mean((0,2)).cpu().numpy()
        eligible=values[0]<=1.05*baseline[0] and bool(np.all(drift<=drift0+1e-12));worst=float(max(values[1:]))
        row=dict(epoch=epoch,train_loss=float(np.mean(losses)) if losses else None,clean_loss=float(values[0]),upper10_loss=float(values[1]),lower10_loss=float(values[2]),upper_drift=float(drift[0]),lower_drift=float(drift[1]),eligible=bool(eligible));history.append(row)
        if epoch==0 or (eligible and worst<best):
            best=worst;best_epoch=epoch;stale=0;selected=pred.cpu().numpy()
            torch.save(dict(model=model.state_dict(),feature_mean=torch.from_numpy(mean),feature_std=torch.from_numpy(std),epoch=epoch,configuration=protocol,monitor=row),out/'melhor_modelo.pt')
        elif epoch:stale+=1
        with (out/'historico.csv').open('w',newline='',encoding='utf-8') as f:writer=csv.DictWriter(f,fieldnames=list(row));writer.writeheader();writer.writerows(history)
        print(json.dumps(row),flush=True)
        if epoch>=4 and stale>=3:break
    np.savez_compressed(out/'predicoes_monitor.npz',predictions=selected,baseline=prepared['monitor']['baseline'],target=prepared['monitor']['target'])
    final=dict(status='clean_teacher_outer_geometry_training_completed',best_epoch=best_epoch,epochs_trained=epoch,best_worst_occlusion_loss=best,baseline_losses=baseline.tolist(),baseline_drift=drift0.tolist(),recognition_validation_gate_passed=bool(best_epoch>0 and best<max(baseline[1:])),checkpoint_sha256=digest(out/'melhor_modelo.pt'),data_audit=completion['data_audit'],test_inference=False,identity_validation_in_training=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)

if __name__=='__main__':main()

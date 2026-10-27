"""Reexecuta SOMENTE o ajuste barato para preservar a última época rejeitada."""
from pathlib import Path
import argparse,csv,json
import numpy as np
import torch
from torch.utils.data import DataLoader,TensorDataset
from adaptador_polar import PolarAdapter,apply_adapter
from treinar_adaptador_polar import monitor_scores,CONDITIONS
from avaliar_candidato_congelado import digest
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'adaptador_polar_cadastro_fixo_2026-10-23'
    final=json.loads((out/'CONCLUIDO.json').read_text());assert not final['recognition_validation_gate_passed']
    with np.load(out/'cache_features.npz') as z:c={k:z[k] for k in z.files}
    rows=[SimpleNamespace(**r) for r in json.loads((out/'rows.json').read_text())]
    with (out/'historico.csv').open(encoding='utf-8',newline='') as f:history=list(csv.DictReader(f))
    fi=c['fit_indices'];mi=c['monitor_indices'];mean=c['raw'][fi,0].mean(0);std=c['raw'][fi,0].std(0).clip(1e-5)
    loader=DataLoader(TensorDataset(torch.from_numpy((c['raw'][fi]-mean)/std),torch.from_numpy(c['base'][fi]),torch.from_numpy(c['teacher'][fi])),batch_size=128,shuffle=True)
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device='cuda' if torch.cuda.is_available() else 'cpu';torch.manual_seed(63)
    model=PolarAdapter().to(device);optimizer=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4);loss_difference=0.
    for epoch in range(1,final['epochs_trained']+1):
        losses=[];model.train()
        for x,b,t in loader:
            x=x.to(device);b=b.to(device);t=t.to(device);optimizer.zero_grad();pred,delta=model(x.flatten(0,1),b.flatten(0,1));pred=pred.reshape(len(x),3,256)
            alignment=1-(pred*t[:,None]).sum(-1);loss=(alignment*alignment.new_tensor([4.,1.,1.])).sum(1).mean()/6+.01*delta.square().mean()
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5);optimizer.step();losses.append(float(loss.detach()))
        recorded=float(history[epoch]['train_loss']);actual=float(np.mean(losses));loss_difference=max(loss_difference,abs(recorded-actual));np.testing.assert_allclose(actual,recorded,rtol=1e-6,atol=1e-8)
    model.eval();vectors={tag:apply_adapter(model,c['raw'][mi,j],c['base'][mi,j],mean,std,device) for j,(tag,_,_) in enumerate(CONDITIONS)}
    valid={tag:c['valid'][mi,j] for j,(tag,_,_) in enumerate(CONDITIONS)};mr=[rows[i] for i in mi];measured,scores=monitor_scores(vectors,valid,mr);last=history[-1];cosines={}
    for j,(tag,_,_) in enumerate(CONDITIONS):
        for key in ['rank1','tar','far']:assert measured[tag][key]==float(last[tag+'_'+key])
        paired=valid[tag]&c['teacher_valid'][mi];cosines[tag]=float(np.sum(vectors[tag][paired].astype(np.float64)*c['teacher'][mi][paired].astype(np.float64),1).mean());np.testing.assert_allclose(cosines[tag],float(last[tag+'_teacher_cosine']),rtol=0,atol=1e-12)
        np.savez_compressed(out/f'scores_rejected_last_{tag}.npz',**scores[tag])
    file=out/'ultima_epoca_rejeitada.pt';torch.save(dict(model=model.state_dict(),raw_mean=torch.from_numpy(mean),raw_std=torch.from_numpy(std),epoch=final['epochs_trained'],rejected=True,monitor=measured,monitor_cosines=cosines),file)
    report=dict(status='rejected_last_epoch_training_reproduced',epoch=final['epochs_trained'],maximum_training_loss_difference=loss_difference,metrics=measured,teacher_cosines=cosines,checkpoint_sha256=digest(file),accepted=False,selected_epoch_unchanged=final['best_epoch'],validation_identity_inference=False,test_inference=False)
    (out/'REPRODUCAO_ULTIMA_EPOCA.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

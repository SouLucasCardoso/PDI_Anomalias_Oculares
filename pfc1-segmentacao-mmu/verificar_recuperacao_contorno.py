"""Confere o pacote restaurado sem refazer os caches de características/imagens."""
from pathlib import Path
import argparse,csv,json
import numpy as np
import torch
from torch import nn
from avaliar_candidato_congelado import digest,fuse
from avaliar_robustez_reconhecimento import metrics
from treinar_contorno_externo import WEIGHT
ROOT=Path(__file__).resolve().parent
ORDER=['rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red']
SUFFIX={'clean':'','upper10':'_oclusao_superior_10','lower10':'_oclusao_inferior_10'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--restored-root',type=Path,required=True);a=p.parse_args();out=a.restored_root
    geometry=[]
    for name in ['contorno_externo_2026-10-23','contorno_consistente_2026-10-23']:
        folder=out/name;final=json.loads((folder/'CONCLUIDO.json').read_text());assert digest(folder/'melhor_modelo.pt')==final['checkpoint_sha256']
        state=torch.load(folder/'melhor_modelo.pt',map_location='cpu',weights_only=True);assert state['epoch']==final['best_epoch']
        assert state['feature_mean'].shape==state['feature_std'].shape==(2048,) and bool(torch.all(state['feature_std']>0))
        with np.load(folder/'predicoes_monitor.npz') as z:pred=torch.from_numpy(z['predictions']);target=torch.from_numpy(z['target']);base=torch.from_numpy(z['baseline'])
        values=(nn.functional.smooth_l1_loss(pred,target[:,None].expand_as(pred),reduction='none')*torch.tensor(WEIGHT)).mean(-1).mean(0).numpy()
        audit=json.loads((folder/'AUDITORIA_REPRODUCAO.json').read_text());np.testing.assert_allclose(values,audit['selected_losses'],rtol=1e-5,atol=1e-10)
        drift=(((pred[:,1:]-pred[:,:1])**2)*torch.tensor(WEIGHT)).mean((0,2)).numpy()
        gate=final['best_epoch']>0 and max(values[1:])<max(final['baseline_losses'][1:]) and values[0]<=1.05*final['baseline_losses'][0] and np.all(drift<=np.array(final['baseline_drift'])+1e-9)
        assert bool(gate)==final['recognition_validation_gate_passed'];geometry.append(dict(experiment=name,gate=bool(gate),selected_epoch=final['best_epoch']))
    folder=out/'contorno_consistente_val_2026-10-23';final=json.loads((folder/'CONCLUIDO.json').read_text());records=[]
    for name,value in final['source_scores_sha256'].items():assert digest(Path(name))==value
    for record in final['results']:
        tag=record['condition'];strategy=record['strategy'];components=[]
        for name in ORDER:
            file=folder/tag/f'scores_{name}.npz' if name in ['polar','spatial','transformer','arc_clahe','arc_red'] else ROOT/'outputs'/f'confirmacao_congelada_val{SUFFIX[tag]}_2026-10-21'/f'scores_{name}.npz'
            with np.load(file) as z:components.append({k:z[k] for k in ['scores','labels','valid']})
        params=final['parameters'][strategy];scores,valid=fuse(components,params['calibration']);labels=components[0]['labels']
        with np.load(folder/f'{strategy}_{tag}.npz') as z:
            np.testing.assert_array_equal(scores,z['scores']);np.testing.assert_array_equal(valid,z['valid']);np.testing.assert_array_equal(labels,z['labels'])
            measured,correct,accepted=metrics(scores,labels,params['threshold'],valid);np.testing.assert_array_equal(correct,z['correct']);np.testing.assert_array_equal(accepted,z['accepted'])
        for key in ['rank1','tar','far','queries','extraction_failures']:assert measured[key]==record[key]
        with (folder/f'{strategy}_{tag}.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
        assert len(rows)==482;np.testing.assert_array_equal(np.array([[float(row[f'score_{j}']) for j in range(16)] for row in rows]),scores)
        records.append(dict(strategy=strategy,condition=tag,correct=int(correct.sum()),accepted=int(accepted.sum())))
    result=dict(status='restored_outer_artifacts_verified',geometry=geometry,identity_records=records,checkpoint_hashes_verified=True,restored_score_fusion_and_csv_exact=True,full_feature_or_image_forward_replayed=False)
    (out/'VERIFICACAO_RECUPERACAO.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()

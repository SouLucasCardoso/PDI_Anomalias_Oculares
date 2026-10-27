"""Confere selecao, checkpoints e monitor; opcionalmente refaz o adaptador no cache."""
from pathlib import Path
from types import SimpleNamespace
import argparse,csv,json
import numpy as np
import torch
from adaptador_polar import PolarAdapter,apply_adapter
from treinar_adaptador_polar_top3 import NAME,CONDITIONS,eligible_clean,advancement
from perda_identidade_polar import selection_key
from treinar_adaptador_polar import monitor_scores
from avaliar_candidato_congelado import digest
from avaliar_robustez_reconhecimento import metrics

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--features',action='store_true');a=p.parse_args();folder=a.root/NAME;done=json.loads((folder/'CONCLUIDO.json').read_text());protocol=json.loads((folder/'protocolo.json').read_text());assert digest(folder/'source.py')==protocol['script_sha256']
    with (folder/'historico.csv').open(encoding='utf-8',newline='') as f:history=list(csv.DictReader(f))
    baseline=done['baseline_monitor'];best=None;selected=0;stale=0
    for row in history:
        measured={t:{k:float(row[t+'_'+k]) for k in ['rank1','tar','far']} for t,_,_ in CONDITIONS};eligible=eligible_clean(measured,baseline);assert eligible==(row['eligible']=='True')
        key=selection_key(measured,{t:float(row[t+'_teacher_cosine']) for t,_,_ in CONDITIONS},baseline,int(row['epoch']))
        epoch=int(row['epoch'])
        if epoch==0 or eligible and (best is None or key>best):
            if eligible:best=key
            selected=epoch;stale=0
        elif epoch:stale+=1
    assert selected==done['selected_epoch'] and epoch==done['epochs_trained'];assert epoch==12 or epoch>=5 and stale>=4
    states={}
    for name,file,key,expected_epoch in [('selected','melhor_modelo.pt','checkpoint_sha256',selected),('last','ultima_epoca.pt','last_checkpoint_sha256',epoch)]:
        assert digest(folder/file)==done[key];state=torch.load(folder/file,map_location='cpu',weights_only=True);assert state['epoch']==expected_epoch;states[name]=state
    checked=[]
    for name in ['baseline','selected','last']:
        group=done[name+'_monitor']
        for tag,record in group.items():
            assert record['threshold']==group['clean']['threshold']
            with np.load(folder/f'scores_{name}_{tag}.npz') as z:
                measured,correct,accepted=metrics(z['scores'],z['labels'],record['threshold'],z['valid']);np.testing.assert_array_equal(correct,z['correct']);np.testing.assert_array_equal(accepted,z['accepted'])
            for key in ['rank1','tar','far','queries','extraction_failures']:assert measured[key]==record[key]
            assert int(correct.sum())==record['correct'] and int(accepted.sum())==record['accepted'];checked.append(dict(strategy=name,condition=tag,correct=int(correct.sum()),accepted=int(accepted.sum())))
    full=False;cache=Path(protocol['source_cache']) if a.features else folder/'cache_features.npz'
    if cache.exists():
        assert digest(cache)==protocol['source_cache_sha256']
        with np.load(cache) as z:c={k:z[k] for k in z.files}
        rows=[SimpleNamespace(**r) for r in json.loads((folder/'rows.json').read_text())];fi=c['fit_indices'];mi=c['monitor_indices'];assert not set(fi)&set(mi)
        assert {rows[i].subject for i in fi}.isdisjoint({rows[i].subject for i in mi});assert len(mi)==960
        mean=c['raw'][fi,0].mean(0);std=c['raw'][fi,0].std(0).clip(1e-5);torch.set_num_threads(4);device='cuda' if torch.cuda.is_available() else 'cpu'
        for name,state in states.items():
            np.testing.assert_array_equal(mean,state['raw_mean'].numpy());np.testing.assert_array_equal(std,state['raw_std'].numpy());model=PolarAdapter().to(device).eval();model.load_state_dict(state['model'])
            vectors={t:apply_adapter(model,c['raw'][mi,j],c['base'][mi,j],mean,std,device) for j,(t,_,_) in enumerate(CONDITIONS)};valid={t:c['valid'][mi,j] for j,(t,_,_) in enumerate(CONDITIONS)}
            measured,scores=monitor_scores(vectors,valid,[rows[i] for i in mi]);assert measured==done[name+'_monitor']
            for tag,data in scores.items():
                with np.load(folder/f'scores_{name}_{tag}.npz') as z:
                    for key,value in data.items():np.testing.assert_array_equal(value,z[key])
        with np.load(folder/'cadastros_ajuste.npz') as z:
            gallery=z['gallery_indices'];padded=z['padded_indices'];eye_labels=z['fit_labels'];sides=z['eye_sides']
            np.testing.assert_array_equal(z['fit_indices'],fi);np.testing.assert_array_equal(z['fit_query_flags'],[rows[i].session==2 for i in fi])
        fit=set(protocol['fit_people']);assert all(rows[i].subject in fit and rows[i].session==1 and c['teacher_valid'][i] for i in gallery)
        eyes=sorted({(rows[i].subject,rows[i].side) for i in fi});expected_gallery=[]
        for j,eye in enumerate(eyes):
            gi=[i for i,r in enumerate(rows) if r.subject in fit and (r.subject,r.side)==eye and r.session==1 and c['teacher_valid'][i]];expected_gallery.extend(gi)
            np.testing.assert_array_equal(padded[j][padded[j]>=0],gi);assert sides[j]==(0 if eye[1]=='L' else 1)
        np.testing.assert_array_equal(expected_gallery,gallery);np.testing.assert_array_equal(eye_labels,[eyes.index((rows[i].subject,rows[i].side)) for i in fi])
        assert all(len(row['gallery_sha256'])==64 for row in history)
        full=True
    gate=advancement(done['selected_monitor'],baseline,selected);assert gate==done['recognition_validation_gate_passed'];assert not done['test_inference'] and not done['validation_identity_inference'] and not done['frozen_candidate_replaced']
    report=dict(status='top3_hardnegative_adapter_verified',selected_epoch=selected,training_selection_reproduced=True,checkpoint_hashes_verified=True,feature_forward_and_scores_exact=full,score_decisions_reproduced=True,monitor_gate_reproduced=bool(gate),records=checked,new_cnn_inference=False)
    validation=a.root/NAME.replace('_2026','_val_2026')
    if (validation/'CONCLUIDO.json').exists() and not gate:
        vf=json.loads((validation/'CONCLUIDO.json').read_text());assert not vf['validation_identity_inference'] and not vf['test_inference'];report['validation_skipped_by_gate']=True
    (folder/('AUDITORIA_REPRODUCAO.json' if full else 'VERIFICACAO_RECUPERACAO.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()



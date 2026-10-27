"""Confere selecao, checkpoints e monitor; opcionalmente refaz o adaptador no cache."""
from pathlib import Path
from types import SimpleNamespace
import argparse,csv,json
import numpy as np
import torch
from ajuste_bloco_polar import FullTail
from encoder_polar_espacial import tail_vectors
from preparar_encoder_espacial import file_hash
from treinar_identidade_iris import IdentityEncoder
from treinar_ajuste_bloco_polar import ROOT,NAME,CONDITIONS,eligible_clean,advancement
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
    assert selected==done['selected_epoch'] and epoch==done['epochs_trained'];assert epoch==8 or epoch>=4 and stale>=3
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
    encoder_file=ROOT/protocol['encoder_relative_path'];assert file_hash(encoder_file)==protocol['encoder_sha256'];encoder=IdentityEncoder();encoder.load_state_dict(torch.load(encoder_file,map_location='cpu',weights_only=True)['model'])
    for state in states.values():
        tail=FullTail(encoder,state['rank']);assert tail.frozen_digest()==state['frozen_sha256']==done['frozen_sha256'];tail.load_adapters(state['adapters'])
        assert sum(p.numel() for p in tail.parameters() if p.requires_grad)==8388608 and all(n.startswith('block.') for n,p in tail.named_parameters() if p.requires_grad)
    full=False;cache_folder=Path(protocol['source_cache']).parent.parent/'encoder_polar_espacial_2026-10-23';cache=cache_folder/'cache_layer3.npy'
    if a.features:
        assert cache.exists();cache_done=json.loads((cache_folder/'CACHE_CONCLUIDO.json').read_text());assert file_hash(cache)==cache_done['sha256'];assert file_hash(cache_folder/'cache_indices.npz')==cache_done['indices_sha256']
        assert file_hash(Path(protocol['source_cache']))==protocol['source_cache_sha256']
        with np.load(protocol['source_cache']) as z:c={k:z[k] for k in z.files}
        with np.load(cache_folder/'cache_indices.npz') as z:mapping=z['mapping'];valid=z['valid']
        features=np.load(cache,mmap_mode='r');rows=[SimpleNamespace(**r) for r in json.loads((folder/'rows.json').read_text())];fi=c['fit_indices'];mi=c['monitor_indices'];assert not set(fi)&set(mi)
        assert {rows[i].subject for i in fi}.isdisjoint({rows[i].subject for i in mi}) and len(mi)==960
        for i,r in enumerate(rows):
            if r.session==1:assert mapping[i,0]==mapping[i,1]==mapping[i,2]
        torch.set_num_threads(4);device='cuda' if torch.cuda.is_available() else 'cpu'
        for name,state in states.items():
            tail=FullTail(encoder,state['rank']).to(device).eval();tail.load_adapters(state['adapters'])
            vectors={t:tail_vectors(tail,features,mapping[mi,j],device) for j,(t,_,_) in enumerate(CONDITIONS)};availability={t:valid[mi,j] for j,(t,_,_) in enumerate(CONDITIONS)}
            measured,scores=monitor_scores(vectors,availability,[rows[i] for i in mi]);assert measured==done[name+'_monitor']
            for tag,data in scores.items():
                with np.load(folder/f'scores_{name}_{tag}.npz') as z:
                    for key,value in data.items():np.testing.assert_array_equal(value,z[key])
                paired=availability[tag]&c['teacher_valid'][mi];cosine=float(np.sum(vectors[tag][paired].astype(np.float64)*c['teacher'][mi][paired].astype(np.float64),1).mean());np.testing.assert_allclose(cosine,state['cosines'][tag],rtol=0,atol=1e-12)
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
    report=dict(status='full_layer4_finetuning_verified',selected_epoch=selected,training_selection_reproduced=True,checkpoint_hashes_verified=True,feature_forward_and_scores_exact=full,score_decisions_reproduced=True,monitor_gate_reproduced=bool(gate),records=checked,new_full_image_inference=False,trainable_scope_and_frozen_state_verified=True)
    (folder/('AUDITORIA_REPRODUCAO.json' if full else 'VERIFICACAO_RECUPERACAO.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

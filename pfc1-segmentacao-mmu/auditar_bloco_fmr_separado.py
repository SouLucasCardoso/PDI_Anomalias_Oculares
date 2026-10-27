"""Audita selecao somente FIT/limpo interno e escores apos congelamento."""
from pathlib import Path
from types import SimpleNamespace
import argparse,csv,json
import numpy as np
import torch
from treinar_bloco_fmr_separado import ROOT,NAME,CONDITIONS,score,calibrate,measured,clean_eligible
from preparar_encoder_espacial import file_hash
from ajuste_bloco_polar import FullTail
from encoder_polar_espacial import tail_vectors
from perda_fmr_polar import fit_impostor_reference

def main():
    from treinar_identidade_iris import IdentityEncoder
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--cache-root',type=Path);a=p.parse_args();folder=a.root/NAME;protocol=json.loads((folder/'protocolo.json').read_text());done=json.loads((folder/'CONCLUIDO.json').read_text());assert file_hash(folder/'source.py')==protocol['script_sha256']==file_hash(ROOT/'treinar_bloco_fmr_separado.py')
    for n,h in protocol['dependencies_sha256'].items():assert file_hash(ROOT/n)==h
    fit=set(protocol['fit_people']);internal=set(protocol['internal_people']);monitor=set(protocol['monitor_people']);assert len(fit)==151 and len(internal)==len(monitor)==16 and not fit&internal and not (fit|internal)&monitor
    rows=[SimpleNamespace(**r) for r in json.loads((folder/'rows.json').read_text())];assert file_hash(folder/'rows.json')==protocol['rows_sha256'];manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());assert not (fit|internal|monitor)&{r['subject'] for r in manifest['val']+manifest['test']}
    with (folder/'historico.csv').open(newline='',encoding='utf-8') as f:history=list(csv.DictReader(f))
    assert [int(r['epoch']) for r in history]==list(range(9));base=done['baseline_internal_clean'];selected=0;best=None
    for row in history:
        m={k:float(row[k]) for k in ['rank1','tar','far']};eligible=clean_eligible(m,base);assert eligible==(row['eligible']=='True')
        if int(row['epoch'])>0 and eligible and (best is None or float(row['fit_loss'])<best):selected=int(row['epoch']);best=float(row['fit_loss'])
    assert selected==done['selected_epoch'];states={}
    for name,file,key,epoch in [('selected','melhor_modelo.pt','checkpoint_sha256',selected),('last','ultima_epoca.pt','last_checkpoint_sha256',8)]:
        assert file_hash(folder/file)==done[key];state=torch.load(folder/file,map_location='cpu',weights_only=True);assert state['epoch']==epoch;states[name]=state
    selected_threshold=states['selected']['internal_clean']['threshold'];assert selected_threshold==done['selected_threshold']
    for prefix,report in [('selected',done['results']),('baseline',done['baseline'])]:
        threshold=selected_threshold if prefix=='selected' else base['threshold']
        for split in ['internal','monitor']:
            for tag in CONDITIONS:
                with np.load(folder/f'scores_{prefix}_{split}_{tag}.npz') as z:data={k:z[k] for k in ['scores','labels','valid']};c=z['correct'];g=z['accepted']
                m,d=measured(data,threshold);assert m==report[split][tag];np.testing.assert_array_equal(c,d['correct']);np.testing.assert_array_equal(g,d['accepted'])
                if prefix=='selected' and split=='internal' and tag=='clean':assert calibrate(data)==threshold
    with np.load(folder/'indices_ajuste.npz') as z:indices={k:z[k] for k in z.files}
    assert all(rows[i].subject in fit for i in indices['fit']);assert all(rows[i].subject in internal for i in indices['internal']);assert all(rows[i].subject in monitor for i in indices['monitor']);assert all(rows[i].subject in fit and rows[i].session==1 for i in indices['gallery']);assert len(indices['fit'])==done['fit_photos']
    encoder=IdentityEncoder();encoder_file=ROOT/protocol['encoder_relative_path'];assert file_hash(encoder_file)==protocol['encoder_sha256'];encoder.load_state_dict(torch.load(encoder_file,map_location='cpu',weights_only=True)['model'])
    for state in states.values():
        tail=FullTail(encoder);assert tail.frozen_digest()==state['frozen_sha256']==done['frozen_sha256'];tail.load_adapters(state['adapters']);assert sum(p.numel() for p in tail.parameters() if p.requires_grad)==8388608
    full=False
    if a.cache_root:
        cache=a.cache_root/'encoder_polar_espacial_2026-10-23';assert file_hash(cache/'cache_layer3.npy')==protocol['cache_sha256'] and file_hash(cache/'cache_indices.npz')==protocol['indices_sha256'];assert file_hash(Path(protocol['source_cache']))==protocol['source_cache_sha256']
        features=np.load(cache/'cache_layer3.npy',mmap_mode='r')
        with np.load(cache/'cache_indices.npz') as z:mapping=z['mapping'];valid=z['valid']
        with np.load(protocol['source_cache']) as z:base_vectors=z['base'];teacher_valid=z['teacher_valid'];old_fi=z['fit_indices']
        expected=np.array([i for i in old_fi if rows[i].subject in fit]);np.testing.assert_array_equal(expected,indices['fit'])
        for split,people in [('internal',internal),('monitor',monitor)]:np.testing.assert_array_equal(indices[split],[i for i,r in enumerate(rows) if r.subject in people])
        eyes=sorted({(rows[i].subject,rows[i].side) for i in expected});gallery=[]
        for j,eye in enumerate(eyes):
            gi=[i for i,r in enumerate(rows) if r.subject in fit and (r.subject,r.side)==eye and r.session==1 and teacher_valid[i]];gallery.extend(gi);np.testing.assert_array_equal(indices['gallery'][indices['positions'][j][indices['present'][j]]],gi)
        np.testing.assert_array_equal(gallery,indices['gallery']);np.testing.assert_array_equal(indices['labels'],[eyes.index((rows[i].subject,rows[i].side)) for i in expected]);np.testing.assert_array_equal(indices['query_flags'],[rows[i].session==2 for i in expected]);np.testing.assert_array_equal(indices['sides'],[0 if s=='L' else 1 for _,s in eyes])
        all_fit=np.array([i for i,r in enumerate(rows) if r.subject in fit]);ref=score(base_vectors[all_fit,0],valid[all_fit,0],[rows[i] for i in all_fit]);threshold,count=fit_impostor_reference(**ref);record=json.loads((folder/'REFERENCIA_AJUSTE.json').read_text());assert threshold==record['reference'] and count==record['comparisons']
        with np.load(folder/'referencia_ajuste.npz') as z:
            for k,v in ref.items():np.testing.assert_array_equal(v,z[k])
            np.testing.assert_array_equal(all_fit,z['fit_indices'])
        torch.set_num_threads(4);device='cuda' if torch.cuda.is_available() else 'cpu';tail=FullTail(encoder).to(device).eval();tail.load_adapters(states['selected']['adapters'])
        for split in ['internal','monitor']:
            ii=indices[split];rr=[rows[i] for i in ii];s1=np.array([r.session==1 for r in rr]);vectors={tag:tail_vectors(tail,features,mapping[ii,j],device) for j,tag in enumerate(CONDITIONS)}
            for j,tag in enumerate(CONDITIONS):
                vectors[tag][s1]=vectors['clean'][s1];original=base_vectors[ii,j].copy();original[s1]=base_vectors[ii[s1],0]
                for prefix,v in [('selected',vectors[tag]),('baseline',original)]:
                    actual=score(v,valid[ii,j],rr)
                    with np.load(folder/f'scores_{prefix}_{split}_{tag}.npz') as z:
                        for k,value in actual.items():np.testing.assert_array_equal(value,z[k])
        full=True
    r=done['results']['monitor'];b=done['baseline']['monitor'];gate=selected>0 and all(r['clean'][k]>=b['clean'][k] for k in ['rank1','tar']) and all(r[t]['far']<=.01 for t in CONDITIONS) and all(r[t][k]>b[t][k] for t in ['upper10','lower10'] for k in ['rank1','tar']);absolute=all(r[t]['rank1']>=.9 and r[t]['tar']>=.9 and r[t]['far']<=.01 for t in CONDITIONS)
    assert bool(gate)==done['monitor_gate_passed'] and bool(absolute)==done['absolute_target_reached'];assert not any(done[k] for k in ['old_monitor_used_for_selection','occluded_internal_used_for_selection','validation_inference','test_inference','candidate_replaced'])
    report=dict(status='separated_fmr_protocol_audited',selected_epoch=selected,selection_uses_only_fit_loss_and_internal_clean=True,monitor_not_in_epoch_history=True,metrics_exact=True,shared_internal_clean_threshold_verified=True,full_cache_reproduction=full,monitor_gate_passed=bool(gate),absolute_target_reached=bool(absolute))
    (folder/('AUDITORIA_REPRODUCAO.json' if full else 'VERIFICACAO_RECUPERACAO.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':main()

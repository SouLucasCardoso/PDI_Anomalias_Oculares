"""Refaz normalizacao e escores salvos sem inferencia de rede."""
from pathlib import Path
from types import SimpleNamespace
import argparse,json
import numpy as np
from avaliar_coorte_polar import ROOT,NAME,CONDITIONS,normalized_match
from preparar_encoder_espacial import file_hash
from treinar_bloco_fmr_separado import calibrate,measured

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();folder=a.root/NAME;done=json.loads((folder/'CONCLUIDO.json').read_text());protocol=json.loads((folder/'protocolo.json').read_text());assert file_hash(folder/'source.py')==protocol['script_sha256']==file_hash(ROOT/'avaliar_coorte_polar.py');assert file_hash(ROOT/'normalizacao_coorte_polar.py')==protocol['normalizer_sha256']
    for n,h in done['files_sha256'].items():assert file_hash(folder/n)==h
    sp=json.loads((folder/'dependency_protocol.json').read_text());assert file_hash(folder/'dependency_protocol.json')==protocol['training_protocol_sha256'];rows=[SimpleNamespace(**r) for r in json.loads((folder/'dependency_rows.json').read_text())];assert file_hash(folder/'dependency_rows.json')==sp['rows_sha256'];fit=set(sp['fit_people']);internal=set(sp['internal_people']);monitor=set(sp['monitor_people']);assert not fit&internal and not (fit|internal)&monitor
    with np.load(folder/'coorte.npz') as z:cohort={k:z[k] for k in ['vectors','valid','eye_sides']};gallery=z['gallery_indices']
    groups=json.loads((folder/'grupos_coorte.json').read_text());cohort['groups']=groups['groups'];eyes=groups['eyes'];assert all(rows[i].subject in fit and rows[i].session==1 for i in gallery)
    for eye,g in zip(eyes,cohort['groups']):assert g==[j for j,i in enumerate(gallery) if [rows[i].subject,rows[i].side]==eye]
    np.testing.assert_array_equal(cohort['eye_sides'],[0 if s=='L' else 1 for _,s in eyes]);threshold=done['threshold']
    for split,people in [('internal',internal),('monitor',monitor)]:
        for tag in CONDITIONS:
            with np.load(folder/f'scores_{split}_{tag}.npz') as z:stored={k:z[k] for k in z.files}
            ii=stored['global_indices'];np.testing.assert_array_equal(ii,[i for i,r in enumerate(rows) if r.subject in people]);rr=[rows[i] for i in ii];assert not {r.subject for r in rr}&fit
            data,stats=normalized_match(stored['photo_vectors'],stored['photo_valid'],rr,cohort);np.testing.assert_array_equal(stats,stored['cohort_stats'])
            for k,v in data.items():np.testing.assert_array_equal(v,stored[k])
            m,d=measured(data,threshold);assert m==done['results'][split][tag]
            for k in ['correct','accepted']:np.testing.assert_array_equal(d[k],stored[k])
            if split=='internal' and tag=='clean':assert calibrate(data)==threshold
    r=done['results']['monitor'];raw=done['raw_control']['monitor'];gate=all(r['clean'][k]>=raw['clean'][k] for k in ['rank1','tar']) and all(r[t]['far']<=.01 for t in CONDITIONS) and all(r[t][k]>=raw[t][k] for t in ['upper10','lower10'] for k in ['rank1','tar']);absolute=all(r[t]['rank1']>=.9 and r[t]['tar']>=.9 and r[t]['far']<=.01 for t in CONDITIONS)
    assert bool(gate)==done['monitor_gate_passed'] and bool(absolute)==done['absolute_target_reached'];assert not any(done[k] for k in ['labels_used_for_normalization','new_training','validation_inference','test_inference','candidate_replaced'])
    audit=dict(status='cohort_scores_reproduced',cohort_fit_only_verified=True,same_side_statistics_verified=True,all_scores_and_statistics_exact=True,internal_clean_threshold_exact=True,monitor_gate_passed=bool(gate),absolute_target_reached=bool(absolute),new_network_inference=False)
    (folder/'AUDITORIA_REPRODUCAO.json').write_text(json.dumps(audit,indent=2),encoding='utf-8');print(json.dumps(audit))
if __name__=='__main__':main()

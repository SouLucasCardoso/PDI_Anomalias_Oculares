"""Audita descritores quando presentes e recuperacao compacta dos escores."""
from pathlib import Path
import argparse,json
import numpy as np
from avaliar_complemento_geometrico import NAME,CONDITIONS,complementary_vectors
from treinar_adaptador_polar import monitor_scores
from avaliar_robustez_reconhecimento import metrics
from avaliar_candidato_congelado import digest

def main():
    from types import SimpleNamespace
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();folder=a.root/NAME
    done=json.loads((folder/'CONCLUIDO.json').read_text());protocol=json.loads((folder/'protocolo.json').read_text());assert digest(folder/'source.py')==protocol['script_sha256']
    tags=[t for t,_,_ in CONDITIONS];rows=[SimpleNamespace(**r) for r in json.loads((folder/'rows.json').read_text())];assert len(rows)==960 and sum(r.session==2 for r in rows)==480
    full=False
    cache=folder/'cache_features.npz'
    if cache.exists():
        assert digest(cache)==done['feature_cache_sha256']
        with np.load(cache) as z:
            original={t:z['original'][:,j] for j,t in enumerate(tags)};ov={t:z['original_valid'][:,j] for j,t in enumerate(tags)};corrected={t:z['corrected'][:,j] for j,t in enumerate(tags)};cv={t:z['corrected_valid'][:,j] for j,t in enumerate(tags)}
        combined={t:complementary_vectors(original[t],corrected[t],protocol['weight_corrected']) for t in tags};bv={t:ov[t]&cv[t] for t in tags}
        for name,vectors,valid in [('original',original,ov),('corrected',corrected,cv),('complement',combined,bv)]:
            measured,scores=monitor_scores(vectors,valid,rows)
            assert measured==done['results'][name]
            for tag in tags:
                with np.load(folder/f'scores_{name}_{tag}.npz') as z:
                    for key,value in scores[tag].items():np.testing.assert_array_equal(z[key],value)
        full=True
    checked=[]
    for name,group in done['results'].items():
        for tag,record in group.items():
            assert record['threshold']==group['clean']['threshold']
            with np.load(folder/f'scores_{name}_{tag}.npz') as z:
                measured,correct,accepted=metrics(z['scores'],z['labels'],record['threshold'],z['valid']);np.testing.assert_array_equal(correct,z['correct']);np.testing.assert_array_equal(accepted,z['accepted'])
            for key in ['rank1','tar','far','queries','extraction_failures']:assert measured[key]==record[key]
            assert int(correct.sum())==record['correct'] and int(accepted.sum())==record['accepted'];checked.append(dict(strategy=name,condition=tag,correct=int(correct.sum()),accepted=int(accepted.sum())))
    candidate=done['results']['complement'];control=done['results']['original'];c=candidate['clean']
    gate=all(c[k]>=control['clean'][k] for k in ['rank1','tar']) and c['far']<=.01 and all(candidate[t][k]>control[t][k] for t in ['upper10','lower10'] for k in ['rank1','tar']) and all(candidate[t]['far']<=.01 for t in ['upper10','lower10'])
    assert gate==done['recognition_validation_gate_passed'];assert not done['validation_identity_inference'] and not done['test_inference'] and not done['frozen_candidate_replaced'] and done['minimum_area'] is None
    report=dict(status='complement_monitor_verified',feature_fusion_and_scores_exact=full,score_decisions_reproduced=True,gate_reproduced=bool(gate),records=checked,validation_and_test_inference=False)
    path=folder/('AUDITORIA_REPRODUCAO.json' if full else 'VERIFICACAO_RECUPERACAO.json');path.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

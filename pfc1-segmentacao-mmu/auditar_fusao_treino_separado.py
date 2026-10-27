"""Refaz calibracao, fusao, metricas e bloqueio dos componentes preservados."""
from pathlib import Path
import argparse,json
import numpy as np
from avaliar_fusao_treino_separado import ROOT,NAME,ORDER,CONDITIONS
from avaliar_candidato_congelado import fuse
from validar_fusao_identidade_adaptada import calibrate as calibrate_components
from treinar_bloco_fmr_separado import calibrate,measured
from preparar_encoder_espacial import file_hash

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();folder=a.root/NAME;done=json.loads((folder/'CONCLUIDO.json').read_text());protocol=json.loads((folder/'protocolo.json').read_text());assert file_hash(folder/'source.py')==protocol['script_sha256']==file_hash(ROOT/'avaliar_fusao_treino_separado.py')
    for n,h in protocol['dependencies_sha256'].items():assert file_hash(ROOT/n)==h
    sp=json.loads((folder/'dependency_training_protocol.json').read_text());assert file_hash(folder/'dependency_training_protocol.json')==protocol['source_protocol_sha256'];rows=json.loads((folder/'rows.json').read_text());internal=set(sp['internal_people']);monitor=set(sp['monitor_people']);fit=set(sp['fit_people']);assert not (internal|monitor)&fit and not internal&monitor;assert {r['subject'] for r in rows}==internal|monitor
    for strategy,prefix in [('original','baseline'),('adapted','selected')]:
        params=done['parameters'][strategy]
        for split,people in [('internal',internal),('monitor',monitor)]:
            q=[r for r in rows if r['subject'] in people and r['session']==2];subjects=sorted(people);labels=np.array([subjects.index(r['subject']) for r in q])
            for tag,_,_ in CONDITIONS:
                components=[]
                for name in ORDER:
                    file=folder/f'dependency_polar_{prefix}_{split}_{tag}.npz' if name=='polar' else folder/f'component_{split}_{tag}_{name}.npz'
                    with np.load(file) as z:c={k:z[k] for k in ['scores','labels','valid']}
                    assert c['scores'].shape==(len(q),16);np.testing.assert_array_equal(c['labels'],labels);components.append(c)
                if split=='internal' and tag=='clean':assert calibrate_components(components)==params['calibration']
                scores,valid=fuse(components,params['calibration']);data=dict(scores=scores,labels=labels,valid=valid)
                if split=='internal' and tag=='clean':assert calibrate(data)==params['threshold']
                m,d=measured(data,params['threshold']);assert m==done['results'][strategy][split][tag]
                with np.load(folder/f'scores_{strategy}_{split}_{tag}.npz') as z:
                    for k,v in d.items():np.testing.assert_array_equal(v,z[k])
    r=done['results']['adapted']['monitor'];b=done['results']['original']['monitor'];gate=all(r['clean'][k]>=max(.9,b['clean'][k]) for k in ['rank1','tar']) and all(r[t]['far']<=.01 for t,_,_ in CONDITIONS) and all(r[t][k]>b[t][k] for t in ['upper10','lower10'] for k in ['rank1','tar']);absolute=all(r[t]['rank1']>=.9 and r[t]['tar']>=.9 and r[t]['far']<=.01 for t,_,_ in CONDITIONS)
    assert bool(gate)==done['monitor_gate_passed'] and bool(absolute)==done['absolute_target_reached'];assert not any(done[k] for k in ['validation_inference','test_inference','candidate_replaced'])
    report=dict(status='train_fusion_reproduced',internal_clean_component_calibration_exact=True,internal_clean_threshold_exact=True,all_twelve_fusions_exact=True,all_metrics_exact=True,side_and_query_alignment_verified=True,monitor_gate_passed=bool(gate),absolute_target_reached=bool(absolute),new_image_inference=False)
    (folder/'AUDITORIA_REPRODUCAO.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':main()

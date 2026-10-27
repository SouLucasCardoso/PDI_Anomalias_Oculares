"""Reproduz controles e troca isolada sem nova inferencia de imagens."""
from pathlib import Path
import argparse,json
import numpy as np
from avaliar_troca_polar_congelada import ROOT,NAME,ORDER
from avaliar_candidato_congelado import fuse
from treinar_bloco_fmr_separado import measured
from preparar_encoder_espacial import file_hash

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();folder=a.root/NAME;done=json.loads((folder/'CONCLUIDO.json').read_text());protocol=json.loads((folder/'protocolo.json').read_text());assert file_hash(folder/'source.py')==protocol['script_sha256']==file_hash(ROOT/'avaliar_troca_polar_congelada.py');assert file_hash(folder/'parametros_originais.json')==protocol['frozen_parameters_sha256'];frozen=json.loads((folder/'parametros_originais.json').read_text())
    for n,h in protocol['dependencies_sha256'].items():assert file_hash(ROOT/n)==h
    assert protocol['threshold']==frozen['frozen_threshold'];clean=False
    for tag,group in done['results'].items():
        components=[]
        for name in ORDER:
            with np.load(folder/f'component_original_{tag}_{name}.npz') as z:components.append({k:z[k] for k in ['scores','labels','valid']})
        for strategy in ['original','adapted']:
            if strategy=='adapted':
                with np.load(folder/f'polar_adapted_{tag}.npz') as z:components[1]={k:z[k] for k in ['scores','labels','valid']}
            for c in components:np.testing.assert_array_equal(c['labels'],components[0]['labels'])
            scores,valid=fuse(components,frozen['component_calibration_red_and_clahe']);m,d=measured(dict(scores=scores,valid=valid,labels=components[0]['labels']),protocol['threshold']);assert m==group[strategy]
            with np.load(folder/f'scores_{strategy}_{tag}.npz') as z:
                for k,v in d.items():np.testing.assert_array_equal(v,z[k])
        if tag=='clean':r=group['adapted'];clean=r['rank1']>=.9 and r['tar']>=.9 and r['far']<=.01
    assert bool(clean)==done['clean_gate_passed'];assert not done['calibration_changed'] and not done['threshold_changed'] and not done['test_inference'] and not done['candidate_replaced']
    if not clean:assert set(done['results'])=={'clean'} and not done['occlusion_inference']
    audit=dict(status='fixed_reference_polar_swap_audited',all_fusions_and_metrics_exact=True,reference_parameters_and_threshold_exact=True,clean_gate_passed=bool(clean),occlusion_inference=done['occlusion_inference'],new_image_inference=False)
    (folder/'AUDITORIA_REPRODUCAO.json').write_text(json.dumps(audit,indent=2),encoding='utf-8');print(json.dumps(audit))
if __name__=='__main__':main()

"""Reproduz limiar global e porta limpa nos artefatos compactos."""
from pathlib import Path
import argparse,json
import numpy as np
from calibracao_multicondicao import calibrate_robust
from normalizacao_fundo_consulta import fuse_background
from treinar_bloco_fmr_separado import ROOT,measured
from preparar_encoder_espacial import file_hash
from avaliar_fusao_treino_separado import ORDER
CAL='calibracao_multicondicao_treino_2026-10-24'
VAL='porta_limpa_multicondicao_val_2026-10-24'

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--nome',choices=[CAL,VAL],required=True);a=p.parse_args();folder=a.root/a.nome;protocol=json.loads((folder/'protocolo.json').read_text());done=json.loads((folder/'CONCLUIDO.json').read_text());assert file_hash(folder/'source.py')==protocol['script_sha256']
    if a.nome==CAL:
        assert file_hash(ROOT/'calibracao_multicondicao.py')==protocol['calibrator_sha256'];internal={}
        for tag in ['clean','upper10','lower10']:
            with np.load(folder/f'scores_internal_{tag}.npz') as z:internal[tag]={k:z[k] for k in ['scores','labels','valid']}
        threshold,parts=calibrate_robust(internal,protocol['target_internal_fmr']);assert threshold==done['threshold'] and parts==done['internal_domain_thresholds']
        for split in ['internal','monitor']:
            for tag in ['clean','upper10','lower10']:
                name=f'scores_{split}_{tag}.npz';assert file_hash(folder/('input_'+name))==protocol['score_files_sha256'][name]
                with np.load(folder/('input_'+name)) as z:data={k:z[k] for k in ['scores','labels','valid']}
                m,d=measured(data,threshold);assert m==done['results'][split][tag]
                with np.load(folder/name) as z:
                    for k,v in d.items():np.testing.assert_array_equal(v,z[k])
        r=done['results']['monitor'];fmr=all(r[t]['far']<=.01 for t in ['clean','upper10','lower10']);absolute=all(r[t]['rank1']>=.9 and r[t]['tar']>=.9 and r[t]['far']<=.01 for t in ['clean','upper10','lower10']);assert bool(fmr)==done['all_monitor_fmr_at_most_one_percent'] and bool(absolute)==done['absolute_target_reached'];assert not done['monitor_used_for_calibration'] and not done['condition_specific_inference_threshold'];result=dict(single_global_threshold_exact=True,all_scores_and_metrics_exact=True,all_monitor_fmr_at_most_one_percent=bool(fmr),absolute_target_reached=bool(absolute))
    else:
        for n,h in protocol['dependencies_sha256'].items():assert file_hash(ROOT/n)==h
        components=[]
        for name in ORDER:
            with np.load(folder/f'component_{name}.npz') as z:components.append({k:z[k] for k in ['scores','labels','valid']})
            if name!='polar':assert file_hash(folder/f'input_scores_{name}.npz')==protocol['original_components_sha256'][name]
            np.testing.assert_array_equal(components[-1]['labels'],components[0]['labels'])
        scores,valid=fuse_background(components,protocol['calibration']);data=dict(scores=scores,valid=valid,labels=components[0]['labels']);m,d=measured(data,protocol['threshold']);assert m==done['result']
        with np.load(folder/'scores_finais.npz') as z:
            for k,v in d.items():np.testing.assert_array_equal(v,z[k])
        gate=m['rank1']>=.9 and m['tar']>=.9 and m['far']<=.01;assert bool(gate)==done['clean_gate_passed'];assert not done['validation_fitting'] and not done['calibration_changed'] and not done['occlusion_inference'];result=dict(clean_fusion_and_metrics_exact=True,train_threshold_unchanged=True,clean_gate_passed=bool(gate))
    assert not done['test_inference'] and not done['candidate_replaced'];report=dict(status='20261024_compact_evidence_audited',experiment=a.nome,**result,new_image_inference=False);(folder/'AUDITORIA_REPRODUCAO.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':main()

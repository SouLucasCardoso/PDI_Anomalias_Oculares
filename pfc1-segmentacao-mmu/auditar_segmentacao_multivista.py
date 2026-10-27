"""Reproduz fusão, métricas e decisão do piloto sem nova inferência."""
from pathlib import Path
import argparse
import csv
import json
import numpy as np
from avaliar_candidato_congelado import fuse,digest
from avaliar_robustez_reconhecimento import metrics,operating_threshold
from validar_fusao_identidade_adaptada import calibrate
from validar_segmentacao_multivista import ORDER,CONDITIONS,ROOT

def main():
    p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,required=True);a=p.parse_args();out=a.folder
    final=json.loads((out/'CONCLUIDO.json').read_text('utf-8'));protocol=json.loads((out/'protocolo.json').read_text('utf-8'))
    assert digest(ROOT/'validar_segmentacao_multivista.py')==protocol['script_sha256']==digest(out/'source.py')
    for name,value in protocol['dependencies_sha256'].items():assert digest(ROOT/name)==value
    grouped={}
    for tag,_,_ in CONDITIONS:
        grouped[tag]={}
        for name in ORDER:
            with np.load(out/tag/f'scores_{name}.npz') as z:grouped[tag][name]={k:z[k] for k in ['scores','labels','valid']}
            assert grouped[tag][name]['scores'].shape==(482,16)
            np.testing.assert_array_equal(grouped[tag][name]['labels'],grouped['clean']['rgb']['labels'])
    fresh=calibrate([grouped['clean'][n] for n in ORDER])
    assert fresh==final['parameters']['tta_clean_calibrated']['calibration']
    recomputed={};maximum=0.;records=[]
    for record in final['results']:
        strategy=record['strategy'];condition=record['condition'];params=final['parameters'][strategy]
        scores,valid=fuse([grouped[condition][n] for n in ORDER],params['calibration'])
        labels=grouped[condition]['rgb']['labels']
        with np.load(out/f'{strategy}_{condition}.npz') as z:
            np.testing.assert_array_equal(scores,z['scores']);np.testing.assert_array_equal(valid,z['valid']);np.testing.assert_array_equal(labels,z['labels'])
            measured,correct,accepted=metrics(scores,labels,params['threshold'],valid)
            np.testing.assert_array_equal(correct,z['correct']);np.testing.assert_array_equal(accepted,z['accepted'])
        for key in ['rank1','tar','far','queries','extraction_failures']:assert measured[key]==record[key]
        if strategy=='tta_clean_calibrated' and condition=='clean':
            imp=np.ones_like(scores,bool);imp[np.arange(482),labels]=False
            assert operating_threshold(scores[imp&valid[:,None]&(scores>-2)])==params['threshold']
        with (out/f'{strategy}_{condition}.csv').open(encoding='utf-8',newline='') as stream:rows=list(csv.DictReader(stream))
        assert len(rows)==482
        for i,row in enumerate(rows):
            assert int(row['query'])==i and int(row['label'])==labels[i]
            np.testing.assert_array_equal(np.array([float(row[f'score_{j}']) for j in range(16)]),scores[i])
        if strategy=='tta_clean_calibrated':recomputed[condition]=measured
        records.append(dict(strategy=strategy,condition=condition,rank1_correct=int(correct.sum()),genuine_accepted=int(accepted.sum()),false_accepts=int(round(measured['far']*482*15)),queries=482,impostor_comparisons=7230))
    clean=recomputed['clean'];gate=clean['rank1']>=.9 and clean['tar']>=.9 and clean['far']<=.01
    gate=gate and all(recomputed[c][m]>final['baseline'][c][m] for c in ['upper10','lower10'] for m in ['rank1','tar']) and all(recomputed[c]['far']<=.01 for c in ['upper10','lower10'])
    assert bool(gate)==final['promotion_gate_passed']
    # Separate cross-condition verification, independent of the runner's assertion.
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text())
    from avaliar_robustez_reconhecimento import load_splits
    samples=load_splits(manifest)['val'];gi=[i for i,r in enumerate(samples) if r.session==1]
    assert len(gi)==480
    for name in ['rgb','native','polar','red']:
        original=np.load(out/'cache_clean'/f'{name}.npy',mmap_mode='r')
        for tag in ['upper10','lower10']:
            altered=np.load(out/f'cache_{tag}'/f'{name}.npy',mmap_mode='r')
            np.testing.assert_array_equal(original[gi],altered[gi])
    result=dict(status='tta_components_decisions_threshold_and_gallery_audited',records=records,promotion_gate_reproduced=bool(gate),fusion_max_difference=maximum,all_queries_retained=True,csv_roundtrip_exact=True,clean_only_calibration_verified=True,enrollment_arrays_exact_across_conditions=True,test_inference=False)
    consensus_folder=out.parent/'consenso_geometrias_val_2026-10-23'
    if (consensus_folder/'CONCLUIDO.json').exists():
        from validar_consenso_geometrias import consensus
        cf=json.loads((consensus_folder/'CONCLUIDO.json').read_text('utf-8'))
        cp=json.loads((consensus_folder/'protocolo.json').read_text('utf-8'))
        assert digest(ROOT/'validar_consenso_geometrias.py')==cp['source_sha256']==digest(consensus_folder/'source.py')
        for name,value in cf['source_scores_sha256'].items():assert digest(Path(name))==value
        audited=[]
        for tag,condition,_ in CONDITIONS:
            suffix='' if tag=='clean' else '_'+condition+'_10'
            branches=[]
            for file in [ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21/scores_finais.npz',out/f'tta_clean_calibrated_{tag}.npz']:
                with np.load(file) as z:branches.append({k:z[k] for k in ['scores','labels','valid']})
            scores,valid=consensus(*branches);labels=branches[0]['labels'];threshold=cf['results'][tag]['threshold']
            with np.load(consensus_folder/f'scores_{tag}.npz') as z:
                np.testing.assert_array_equal(scores,z['scores']);np.testing.assert_array_equal(valid,z['valid'])
                measured,correct,accepted=metrics(scores,labels,threshold,valid)
                np.testing.assert_array_equal(correct,z['correct']);np.testing.assert_array_equal(accepted,z['accepted'])
            for key in ['rank1','tar','far','queries','extraction_failures']:assert measured[key]==cf['results'][tag][key]
            if tag=='clean':
                imp=np.ones_like(scores,bool);imp[np.arange(482),labels]=False
                assert operating_threshold(scores[imp&valid[:,None]&(scores>-2)])==threshold
            audited.append(dict(condition=tag,rank1_correct=int(correct.sum()),genuine_accepted=int(accepted.sum()),false_accepts=int(round(measured['far']*7230))))
        clean=cf['results']['clean'];consensus_gate=clean['rank1']>=.9 and clean['tar']>=.9 and clean['far']<=.01
        consensus_gate=consensus_gate and all(cf['results'][c][m]>cf['baseline'][c][m] for c in ['upper10','lower10'] for m in ['rank1','tar']) and all(cf['results'][c]['far']<=.01 for c in ['upper10','lower10'])
        assert bool(consensus_gate)==cf['promotion_gate_passed']
        result['consensus_audit']=dict(records=audited,score_roundtrip_exact=True,clean_only_threshold_verified=True,promotion_gate_reproduced=bool(consensus_gate))
    (out/'AUDITORIA.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))

if __name__=='__main__':main()

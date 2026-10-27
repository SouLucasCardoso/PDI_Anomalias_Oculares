"""Consenso fixo de dois processamentos da mesma foto; validação apenas."""
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from avaliar_candidato_congelado import digest
from avaliar_robustez_reconhecimento import metrics,operating_threshold
from normalizar_consulta import normalize
ROOT=Path(__file__).resolve().parent
CONDITIONS={'clean':'','upper10':'_oclusao_superior_10','lower10':'_oclusao_inferior_10'}

def consensus(first,second):
    if first['scores'].shape!=second['scores'].shape:raise ValueError('Candidate pools differ')
    available=(first['scores']>-2)&(second['scores']>-2)
    valid=first['valid']&second['valid']&available.any(1)
    logits=[]
    for branch in [first,second]:
        s=np.clip(branch['scores'],1e-12,1-1e-12);logits.append(np.log(s/(1-s)))
    values=1/(1+np.exp(-np.clip((logits[0]+logits[1])/2,-30,30)))
    values[~available]=-2
    return normalize(values,valid)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args()
    out=a.output_root/'consenso_geometrias_val_2026-10-23';source=a.output_root/'segmentacao_multivista_val_2026-10-23'
    if a.registrar:
        out.mkdir(parents=True,exist_ok=False)
        protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Exploratory development validation; follow-up registered after clean TTA Rank1=433/482 and TAR431/482, before viewing occluded TTA results. No independent confirmation.',
            strategy='Equal mean of logits of original frozen fusion and clean-calibrated TTA fusion, then same per-query score normalization. Exactly one weight choice: 50/50. Two processing hypotheses of ONE photo, same side and16candidates. No query-label selection or quality filtering.',
            calibration='One new threshold on CLEAN validation only; same frozen threshold for both10% occlusions. Branches use their own already fixed clean component calibration. AND availability/validity retains failures as rejections.',
            evaluation='Clean Rank1/TAR>=90% and FMR<=1%; both occluded Rank1/TAR improve versus original and FMR<=1%. No promotion or test inference automatically.',
            stopping='One fixed consensus, no weight search or best-per-query branch selection.',
            source_sha256=digest(Path(__file__)),tta_protocol_sha256=digest(source/'protocolo.json'))
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Protocolo registrado antes dos resultados ocluidos.');return
    protocol=json.loads((out/'protocolo.json').read_text('utf-8'));assert protocol['source_sha256']==digest(Path(__file__)) and protocol['tta_protocol_sha256']==digest(source/'protocolo.json')
    assert not (out/'CONCLUIDO.json').exists()
    tta=json.loads((source/'CONCLUIDO.json').read_text('utf-8'));data={};hashes={}
    for tag,suffix in CONDITIONS.items():
        branches=[]
        for file in [ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21/scores_finais.npz',source/f'tta_clean_calibrated_{tag}.npz']:
            hashes[str(file)]=digest(file)
            with np.load(file) as z:branches.append({k:z[k] for k in ['scores','valid','labels']})
        np.testing.assert_array_equal(branches[0]['labels'],branches[1]['labels'])
        scores,valid=consensus(*branches);data[tag]=dict(scores=scores,valid=valid,labels=branches[0]['labels'])
    c=data['clean'];labels=c['labels'];imp=np.ones_like(c['scores'],bool);imp[np.arange(len(labels)),labels]=False
    threshold=operating_threshold(c['scores'][imp&c['valid'][:,None]&(c['scores']>-2)])
    results={}
    for tag,c in data.items():
        result,correct,accepted=metrics(c['scores'],c['labels'],threshold,c['valid']);result.update(rank1_correct=int(correct.sum()),genuine_accepted=int(accepted.sum()),threshold=threshold)
        np.savez_compressed(out/f'scores_{tag}.npz',**c,correct=correct,accepted=accepted);results[tag]=result
    clean=results['clean'];gate=clean['rank1']>=.9 and clean['tar']>=.9 and clean['far']<=.01
    gate=gate and all(results[tag][m]>tta['baseline'][tag][m] for tag in ['upper10','lower10'] for m in ['rank1','tar']) and all(results[tag]['far']<=.01 for tag in ['upper10','lower10'])
    final=dict(status='fixed_two_geometry_consensus_validation_completed',results=results,baseline=tta['baseline'],promotion_gate_passed=bool(gate),source_scores_sha256=hashes,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2))

if __name__=='__main__':main()

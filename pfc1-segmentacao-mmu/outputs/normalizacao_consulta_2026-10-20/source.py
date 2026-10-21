"""Controle fixo para dispersao das similaridades de uma unica consulta."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent

def main():
    from normalizar_consulta import normalize
    from avaliar_robustez_reconhecimento import operating_threshold,metrics
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,required=True);args=parser.parse_args()
    source=ROOT/'outputs/fusao_espacial_val_2026-10-20/scores.npz'
    out=args.output_root/'normalizacao_consulta_2026-10-20';out.mkdir(exist_ok=True,parents=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve existing experiment')
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'UBIPr primary, single query; development validation only; no test or occlusion',
        'method':'Invert logistic fixed-three-way fusion; per-query mean/std across all available enrolled eyes; logistic mapping. Query identity is not used to normalize. No parameter search.',
        'selection':'One fixed variant; all482 queries retained; original rank order must be unchanged for valid rows',
        'calibration':'Threshold calibrated empirical validation FMR<=1%; repeatedly used validation, no independent confirmation',
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'module_sha256':hashlib.sha256((ROOT/'normalizar_consulta.py').read_bytes()).hexdigest()}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    with np.load(source) as z:data={k:z[k] for k in z.files}
    scores,valid=normalize(data['scores'],data['valid']);labels=data['labels']
    np.testing.assert_array_equal(scores[valid].argmax(1),data['scores'][valid].argmax(1))
    imp=np.ones_like(scores,dtype=bool);imp[np.arange(len(labels)),labels]=False
    threshold=operating_threshold(scores[imp&valid[:,None]&(scores>-2)])
    result,correct,accepted=metrics(scores,labels,threshold,valid);result.update(threshold=threshold,joint_success=float((correct&accepted).mean()))
    np.savez_compressed(out/'scores.npz',scores=scores,labels=labels,valid=valid,correct=correct,accepted=accepted)
    final={'status':'single_query_score_normalization_completed','metrics':result,'test_inference':False,'minimum_area':None}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2))

if __name__=='__main__':main()

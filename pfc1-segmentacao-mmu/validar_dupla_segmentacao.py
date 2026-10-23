"""Duas mascaras da mesma foto, fusao fixa e apenas validacao."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent

def combine(left,right):
    from normalizar_consulta import normalize
    np.testing.assert_array_equal(left['labels'],right['labels']);available=(left['scores']>-2)&(right['scores']>-2);valid=left['valid']&right['valid']&available.any(1)
    logits=[np.log(np.clip(c['scores'],1e-12,1-1e-12)/np.clip(1-c['scores'],1e-12,1)) for c in [left,right]]
    scores=1/(1+np.exp(-np.clip(np.mean(logits,axis=0),-30,30)));scores[~available]=-2
    scores,valid=normalize(scores,valid);return dict(scores=scores,valid=valid,labels=left['labels'])

def main():
    from avaliar_robustez_reconhecimento import metrics
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'dupla_segmentacao_val_2026-10-21'
    # Register the fixed hypothesis before checking whether all source scores exist.
    if not out.exists():
        out.mkdir(parents=True)
        protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Exploratory development validation only; hypothesis after observing clean-recognition drop under robust segmenter; not independent confirmation',
          'method':'Same single original query photo through original and robust predicted masks. Each branch uses frozen identity fusion and predefined query normalization. Equal mean branch logits, then same per-query normalization. No identity/gray/quality flag selects branch, no weight search.',
          'conditions':'Clean and upper/lower10% native reference iris occlusion, all482 queries; require both branches valid, failures retained',
          'threshold':0.8581747485460748,'calibration':'Original frozen threshold unchanged for comparison; no per-condition recalibration',
          'limitations':'Both enrollment and query templates use respective segmentation branch. Extra compute, not extra photos. No test inference or automatic replacement; overlap and repeated validation limitations remain.',
          'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    else:
        assert (out/'source.py').read_bytes()==Path(__file__).read_bytes(),'Preserve registered method'
    if (out/'CONCLUIDO.json').exists():raise ValueError('Preserve completed run')
    paired=a.output_root/'validacao_segmentacao_oclusao_identidade_2026-10-21/CONCLUIDO.json'
    if not paired.exists():print('Hypothesis registered; waiting for paired validation. Rerun same script after completion.',flush=True);return
    pairs=json.loads(paired.read_text())['records'];results=[]
    for condition in ['original','oclusao_superior','oclusao_inferior']:
        sources=[Path(next(r['source'] for r in pairs if r['segmenter']==name and r['condition']==condition))/'scores_finais.npz' for name in ['original','robust']];arrays=[]
        for source in sources:
            with np.load(source) as z:arrays.append({k:z[k] for k in ['scores','labels','valid']})
        data=combine(*arrays);result,correct,accepted=metrics(data['scores'],data['labels'],0.8581747485460748,data['valid']);data.update(correct=correct,accepted=accepted);result.update(condition=condition,threshold=0.8581747485460748,joint_success=float((correct&accepted).mean()),source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources});results.append(result);np.savez_compressed(out/f'scores_{condition}.npz',**data)
    final=dict(status='equal_dual_segmentation_validation_completed',results=results,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()

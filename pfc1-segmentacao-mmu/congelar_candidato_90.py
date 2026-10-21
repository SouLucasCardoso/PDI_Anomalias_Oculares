"""Audita e congela candidato de desenvolvimento sem inferencia de teste."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_robustez_reconhecimento import metrics
    from normalizar_consulta import normalize
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'candidato_congelado_2026-10-21';out.mkdir(parents=True,exist_ok=True)
    if (out/'CONGELADO.json').exists():raise ValueError('Do not overwrite freeze')
    sources=[ROOT/'outputs'/n for n in ['arciris_polar_2026-10-21','arciris_red_2026-10-21','arciris_duas_vistas_2026-10-21']]
    arrays=[]
    for folder in sources[:2]:
        with np.load(folder/'scores_fusion8.npz') as z:arrays.append({k:z[k] for k in ['scores','labels','valid']})
    available=np.logical_and.reduce([z['scores']>-2 for z in arrays]);valid=np.logical_and.reduce([z['valid'] for z in arrays])&available.any(1)
    logits=[np.log(np.clip(z['scores'],1e-12,1-1e-12)/np.clip(1-z['scores'],1e-12,1)) for z in arrays]
    scores=1/(1+np.exp(-np.mean(logits,axis=0)));scores[~available]=-2;scores,valid=normalize(scores,valid)
    with np.load(sources[2]/'scores_equal_views_normalized.npz') as z:
        np.testing.assert_array_equal(scores,z['scores']);np.testing.assert_array_equal(valid,z['valid']);labels=z['labels'];saved_correct=z['correct'];saved_accepted=z['accepted']
    result=json.loads((sources[2]/'CONCLUIDO.json').read_text());selected=next(r for r in result['results'] if r['variant']=='equal_views_normalized');threshold=selected['threshold']
    measured,correct,accepted=metrics(scores,labels,threshold,valid);np.testing.assert_array_equal(correct,saved_correct);np.testing.assert_array_equal(accepted,saved_accepted)
    assert scores.shape==(482,16) and (~valid).sum()==4
    impostors=np.ones_like(scores,dtype=bool);impostors[np.arange(len(labels)),labels]=False
    false_accepts=int(((scores>=threshold)&valid[:,None])[impostors].sum());assert impostors.sum()==482*15 and false_accepts==71
    assert correct.sum()==434 and accepted.sum()==437 and measured['rank1']>=.9 and measured['tar']>=.9 and measured['far']<=.01
    calibration=[json.loads((f/'CONCLUIDO.json').read_text())['normalization'] for f in sources[:2]]
    audit={'frozen_utc':datetime.now(timezone.utc).isoformat(),'status':'development_target_reached_pending_confirmation',
      'scope':{'primary_dataset':'UBIPr','original_query_images':1,'supplied_eye_side_required':True,'candidate_eyes':16,'queries':482,'impostor_comparisons':7230,'retained_extraction_failures':4},
      'counts':{'rank1_correct':int(correct.sum()),'genuine_accepts':int(accepted.sum()),'correct_and_accepted':int((correct&accepted).sum()),'false_accepts':false_accepts},
      'metrics':measured,'frozen_threshold':threshold,'component_calibration_red_and_clahe':calibration,
      'method':'Seven prior components each1/8; ArcIris contributes1/8 as mean of red and CLAHE standardized scores; logistic then per-query logit standardization over16 candidates. Fixed threshold above. No test recalibration.',
      'limitations':['Repeatedly reused development validation; selection bias','ArcIris external pretraining identities undocumented; overlap unknown','Not a minimum iris area result','Rank1 and TAR are separate criteria, not necessarily same successes'],
      'exact_score_reconstruction':True,'test_inference':False,'minimum_area':None,
      'artifacts_sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for folder in sources for f in folder.glob('*') if f.is_file()},
      'next_required':'Confirm frozen configuration/threshold on separate evaluation with previous exposure disclosed, then assess occlusion curves; do not retune using confirmation results.'}
    (out/'CONGELADO.json').write_text(json.dumps(audit,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print(json.dumps(audit['counts']|{'metrics':measured,'threshold':threshold},indent=2))
if __name__=='__main__':main()

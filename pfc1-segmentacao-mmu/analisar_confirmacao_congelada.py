"""Contagens e incerteza por pessoa, sem alterar calibracao ou criterio."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_robustez_reconhecimento import load_splits,metrics
    from relatar_validacao_hdbif import cluster_interval
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'analise_confirmacao_congelada_2026-10-21';out.mkdir(parents=True,exist_ok=False)
    source=a.output_root/'confirmacao_congelada_test_2026-10-21';result=json.loads((source/'CONCLUIDO.json').read_text());threshold=result['result']['threshold']
    with np.load(source/'scores_finais.npz') as z:scores=z['scores'];labels=z['labels'];valid=z['valid'];stored_correct=z['correct'];stored_accepted=z['accepted']
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['test'];queries=[r for r in rows if r.session==2];subjects=np.array([r.subject for r in queries]);candidate_subjects=sorted(set(subjects))
    measured,correct,accepted=metrics(scores,labels,threshold,valid);np.testing.assert_array_equal(correct,stored_correct);np.testing.assert_array_equal(accepted,stored_accepted)
    assert scores.shape==(len(queries),len(candidate_subjects));imp=np.ones_like(scores,dtype=bool);imp[np.arange(len(labels)),labels]=False
    fa=((scores>=threshold)&valid[:,None])[imp].reshape(len(labels),-1);joint=correct&accepted
    confidence={name:cluster_interval(values,subjects) for name,values in [('rank1',correct),('tar',accepted),('joint',joint),('fmr',fa.mean(1))]}
    counts=dict(queries=len(queries),people=len(set(subjects)),candidate_eyes_per_query=scores.shape[1],impostor_comparisons=int(imp.sum()),false_accepts=int(fa.sum()),rank1_correct=int(correct.sum()),genuine_accepted=int(accepted.sum()),correct_and_accepted=int(joint.sum()),failed_queries=int((~valid).sum()))
    analysis={'analyzed_utc':datetime.now(timezone.utc).isoformat(),'counts':counts,'metrics':measured,'threshold_unchanged':threshold,'cluster_bootstrap_95_percent':confidence,
              'uncertainty_scope':'5000 person-cluster bootstrap replicates, fixed gallery/threshold, pointwise descriptive intervals; excludes selection bias and unknown external-pretraining overlap',
              'minimum_area':None,'original_condition_passed':result['target_reached'],
              'minimum_reason':'Occlusion curves not yet evaluated' if result['target_reached'] else 'Original condition fails frozen Rank1>=90%,TAR>=90%,FMR<=1%; no global minimum can be established for this candidate',
              'fresh_blind_test':False,'external_pretraining_overlap_unknown':True,
              'scores_sha256':hashlib.sha256((source/'scores_finais.npz').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'AUDITORIA.json').write_text(json.dumps(analysis,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    with (out/'consultas.csv').open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=['image','subject','side','predicted_subject','valid','correct','genuine_accepted','correct_and_accepted','genuine_score']);writer.writeheader()
        for i,r in enumerate(queries):writer.writerow(dict(image=Path(r.image).name,subject=r.subject,side=r.side,predicted_subject=candidate_subjects[int(scores[i].argmax())] if valid[i] else '',valid=bool(valid[i]),correct=bool(correct[i]),genuine_accepted=bool(accepted[i]),correct_and_accepted=bool(joint[i]),genuine_score=float(scores[i,labels[i]])))
    print(json.dumps(analysis,indent=2),flush=True)

if __name__=='__main__':main()

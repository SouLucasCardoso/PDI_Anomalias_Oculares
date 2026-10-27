"""Refaz regressao, escores e gate a partir dos vetores internos, sem nova inferencia."""
from pathlib import Path
import argparse,json
import numpy as np
from transportar_descritor_polar import apply_transport
from treinar_identidade_residual import fit_residual
ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_candidato_congelado import digest,global_scores
    from avaliar_robustez_reconhecimento import identity,metrics,operating_threshold
    from treinar_segmentacao_ubipr import Sample
    from validar_lateralidade_informada import subset
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--compact',action='store_true');a=p.parse_args();out=a.output_root/'transporte_descritor_polar_2026-10-23'
    result=json.loads((out/'CONCLUIDO.json').read_text());protocol=json.loads((out/'protocolo.json').read_text())
    assert digest(out/'source.py')==protocol['script_sha256']
    assert digest(ROOT/'treinar_identidade_residual.py')==protocol['residual_source_sha256'];assert digest(ROOT/'pupila_eliptica.py')==protocol['shape_source_sha256']
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';assert digest(manifest_file)==protocol['manifest_sha256'];raw=json.loads(manifest_file.read_text());rows=[Sample(**r) for r in raw['train']]
    fit=set(protocol['fit_people']);monitor=set(protocol['monitor_people']);assert not fit&monitor
    assert not (fit|monitor)&{r['subject'] for r in raw['val']}
    if a.compact:
        with np.load(out/'evidencia_compacta.npz') as z:
            data={k:z[k] for k in z.files}
        rows=[rows[int(i)] for i in data.pop('original_indices')]
        data['student']=data['teacher'].copy();data['student'][data['changed']]=data.pop('student_changed')
        data['transported']=data['teacher'].copy();data['transported'][data['changed']]=data.pop('transported_changed')
    else:
        with np.load(out/'cache_embeddings.npz') as z:data={k:z[k] for k in z.files}
    with np.load(out/'transporte.npz') as z:parameters={k:z[k] for k in z.files}
    assert digest(out/'transporte.npz')==result['parameters_sha256']
    fit_indices=data['fit_indices'];mon_indices=data['monitor_changed_indices']
    assert all(rows[int(i)].subject in fit for i in fit_indices) and all(rows[int(i)].subject in monitor for i in mon_indices)
    expected_fit=np.array([i for i,r in enumerate(rows) if r.subject in fit and data['valid'][i] and data['changed'][i]])
    np.testing.assert_array_equal(fit_indices,expected_fit)
    fitted=fit_residual(data['student'][fit_indices],data['teacher'][fit_indices]-data['student'][fit_indices],np.ones(len(fit_indices)),1.)
    for key in parameters:np.testing.assert_allclose(fitted[key],parameters[key],atol=1e-12,rtol=1e-12)
    corrected=apply_transport(data['student'],data['changed'],parameters);np.testing.assert_array_equal(corrected,data['transported']);np.testing.assert_array_equal(corrected[~data['changed']],data['teacher'][~data['changed']])
    positions=[i for i,r in enumerate(rows) if r.subject in monitor];monrows=[rows[i] for i in positions];ids=sorted({identity(r) for r in monrows});replayed={};maximum=0.
    for method in ['original','ellipse','transported']:
        vectors=data[dict(original='teacher',ellipse='student',transported='transported')[method]]
        full,valid=global_scores(vectors[positions],data['valid'][positions],monrows);scores,labels,_=subset(full,monrows,ids)
        with np.load(out/f'scores_{method}.npz') as z:
            np.testing.assert_array_equal(scores,z['scores']);np.testing.assert_array_equal(labels,z['labels']);np.testing.assert_array_equal(valid,z['valid']);maximum=max(maximum,float(np.max(abs(scores-z['scores']))))
            record=next(r for r in result['results'] if r['method']==method)
            measured,correct,accepted=metrics(scores,labels,record['threshold'],valid)
            for k in ['rank1','tar','far','queries','extraction_failures']:assert measured[k]==record[k]
            np.testing.assert_array_equal(correct,z['correct']);np.testing.assert_array_equal(accepted,z['accepted'])
            imp=np.ones_like(scores,bool);imp[np.arange(len(labels)),labels]=False;assert operating_threshold(scores[imp&valid[:,None]&(scores>-2)])==record['threshold']
            replayed[method]=record
    cosine=lambda f:float(np.sum(f[mon_indices].astype(np.float64)*data['teacher'][mon_indices].astype(np.float64),axis=1).mean())
    before=cosine(data['student']);after=cosine(corrected)
    assert before==result['monitor_teacher_cosine_before'] and after==result['monitor_teacher_cosine_after']
    gate=bool(after>before and all(replayed['transported'][k]>=replayed[m][k] for k in ['rank1','tar'] for m in ['original','ellipse']))
    assert gate==result['recognition_validation_gate_passed']
    final=dict(status='train_transport_replay_verified',evidence_scope='All255changed plus all960monitor photos; ordinary fit photos omitted' if a.compact else 'All7716training photos',fit_indices_verified=len(fit_indices),monitor_changed_indices_verified=len(mon_indices),maximum_score_difference=maximum,unchanged_retained_rows_bit_exact=True,gate_reproduced=gate,validation_identity_inference=False,test_inference=False,frozen_candidate_replaced=False,limits='Internal monitor already seen by original encoder and used in geometry selection; proxy alignment, not independent generalization.')
    (out/'VERIFICACAO_RELOAD.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2))

if __name__=='__main__':main()

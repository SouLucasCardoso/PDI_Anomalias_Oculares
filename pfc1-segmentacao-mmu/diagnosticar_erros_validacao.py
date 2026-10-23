"""Auditoria descritiva de falhas: nenhum ajuste de modelo ou limiar."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import argparse, csv, hashlib, json
import numpy as np
ROOT=Path(__file__).resolve().parent
ORDER=['rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red']


def decisions(data):
    scores=data['scores']; valid=data['valid']
    if scores.ndim!=2 or len(valid)!=len(scores):raise ValueError('Invalid dimensions')
    prediction=np.argmax(scores,axis=1)
    return prediction,valid&(scores>-2).any(1)&(prediction==data['labels'])


def transitions(clean, altered):
    clean=np.asarray(clean,dtype=bool); altered=np.asarray(altered,dtype=bool)
    if clean.shape!=altered.shape:raise ValueError('Unpaired decisions')
    return dict(both_correct=int((clean&altered).sum()),lost_correct=int((clean&~altered).sum()),
                recovered=int((~clean&altered).sum()),both_wrong=int((~clean&~altered).sum()))


def write_csv(file, rows):
    with file.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    out=a.output_root/'diagnostico_erros_val_2026-10-21';out.mkdir(parents=True,exist_ok=False)
    protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),
        scope='Descriptive development-validation audit only; no new test inference, model selection, threshold fitting or deployment change',
        analysis='All482 queries, clean and upper/lower10%, original/robust segmenter branches. Per-person/eye errors, component rank1, correct-component coverage, clean-to-occluded transitions and cross-segmenter transitions.',
        oracle_warning='Any-component-correct is a label-informed diagnostic coverage, NOT an achievable recognizer, not TAR, not reported system performance. No query-specific component/segmenter selection.',
        privacy='Query filenames and dataset subject IDs only; no new personal captures.',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    manifest=json.loads(manifest_file.read_text()); rows=manifest['val']
    identity=lambda r:f"{r['subject']}_{r['side']}"
    eligible={identity(r) for r in rows if r['session']==1}&{identity(r) for r in rows if r['session']==2}
    rows=[r for r in rows if identity(r) in eligible and r['session']==2]
    subjects=sorted({r['subject'] for r in rows}); labels=np.array([subjects.index(r['subject']) for r in rows])
    assert len(rows)==482 and len(subjects)==16
    source_hashes={str(manifest_file):hashlib.sha256(manifest_file.read_bytes()).hexdigest()}
    def read(file):
        source_hashes[str(file)]=hashlib.sha256(file.read_bytes()).hexdigest()
        with np.load(file) as z:data={k:z[k] for k in z.files}
        np.testing.assert_array_equal(data['labels'],labels)
        assert data['scores'].shape==(482,16)
        return data
    summaries=[]; records=[]; person_rows=[]; all_decisions={}; component_rows=[]
    for branch,tag in [('original',''),('robust','_segmentador_8f126141f4dd')]:
        all_decisions[branch]={}
        for condition,suffix in [('clean',''),('upper10','_oclusao_superior_10'),('lower10','_oclusao_inferior_10')]:
            folder=ROOT/'outputs'/f'confirmacao_congelada_val{suffix}{tag}_2026-10-21'
            fused=read(folder/'scores_finais.npz'); prediction,correct=decisions(fused)
            if 'correct' in fused:np.testing.assert_array_equal(correct,fused['correct'])
            components=[read(folder/f'scores_{name}.npz') for name in ORDER]
            component_correct=np.stack([decisions(c)[1] for c in components],axis=1)
            component_predictions=np.stack([decisions(c)[0] for c in components],axis=1)
            available=np.stack([c['valid']&(c['scores']>-2).any(1) for c in components],axis=1)
            coverage=component_correct.any(1); all_decisions[branch][condition]=correct
            wrong=~correct
            summaries.append(dict(branch=branch,condition=condition,queries=482,correct=int(correct.sum()),errors=int(wrong.sum()),
                extraction_failures=int((~fused['valid']).sum()),diagnostic_any_component_correct=int(coverage.sum()),
                fusion_errors_with_correct_component=int((wrong&coverage).sum()),errors_without_correct_component=int((wrong&~coverage).sum()),
                all_nine_available_agree_wrong=int((available.all(1)&(component_predictions==component_predictions[:,:1]).all(1)&wrong).sum())))
            for j,name in enumerate(ORDER):
                component_rows.append(dict(branch=branch,condition=condition,component=name,correct=int(component_correct[:,j].sum()),
                    correct_where_fusion_wrong=int((component_correct[:,j]&wrong).sum()),invalid=int((~available[:,j]).sum())))
            for subject in subjects:
                idx=np.array([r['subject']==subject for r in rows]); counts=Counter(subjects[prediction[i]] for i in np.flatnonzero(idx&wrong&fused['valid']))
                person_rows.append(dict(branch=branch,condition=condition,subject=subject,queries=int(idx.sum()),correct=int((idx&correct).sum()),
                    errors=int((idx&wrong).sum()),invalid=int((idx&~fused['valid']).sum()),confused_with=json.dumps(dict(counts),sort_keys=True)))
            for i,r in enumerate(rows):
                values=fused['scores'][i]; genuine=float(values[labels[i]]); impostor=values.copy();impostor[labels[i]]=-np.inf
                records.append(dict(branch=branch,condition=condition,image=Path(r['image']).name,subject=r['subject'],side=r['side'],
                    predicted_subject=subjects[prediction[i]] if fused['valid'][i] else '',valid=bool(fused['valid'][i]),correct=bool(correct[i]),
                    genuine_score=genuine,margin=genuine-float(impostor.max()),correct_component_count=int(component_correct[i].sum()),
                    correct_components='|'.join(name for j,name in enumerate(ORDER) if component_correct[i,j])))
    changes={branch:{condition:transitions(values['clean'],values[condition]) for condition in ('upper10','lower10')} for branch,values in all_decisions.items()}
    branch_changes={condition:transitions(all_decisions['original'][condition],all_decisions['robust'][condition]) for condition in ('clean','upper10','lower10')}
    write_csv(out/'consultas.csv',records);write_csv(out/'por_pessoa.csv',person_rows);write_csv(out/'componentes.csv',component_rows)
    final=dict(status='validation_error_audit_completed',summaries=summaries,clean_to_occlusion=changes,original_to_robust=branch_changes,
        source_sha256=source_hashes,test_inference=False,frozen_candidate_replaced=False,minimum_area=None,
        limitations='Descriptive reused validation only. Component coverage uses ground truth; never an operational prediction or proof that fusion learning can attain that coverage. Cross-branch scores use saved original frozen calibration, no recalibration in this audit.')
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8')
    print(json.dumps({k:final[k] for k in ('summaries','clean_to_occlusion','original_to_robust')},indent=2),flush=True)


if __name__=='__main__':main()

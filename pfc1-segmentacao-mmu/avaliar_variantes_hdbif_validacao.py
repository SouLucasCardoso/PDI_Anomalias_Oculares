"""Ablacao predefinida de rotacao e normalizacao; somente validacao clinica."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import numpy as np
from matcher_hdbif_fft import prepare,distances,best_score

ROOT=Path(__file__).resolve().parent
VARIANTS=[('default_raw',16,False),('default_normalized',16,True),
          ('full_rotation_raw',None,False),('full_rotation_normalized',None,True)]

def main():
    from avaliar_robustez_reconhecimento import operating_threshold,metrics
    original=ROOT/'outputs/hdbif_slpvld_validacao_completa_2026-10-20'
    if not (original/'CONCLUIDO.json').exists(): raise RuntimeError('Validation baseline incomplete')
    out=ROOT/'outputs/hdbif_slpvld_ablacao_validacao_2026-10-20'; out.mkdir(parents=True,exist_ok=True)
    manifest=ROOT/'outputs/biometria_clinica_triagem_2026-10-20/manifesto.json'
    rows=json.loads(manifest.read_text(encoding='utf-8'))['val']
    rows.sort(key=lambda r:(r['subject'],r['side'],r['role'],r['capture_date'],r['image']))
    protocol={'purpose':'Validation-only development ablation; no clinical test evaluation',
        'variants':VARIANTS,'selection':'Max validation TAR at validation FMR<=1%; ties Rank1, then listed variant order',
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'matcher_sha256':hashlib.sha256((ROOT/'matcher_hdbif_fft.py').read_bytes()).hexdigest(),
        'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
        'baseline_protocol_sha256':hashlib.sha256((original/'protocolo.json').read_bytes()).hexdigest(),
        'rationale':'Broad capture rotations and variable usable mask area observed on validation; encoding and masks unchanged',
        'minimum_area_criterion':'Unchanged; this study measures original-image recognition only'}
    target=out/'protocolo.json'
    if target.exists(): raise ValueError('Preserve previous ablation; choose a new output folder')
    target.write_text(json.dumps(dict(protocol,registered_utc=datetime.now(timezone.utc).isoformat()),indent=2),encoding='utf-8')
    cache=[]
    for row in rows:
        with np.load(original/'templates'/(Path(row['image']).stem+'.npz'),allow_pickle=False) as saved:
            audit=json.loads(str(saved['audit']))
            cache.append(prepare(saved['code'],saved['mask']) if audit['valid'] else None)
    ids=sorted({(r['subject'],r['side']) for r in rows})
    gallery=[next(i for i,r in enumerate(rows) if (r['subject'],r['side'])==eye and r['role']=='gallery') for eye in ids]
    queries=[i for i,r in enumerate(rows) if r['role']=='query']
    labels=np.array([ids.index((rows[i]['subject'],rows[i]['side'])) for i in queries])
    matrices={name:np.full((len(queries),len(gallery)),-2.,dtype=float) for name,_,_ in VARIANTS}
    for qi,index in enumerate(queries):
        for gi,enrolled in enumerate(gallery):
            if cache[index] is None or cache[enrolled] is None: continue
            raw,normalized,_=distances(cache[index],cache[enrolled])
            for name,shift,norm in VARIANTS:
                matrices[name][qi,gi]=best_score(normalized if norm else raw,shift)
        if (qi+1)%10==0: print(f'Comparacoes FFT {qi+1}/{len(queries)}',flush=True)
    with np.load(original/'scores.npz') as saved:
        if not np.allclose(saved['scores'],matrices['default_raw'],rtol=0,atol=1e-12):
            raise ValueError('FFT and official exhaustive matching differ; reject ablation')
    summaries=[]
    impostor=np.ones_like(matrices['default_raw'],dtype=bool); impostor[np.arange(len(labels)),labels]=False
    for name,shift,norm in VARIANTS:
        scores=matrices[name]; valid=(scores>-2).any(axis=1)
        threshold=operating_threshold(scores[impostor & (scores>-2)])
        measures,correct,accepted=metrics(scores,labels,threshold,valid)
        summaries.append({'variant':name,'max_shift_columns':shift,'score_normalized':norm,
                          'threshold':threshold,'metrics':measures})
        np.savez_compressed(out/(name+'.npz'),scores=scores,labels=labels,valid=valid,correct=correct,accepted=accepted)
    chosen=max(enumerate(summaries),key=lambda item:(item[1]['metrics']['tar'],item[1]['metrics']['rank1'],-item[0]))[1]['variant']
    report={'status':'validation_ablation_completed_test_untouched','scientific_final_result':False,
            'official_fft_equivalence_checked_all_pairs':True,'selected_on_validation':chosen,'variants':summaries,
            'note':'Development selection; requires frozen independent clinical test and no minimum-area inference.'}
    (out/'resultado.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__': main()

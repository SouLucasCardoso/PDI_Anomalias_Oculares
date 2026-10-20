"""Diagnostico exploratorio por consulta, condicionado ao sucesso original."""
from datetime import datetime,timezone
from pathlib import Path
import csv
import hashlib
import json
import time
import numpy as np

ROOT=Path(__file__).resolve().parent

def query_minima(original, levels):
    original=np.asarray(original,dtype=bool); alive=original.copy()
    minimum=np.full(len(original),-1,dtype=int); minimum[original]=100
    for level,good in sorted(levels,key=lambda pair:pair[0]):
        alive &= np.asarray(good,dtype=bool)
        minimum[alive]=100-int(level)
    return [int(v) if v>=0 else None for v in minimum]

def identified(path,threshold):
    with np.load(path,allow_pickle=False) as saved:
        scores=saved['scores'].astype(np.float64); labels=saved['labels']; valid=saved['valid']
    return valid & (scores.argmax(axis=1)==labels) & (scores[np.arange(len(labels)),labels]>=threshold)

def main():
    out=ROOT/'outputs/tolerancia_condicional_exploratoria_2026-10-20'; out.mkdir(parents=True,exist_ok=True)
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),
        'status':'Exploratory secondary analysis after initial primary results; not a fresh preregistered confirmatory test',
        'eligibility':'Query correctly identified Rank1 AND genuine above frozen validation threshold in original image',
        'quantity':'Per-query smallest tested preserved reference fraction with success at all larger fractions; original failures undefined',
        'retention':'Fraction of eligible original successes still identified; denominator reported separately from all queries',
        'scope':'Iris-input branches only; exclude whole-image context from iris-area inference',
        'primary_criterion':'Unchanged global Rank1/TAR>=90%; this analysis cannot replace it or establish a population minimum',
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if (out/'protocolo.json').exists(): raise ValueError('Preserve prior analysis; use a new version')
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    learned=ROOT/'outputs/area_encoder_ubipr_2026-10-20'
    deadline=time.monotonic()+6*3600
    while not (learned/'CONCLUIDO.json').exists():
        if time.monotonic()>deadline: raise TimeoutError('Encoder area experiment incomplete')
        time.sleep(15)
    from relatar_validacao_hdbif import cluster_interval
    original=ROOT/'outputs/biometria_area_completa_2026-10-20'
    calibration=json.loads((original/'calibracao.json').read_text(encoding='utf-8'))
    nn_protocol=json.loads((learned/'protocolo.json').read_text(encoding='utf-8'))
    with (original/'manifesto_auditado.csv').open(encoding='utf-8-sig',newline='') as stream:
        queries=[r for r in csv.DictReader(stream) if r['split']=='test' and r['session']=='2']
    subjects=np.array([int(r['subject']) for r in queries]); per_query=[]; curves=[]; summaries=[]
    configurations=[('DINO_referencia',original,'iris_referencia',calibration['iris_referencia']['threshold']),
                    ('DINO_UNet',original,'iris_unet',calibration['iris_unet']['threshold']),
                    ('Encoder_treinado',learned,None,nn_protocol['threshold'])]
    inputs={}
    for name,folder,branch,threshold in configurations:
        baseline_path=folder/(f'scores_{branch}_original.npz' if branch else 'scores_original.npz')
        base=identified(baseline_path,threshold)
        if len(base)!=len(queries): raise ValueError('Query population mismatch')
        inputs[str(baseline_path.relative_to(ROOT))]=hashlib.sha256(baseline_path.read_bytes()).hexdigest()
        for kind in ('oclusao_superior','oclusao_inferior'):
            levels=[]
            for level in range(10,100,10):
                path=folder/(f'scores_{branch}_{kind}_{level}.npz' if branch else f'scores_{kind}_{level}.npz')
                good=identified(path,threshold); levels.append((level,good))
                inputs[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
                ci=cluster_interval(good[base],subjects[base]) if base.any() else [None,None]
                curves.append({'model':name,'orientation':kind,'preserved_percent':100-level,
                    'all_queries':len(base),'original_successes':int(base.sum()),
                    'retained_original_successes':int((base&good).sum()),
                    'conditional_retention':float(good[base].mean()) if base.any() else None,
                    'ci95_low':ci[0],'ci95_high':ci[1],
                    'overall_joint_identification':float(good.mean())})
            minima=query_minima(base,levels)
            defined=[v for v in minima if v is not None]
            summaries.append({'model':name,'orientation':kind,'total_queries':len(base),
                'original_identifiable_queries':int(base.sum()),'original_joint_identification':float(base.mean()),
                'conditional_median_required_percent':float(np.median(defined)) if defined else None,
                'conditional_p25_p75_required_percent':np.quantile(defined,[.25,.75]).tolist() if defined else None,
                'warning':'Conditional selected cases, not a global minimum or clinically validated anatomical area'})
            for row,eligible,value in zip(queries,base,minima):
                per_query.append({'model':name,'orientation':kind,'subject':row['subject'],'side':row['side'],
                    'image':Path(row['image']).name,'eligible_original_joint_success':bool(eligible),
                    'minimum_tested_preserved_percent':value})
    for name,rows in [('consultas.csv',per_query),('retencao.csv',curves)]:
        with (out/name).open('w',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (out/'inputs_sha256.json').write_text(json.dumps(inputs,indent=2),encoding='utf-8')
    result={'status':'exploratory_conditional_analysis_completed','summaries':summaries,
        'interpretation':'Distribution only among queries identifiable in original; other queries remain in exported table as undefined. Primary global minimum remains unchanged.'}
    (out/'resultado.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (out/'CONCLUIDO.json').write_text(json.dumps({'completed':True},indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__': main()

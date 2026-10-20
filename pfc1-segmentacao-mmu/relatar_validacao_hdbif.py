"""Relatorio de desenvolvimento com bootstrap por pessoa e galeria fixa."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import numpy as np

ROOT=Path(__file__).resolve().parent

def cluster_interval(values, subjects, repetitions=5000):
    values=np.asarray(values,dtype=float); subjects=np.asarray(subjects)
    if not len(values) or len(values)!=len(subjects): raise ValueError('Invalid bootstrap observations')
    unique=np.unique(subjects)
    totals=np.array([values[subjects==s].sum() for s in unique])
    counts=np.array([(subjects==s).sum() for s in unique])
    draws=np.random.default_rng(42).integers(0,len(unique),(repetitions,len(unique)))
    estimates=totals[draws].sum(axis=1)/counts[draws].sum(axis=1)
    return np.quantile(estimates,[.025,.975]).tolist()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split',choices=('val','test'),default='val')
    parser.add_argument('--wait',action='store_true'); args=parser.parse_args()
    folder=ROOT/('outputs/hdbif_slpvld_validacao_completa_2026-10-20' if args.split=='val' else 'outputs/hdbif_slpvld_teste_congelado_2026-10-20')
    if args.wait:
        deadline=time.monotonic()+4*3600
        while not (folder/'CONCLUIDO.json').exists():
            if time.monotonic()>deadline: raise TimeoutError('Validation did not finish')
            time.sleep(30)
    if not (folder/'CONCLUIDO.json').exists(): raise RuntimeError('Validation incomplete')
    protocol=json.loads((folder/'protocolo.json').read_text(encoding='utf-8'))
    result=json.loads((folder/'resultado.json').read_text(encoding='utf-8'))
    rows=json.loads((ROOT/'outputs/biometria_clinica_triagem_2026-10-20/manifesto.json').read_text(encoding='utf-8'))[args.split]
    rows.sort(key=lambda r:(r['subject'],r['side'],r['role'],r['capture_date'],r['image']))
    queries=[r for r in rows if r['role']=='query']; subjects=np.array([r['subject'] for r in queries])
    with np.load(folder/'scores.npz') as saved:
        correct=saved['correct']; accepted=saved['accepted']; scores=saved['scores']; labels=saved['labels']; valid=saved['valid']
    if len(queries)!=len(correct): raise ValueError('Query ordering mismatch')
    impostor=np.ones_like(scores,dtype=bool); impostor[np.arange(len(labels)),labels]=False
    false_matches=((scores>=result['threshold']) & valid[:,None] & impostor).sum(axis=1)/(scores.shape[1]-1)
    intervals={name:cluster_interval(values,subjects) for name,values in [('rank1',correct),('tar',accepted),('fmr',false_matches)]}
    report={'generated_utc':datetime.now(timezone.utc).isoformat(),
        'status':'development_validation_only' if args.split=='val' else 'held_out_test_frozen_protocol','metrics':result['metrics'],
        'conditional_cluster_ci95':intervals,'people':len(set(subjects)),
        'bootstrap':'5000 resamples of people, seed42, percentile95%, fixed gallery, fixed validation-calibrated threshold',
        'limitations':['Validation used both for calibration and development assessment; not held-out test performance' if args.split=='val' else 'Recognizer and threshold frozen from validation; no test recalibration',
                       'Intervals do not propagate uncertainty in threshold estimation or enrollment gallery',
                       'Clinical labels co-occur; normal vs other groups are observational',
                       'No minimum-area estimate from this unperturbed validation evaluation']}
    stem='validacao' if args.split=='val' else 'teste'
    (folder/f'relatorio_{stem}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    lines=['# HDBIF — '+('validação clínica de desenvolvimento' if args.split=='val' else 'teste clínico com protocolo congelado'),'',
           f"Amostra: {protocol['counts']['people']} pessoas, {protocol['counts']['eyes']} olhos e {len(queries)} consultas.",'',
           '| Medida | Estimativa | IC 95% condicional por pessoa |','|---|---:|---:|']
    for name,field in [('rank1','rank1'),('tar','tar'),('fmr','far')]:
        lo,hi=intervals[name]
        lines.append(f"| {name.upper()} | {100*result['metrics'][field]:.2f}% | {100*lo:.2f}% a {100*hi:.2f}% |")
    lines+=['',f"Falhas em imagens: {result['failed_images']}; falhas de cadastro: {result['failed_enrollments']}; comparações indisponíveis: {result['unavailable_pair_comparisons']}.",'',
            'O limiar foi calibrado nesta própria validação para FMR empírica de até 1%. As estimativas são de desenvolvimento.' if args.split=='val' else 'O reconhecedor e o limiar foram congelados na validação. A FMR observada no teste pode diferir do alvo de validação.',
            'Os intervalos mantêm galeria e limiar fixos, sem propagar a incerteza de sua estimação. A avaliação original não determina um mínimo de área nem efeitos causais de doenças.']
    (folder/f'RELATORIO_{stem.upper()}.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__': main()

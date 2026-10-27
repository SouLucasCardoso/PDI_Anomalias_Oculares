"""Reproduz incerteza usando somente96linhas de contagens por participante."""
from pathlib import Path
import argparse,csv,json
import numpy as np
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'incerteza_fronteira_area_2026-10-23'
    from avaliar_candidato_congelado import digest
    result=json.loads((out/'CONCLUIDO.json').read_text());protocol=json.loads((out/'protocolo.json').read_text());assert digest(out/'source.py')==protocol['script_sha256']
    with (out/'estatisticas_por_pessoa.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
    people=sorted({int(r['subject']) for r in rows});conditions=[r['condition'] for r in result['records']];assert len(rows)==96 and len(people)==16
    count=np.zeros((16,6,3),np.int64);queries=np.zeros(16,np.int64)
    for row in rows:
        i=people.index(int(row['subject']));j=conditions.index(row['condition']);queries[i]=int(row['queries']);count[i,j]=[int(row[k]) for k in ['correct','accepted','false_accepts']]
    assert queries.sum()==486
    draws=np.random.default_rng(20261001).integers(0,16,(5000,16));multiplicities=np.stack([np.bincount(r,minlength=16) for r in draws]);denominator=multiplicities@queries
    totals=np.einsum('bp,pcm->bcm',multiplicities,count);sample=totals/denominator[:,None,None];sample[:,:,2]/=15
    approved=(10*totals[:,:,0]>=9*denominator[:,None])&(10*totals[:,:,1]>=9*denominator[:,None])&(100*totals[:,:,2]<=15*denominator[:,None])
    maximum=0.
    for j,record in enumerate(result['records']):
        assert count[:,j,0].sum()==record['rank1_correct'] and count[:,j,1].sum()==record['genuine_accepted'] and count[:,j,2].sum()==record['false_accepts']
        for m,key in enumerate(['rank1','tar','fmr']):
            expected=np.quantile(100*sample[:,j,m],[.025,.975]);stored=np.array(record['intervals95_percent'][key]);np.testing.assert_allclose(expected,stored,atol=1e-12,rtol=0);maximum=max(maximum,float(abs(expected-stored).max()))
        assert float(approved[:,j].mean())==record['joint_pass_fraction_of_resamples']
        for m,key in [(0,'rank1'),(1,'tar')]:np.testing.assert_allclose(np.quantile(100*(sample[:,0,m]-sample[:,j,m]),[.025,.975]),record[f'paired_{key}_loss_pp_ci95'],atol=1e-12,rtol=0)
    for key,indices in [('upper_grid_0_1',[0,1]),('lower_grid_0_1_2',[0,2,3]),('common_grid_0_1',[0,1])]:
        passing=approved[:,indices].copy()
        if key=='common_grid_0_1':passing[:,1]&=approved[:,2]
        observed={k:0 for k in result['bootstrap_prefix_distributions'][key]}
        for row in passing:
            if not row[0]:label='original_fails_no_approved_prefix'
            else:
                consecutive=0
                for passed in row[1:]:
                    if not passed:break
                    consecutive+=1
                label=f'{100-consecutive}_percent_on_available_grid'
            observed[label]+=1
        assert sum(observed.values())==5000
        for label,n in observed.items():assert n==result['bootstrap_prefix_distributions'][key][label]['draws']
    difference=100*(sample[:,4,0]-sample[:,5,0]);np.testing.assert_allclose(np.quantile(difference,[.025,.975]),result['upper_minus_lower_rank1_at10pp']['ci95_pp'],atol=1e-12,rtol=0)
    final=dict(status='boundary_uncertainty_reproduced_from_person_counts',person_condition_rows=96,people=16,queries=486,repetitions=5000,maximum_interval_difference_pp=maximum,all_prefix_categories_account_for5000_draws=True,integer_boundary_criteria_verified=True,new_inference=False,threshold_recalibrated=False)
    (out/'VERIFICACAO_REPLAY.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2))

if __name__=='__main__':main()

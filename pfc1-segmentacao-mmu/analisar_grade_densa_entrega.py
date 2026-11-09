"""Auditoria independente da grade inteira de 1 a 31% e do candidato congelado."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,hashlib,json,os
import numpy as np
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
fmt=lambda x,n=2:f'{x:.{n}f}'.replace('.',',')
SCHEDULE=[('original',0)]+[(d,n) for n in range(1,32) for d in ('oclusao_superior','oclusao_inferior')]


def recount(data,threshold,subset=None):
    s=data['scores'];y=data['labels'];v=data['valid']
    if subset is not None:s,y,v=s[subset],y[subset],v[subset]
    correct=(s.argmax(1)==y)&v;accepted=(s[np.arange(len(y)),y]>=threshold)&v
    imp=np.ones(s.shape,bool);imp[np.arange(len(y)),y]=False
    false=((s>=threshold)&v[:,None]&imp).sum(1)
    counts={'queries':len(y),'correct':int(correct.sum()),'accepted':int(accepted.sum()),'joint':int((correct&accepted).sum()),
        'false_accepts':int(false.sum()),'impostors':int(imp.sum()),'extraction_failures':int((~v).sum())}
    vector=np.column_stack((correct,accepted,correct&accepted,false)).astype(float)
    return counts,vector


def passes(c,joint=False):
    return (10*c['correct']>=9*c['queries'] and 10*c['accepted']>=9*c['queries']
        and 100*c['false_accepts']<=c['impostors'] and (not joint or 10*c['joint']>=9*c['queries']))


def main():
    p=argparse.ArgumentParser();p.add_argument('--reference-run',type=Path,required=True)
    p.add_argument('--candidate-run',type=Path);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    reference=a.reference_run.resolve();candidate=a.candidate_run.resolve() if a.candidate_run else None
    out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    completion=json.loads((reference/'CONCLUIDO.json').read_text());assert completion['conditions']==63
    rfile=reference/'resultados.json';assert sha(rfile)==completion['results_sha256']
    records=json.loads(rfile.read_text());assert {(r['condition'],r['loss_percent']) for r in records}==set(SCHEDULE)
    ref_protocol=json.loads((reference/'protocolo.json').read_text())
    for name,expected in ref_protocol['source_sha256'].items():assert sha(ROOT/name)==expected
    frozen_file=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json';frozen=json.loads(frozen_file.read_text());threshold=frozen['frozen_threshold']
    assert sha(frozen_file)==ref_protocol['frozen_sha256']
    area_file=ROOT/'outputs/ensaio_oclusoes_2026-11-08/inferencia/confirmacao_congelada_test_oclusao_superior_1_2026-10-21/interventions.json'
    defined=np.array([r['fraction_defined'] for r in json.loads(area_file.read_text())],bool);assert len(defined)==486 and defined.sum()==480
    bykey={(r['condition'],r['loss_percent']):r for r in records};raw={};verified=[];secondary=[]
    for condition,level in SCHEDULE:
        record=bykey[(condition,level)];file=reference/f'scores_reference_{condition}_{level}.npz';assert sha(file)==record['scores_sha256']
        with np.load(file,allow_pickle=False) as z:d={k:z[k].copy() for k in z.files}
        counts,vector=recount(d,threshold);assert counts==record['counts'] and counts['queries']==486 and counts['impostors']==7290
        sc,_=recount(d,threshold,defined);secondary.append({'condition':condition,'level':level,'reference':sc})
        if level:
            area=json.loads((Path(record['source_folder'])/'interventions.json').read_text());assert len(area)==486
            for item in area:
                n=item['reference_pixels'];fraction=item['affected_fraction']
                assert abs(fraction-(round(n*level/100)/n if n else 0.))<1e-12
            assert sum(r['fraction_defined'] for r in area)==480
        raw[(condition,level)]={'reference':(d,counts,vector)}
        verified.append({'condition':condition,'level':level,'reference_counts':counts,'reference_scores_sha256':sha(file)})
    # Query order is shared with the registered frozen evaluator.
    from avaliar_robustez_reconhecimento import load_splits
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());rows=load_splits(manifest)['test']
    subjects=np.array([r.subject for r in rows if r.session==2]);people=np.unique(subjects);assert len(people)==16
    draws=np.random.default_rng(20261108).integers(0,16,(5000,16));den=np.array([(subjects==s).sum() for s in people])[draws].sum(1)
    candidate_records=None;gate=None
    if candidate is not None:
        cdone=json.loads((candidate/'CONCLUIDO.json').read_text());assert cdone['conditions']==63
        cfile=candidate/'resultados.json';assert sha(cfile)==cdone['results_sha256'];candidate_records=json.loads(cfile.read_text())
        cp=json.loads((candidate/'protocolo.json').read_text())
        for name,expected in cp['source_sha256'].items():assert sha(ROOT/name)==expected
        assert sha(candidate/'CANDIDATO_CONGELADO.json')==cp['selection_sha256']
        for j,(condition,level) in enumerate(SCHEDULE):
            record=next(r for r in candidate_records if r['condition']==condition and r['level']==level)
            file=candidate/f'{condition}_{level}/scores_candidato.npz';assert sha(file)==record['scores_sha256']
            with np.load(file) as z:d={k:z[k].copy() for k in z.files}
            np.testing.assert_array_equal(d['labels'],raw[(condition,level)]['reference'][0]['labels'])
            c,vec=recount(d,threshold);assert c==record['candidate']['counts']
            assert raw[(condition,level)]['reference'][1]==record['baseline']['counts']
            raw[(condition,level)]['candidate']=(d,c,vec);verified[j]['candidate_counts']=c;verified[j]['candidate_scores_sha256']=sha(file)
            sc,_=recount(d,threshold,defined);secondary[j]['candidate']=sc
            difference=vec-raw[(condition,level)]['reference'][2]
            totals=np.array([difference[subjects==s].sum(0) for s in people])[draws].sum(1)
            ci=np.quantile(100*totals/np.column_stack((den,den,den,15*den)),[.025,.975],axis=0)
            for k,key in enumerate(('rank1','tar','joint','fmr')):np.testing.assert_allclose(ci[:,k],record['paired_gain95_pp'][key],atol=1e-10,rtol=0)
        b=raw[('original',0)]['reference'][1];c=raw[('original',0)]['candidate'][1]
        gate=(c['correct']>=b['correct'] and c['accepted']>=b['accepted'] and 100*c['false_accepts']<=c['impostors']
            and sum(r['candidate'][1]['joint'] for r in raw.values())>sum(r['reference'][1]['joint'] for r in raw.values())
            and all(r['candidate'][1]['false_accepts']<=r['reference'][1]['false_accepts'] for r in raw.values()))
        assert bool(gate)==cdone['comparison_gate_passed']
    names=('reference','candidate') if candidate_records is not None else ('reference',);minimum={}
    for name in names:
        minimum[name]={}
        for direction in ('oclusao_superior','oclusao_inferior'):
            minimum[name][direction]={}
            for rule,joint in (('marginal',False),('joint90',True)):
                prefix=[]
                for level in range(32):
                    c=raw[('original',0) if level==0 else (direction,level)][name][1]
                    if not passes(c,joint):break
                    prefix.append(level)
                minimum[name][direction][rule]={'passing_loss_prefix':prefix,'minimum_nominal_support_on_registered_prefix':100-prefix[-1] if prefix else None}
    audit={'status':'verified','conditions':63,'counts_recomputed':verified,'fixed_area_defined480':secondary,
        'minimum':minimum,'comparison_gate_passed':gate,'all_queries_retained':486,'impostors_per_condition':7290,
        'occlusion_counts_checked_against_original_reference':True,'sources_unchanged':True,
        'recognizer_replaced':False,'independent_confirmation':False,'clinical_effect_measured':False,
        'reference_completion_sha256':sha(reference/'CONCLUIDO.json'),'analyst_sha256':sha(__file__)}
    write_text=lambda p,v:Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
    write_text(out/'AUDITORIA_FINAL.json',audit)
    os.environ.setdefault('MPLCONFIGDIR',str(Path(os.environ['TEMP'])/'pfc-matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(7.6,4.4),layout='constrained')
    for direction,color,label in (('oclusao_superior','#1f5d99','Superior'),('oclusao_inferior','#ae4528','Inferior')):
        selected=[bykey[('original',0)]]+[bykey[(direction,n)] for n in range(1,32)]
        for ax,metric,ci_key in zip(axes,('rank1','far'),('rank1','fmr')):
            values=np.array([100*r['rates'][metric] for r in selected]);ci=np.array([r['interval95_cluster_person_pp'][ci_key] for r in selected])
            ax.plot(range(32),values,'o-',color=color,label=label,linewidth=1.5,markersize=2.4)
            ax.fill_between(range(32),ci[:,0],ci[:,1],color=color,alpha=.12)
            ax.set_xlabel('Área anotada ocluída (%)');ax.grid(alpha=.18);ax.set_xticks([0,5,10,15,20,25,30]);ax.set_xlim(-1,32)
            ax.axvline(30,color='#777777',linestyle=':',linewidth=1)
    axes[0].axhline(90,color='black',linestyle='--',linewidth=1,label='Critério nominal 90%');axes[0].set_ylim(0,100)
    axes[0].set_ylabel('Identificação Rank-1 (%)');axes[0].legend(loc='lower left',fontsize=9)
    axes[1].axhline(1,color='black',linestyle='--',linewidth=1,label='Critério nominal 1%');axes[1].set_ylabel('Falsas correspondências FMR (%)');axes[1].legend(loc='upper left',fontsize=9)
    fig.suptitle('Grade de 1% a 31% — 486 consultas por condição',fontsize=12)
    fig.savefig(out/'curva_area_identificacao.png',dpi=300);plt.close(fig)
    if candidate_records is not None:
        fig,axes=plt.subplots(1,2,figsize=(10,4.5),layout='constrained')
        for direction,color,label in (('oclusao_superior','#1f5d99','Superior'),('oclusao_inferior','#ae4528','Inferior')):
            for name,style in (('reference','--'),('candidate','-')):
                counts=[raw[('original',0) if n==0 else (direction,n)][name][1] for n in range(32)]
                axes[0].plot(range(32),[100*c['correct']/c['queries'] for c in counts],style,color=color,label=f'{label}/{name}')
                axes[1].plot(range(32),[100*c['false_accepts']/c['impostors'] for c in counts],style,color=color)
        axes[0].set_ylabel('Rank-1 (%)');axes[1].set_ylabel('FMR (%)');axes[0].legend(fontsize=8)
        for ax in axes:ax.set_xlabel('Oclusão anotada (%)');ax.grid(alpha=.2)
        fig.savefig(out/'comparacao_contorno.png',dpi=220);plt.close(fig)
    lines=['# Resultado da grade completa de 1% a 31%','',
        'Foram auditadas 63 condições: controle e todos os níveis inteiros de perda nas duas orientações. Em cada condição foram mantidas 486 consultas, inclusive falhas, e 7.290 pares impostores.','',
        '![Curva completa, com intervalos descritivos por pessoa](curva_area_identificacao.png)','',
        '| Perda | Suporte | Rank-1 superior | Rank-1 inferior | TAR superior | TAR inferior | FMR superior | FMR inferior |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|']
    flat=[]
    for level in range(32):
        u=bykey[('original',0) if level==0 else ('oclusao_superior',level)]['rates'];l=bykey[('original',0) if level==0 else ('oclusao_inferior',level)]['rates']
        lines.append(f"| {level}% | {100-level}% | {fmt(100*u['rank1'])}% | {fmt(100*l['rank1'])}% | {fmt(100*u['tar'])}% | {fmt(100*l['tar'])}% | {fmt(100*u['far'],3)}% | {fmt(100*l['far'],3)}% |")
        flat.append({'occlusion_percent':level,'nominal_support_percent':100-level,**{f'{d}_{k}':r[k] for d,r in (('upper',u),('lower',l)) for k in ('rank1','tar','far','joint')}})
    with (out/'tabela_completa.csv').open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    lines+=['','## Fronteira observada, condicionada à grade','']
    for name,v in minimum.items():
        for direction,rules in v.items():
            for rule,result in rules.items():lines.append(f"- {name}/{direction}/{rule}: suporte mínimo no prefixo = {result['minimum_nominal_support_on_registered_prefix']}%; perdas aprovadas = {result['passing_loss_prefix']}.")
    if candidate_records is not None:lines+=['',f'Regra completa de comparação do candidato aprovada: **{gate}**. Melhoras locais e o critério absoluto de 90/90/1 são distintos.','',
        '![Comparação com o candidato congelado](comparacao_contorno.png)']
    lines+=['','## Alcance','',
        'Suporte nominal restante é relativo à anotação original, sem medir o anel completo da ISO ou a extensão de doença. A grade inteira reduz a lacuna entre pontos testados, mas não estabelece mínimo universal. O processamento foi recalculado após cada perda; o efeito reúne textura retirada e instabilidade de segmentação/geometria.','',
        'O subconjunto secundário mantém as mesmas 480 referências definidas, sem selecionar acertos. Os intervalos são descritivos, por pessoa, com galeria fixa e teste previamente exposto ao desenvolvimento. Não certificam simultaneamente toda a curva nem substituem confirmação independente.']
    (out/'RESULTADO_PARA_DEFESA.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    write_text(out/'CONCLUIDO.json',{'status':'concluido','conditions':63,'candidate_comparison_gate':gate,
        'audit_sha256':sha(out/'AUDITORIA_FINAL.json'),'figure_sha256':sha(out/'curva_area_identificacao.png'),
        'report_sha256':sha(out/'RESULTADO_PARA_DEFESA.md'),'sources_unchanged':True})
    print(json.dumps({'conditions':63,'minimum':minimum,'comparison_gate_passed':gate}),flush=True)


if __name__=='__main__':main()

"""Reconta grade13 e coorte480 sem selecionar modelo nem limiar."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os
import numpy as np
from PIL import Image
from avaliar_candidato_congelado import fuse
from avaliar_robustez_reconhecimento import load_splits,metrics
from treinar_segmentacao_ubipr import decode_mask
from confirmar_reconhecedor_entrega import load_components
from analisar_confirmacao_reconhecedor_entrega import measured
from recorte_iris_sam31_alta_res import sha
from rodada_reconhecedor_entrega import write
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args();run=a.run_dir.resolve();out=run/'analise';out.mkdir()
    result=json.loads((run/'CONCLUIDO.json').read_text());assert len(result['records'])==13
    protocol=json.loads((run/'protocolo.json').read_text());assert sha(ROOT/protocol['source_file'])==protocol['source_sha256']
    assert sha(run/'CANDIDATO_CONGELADO.json')==protocol['candidate_sha256']
    for name,expected in protocol['sources_sha256'].items():assert sha(ROOT/name)==expected
    write(out/'PROTOCOLO_ANALISE.json',{'registered_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sha(__file__),'scope':'Recount13points,all486queries primary,predefined480area-defined cohort secondary; no weight/threshold selection; descriptive paired person bootstrap5kseed20261108'})
    frozen=json.loads((ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json').read_text());threshold=protocol['threshold']
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());queries=[r for r in load_splits(manifest)['test'] if r.session==2];defined=np.array([bool((decode_mask(Image.open(r.mask))==1).any()) for r in queries]);assert len(queries)==486 and defined.sum()==480
    people=np.unique([r.subject for r in queries]);subjects=np.array([r.subject for r in queries]);draws=np.random.default_rng(20261108).integers(0,len(people),(5000,len(people)));denom=np.array([(subjects==p).sum() for p in people]);records=[]
    for record in result['records']:
        condition,level=record['condition'],record['level'];suffix='' if condition=='original' else f'_{condition}_{level}'
        old=ROOT/'outputs/ensaio_oclusoes_2026-11-08/inferencia'/f'confirmacao_congelada_test{suffix}_2026-10-21'
        for name,expected in record['audit']['old_components_sha256'].items():assert sha(old/name)==expected
        components=load_components(old);scores,valid=fuse(components,frozen['component_calibration_red_and_clahe']);baseline={'scores':scores,'valid':valid,'labels':components[0]['labels']}
        path=run/f'{condition}_{level}'/'scores_candidato.npz'
        with np.load(path,allow_pickle=False) as z:candidate={k:z[k].copy() for k in ('scores','valid','labels')}
        np.testing.assert_array_equal(candidate['labels'],baseline['labels']);primary={};secondary={};events={}
        for name,data in (('baseline',baseline),('candidate',candidate)):
            m,c=measured(data,threshold);sm,sc=measured(data,threshold,defined)
            for key in ('rank1','tar','far','joint_success'):assert abs(m[key]-record[name]['metrics'][key])<1e-12
            assert all(c[k]==v for k,v in record[name]['counts'].items() if k in c)
            primary[name]={'metrics':m,'counts':c};secondary[name]={'metrics':sm,'counts':sc}
            _,correct,accepted=metrics(data['scores'],data['labels'],threshold,data['valid']);events[name]=np.column_stack((correct,accepted,correct&accepted)).astype(float)
        delta=events['candidate']-events['baseline'];totals=np.array([delta[subjects==p].sum(0) for p in people]);ci=np.quantile(100*totals[draws].sum(1)/denom[draws].sum(1)[:,None],[.025,.975],axis=0)
        np.testing.assert_allclose(ci,record['descriptive_interval95_pp'],atol=1e-12,rtol=0)
        records.append({'condition':condition,'level':level,'primary':primary,'fixed480':secondary,'paired_gain_pp':(100*delta.mean(0)).tolist(),'descriptive_interval95_pp':ci.tolist(),'candidate_sha256':sha(path)})
    levels=(0,1,5,10,20,30,31);minimum={}
    for name in ('baseline','candidate'):
        minimum[name]={}
        for direction in ('oclusao_superior','oclusao_inferior'):
            values={r['level']:r['primary'][name]['metrics'] for r in records if r['condition'] in ('original',direction)}
            passing=lambda m:m['rank1']>=.9 and m['tar']>=.9 and m['far']<=.01
            prefix=[]
            for level in levels:
                if not passing(values[level]):break
                prefix.append(level)
            minimum[name][direction]={'passing_prefix_loss_percent':prefix,'minimum_retained_percent_on_grid':100-max(prefix) if prefix else None,'joint90_passing_points':[n for n in levels if passing(values[n]) and values[n]['joint_success']>=.9]}
    audit={'all13conditions_and_intervals_recomputed':True,'queries':486,'area_defined_queries':480,'undefined_area_kept_primary':6,'selected_epoch':result['selected_epoch'],
        'comparison_gate_passed':result['comparison_gate_passed'],'minimum':minimum,'records':records,'source_and_selection_unchanged':True,
        'completed_sha256':sha(run/'CONCLUIDO.json'),'source_sha256':sha(__file__),'independent_confirmation':False,'clinical_effect_measured':False,'universal_minimum_claimed':False}
    write(out/'AUDITORIA_FINAL.json',audit)
    os.environ.setdefault('MPLCONFIGDIR',str(Path(os.environ['TEMP'])/'pfc-matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':16})
    fig,axes=plt.subplots(2,1,figsize=(10.08,10.4),sharex=True)
    for direction,color,label in (('oclusao_superior','#b95b00','Superior'),('oclusao_inferior','#075a91','Inferior')):
        selected=[next(r for r in records if r['level']==n and r['condition']==('original' if n==0 else direction)) for n in levels]
        for name,style,marker,title in (('baseline','--','o','referência'),('candidate','-','s','polar adaptado')):
            for ax,key in zip(axes,('rank1','far')):ax.plot(levels,[100*r['primary'][name]['metrics'][key] for r in selected],color=color,linestyle=style,marker=marker,linewidth=2,markersize=5,label=f'{label} — {title}')
    axes[0].axhline(90,color='gray',linestyle=':');axes[1].axhline(1,color='gray',linestyle=':');axes[0].set_ylim(20,100);axes[1].set_ylim(0,4.5);axes[0].set_ylabel('Identificação Rank-1 (%)');axes[1].set_ylabel('Falsas correspondências (%)');axes[1].set_xlabel('Perda do suporte originalmente anotado (%)');axes[1].set_xticks(levels);axes[1].tick_params(axis='x',labelsize=12);axes[0].legend(loc='lower left',ncol=2,fontsize=12,frameon=False)
    for ax in axes:ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
    fig.subplots_adjust(top=.98,bottom=.1,left=.13,right=.98,hspace=.14);fig.savefig(out/'curva_comparacao_polar_sam31.png',dpi=180);plt.close(fig)
    lines=['# Resultado final — polar adaptado à geometria SAM3.1','',f"Época selecionada na validação: {result['selected_epoch']}. Regra completa de comparação aprovada: {result['comparison_gate_passed']}.",'',
        '| Perda | Posição | Versão | Rank-1 | TAR | FMR | Correto e aceito |','|---:|---|---|---:|---:|---:|---:|']
    for r in records:
        for name,z in r['primary'].items():
            m=z['metrics'];lines.append(f"| {r['level']}% | {r['condition']} | {name} | {100*m['rank1']:.2f}% | {100*m['tar']:.2f}% | {100*m['far']:.3f}% | {100*m['joint_success']:.2f}% |")
    lines+=['','A regra de comparação preserva o controle limpo e exige ganho médio conjunto sem aumentar FMR em nenhuma condição. O alvo marginal por ponto (Rank-1/TAR≥90%,FMR≤1%) é informado separadamente do requisito conjunto correto-e-aceito≥90%.','',
        'A referência principal mantém486consultas, incluindo6sem área anotada definida. A coorte fixa de480casos com área definida foi recontada separadamente, sem escolher acertos. Os intervalos são descritivos, por pessoa e galeria fixa; seleção repetida e exposição anterior ao teste impedem chamar o resultado de confirmação independente. Nenhuma área obtida é mínimo universal ou efeito clínico de doença.','',f'Menores suportes nominais na grade, condicionados aos critérios: {json.dumps(minimum,ensure_ascii=False)}.']
    (out/'RESULTADO_PARA_DEFESA.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in audit.items() if k not in ('records','minimum')}))

if __name__=='__main__':main()

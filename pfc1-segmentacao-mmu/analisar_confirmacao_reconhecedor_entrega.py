"""Reconta todos os pontos e produz figura de comparacao exploratoria."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os
import numpy as np
from PIL import Image
from avaliar_candidato_congelado import fuse
from avaliar_robustez_reconhecimento import load_splits,metrics
from treinar_segmentacao_ubipr import decode_mask
from confirmar_reconhecedor_entrega import load_components
from recorte_iris_sam31_alta_res import sha
from rodada_reconhecedor_entrega import write
ROOT=Path(__file__).resolve().parent

def measured(d,threshold,subset=None):
    s=d['scores'];y=d['labels'];v=d['valid']
    if subset is not None:s=s[subset];y=y[subset];v=v[subset]
    m,c,a=metrics(s,y,threshold,v);m['joint_success']=float((c&a).mean())
    imp=np.ones(s.shape,bool);imp[np.arange(len(y)),y]=False
    return m,{'queries':len(y),'correct':int(c.sum()),'accepted':int(a.sum()),'joint':int((c&a).sum()),'false_accepts':int(((s>=threshold)&imp&v[:,None]).sum()),'impostors':int(imp.sum()),'failures':int((~v).sum())}

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args();run=a.run_dir.resolve();out=run/'analise';out.mkdir(exist_ok=True)
    final=json.loads((run/'CONCLUIDO.json').read_text());assert len(final['records'])==13
    protocol=json.loads((run/'protocolo.json').read_text());assert sha(run/'CANDIDATO_CONGELADO.json')==protocol['selection_sha256']
    for name,expected in protocol['dependencies_sha256'].items():assert sha(ROOT/name)==expected
    assert sha(ROOT/'confirmar_reconhecedor_entrega.py')==protocol['source_sha256']
    write(out/'PROTOCOLO_ANALISE.json',{'registered_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sha(__file__),
        'purpose':'Recount all13conditions, report primary all486 and same fixed480area-defined cohort as prior experiment; no candidate/threshold selection; no favorable-case filtering',
        'uncertainty':'Stored descriptive paired person bootstrap,5000draws,seed20261108,fixedgallery; repeated development/test exposure and multiple comparisons limit inference'})
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());queries=[r for r in load_splits(manifest)['test'] if r.session==2]
    defined=np.array([bool((decode_mask(Image.open(r.mask))==1).any()) for r in queries]);assert len(defined)==486 and defined.sum()==480
    frozen=json.loads((ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json').read_text());threshold=frozen['frozen_threshold'];records=[]
    original_root=ROOT/'outputs/ensaio_oclusoes_2026-11-08'
    for record in final['records']:
        condition,level=record['condition'],record['level'];suffix='' if condition=='original' else f'_{condition}_{level}'
        old=original_root/'inferencia'/f'confirmacao_congelada_test{suffix}_2026-10-21'
        for name,expected in record['audit']['old_components_sha256'].items():assert sha(old/name)==expected
        components=load_components(old);scores,valid=fuse(components,frozen['component_calibration_red_and_clahe']);labels=components[0]['labels']
        baseline={'scores':scores,'valid':valid,'labels':labels}
        path=run/f'{condition}_{level}'/'scores_candidato.npz'
        with np.load(path,allow_pickle=False) as z:candidate={k:z[k].copy() for k in ('scores','labels','valid')}
        np.testing.assert_array_equal(labels,candidate['labels']);recount={};secondary={}
        for name,data in (('baseline',baseline),('candidate',candidate)):
            m,c=measured(data,threshold)
            for key in ('rank1','tar','far','joint_success'):assert abs(m[key]-record[name]['metrics'][key])<1e-12
            assert all(c[k]==v for k,v in record[name]['counts'].items() if k in c)
            recount[name]={'metrics':m,'counts':c};sm,sc=measured(data,threshold,defined);secondary[name]={'metrics':sm,'counts':sc}
        records.append({'condition':condition,'level':level,'recounted':recount,'fixed_area_defined480':secondary,
            'paired_gain_pp':record['paired_gain_pp'],'descriptive_interval95_pp':record['descriptive_interval95_pp'],'candidate_scores_sha256':sha(path)})
    levels=(0,1,5,10,20,30,31);minimum={}
    def passes(m):return m['rank1']>=.9 and m['tar']>=.9 and m['far']<=.01
    for name in ('baseline','candidate'):
        minimum[name]={}
        for direction in ('oclusao_superior','oclusao_inferior'):
            bylevel={r['level']:r['recounted'][name]['metrics'] for r in records if r['condition']==direction or r['condition']=='original'}
            prefix=[]
            for level in levels:
                if not passes(bylevel[level]):break
                prefix.append(level)
            minimum[name][direction]={'passing_prefix_loss_percent':prefix,'minimum_retained_percent_on_registered_grid':100-max(prefix) if prefix else None,
                'all_grid_points_meeting_marginal_criteria':[level for level in levels if passes(bylevel[level])],
                'joint90_also_required_passing_points':[level for level in levels if passes(bylevel[level]) and bylevel[level]['joint_success']>=.9]}
    audit={'all13conditions_recounted':True,'candidate_selection_and_sources_unchanged':True,'primary_queries':486,'area_defined_queries':480,
        'empty_reference_queries_retained_primary':6,'comparison_gate_passed':final['comparison_gate_passed'],'minimum':minimum,'records':records,
        'comparison_sha256':sha(run/'CONCLUIDO.json'),'analyst_sha256':sha(__file__),'independent_confirmation':False,'clinical_effect_measured':False,'universal_minimum_claimed':False}
    write(out/'AUDITORIA_FINAL.json',audit)
    os.environ.setdefault('MPLCONFIGDIR',str(Path(os.environ['TEMP'])/'pfc-matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12})
    fig,axes=plt.subplots(2,1,figsize=(10.08,10.4),sharex=True)
    for direction,color,label in (('oclusao_superior','#b95b00','Superior'),('oclusao_inferior','#075a91','Inferior')):
        selected=[next(r for r in records if r['level']==level and r['condition']==('original' if level==0 else direction)) for level in levels]
        for name,style,marker,version in (('baseline','--','o','referência'),('candidate','-','s','candidato')):
            for ax,key in zip(axes,('rank1','far')):
                values=[100*r['recounted'][name]['metrics'][key] for r in selected]
                ax.plot(levels,values,color=color,linestyle=style,marker=marker,linewidth=2,markersize=5,label=f'{label} — {version}',alpha=.75 if name=='baseline' else 1)
    axes[0].axhline(90,color='#555555',linestyle=':',linewidth=1);axes[1].axhline(1,color='#555555',linestyle=':',linewidth=1)
    axes[0].set_ylabel('Identificação Rank-1 (%)');axes[0].set_ylim(20,100)
    axes[1].set_ylabel('Falsas correspondências (%)');axes[1].set_xlabel('Perda do suporte originalmente anotado (%)');axes[1].set_ylim(0,4.5)
    axes[1].set_xticks(levels);axes[0].legend(loc='lower left',ncol=2,fontsize=10,frameon=False)
    for ax in axes:ax.grid(alpha=.22);ax.spines[['top','right']].set_visible(False)
    fig.subplots_adjust(top=.98,bottom=.09,left=.12,right=.98,hspace=.13)
    fig.savefig(out/'curva_comparacao_reconhecedor.png',dpi=180);plt.close(fig)
    lines=['# Resultado para a defesa — melhoria do reconhecedor','',
        'O contorno contínuo foi aplicado somente aos descritores polares; os quatro descritores RGB mantiveram a entrada anterior. A escolha ocorreu na validação, antes da nova inferência. O ajuste supervisionado de cinco épocas não passou pela regra registrada e manteve a época zero.','',
        '| Perda | Posição | Versão | Rank-1 | TAR | FMR | Correto e aceito |','|---:|---|---|---:|---:|---:|---:|']
    for r in records:
        for name,z in r['recounted'].items():
            m=z['metrics'];lines.append(f"| {r['level']}% | {r['condition']} | {name} | {100*m['rank1']:.2f}% | {100*m['tar']:.2f}% | {100*m['far']:.3f}% | {100*m['joint_success']:.2f}% |")
    lines+=['','## Alcance do resultado','',
        f"Regra completa de comparação aprovada: **{'sim' if final['comparison_gate_passed'] else 'não'}**. Essa regra exigia preservar o controle limpo, melhorar a média conjunta e não aumentar a FMR em nenhuma condição. Melhoras pontuais não equivalem à superioridade geral.",'',
        'Critérios marginais por ponto: Rank-1≥90%,TAR≥90%,FMR≤1%. Na grade registrada:']
    for name,r in minimum.items():
        for direction,z in r.items():lines.append(f"- {name}/{direction}: menor suporte nominal no prefixo aprovado = {z['minimum_retained_percent_on_registered_grid']}%; perdas aprovadas no prefixo = {z['passing_prefix_loss_percent']}.")
    lines+=['','O percentual é condicionado à grade, reconhecedor, limiar, galeria e suporte originalmente anotado. O critério conjunto correto-e-aceito≥90% é diferente e está auditado separadamente. As486consultas incluem6referências de área vazia, mantidas no denominador primário; a coorte fixa de480casos com área definida também foi recontada, sem selecionar acertos. Nenhum desses percentuais é mínimo universal, medida de doença ou conformidade ISO.','',
        'A coluna de ganho pareado e os intervalos descritivos por pessoa estão em AUDITORIA_FINAL.json. Há seleção na validação e exposição prévia ao teste; não se trata de confirmação independente. Nenhum checkpoint do aplicativo ou resultado anterior foi substituído.']
    (out/'RESULTADO_PARA_DEFESA.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'conditions':13,'queries':486,'area_defined':480,'comparison_gate_passed':final['comparison_gate_passed'],'minimum':minimum}),flush=True)

if __name__=='__main__':main()

"""Consolida rodada exploratoria e distingue distribuicoes condicionais do minimo global."""
from pathlib import Path
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent

def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as stream: return list(csv.DictReader(stream))

def main():
    from relatar_validacao_hdbif import cluster_interval
    new=ROOT/'outputs/area_encoder_ubipr_2026-10-20'
    initial=ROOT/'outputs/biometria_area_completa_2026-10-20'
    conditional=ROOT/'outputs/tolerancia_condicional_exploratoria_2026-10-20'
    if not (new/'CONCLUIDO.json').exists() or not (conditional/'CONCLUIDO.json').exists(): raise RuntimeError('Experiments incomplete')
    out=ROOT/'outputs/consolidacao_biometria_2026-10-20'
    result=json.loads((new/'area_minima.json').read_text(encoding='utf-8'))
    protocol=json.loads((new/'protocolo.json').read_text(encoding='utf-8'))
    queries=[r for r in read_csv(initial/'manifesto_auditado.csv') if r['split']=='test' and r['session']=='2']
    subjects=np.array([r['subject'] for r in queries])
    with np.load(new/'scores_original.npz') as saved:
        scores=saved['scores']; labels=saved['labels']; valid=saved['valid']; correct=saved['correct']; accepted=saved['accepted']
    impostor=np.ones_like(scores,dtype=bool); impostor[np.arange(len(labels)),labels]=False
    false_per_query=((scores>=protocol['threshold']) & valid[:,None] & impostor).sum(axis=1)/(scores.shape[1]-1)
    intervals={name:cluster_interval(value,subjects) for name,value in [('rank1',correct),('tar',accepted),('fmr',false_per_query),('joint_identification',correct&accepted)]}
    rows=read_csv(conditional/'consultas.csv'); histograms=[]
    for model in sorted({r['model'] for r in rows}):
        for kind in ('oclusao_superior','oclusao_inferior'):
            subset=[r for r in rows if r['model']==model and r['orientation']==kind]
            defined=[int(r['minimum_tested_preserved_percent']) for r in subset if r['minimum_tested_preserved_percent']]
            histograms.append({'model':model,'orientation':kind,'all_queries':len(subset),'eligible_queries':len(defined),
                'people_with_eligible_queries':len({r['subject'] for r in subset if r['minimum_tested_preserved_percent']}),
                'smallest_tested_fraction_histogram':{str(p):defined.count(p) for p in range(10,101,10)}})
    (out/'segunda_rodada_ic95.json').write_text(json.dumps({'conditional_fixed_model_ci95':intervals,
        'casewise_histograms':histograms,'note':'Interpolated medians such as95% are not tested levels; global minimum remains undefined'},indent=2),encoding='utf-8')
    old_rows=[r for r in read_csv(initial/'resumo.csv') if r['branch']=='iris_referencia']
    new_rows=read_csv(new/'resumo.csv')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(11,7.8),sharex=True,sharey=True)
    for line,(kind,label) in enumerate([('oclusao_superior','Oclusão superior'),('oclusao_inferior','Oclusão inferior')]):
        for col,(metric,title) in enumerate([('rank1','Rank-1'),('tar','TAR')]):
            ax=axes[line,col]
            for data,name,color in [(old_rows,'DINOv3 referência','#c05d25'),(new_rows,'Encoder treinado referência','#156082')]:
                selected=sorted([r for r in data if r['condition'] in ('original',kind)],key=lambda r:100-int(r['level']))
                ax.plot([100-int(r['level']) for r in selected],[100*float(r[metric]) for r in selected],'o-',label=name,color=color,markersize=4)
            ax.axhline(90,color='#777',linestyle='--',linewidth=.8); ax.set_ylim(0,100); ax.set_xlim(10,100)
            ax.set_title(label+' — '+title); ax.set_xlabel('Área preservada alvo na referência (%)'); ax.set_ylabel('Consultas (%)'); ax.grid(alpha=.18)
    fig.suptitle('Comparação exploratória entre configurações de reconhecimento',fontsize=14)
    fig.legend(*axes[0,0].get_legend_handles_labels(),loc='lower center',ncol=2,frameon=False)
    fig.text(.5,.045,'Mesmo UBIPr · 486 consultas · 32 olhos na galeria · teste previamente examinado · limiares de validação',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.08,1,.95))
    fig.savefig(out/'comparacao_encoder_treinado.png',dpi=220); fig.savefig(out/'comparacao_encoder_treinado.svg'); plt.close(fig)
    retention=read_csv(conditional/'retencao.csv')
    selected=[r for r in retention if r['model']=='Encoder_treinado']
    fig,ax=plt.subplots(figsize=(9,5))
    for kind,name,color in [('oclusao_superior','Superior','#156082'),('oclusao_inferior','Inferior','#c05d25')]:
        data=sorted([r for r in selected if r['orientation']==kind],key=lambda r:int(r['preserved_percent']))
        x=[int(r['preserved_percent']) for r in data]+[100]
        ax.plot(x,[100*float(r['conditional_retention']) for r in data]+[100],'o-',label=name,color=color)
        ax.fill_between(x,[100*float(r['ci95_low']) for r in data]+[100],[100*float(r['ci95_high']) for r in data]+[100],color=color,alpha=.12)
    ax.set_xlim(10,100); ax.set_ylim(0,100); ax.grid(alpha=.18); ax.legend(frameon=False)
    ax.set_xlabel('Área preservada alvo (%)'); ax.set_ylabel('Identificações originais mantidas (%)')
    ax.set_title('Retenção entre 234 consultas originalmente identificadas')
    fig.text(.5,.02,'Análise condicional exploratória · selecionadas de 486 consultas · não representa mínimo global',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.07,1,1)); fig.savefig(out/'retencao_condicional_encoder.png',dpi=220); fig.savefig(out/'retencao_condicional_encoder.svg'); plt.close(fig)
    text=['# Segunda rodada exploratória concluída','',
        'O encoder ResNet18 com margem angular foi treinado em 183 pessoas e 366 classes de olho. O treinamento terminou na época 23; o checkpoint foi selecionado na época15, somente pela validação. O teste UBIPr já havia sido examinado na rodada DINOv3; esta comparação é exploratória.','',
        '| Medida no original | Estimativa | IC 95% condicional por pessoa |','|---|---:|---:|']
    for name,field in [('rank1','rank1'),('tar','tar'),('fmr','far')]:
        lo,hi=intervals[name]; text.append(f"| {name.upper()} | {100*result['baseline'][field]:.2f}% | {100*lo:.2f}% a {100*hi:.2f}% |")
    text+=['','Foram concluídas as 19 condições. O mínimo global segue **não determinado** pelo critério registrado de90% de Rank-1 e TAR. A configuração treinada e a referência DINOv3 diferem em arquitetura, treinamento e resolução; o resultado não isola causalmente apenas a margem angular.','',
        '## Diagnóstico por consulta','',
        '234 das486 consultas foram identificadas corretamente e com escore genuíno acima do limiar no original. Com90% da área preservada, mantiveram o sucesso117 dessas234 sob oclusão superior (50%) e115 sob oclusão inferior (49,15%). As demais consultas originalmente não identificadas continuam exportadas como mínimo indefinido.','',
        'Os valores por consulta indicam a menor fração **testada** que passa em todos os níveis maiores. Um resultado100% significa que nenhum nível com oclusão testado satisfaz a regra; não prova que uma perda entre1% e9% seja inviável. A mediana interpolada95% presente no JSON estatístico não é um nível efetivamente testado. Usar a tabela por níveis e os histogramas, sem anunciá-la como mínimo validado.','',
        '## Nuclear Cataract','',
        'A preparação foi interrompida após revisão de oito exemplos de calibração e antes de qualquer escore de reconhecimento. Várias máscaras eram fragmentos sem recorte confiável da íris. Os dados foram preservados; os protocolos e códigos registrados permanecem arquivados. A ausência de avaliação não permite afirmar falha biométrica de toda a base, apenas inadequação do pipeline atual para prosseguir.','',
        'Os resultados não estabelecem causalidade de doença nem um mínimo universal. As figuras e os dados auxiliares estão nesta pasta e em `tolerancia_condicional_exploratoria_2026-10-20`.']
    content='\n'.join(text)+'\n'
    for before,after in [('época15','época 15'),('de90%','de 90%'),('das486','das 486'),('Com90%','Com 90%'),
                         ('sucesso117','sucesso 117'),('dessas234','dessas 234'),('e115','e 115'),
                         ('resultado100%','resultado 100%'),('entre1%','entre 1%'),('e9%','e 9%'),('interpolada95%','interpolada 95%')]:
        content=content.replace(before,after)
    (out/'SEGUNDA_RODADA.md').write_text(content,encoding='utf-8')
    print(json.dumps({'completed':True,'baseline':result['baseline'],'ci95':intervals},indent=2))

if __name__=='__main__': main()

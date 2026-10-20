"""Consolida experimentos concluidos e gera figuras, sem novas inferencias."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
NAMES={'inteira':'Imagem inteira','iris_referencia':'Íris: referência','iris_unet':'Íris: U-Net'}
COLORS={'inteira':'#156082','iris_referencia':'#c05d25','iris_unet':'#6f4d96'}

def main():
    folder=ROOT/'outputs/biometria_area_completa_2026-10-20'
    clinical=ROOT/'outputs/hdbif_slpvld_teste_congelado_2026-10-20'
    if not (folder/'CONCLUIDO.json').exists() or not (clinical/'CONCLUIDO.json').exists(): raise RuntimeError('Experiments incomplete')
    with (folder/'resumo.csv').open(encoding='utf-8-sig',newline='') as stream: rows=list(csv.DictReader(stream))
    protocol=json.loads((folder/'protocolo.json').read_text(encoding='utf-8'))
    report=json.loads((clinical/'resultado.json').read_text(encoding='utf-8'))
    out=ROOT/'outputs/consolidacao_biometria_2026-10-20'; out.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    coverage_audit=[]
    for kind,level in protocol['conditions']:
        if kind=='original': continue
        with np.load(folder/f'embeddings_test_{kind}_{level}.npz') as saved:
            defined=saved['iris_referencia_valid']; coverage=saved['coverage']
        coverage_audit.append({'condition':kind,'occluded_target_percent':level,'queries_total':len(coverage),
            'queries_with_defined_reference_area':int(defined.sum()),'empty_reference_masks':int((~defined).sum()),
            'affected_mean_defined_masks':float(coverage[defined].mean()),
            'affected_min_defined_masks':float(coverage[defined].min()),
            'affected_max_defined_masks':float(coverage[defined].max()),
            'affected_mean_including_zero_placeholders':float(coverage.mean())})
    with (out/'cobertura_auditada.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(coverage_audit[0])); writer.writeheader(); writer.writerows(coverage_audit)
    fig,axes=plt.subplots(2,2,figsize=(11,7.8),sharex=True,sharey=True)
    for line,(kind,label) in enumerate([('oclusao_superior','Oclusão superior'),('oclusao_inferior','Oclusão inferior')]):
        for col,(metric,title) in enumerate([('rank1','Identificação Rank-1'),('tar','Verificação TAR')]):
            ax=axes[line,col]
            for branch in protocol['branches']:
                data=[r for r in rows if r['branch']==branch and r['condition'] in ('original',kind)]
                data.sort(key=lambda r:100-int(r['level']))
                ax.plot([100-int(r['level']) for r in data],[100*float(r[metric]) for r in data],
                        'o-',label=NAMES[branch],color=COLORS[branch],markersize=4)
            ax.axhline(90,color='#777',linestyle='--',linewidth=.8)
            ax.set_title(label+' — '+title); ax.set_ylim(0,100); ax.set_xlim(10,100)
            ax.set_xticks(range(10,101,10)); ax.grid(alpha=.18); ax.set_ylabel('Consultas (%)')
            ax.set_xlabel('Área preservada alvo na íris anotada (%)')
    fig.legend(*axes[0,0].get_legend_handles_labels(),loc='lower center',ncol=3,frameon=False)
    fig.suptitle('UBIPr: perda controlada de área e reconhecimento com DINOv3',fontsize=14)
    fig.text(.5,.045,'486 consultas · 16 pessoas · galeria fixa de 32 olhos · linha tracejada: critério exploratório de 90%',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.075,1,.95))
    fig.savefig(out/'curvas_area_preservada.png',dpi=220); fig.savefig(out/'curvas_area_preservada.svg'); plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(11,7.8),sharex=True)
    for line,(kind,label) in enumerate([('oclusao_superior','Oclusão superior'),('oclusao_inferior','Oclusão inferior')]):
        for col,(metric,low,high,title) in enumerate([('loss_rank1_pp','ci_low_pp','ci_high_pp','Perda de Rank-1'),
                                                    ('loss_tar_pp','tar_ci_low_pp','tar_ci_high_pp','Perda de TAR')]):
            ax=axes[line,col]
            for branch in protocol['branches']:
                data=[r for r in rows if r['branch']==branch and r['condition'] in ('original',kind)]
                data.sort(key=lambda r:100-int(r['level']))
                x=[100-int(r['level']) for r in data]
                ax.plot(x,[float(r[metric]) for r in data],'o-',color=COLORS[branch],label=NAMES[branch],markersize=4)
                ax.fill_between(x,[float(r[low]) for r in data],[float(r[high]) for r in data],color=COLORS[branch],alpha=.12)
            ax.axhline(0,color='#777',linewidth=.8); ax.grid(alpha=.18)
            ax.set_title(label+' — '+title); ax.set_xlabel('Área preservada alvo (%)'); ax.set_ylabel('Perda em pontos percentuais')
            ax.set_xlim(10,100)
    fig.legend(*axes[0,0].get_legend_handles_labels(),loc='lower center',ncol=3,frameon=False)
    fig.suptitle('UBIPr: perdas pareadas em relação à condição original',fontsize=14)
    fig.text(.5,.045,'Faixas: IC 95% por 5.000 reamostragens de pessoas · galeria fixa · perdas negativas indicam aumento observado',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.075,1,.95))
    fig.savefig(out/'perdas_pareadas_ic95.png',dpi=220); fig.savefig(out/'perdas_pareadas_ic95.svg'); plt.close(fig)
    with np.load(clinical/'scores.npz') as saved:
        scores=saved['scores']; labels=saved['labels']; valid=saved['valid']; correct=saved['correct']; accepted=saved['accepted']
    audits=json.loads((clinical/'auditoria.json').read_text(encoding='utf-8'))
    # Audit order is identical to score construction. These diagnostics are post hoc.
    ids=sorted({(r['subject'],r['side']) for r in audits})
    enrollments=[next(r for r in audits if (r['subject'],r['side'])==eye and r['role']=='gallery') for eye in ids]
    wrong_scores=scores.copy(); wrong_scores[np.arange(len(labels)),labels]=-2
    false_above=(wrong_scores>=report['threshold']) & valid[:,None]
    winner=scores.argmax(axis=1)
    mistaken=[int(((winner==i)&(~correct)&valid).sum()) for i in range(len(ids))]
    top=sorted(range(len(ids)),key=lambda i:mistaken[i],reverse=True)[:10]
    diagnostics={'status':'post_hoc_descriptive_only_no_test_tuning',
        'joint_correct_rank1_and_genuine_accepted':float((correct & accepted).mean()),
        'queries_with_any_impostor_above_threshold':float(false_above.any(axis=1).mean()),
        'note':'TAR is pairwise genuine acceptance; not thresholded identification accuracy. This is not open-set FPIR.',
        'most_frequent_wrong_gallery_winners':[{'image':enrollments[i]['image'],
            'wrong_rank1_queries':mistaken[i],'predicted_valid_polar_fraction':enrollments[i]['valid_polar_fraction']} for i in top]}
    (out/'diagnostico_pos_hoc_teste.json').write_text(json.dumps(diagnostics,indent=2),encoding='utf-8')
    selected=diagnostics['most_frequent_wrong_gallery_winners'][:5]
    fig,ax=plt.subplots(figsize=(10,4.5))
    names=[r['image'].replace('.JPG','') for r in selected]
    bars=ax.barh(names[::-1],[r['wrong_rank1_queries'] for r in selected][::-1],color='#156082')
    for bar,row in zip(bars,selected[::-1]):
        ax.text(bar.get_width()+1,bar.get_y()+bar.get_height()/2,
                f"{row['wrong_rank1_queries']} consultas | polar válido previsto: {100*row['predicted_valid_polar_fraction']:.2f}%",va='center',fontsize=9)
    ax.set_xlim(0,235); ax.set_xlabel('Consultas em que o cadastro foi o candidato errado de maior escore')
    ax.set_title('HDBIF: cinco cadastros que mais concentraram erros no teste')
    fig.text(.5,.02,'Análise posterior e seletiva de falhas; área prevista não é referência clínica. Nenhum caso foi excluído.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.07,1,1))
    fig.savefig(out/'diagnostico_cadastros_pouca_area.png',dpi=200); fig.savefig(out/'diagnostico_cadastros_pouca_area.svg'); plt.close(fig)
    original=[r for r in rows if r['condition']=='original']
    lines=['# Resultados concluídos — rodada inicial','',
        'Todos os números abaixo são novos experimentos. Os pilotos técnicos não entram nas estimativas finais. A segunda rodada de treinamento de identidade é separada.','',
        '## Segmentação UBIPr','',
        'Treinamento: 30 épocas; checkpoint escolhido na época 26, apenas pela validação. Dice de teste da íris: **0,9342**; Dice médio de primeiro plano: **0,8944**.','',
        '## Reconhecimento DINOv3 sem oclusão','',
        '486 consultas de 16 pessoas, galeria de 32 olhos. Limiar por ramo calibrado na validação.','',
        '| Entrada | Rank-1 | TAR | FMR de teste |','|---|---:|---:|---:|']
    for r in original: lines.append(f"| {NAMES[r['branch']]} | {100*float(r['rank1']):.2f}% | {100*float(r['tar']):.2f}% | {100*float(r['far']):.2f}% |")
    lines+=['','Foram concluídas 19 condições e 57 combinações de condição e entrada. **Mínimo não determinado** em todos os ramos pelo critério registrado, porque a condição original não alcança Rank-1 e TAR de 90%. Isso não demonstra que a íris seja inutilizável para outros reconhecedores.','',
        'Os níveis descrevem a fração alvo da máscara anotada, apenas quando ela existe. Seis consultas têm referência de íris vazia; a média da cobertura em todas as consultas inclui esses zeros. Esse detalhe não deve ser interpretado como oclusão clínica medida.','',
        '## Reconhecimento HDBIF no teste clínico','',
        '319 consultas, 107 pessoas e galeria de 176 olhos. Reconhecedor e limiar congelados na validação.','',
        f"Rank-1: **{100*report['metrics']['rank1']:.2f}%**; TAR: **{100*report['metrics']['tar']:.2f}%**; FMR: **{100*report['metrics']['far']:.2f}%**.",
        '', 'IC 95% condicional por pessoa: Rank-1 11,01–21,45%; TAR 43,00–58,95%; FMR 1,95–3,02%.',
        '', 'A galeria clínica de teste é maior que a de validação (176 contra 60 olhos). Não atribuir a diferença de Rank-1 exclusivamente a doença ou a sobreajuste. A FMR pairwise também mudou de distribuição e excedeu o alvo da validação.',
        '',f"Diagnóstico descritivo posterior: Rank-1 correto e genuíno acima do limiar simultaneamente em {100*diagnostics['joint_correct_rank1_and_genuine_accepted']:.2f}% das consultas. TAR isolada não mede identificação correta entre todos os candidatos.",
        '', 'Há 10 imagens com falha, três cadastros com falha e 2.582 comparações indisponíveis. Foram mantidos no protocolo e nos denominadores. Não houve ajustes no teste. As análises posteriores de qualidade não autorizam seleção retrospectiva de casos.',
        '', '## Artefatos','',
        '`curvas_area_preservada.png` e `.svg`: figura das curvas completas; `diagnostico_pos_hoc_teste.json`: diagnóstico exploratório de identificação e candidatos errados. Os relatórios originais permanecem nas pastas de cada execução.']
    (out/'RESULTADOS_CONCLUIDOS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'consolidated':str(out),'post_hoc_diagnostics':diagnostics},indent=2),flush=True)

if __name__=='__main__': main()

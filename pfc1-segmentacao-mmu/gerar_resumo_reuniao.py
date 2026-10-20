"""Gera painel da reunião a partir das curvas concluídas, sem novos experimentos."""
from pathlib import Path
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / 'Relatórios-de-Avanço'

def main():
    with (ROOT/'outputs/area_encoder_ubipr_2026-10-20/resumo.csv').open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':11, 'axes.spines.top':False, 'axes.spines.right':False})
    fig = plt.figure(figsize=(15,9), facecolor='#f5f7fa')
    fig.suptitle('TCC · Avanço em 20/10/2026', fontsize=24, fontweight='bold', x=.055, ha='left', y=.97)
    fig.text(.055,.915,'Objetivo: medir a perda de reconhecimento ao reduzir a região visível da íris.',fontsize=14)
    ax = fig.add_axes([.055,.40,.48,.43], facecolor='white')
    for kind,label,color in [('oclusao_superior','Oclusão superior','#146b91'),('oclusao_inferior','Oclusão inferior','#d16b30')]:
        data = sorted([r for r in rows if r['condition'] in ('original',kind)], key=lambda r:100-int(r['level']))
        ax.plot([100-int(r['level']) for r in data], [100*float(r['rank1']) for r in data], 'o-', label=label, color=color, linewidth=2)
    ax.axhline(90, color='#8b3643', linestyle='--', label='Critério global: 90%')
    ax.set(xlim=(10,100),ylim=(0,100),xlabel='Área anotada preservada (%)',ylabel='Identificação correta · Rank-1 (%)',title='Extrator treinado · 486 consultas / 32 olhos')
    ax.grid(alpha=.15); ax.legend(loc='upper left', fontsize=10)
    info = fig.add_axes([.59,.38,.36,.47]); info.axis('off')
    blocks = [
        ('SEGMENTAÇÃO RETREINADA','Dice da íris: 0,9342 no teste\nU-Net · 30 épocas · seleção na validação'),
        ('RECONHECIMENTO SEM OCLUSÃO ADICIONAL','Rank-1: 67,90%  |  TAR: 55,14%\nFMR: 0,96% · UBIPr · análise exploratória'),
        ('TESTE CLÍNICO · SLP-VLD','319 consultas · 107 pessoas · 176 olhos\nRank-1: 15,99%  |  TAR: 50,78%  |  FMR: 2,45%'),
        ('OCULTAR 10% DA REGIÃO ANOTADA','Entre 234 consultas identificadas no original:\n117 mantidas (superior); 115 (inferior).')]
    for i,(title,body) in enumerate(blocks):
        y=1-i*.25
        info.text(0,y,title,weight='bold',color='#146b91',fontsize=11,va='top')
        info.text(0,y-.065,body,fontsize=11,va='top',linespacing=1.6)
    fig.text(.055,.245,'Conclusão: o percentual mínimo global ainda não foi determinado.',fontsize=18,weight='bold',color='#8b3643')
    fig.text(.055,.19,'O desempenho original ficou abaixo de 90% de Rank-1 e TAR. A curva mede área anotada visível, não a íris anatômica total.',fontsize=11)
    fig.text(.055,.145,'Limitações: teste UBIPr já examinado; seguimento exploratório. Oclusão simulada não demonstra efeito causal de doença.',fontsize=11)
    fig.text(.055,.10,'Entregas: treinamentos e 19 condições concluídos · 18 testes automatizados aprovados · resultados e pesos preservados.',fontsize=11)
    fig.text(.055,.055,'Próximos passos: alinhar conclusões com o orientador, revisar referências e diagramar o artigo para 09/11.',fontsize=11)
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT/'RESULTADOS_REUNIAO_2026-10-20.png', dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)

if __name__ == '__main__':
    main()

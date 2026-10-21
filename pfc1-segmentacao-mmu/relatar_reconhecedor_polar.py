"""Consolida resultados positivos e negativos sem selecionar escores de teste."""
from pathlib import Path
import csv,json
import numpy as np
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs/tripletiris_elipse_validacao_2026-10-20'

def main():
    from avaliar_robustez_reconhecimento import load_splits,paired_ci
    folders=[ROOT/'outputs/tripletiris_validacao_2026-10-20',OUT]
    summaries=[json.loads((p/'CONCLUIDO.json').read_text()) for p in folders]
    assert all(not s['technical_smoke'] and s['counts']['queries']==482 for s in summaries)
    allresults=[r for s in summaries for r in s['results']];assert len(allresults)==15
    with (OUT/'resumo_completo.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(allresults[0]));writer.writeheader();writer.writerows(allresults)
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val'];subjects=np.array([r.subject for r in rows if r.session==2])
    comparisons=[]
    for kind in ('reference','automatic'):
        name='roi_'+kind
        with np.load(folders[0]/(name+'_top3.npz')) as z:a={k:z[k] for k in z.files}
        with np.load(OUT/(name+'_ellipse_top3.npz')) as z:b={k:z[k] for k in z.files}
        np.testing.assert_array_equal(a['labels'],b['labels'])
        comparisons.append({'variant':kind,'ellipse_minus_circular_gain_pp':{key:100*(b[value].mean()-a[value].mean()) for key,value in [('rank1','correct'),('tar','accepted')]},
            'gain_ci95_pp':{key:paired_ci(b[value],a[value],subjects) for key,value in [('rank1','correct'),('tar','accepted')]}})
    audits=json.loads((OUT/'auditoria.json').read_text());geometry={}
    for kind in ('roi_reference_ellipse','roi_automatic_ellipse'):
        selected=[r for r in audits if r['variant']==kind]
        geometry[kind]={'images':len(selected),'failed_images':sum(not r['valid'] for r in selected),
            'hole_pupil':sum(r['geometry'] is not None and r['geometry']['pupil_source']=='largest_enclosed_mask_hole' for r in selected),
            'regressor_pupil_fallback':sum(r['geometry'] is not None and r['geometry']['pupil_source']=='circle_regressor_fallback' for r in selected)}
    (OUT/'comparacoes_pareadas.json').write_text(json.dumps({'comparisons':comparisons,'geometry_audit':geometry,'note':'Development only; pointwise5000 person-cluster bootstrap, fixed gallery and validation-calibrated thresholds; no selection bias correction'},indent=2),encoding='utf-8')
    lines=['# Reconhecedor polar e aproximação elíptica — 20/10/2026','',
        '## 1. Trabalho concluído','',
        'Foram baixados e verificados 12 arquivos de fontes oficiais do CVRL TripletIris e dois pesos públicos, somando aproximadamente 162,5 MB. Foi instalado um novo reconhecedor polar ConvNeXt-tiny de 2.048 dimensões, com o regressor de círculos 1543 previsto pelos autores. Não foi alterado o ambiente de dependências nem retreinado esse reconhecedor.','',
        'O piloto verificou o pipeline e a comparação euclidiana contra o código original em 16 pares, com erro máximo de similaridade de aproximadamente 1,4 × 10⁻¹⁶. Depois foram executadas nove variantes completas com limites circulares e seis com aproximação elíptica. Cada variante inclui 482 consultas de 16 pessoas e 32 olhos, com até 480 capturas de cadastro da sessão 1. Nenhum novo escore de teste ou oclusão foi produzido.','',
        '## 2. Todos os resultados de validação','',
        '| Variante | Rank-1 | TAR | FMR | Falhas de consulta |','|---|---:|---:|---:|---:|']
    for r in allresults:
        fmt=lambda key:f"{100*r[key]:.2f}%".replace('.',',')
        lines.append(f"| {r['variant']} | {fmt('rank1')} | {fmt('tar')} | {fmt('far')} | {r['extraction_failures']} |")
    lines+=['','As regras first, max e top3 representam foto única, maior similaridade e média das três melhores similaridades. Cada variante tem limiar recalibrado para FMR empírica de até 1% na própria validação. Full_author segue o canal vermelho e a conversão de imagem do demonstrador; ROI localiza o recorte pela referência ou U-Net. As máscaras não removem a textura externa da faixa polar.','',
        '## 3. Decisão e interpretação','',
        'O maior Rank-1 TripletIris foi **41,49%**, com **11,62% de TAR**, na imagem inteira com cadastro top-3. A maior TAR entre as variantes foi **13,90%**, com **25,93% de Rank-1**, no recorte de referência com uma foto. Não combinar esses máximos de variantes diferentes como se fossem um único resultado.','',
        'No recorte automático top-3, o TripletIris circular obteve **38,59% de Rank-1 e 12,86% de TAR**. Com a aproximação elíptica, obteve **28,42% e 9,54%**. A hipótese geométrica não melhorou o reconhecimento nesta configuração. Os intervalos pareados dessas diferenças estão registrados separadamente.','',
        'O encoder anterior com máscaras automáticas top-3 havia obtido 67,01% de Rank-1 e 59,34% de TAR no controle multicaptura. Seu modelo continua preservado. O novo reconhecedor e a aproximação elíptica **não foram adotados como substitutos**. Isso é uma comparação de sistemas completos: modelo, pré-treinamento, canal, normalização e amostragem mudam, portanto não se isola uma única causa. Não se pode concluir que todo reconhecedor específico de íris ou toda normalização polar seja inferior.','',
        'A inspeção visual mostrou melhor acompanhamento do contorno segmentado em alguns exemplos com elipses, mas esses contornos incluem os limites da região visível, e não necessariamente as bordas anatômicas ocultas. Há fallback para pupila regredida quando a máscara não tem um orifício interno válido. O amostrador elíptico também difere do código circular oficial. Melhor aparência de um recorte não substitui a avaliação de identidade.','',
        'Não foi estabelecida independência entre as populações de pré-treinamento dos pesos públicos e o UBIPr. A validação já foi usada repetidamente no desenvolvimento local. As estimativas orientam investigação; não confirmam generalização independente nem estabelecem causa clínica.','',
        '## 4. Área mínima e direção técnica','',
        'Nenhuma variante atingiu simultaneamente 90% de Rank-1 e TAR. O mínimo global segue **não determinado**. A normalização ou o encaixe da máscara não fornecem, isoladamente, um percentual anatômico suficiente. Não foi recalculada a curva de oclusão com um reconhecedor ainda abaixo do critério original.','',
        'Esta rodada não sustenta substituir o encoder nem prolongar uma busca por variantes na mesma validação como se cada escolha fosse confirmação nova. Um próximo experimento precisa de hipótese de domínio e representação própria, como treinamento em uma faixa polar adequada às capturas visíveis, com protocolo e avaliação independente definidos antes da confirmação. A coleta de mais níveis de oclusão, por si só, não resolve o desempenho original.','',
        '## 5. Verificação e artefatos','',
        'Os 32 testes automatizados passaram. Os três novos testes geométricos verificam ângulos, anel sintético com pupila, fallback e máscara vazia. Fontes, pesos, protocolos, escores e imagens foram preservados. Exemplos visuais são os dois primeiros cadastros de cada variante, sem seleção por escore; não equivalem a auditoria manual completa de todas as capturas.','',
        '- [Protocolo e reprodução](../../PROTOCOLO_RECONHECEDOR_POLAR_2026-10-20.md).',
        '- [Resultados circulares](../tripletiris_validacao_2026-10-20/CONCLUIDO.json).',
        '- [Resultados elípticos](CONCLUIDO.json).',
        '- [Tabela completa](resumo_completo.csv).',
        '- [Comparações pareadas e auditoria geométrica](comparacoes_pareadas.json).','',
        '![Limites aproximados e faixas polares — exemplos reais](qa_polar_tripletiris.png)','',
        'Fonte do modelo: [CVRL OpenSourceIrisRecognition](https://github.com/CVRL/OpenSourceIrisRecognition), revisão fixada no protocolo.','']
    (OUT/'RELATORIO_RECONHECEDOR_POLAR.md').write_text('\n'.join(lines),encoding='utf-8')
    print('15 variants and geometry audit consolidated; no model replacement.')

if __name__=='__main__':main()

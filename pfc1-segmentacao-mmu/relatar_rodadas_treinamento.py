"""Resumo das duas hipoteses, incluindo modelos iniciais preservados."""
from pathlib import Path
import csv,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parent

def main():
    folders=['identidade_automatica_2026-10-20','identidade_metrica_automatica_2026-10-20']
    results=[]
    for name in folders:
        path=ROOT/'outputs'/name
        result=json.loads((path/'CONCLUIDO.json').read_text())
        with (path/'historico.csv').open(encoding='utf-8',newline='') as f:history=list(csv.DictReader(f))
        best=next(r for r in history if int(r['epoch'])==result['best_epoch'])
        results.append((name,result,history[0],best))
    with np.load(ROOT/'outputs'/folders[0]/'scores_baseline.npz') as z:a={k:z[k] for k in z.files}
    with np.load(ROOT/'outputs'/folders[1]/'scores_baseline.npz') as z:b={k:z[k] for k in z.files}
    for key in a:np.testing.assert_array_equal(a[key],b[key])
    lines=['# Novas rodadas de treinamento — 20/10/2026','',
        '## Execuções e objetivo','',
        'Foram concluídas duas tentativas controladas de adaptar o encoder à segmentação automática, sem nova inferência de teste ou oclusão. As duas começaram dos pesos anteriores de identidade e reutilizaram os mesmos recortes da U-Net congelada. Treino: 183 pessoas e 366 classes de olho, com 7.645 imagens após rejeitar 71 máscaras previstas vazias. Validação: 16 pessoas, 32 olhos, 480 capturas de cadastro e 482 consultas; quatro falhas de consulta permanecem no denominador.','',
        'A primeira tentativa ajustou o encoder e a cabeça angular em recortes automáticos. A segunda acrescentou perda triplet batch-hard e lotes com 16 olhos distintos e quatro capturas por olho, para aproximar capturas da mesma identidade e afastar identidades diferentes. Os hiperparâmetros e os hashes foram registrados antes de cada execução. Nenhuma máscara de referência foi usada para corrigir os recortes.','',
        '## Resultados selecionados','',
        '| Rodada | Épocas de ajuste | Época selecionada | Rank-1 | TAR | FMR |',
        '|---|---:|---:|---:|---:|---:|']
    for i,(name,result,baseline,best) in enumerate(results):
        label='Adaptação angular simples' if i==0 else 'Angular + triplet balanceado'
        fmt=lambda key:f"{100*float(best[key]):.2f}%".replace('.',',')
        lines.append(f"| {label} | {result['epochs_completed']} | {result['best_epoch']} | {fmt('rank1')} | {fmt('tar')} | {fmt('far')} |")
    both_initial=all(r[1]['best_epoch']==0 for r in results)
    lines+=['',
        '**As duas tentativas mantiveram a época zero: não houve ganho pelo critério registrado. Os parâmetros do modelo anterior foram preservados.**' if both_initial else 'A escolha manteve a maior TAR, com desempate por Rank-1, incluindo os pesos iniciais como época zero.',
        '',
        'O critério de escolha é a TAR no alvo empírico de FMR de até 1%, com desempate por Rank-1. Ele não escolhe uma época apenas porque o Rank-1 isolado sobe. As perdas de treino caíram, mas isso não constitui melhora de reconhecimento em pessoas diferentes. Não adotamos uma época pior em TAR nem reduzimos o critério de 90% para anunciar sucesso.','',
        'Os escores da época zero das duas execuções foram conferidos e são idênticos. A referência desta rodada é 66,80% de Rank-1, 59,34% de TAR e 0,99% de FMR. O controle multicaptura anterior tinha 67,01% de Rank-1: houve uma decisão Rank-1 diferente, sem mudança de validade das consultas, após mudar os lotes da segmentação e do encoder. Essa diferença não foi atribuída causalmente a um único componente nem tratada como ganho ou perda de treinamento.','',
        '## O que o resultado indica','',
        'As hipóteses de adaptação simples e da combinação angular/triplet testada não trouxeram ganho de TAR nesta validação. Isso não prova que todo treinamento métrico seja ineficaz, mas não sustenta continuar aumentando épocas nessas configurações. A época zero foi incluída para impedir a adoção automática de um ajuste sem melhora no critério principal.','',
        'A próxima hipótese deve mudar a representação ou o método de reconhecimento de forma fundamentada: por exemplo, um modelo específico de íris com normalização polar adequada, após controle da geometria. Antes de confirmar qualquer ganho, é necessário definir uma avaliação independente; as mesmas pessoas de validação já foram utilizadas repetidamente para escolher ajustes e checkpoints.','',
        'O mínimo global de área permanece **não determinado**. Ainda faltam 23,20 pp de Rank-1 e 30,66 pp de TAR para 90% no original desta rodada. Nenhuma nova curva de oclusão foi calculada. O percentual de suporte polar de experimentos anteriores é um filtro de qualidade do template, não um mínimo de área anatômica.','',
        '## Verificações e artefatos','',
        'Vinte e nove testes automatizados passaram, incluindo retenção de falhas, composição dos lotes balanceados e comportamento/gradientes da perda triplet. O piloto técnico foi mantido separado. Código, histórico, parâmetros selecionados e escores de cada rodada foram preservados.','',
        '- [Protocolo de adaptação e aprendizagem métrica](../../PROTOCOLO_ADAPTACAO_AUTOMATICA_2026-10-20.md).',
        '- [Histórico da adaptação simples](../identidade_automatica_2026-10-20/historico.csv).',
        '- [Relatório detalhado da adaptação simples](../identidade_automatica_2026-10-20/RELATORIO_ADAPTACAO.md).',
        '- [Histórico angular/triplet](historico.csv).',
        '- [Protocolo angular/triplet com hashes](protocolo.json).','',
        '![Primeiros oito recortes automáticos não vazios de treino, antes das ampliações aleatórias](../identidade_automatica_2026-10-20/qa_entradas_treino.png)','']
    path=ROOT/'outputs'/folders[1]/'RELATORIO_TREINAMENTOS.md'
    path.write_text('\n'.join(lines),encoding='utf-8')
    print('Training summary written; identical epoch0 scores checked.')

if __name__=='__main__':main()

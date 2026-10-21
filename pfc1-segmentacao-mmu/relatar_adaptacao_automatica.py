"""Relata ajuste com mascaras automaticas e compara com epoca zero pareada."""
from pathlib import Path
import csv,json
import numpy as np
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs/identidade_automatica_2026-10-20'

def main():
    from avaliar_robustez_reconhecimento import load_splits,paired_ci
    result=json.loads((OUT/'CONCLUIDO.json').read_text())
    if result['technical_smoke']:raise ValueError('Technical pilot is not scientific result')
    with (OUT/'historico.csv').open(encoding='utf-8',newline='') as f:history=list(csv.DictReader(f))
    baseline=history[0];best=next(r for r in history if int(r['epoch'])==result['best_epoch'])
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val'];subjects=np.array([r.subject for r in rows if r.session==2])
    with np.load(OUT/'scores_baseline.npz') as z:a={k:z[k] for k in z.files}
    with np.load(OUT/'scores_melhor.npz') as z:b={k:z[k] for k in z.files}
    np.testing.assert_array_equal(a['labels'],b['labels']);np.testing.assert_array_equal(a['valid'],b['valid']);assert len(subjects)==482
    intervals={key:paired_ci(b[field],a[field],subjects) for key,field in [('rank1','correct'),('tar','accepted')]}
    comparison={'baseline':baseline,'best':best,'gain_pp':{key:100*(float(best[key])-float(baseline[key])) for key in ('rank1','tar')},
        'gain_ci95_pp':intervals,'note':'Conditional person-cluster 5000 bootstrap, fixed gallery and checkpoint-specific validation thresholds; checkpoint selected on same validation, so exploratory and selection-biased, not independent confirmation'}
    (OUT/'comparacao_pareada.json').write_text(json.dumps(comparison,indent=2),encoding='utf-8')
    lines=['# Adaptação ao recorte automático — 20/10/2026','',
        '## 1. Treinamento executado','',
        f'Foi concluído um ajuste do encoder anterior em recortes produzidos exclusivamente pela U-Net congelada. O treinamento usou 7.716 imagens de 183 pessoas e 366 classes de olho antes da exclusão de máscaras previstas vazias. Foram executadas {result["epochs_completed"]} épocas de ajuste, com seleção da época {result["best_epoch"]}. A época zero contém os pesos anteriores, permitindo conservar o modelo inicial caso não haja melhora pelo critério registrado.','',
        'Os parâmetros atualizados são do encoder e da cabeça angular; a U-Net não foi retreinada. A cabeça foi inicializada do checkpoint anterior, com a mesma ordem das classes. Foram usados AdamW, taxas de aprendizado de 0,00003 para encoder e 0,0001 para cabeça, margem angular 0,3, batch 64 e semente 43. As ampliações de treino incluem rotação e brilho/contraste, sem oclusão artificial.','',
        '## 2. Comparação no original','',
        'As 482 consultas pertencem a 16 pessoas distintas das pessoas de treino; a galeria contém as capturas da sessão 1 de 32 olhos. A comparação usa média das três melhores correspondências por olho. O limiar é recalibrado na validação para cada checkpoint, com FMR empírica de até 1%. As mesmas máscaras automáticas, consultas e capturas de cadastro são usadas na época zero e no modelo selecionado.','',
        '| Configuração | Rank-1 | TAR | FMR | Identificação e aceitação conjuntas | Falhas de consulta |','|---|---:|---:|---:|---:|---:|']
    for label,r in [('Modelo anterior, época zero',baseline),(f'Modelo selecionado, época {result["best_epoch"]}',best)]:
        fmt=lambda key:f"{100*float(r[key]):.2f}%".replace('.',',')
        lines.append(f"| {label} | {fmt('rank1')} | {fmt('tar')} | {fmt('far')} | {fmt('joint_success')} | {r['extraction_failures']} |")
    lines+=['','A época selecionada foi zero: a adaptação simples não superou a TAR inicial e os parâmetros anteriores foram mantidos.' if result['best_epoch']==0 else 'A seleção manteve o checkpoint com maior TAR na validação, com desempate por Rank-1.','',
        'Os intervalos de ganho são condicionais à galeria e aos modelos escolhidos. Como o mesmo conjunto selecionou o checkpoint, eles não corrigem o viés de seleção e não devem ser interpretados como confirmação independente.','']
    for key in ('rank1','tar'):
        lo,hi=intervals[key];lines.append(f'- {key.upper()}: ganho de {comparison["gain_pp"][key]:.2f} pp; IC 95% pontual {lo:.2f} a {hi:.2f} pp.')
    lines+=['','## 3. Limites e mínimo de área','',
        'Essa validação já foi utilizada repetidamente no desenvolvimento, inclusive para selecionar o checkpoint inicial. A melhora ou ausência de melhora deve ser descrita como exploratória. As imagens de teste e as bases clínicas não receberam nova inferência. A validação mede reconhecimento com máscaras automáticas, mas não prova que o encoder use exclusivamente textura anatômica de íris: erros de máscara podem incluir contexto externo.','',
        'O limiar biométrico pode mudar com o checkpoint; por isso a TAR compara os sistemas calibrados no mesmo alvo, não uma única escala absoluta de similaridade. Nenhum ganho pode ser atribuído somente à máscara: o ajuste muda os pesos e a distribuição de treino.','',
        f'No modelo selecionado, faltam {max(0,90-100*float(best["rank1"])):.2f} pp de Rank-1 e {max(0,90-100*float(best["tar"])):.2f} pp de TAR para o critério operacional de 90%. Essa distância não é uma previsão de épocas necessárias. Sem alcançar e confirmar o desempenho original, não se estabelece uma área mínima global. Não foi produzida nova curva de oclusão nesta rodada.','',
        '## 4. Auditoria e reprodução','',
        'Os recortes foram produzidos em lotes de 32 pela U-Net em FP32; o encoder foi avaliado em lotes de 128, em vez dos 64 anteriores. Frente ao controle anterior, as identidades e a validade das consultas foram idênticas, houve uma decisão Rank-1 diferente e duas decisões de aceitação diferentes nos respectivos limiares. A maior diferença absoluta de escore foi 0,02443. As duas mudanças de lote não foram isoladas causalmente. A época zero desta execução é a referência pareada principal, sem atribuir essas diferenças a treinamento. Máscaras vazias são excluídas só do treino e permanecem como falhas na validação.','',
        'Vinte e seis testes automatizados passaram, incluindo controles de retenção de falhas e de cadastro sem máscara. O piloto técnico ficou separado das estimativas científicas. Pesos anteriores, novos pesos selecionados, protocolo, histórico, auditoria e escores foram preservados.','',
        '- [Protocolo de adaptação](../../PROTOCOLO_ADAPTACAO_AUTOMATICA_2026-10-20.md).',
        '- [Registro e hashes](protocolo.json).',
        '- [Histórico completo](historico.csv).',
        '- [Conclusão da execução](CONCLUIDO.json).',
        '- [Comparação e intervalos](comparacao_pareada.json).','']
    (OUT/'RELATORIO_ADAPTACAO.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'best_epoch':result['best_epoch'],'baseline_rank1':float(baseline['rank1']),'baseline_tar':float(baseline['tar']),'selected_rank1':float(best['rank1']),'selected_tar':float(best['tar']),'gain_pp':comparison['gain_pp']},indent=2))

if __name__=='__main__':main()

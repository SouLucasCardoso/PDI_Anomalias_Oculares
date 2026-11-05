"""Observador da cabeca residual; reutiliza auditoria registrada dos escores."""
import time
from pathlib import Path

import analisar_sam3_area as core
import analisar_sam3_negativos_internos as sensitivity

ROOT = Path(__file__).resolve().parent
BASE = ROOT / 'outputs/sam31_residual_2026-11-05'
FLOW = BASE / 'fluxo'


def render_once():
    core.BASE, core.OUT, core.FLOW = BASE, BASE / 'analise_area', FLOW
    core.FILES = ('analisar_sam3_residual.py', 'analisar_sam3_area.py',
                  'analisar_sam3_negativos_internos.py', 'analisar_rodada_segmentacao_area.py',
                  'avaliar_prontidao_anomalias.py', 'analisar_sensibilidade_referencia_area.py')
    core.render()
    sensitivity.BASE, sensitivity.FLOW = BASE, FLOW
    sens = sensitivity.sensitivity()
    file = BASE / 'analise_area/RELATORIO_ATUAL.md'
    lines = [file.read_text(encoding='utf-8'),
             '\n\nEnsaio de 05/11: correção residual com 32 canais; adaptador-base selecionado na época 15 e extrator SAM3.1 congelados, incluindo as estatísticas BatchNorm do controle.',
             'A cabeça de saída começa em zero e preserva os logits do controle na inicialização. A correção é limitada a ±4 por logit. Somente a cabeça de correção recebe gradientes.',
             'Até 24 épocas, lotes de 8 e parada após 6 épocas sem ganho elegível. Perda original CE/Dice/Tversky; a penalização extra de negativos internos reprovada na rodada anterior não é usada.',
             'São reutilizados os 22.040 mapas fechados, com hash a cada leitura. Época zero é medida novamente nas quatro condições; não é inferida a partir do teste curto.',
             'Nenhuma referência clínica ou imagem de teste seleciona pesos. Os controles originais de identidade serão reutilizados após auditoria; o novo candidato usa cache exclusivo.',
             'A sensibilidade mantém todas as 482 consultas na análise principal; 472 têm referência de área definida. Não foi alterado o limiar de reconhecimento.']
    if (FLOW / 'CONCLUIDO.json').exists() and not core.read(FLOW / 'CONCLUIDO.json')['new_candidate_evaluated']:
        lines += ['**Rodada encerrada sem ganho de correção selecionado. Não houve nova avaliação de reconhecimento ou mínimo de área.**']
    if sens['conservative_minimum_annotated_visible_percent'] is not None:
        lines += [f"Mínimo conservador nos prefixos completos registrados: {sens['conservative_minimum_annotated_visible_percent']}% da área visível anotada."]
    temporary = file.with_suffix('.md.part')
    temporary.write_text('\n\n'.join(lines) + '\n', encoding='utf-8')
    temporary.replace(file)


def render():
    for attempt in range(8):
        try:
            render_once()
            return
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(.5)


if __name__ == '__main__':
    render()

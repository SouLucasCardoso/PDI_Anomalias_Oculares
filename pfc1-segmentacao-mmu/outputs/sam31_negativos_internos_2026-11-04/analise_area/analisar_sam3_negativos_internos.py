"""Observador versionado da continuacao com negativos internos; nao faz inferencia."""
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np

import analisar_sam3_area as core
from analisar_rodada_segmentacao_area import validation_queries
from analisar_sensibilidade_referencia_area import stratify

ROOT = Path(__file__).resolve().parent
BASE = ROOT / 'outputs/sam31_negativos_internos_2026-11-04'
FLOW = BASE / 'fluxo'


def configure():
    core.BASE, core.OUT, core.FLOW = BASE, BASE / 'analise_area', FLOW
    core.FILES = ('analisar_sam3_negativos_internos.py', 'analisar_sam3_area.py',
                  'analisar_rodada_segmentacao_area.py', 'avaliar_prontidao_anomalias.py',
                  'analisar_sensibilidade_referencia_area.py')


def sensitivity():
    flow = core.read(FLOW / 'protocolo_fluxo.json')
    cohort_file = FLOW / 'consultas.json'
    if core.sha(cohort_file) != flow['cohort_sha256']:
        raise ValueError('Coorte de area alterada')
    cohort = core.read(cohort_file)
    queries, _, labels = validation_queries(core.read(ROOT / 'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'))
    if [Path(r['image']).name for r in queries] != [r['image'] for r in cohort]:
        raise ValueError('Ordem da coorte divergente')
    areas = np.array([r['reference_iris_pixels'] for r in cohort], dtype=np.int64)
    criteria = core.read(ROOT / 'criterios_prontidao_anomalias.json')['identification_study']
    audit = core.read(BASE / 'analise_area/AUDITORIA.json')
    records, defined = {}, {}
    for row in audit['records']:
        if row['segmenter'] != 'novo':
            continue
        evidence = BASE / 'identidade/evidencias' / row['key'] / 'scores_finais.npz'
        with np.load(evidence, allow_pickle=False) as saved:
            np.testing.assert_array_equal(saved['labels'], labels)
            values = stratify(saved['scores'], labels, saved['valid'], areas, audit['threshold'], criteria)
        records[row['key']] = values
        defined[('novo', row['condition'], row['loss_percent'])] = values['defined_reference']
    frontier = core.area_frontier(defined, flow['area_loss_grid'])
    primary = audit['frontier']
    minimum = None
    if primary['minimum_assigned'] and frontier['minimum_assigned']:
        minimum = max(primary['orientations']['both_orientations']['minimum_on_complete_grid_percent'],
                      frontier['orientations']['both_orientations']['minimum_on_complete_grid_percent'])
    result = {'registered_strata_before_new_scores': True, 'all_queries': len(areas),
              'defined_reference': int((areas > 0).sum()), 'undefined_reference': int((areas == 0).sum()),
              'records': records, 'defined_frontier': frontier,
              'conservative_minimum_annotated_visible_percent': minimum,
              'undefined_reference_has_no_area_fraction': True, 'test_inference': False}
    core.write(BASE / 'analise_area/SENSIBILIDADE.json', result)
    return result


def render():
    configure()
    core.render()
    sens = sensitivity()
    file = BASE / 'analise_area/RELATORIO_ATUAL.md'
    text = file.read_text(encoding='utf-8')
    detail = ['\n\nContinuação de 04/11: pesos da época15 anterior; até12 épocas adicionais, com parada após4 sem ganho.',
              'A perda adicional pesa pixels já anotados como não íris dentro de contornos fechados de íris. Não constitui anotação independente de pupila.',
              'Os22.040 mapas anteriores são reutilizados com seus hashes; não há nova extração de mapas neste treino.',
              'Os três controles originais de reconhecimento serão reutilizados após auditoria dos escores, fontes e ambiente. As inferências do novo candidato terão cache exclusivo.',
              'A seleção usa apenas segmentação nas quatro condições. As metas de identificação e o limiar congelado permanecem registrados.',
              'Sensibilidade registrada:472 referências de área definidas e10 indefinidas; todas482 permanecem na análise principal.']
    if (FLOW / 'CONCLUIDO.json').exists():
        result = core.read(FLOW / 'CONCLUIDO.json')
        if not result['new_candidate_evaluated']:
            detail += ['**Rodada encerrada sem ganho selecionado: época0 manteve os pesos anteriores. Não foi executada nova identificação ou grade de área.**']
    if sens['conservative_minimum_annotated_visible_percent'] is not None:
        detail += [f"Mínimo conservador nos dois prefixos registrados: **{sens['conservative_minimum_annotated_visible_percent']}%** da área visível anotada."]
    if (FLOW / 'ERRO.json').exists() and not (FLOW / 'CONCLUIDO.json').exists():
        detail += ['Há um erro registrado em fluxo/ERRO.json; consultar os logs e o estado da tarefa.']
    tmp = file.with_suffix('.md.part')
    tmp.write_text(text + '\n\n'.join(detail) + '\n', encoding='utf-8')
    tmp.replace(file)
    return (FLOW / 'CONCLUIDO.json').exists()


if __name__ == '__main__':
    render()

"""Observador da rodada SAM3: progresso, escores auditados e area; sem inferencia."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

import numpy as np

from analisar_rodada_segmentacao_area import measure, paired_difference, validation_queries
from avaliar_prontidao_anomalias import identity_gate

ROOT = Path(__file__).resolve().parent
BASE = ROOT / 'outputs/sam31_iris_adaptacao_2026-11-03'
OUT = BASE / 'analise_area'
FLOW = ROOT / 'outputs/prontidao_anomalias_2026-11-03'
MODES = {'clean': 'Original', 'zoom3': 'Zoom 3×', 'oblique': 'Oblíqua', 'glasses': 'Óculos'}
ORIENTATIONS = ('oclusao_superior', 'oclusao_inferior')
FILES = ('analisar_sam3_area.py', 'acompanhar_analise_sam3_area.py',
         'analisar_rodada_segmentacao_area.py', 'avaliar_prontidao_anomalias.py')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    temporary = path.with_suffix(path.suffix + '.part')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    temporary.replace(path)


def register():
    OUT.mkdir(exist_ok=True)
    training = read(BASE / 'protocolo.json')
    flow = read(FLOW / 'protocolo_fluxo.json')
    for sources in (training['frozen']['sources'], flow['sources']):
        for name, expected in sources.items():
            if sha(ROOT / name) != expected:
                raise ValueError('Fonte da rodada mudou: ' + name)
    binding = {
        'sources': {name: sha(ROOT / name) for name in FILES},
        'training_protocol_sha256': sha(BASE / 'protocolo.json'),
        'flow_protocol_sha256': sha(FLOW / 'protocolo_fluxo.json'),
        'frozen_configuration_sha256': sha(ROOT / 'outputs/candidato_congelado_2026-10-21/CONGELADO.json'),
        'criteria_sha256': sha(ROOT / 'criterios_prontidao_anomalias.json'),
        'numpy_version': importlib.metadata.version('numpy'),
    }
    if (OUT / 'protocolo.json').exists():
        if read(OUT / 'protocolo.json')['binding'] != binding:
            raise ValueError('Preservar o observador registrado antes de mudar fontes/ambiente')
    else:
        write(OUT / 'protocolo.json', {
            'registered_utc': datetime.now(timezone.utc).isoformat(), 'binding': binding,
            'scope': 'Observational only; no training, inference, selection, recalibration or test access',
            'bootstrap': {'replicates': 5000, 'seed': 127, 'cluster': 'query person', 'gallery': 'fixed'},
            'intervals': 'Pointwise descriptive; not simultaneous certification of the area frontier',
            'manual_clinical_references_required_for_ubipr_area': False,
            'minimum_rule': 'Full registered grid, initial consecutive passing prefix, both orientations; no interpolation',
        })
        for name in FILES:
            (OUT / name).write_bytes((ROOT / name).read_bytes())
    return training, flow


def intervention_area(rows, condition, loss, query_names):
    """Verifica todos os denominadores e o arredondamento exato dos pixels alterados."""
    if condition == 'original':
        if rows:
            raise ValueError('Condicao original com intervencoes')
        return None
    if condition not in ORIENTATIONS or not 0 < loss < 100:
        raise ValueError('Intervencao fora do protocolo')
    if len(rows) != len(query_names) or {r['image'] for r in rows} != set(query_names):
        raise ValueError('Consultas ausentes/duplicadas nas intervencoes')
    retained = []
    for row in rows:
        n = row['reference_pixels']
        if not isinstance(n, int) or n < 0 or bool(n) != row['fraction_defined']:
            raise ValueError('Denominador de area invalido')
        expected = round(n * loss / 100) / n if n else 0.
        if not np.isclose(row['affected_fraction'], expected, rtol=0, atol=1e-14):
            raise ValueError('Intervencao nao corresponde ao numero registrado de pixels')
        if n:
            retained.append(100 * (1 - expected))
    return {'nominal_retained_percent': 100 - loss, 'defined_queries': len(retained),
            'undefined_queries_retained_in_identity': len(rows) - len(retained),
            'actual_retained_percent_min_mean_max':
            [float(np.min(retained)), float(np.mean(retained)), float(np.max(retained))] if retained else None}


def area_frontier(records, losses):
    clean = records.get(('novo', 'original', 0))
    if clean is None or not clean['passed']:
        return {'clean_gate_passed': bool(clean and clean['passed']),
                'grid_complete': False, 'minimum_assigned': False, 'orientations': {}}
    results = {}
    decisions = []
    for orientation in ORIENTATIONS:
        passed = [True] + [records.get(('novo', orientation, loss), {}).get('passed') for loss in losses[1:]]
        decisions.append(passed)
        results[orientation] = passed
    results['both_orientations'] = [a and b if a is not None and b is not None else None
                                    for a, b in zip(*decisions)]
    complete = all(v is not None for sequence in decisions for v in sequence)
    frontier = {}
    for name, sequence in results.items():
        minimum = 100
        for loss, passed in zip(losses, sequence):
            if passed is not True:
                break
            minimum = 100 - loss
        frontier[name] = {'passed_by_registered_loss': sequence,
                          'minimum_on_complete_grid_percent': minimum if complete else None}
    return {'clean_gate_passed': True, 'grid_complete': complete,
            'minimum_assigned': complete, 'orientations': frontier}


def audit_identity(training, flow):
    directory = BASE / 'identidade'
    paths = sorted(directory.glob('novo_*.json')) + sorted(directory.glob('original_*.json'))
    if not paths:
        if (OUT / 'AUDITORIA.json').exists() and read(OUT / 'AUDITORIA.json')['records']:
            raise ValueError('Os resultados auditados desapareceram')
        return {'records': [], 'paired_comparisons': [], 'frontier': area_frontier({}, flow['area_loss_grid'])}
    final = read(BASE / 'CONCLUIDO.json')
    if final['development_smoke_only']:
        raise ValueError('Smoke nao fornece candidato para a analise')
    candidate = final['checkpoint_sha256']
    if sha(BASE / f'candidato_epoca_{final["best_epoch"]:02}.pt') != candidate:
        raise ValueError('Checkpoint final divergente')
    manifest = ROOT / 'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    if sha(manifest) != training['frozen']['manifest_sha256']:
        raise ValueError('Manifesto alterado')
    queries, people, labels = validation_queries(read(manifest))
    if (len(queries), len(people)) != (482, 16):
        raise ValueError('Populacao diferente das 482 consultas/16 pessoas')
    subjects = np.array([r['subject'] for r in queries])
    names = [Path(r['image']).name for r in queries]
    frozen = read(ROOT / 'outputs/candidato_congelado_2026-10-21/CONGELADO.json')
    criteria = read(ROOT / 'criterios_prontidao_anomalias.json')['identification_study']
    threshold = frozen['frozen_threshold']
    records, indexed, vectors = [], {}, {}
    previous = read(OUT / 'AUDITORIA.json') if (OUT / 'AUDITORIA.json').exists() else {'records': []}
    old_hashes = {r['key']: r['evidence_sha256'] for r in previous['records']}
    for path in paths:
        row = read(path)
        custom = path.stem.startswith('novo_')
        condition, loss = row['condition'], row['loss_percent']
        if path.stem != ('novo' if custom else 'original') + '_' + condition + '_' + str(loss):
            raise ValueError('Nome e condicao divergentes')
        if condition == 'original' and loss != 0 or condition != 'original' and loss not in flow['area_loss_grid'][1:]:
            raise ValueError('Nivel fora da grade registrada')
        expected_candidate = candidate if custom else None
        evidence = directory / 'evidencias' / path.stem
        files = ('scores_finais.npz', 'protocolo.json', 'ADAPTADOR_SAM3.json', 'interventions.json', 'source.py')
        hashes = {name: sha(evidence / name) for name in files}
        if path.stem in old_hashes and hashes != old_hashes[path.stem]:
            raise ValueError('Evidencia mudou depois da primeira auditoria')
        protocol, adapter = read(evidence / 'protocolo.json'), read(evidence / 'ADAPTADOR_SAM3.json')
        if row['checkpoint_sha256'] != expected_candidate or adapter['candidate_sha256'] != expected_candidate:
            raise ValueError('Resultado de outro candidato')
        for name, checksum in adapter['sources'].items():
            if flow['sources'].get(name) != checksum:
                raise ValueError('Resultado de outra implementacao')
        if adapter['versions'] != flow['versions']:
            raise ValueError('Controles de ambientes diferentes')
        expected_unet = candidate if custom else '2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
        if (protocol['split'] != 'val' or protocol['fixed_geometry_diagnostic'] or
                protocol['queries'] != 482 or protocol['candidates'] != 16 or
                protocol['condition'] != condition or protocol['occluded_percent'] != loss or
                protocol['unet_sha256'] != expected_unet or protocol['threshold'] != threshold or
                protocol['frozen_sha256'] != sha(ROOT / 'outputs/candidato_congelado_2026-10-21/CONGELADO.json') or
                hashes['source.py'] != flow['sources']['avaliar_candidato_congelado.py']):
            raise ValueError('Protocolo de identidade divergente')
        with np.load(evidence / 'scores_finais.npz', allow_pickle=False) as saved:
            np.testing.assert_array_equal(saved['labels'], labels)
            if saved['scores'].shape != (482, 16):
                raise ValueError('Matriz com dimensoes incorretas')
            counts, rates, _, per_query = measure(saved['scores'], labels, saved['valid'], threshold)
            np.testing.assert_array_equal(saved['correct'], per_query['rank1'])
            np.testing.assert_array_equal(saved['accepted'], per_query['tar'])
        passed = identity_gate(counts, criteria)
        if counts != row['counts'] or rates != row['rates'] or passed != row['passed_new_readiness_criterion']:
            raise ValueError('Contagens ou decisao divergentes')
        actual_area = intervention_area(read(evidence / 'interventions.json'), condition, loss, names)
        intervals = {metric: paired_difference(np.zeros(len(queries)), values, subjects)['interval95_cluster_person_pp']
                     for metric, values in per_query.items()}
        record = {'key': path.stem, 'segmenter': 'novo' if custom else 'original',
                  'condition': condition, 'loss_percent': loss, 'counts': counts, 'rates': rates,
                  'passed': passed, 'interval95_cluster_person_pp': intervals,
                  'evidence_sha256': hashes, 'actual_area': actual_area}
        key = (record['segmenter'], condition, loss)
        if key in indexed:
            raise ValueError('Registro duplicado')
        indexed[key], vectors[key] = record, per_query
        records.append(record)
    comparisons = []
    for condition, level in (('original', 0), ('oclusao_superior', 10), ('oclusao_inferior', 10)):
        old, new = ('original', condition, level), ('novo', condition, level)
        if old in vectors and new in vectors:
            comparisons.append({'condition': condition, 'loss_percent': level,
                                'paired': {m: paired_difference(vectors[old][m], vectors[new][m], subjects)
                                           for m in vectors[old]}})
    frontier = area_frontier(indexed, flow['area_loss_grid'])
    complete_file = directory / 'CONCLUIDO.json'
    if complete_file.exists():
        completed = read(complete_file)
        if completed['checkpoint_sha256'] != candidate or completed['minimum_assigned'] != frontier['minimum_assigned']:
            raise ValueError('Conclusao do fluxo diverge dos escores')
        for name, result in completed['frontier'].items():
            checked = frontier['orientations'][name]
            if (result['passed'] != checked['passed_by_registered_loss'] or
                    result['nominal_visible_area_on_registered_prefix'] != checked['minimum_on_complete_grid_percent']):
                raise ValueError('Fronteira do fluxo divergente')
    if set(old_hashes) - {r['key'] for r in records}:
        raise ValueError('Um resultado auditado desapareceu')
    return {'queries': 482, 'people': 16, 'threshold': threshold, 'checkpoint_sha256': candidate,
            'records': records, 'paired_comparisons': comparisons, 'frontier': frontier,
            'all_failures_retained': True, 'validation_reused_not_blind': True}


def render():
    training, flow = register()
    run = Path(training['frozen']['configuration']['run'])
    progress = read(run / 'progresso.json') if (run / 'progresso.json').exists() else {}
    status = read(run / 'status.json') if (run / 'status.json').exists() else {}
    final = read(BASE / 'CONCLUIDO.json') if (BASE / 'CONCLUIDO.json').exists() else None
    audit = audit_identity(training, flow)
    write(OUT / 'AUDITORIA.json', audit)
    lines = ['# SAM3.1 — treino, reconhecimento e área', '',
             'Atualizado em ' + datetime.now(timezone.utc).isoformat() + ' (UTC).', '',
             '**As revisões clínicas podem ser feitas depois; não são requisito para esta curva UBIPr.**', '',
             'O extrator visual SAM3.1 é congelado; o decodificador RGB+SAM3 recebe treino supervisionado.', '']
    stage = progress.get('stage', status.get('stage', 'pending'))
    if status.get('stage') == 'failed':
        lines += ['**Execução interrompida:** ' + status.get('error', 'conferir log'), '']
    elif final:
        lines += [f"Treino concluído. Candidato selecionado: **época {final['best_epoch']}**.", '']
        if final['best_epoch'] == 0:
            lines += ['A época zero foi selecionada: não houve ganho selecionado com a adaptação supervisionada.', '']
    elif stage == 'sam3_cache':
        n, total = progress['completed'], progress['total']
        lines += [f'Preparação dos mapas SAM3: **{n:,}/{total:,} ({100*n/total:.1f}%)**.'.replace(',', '.'), '',
                  'Depois desta etapa, o decodificador fará até 20 épocas. Ainda não há novo resultado de identificação.', '']
    else:
        lines += [f"Etapa atual: **{stage}**; época {status.get('epoch', '—')}, lote {progress.get('batch', '—')}/{progress.get('batches', '—')}.", '']
    histories = []
    for file in sorted(BASE.glob('validacao_epoca_*.json')):
        data = read(file)
        histories.append({'epoch': int(file.stem.rsplit('_', 1)[1]),
                          'dice': {m: data[m]['macro_dice'] for m in MODES}})
    if histories:
        lines += ['| Época | Original | Zoom 3× | Oblíqua | Óculos |', '|---:|---:|---:|---:|---:|']
        for row in histories:
            lines.append('| ' + str(row['epoch']) + ' | ' + ' | '.join(f'{100*row["dice"][m]:.2f}%' for m in MODES) + ' |')
        lines += ['', 'Todas as condições usam as 1.652 imagens de validação. A seleção consulta somente segmentação.', '']
    records = audit['records']
    if records:
        lines += ['| Modelo/condição/perda | Rank-1 | TAR | Correto e aceito | FMR | Falhas | Critério |',
                  '|---|---:|---:|---:|---:|---:|---|']
        for row in records:
            r, c = row['rates'], row['counts']
            lines.append(f"| {row['segmenter']} / {row['condition']} / {row['loss_percent']}% | {100*r['rank1']:.2f}% | {100*r['tar']:.2f}% | {100*r['joint']:.2f}% | {100*r['fmr']:.3f}% | {c['extraction_failures']} | {'Passou' if row['passed'] else 'Não passou'} |")
        lines += ['', 'Critério novo: Rank-1, TAR e acerto aceito simultâneo ≥90%; FMR ≤1%, comparados por contagens inteiras.', '']
    frontier = audit['frontier']
    if frontier['minimum_assigned']:
        lines += ['Menor área nominal aprovada no prefixo completo da grade:', '']
        for name, result in frontier['orientations'].items():
            lines.append(f"- {name}: {result['minimum_on_complete_grid_percent']}% da íris visível originalmente anotada.")
    elif not frontier['clean_gate_passed'] and any(r['key'] == 'novo_original_0' for r in records):
        lines += ['**Candidato reprovado sem oclusão. Nenhum novo mínimo foi atribuído.**']
    else:
        lines += ['**Ainda não há percentual mínimo novo:** aguardar identificação sem oclusão e a grade completa das duas orientações.']
    lines += ['', 'Os intervalos descritivos de 95%, com 5.000 reamostragens por pessoa e galeria fixa, estão em [AUDITORIA.json](AUDITORIA.json). Não são uma garantia simultânea da fronteira de área.', '',
              'Oclusão cinza sintética e validação reutilizada no desenvolvimento. A área não representa a íris anatômica inteira ou a extensão de uma doença. Não houve nova inferência no teste ou demonstração de efeito clínico.', '',
              '[Estado separado do piloto clínico](../../prontidao_anomalias_2026-11-03/PRONTIDAO.md).']
    temporary = OUT / 'RELATORIO_ATUAL.md.part'
    temporary.write_text('\n'.join(lines), encoding='utf-8')
    temporary.replace(OUT / 'RELATORIO_ATUAL.md')
    state = {'updated_utc': datetime.now(timezone.utc).isoformat(), 'training_status': status,
             'progress': progress, 'identity_records_audited': len(records), 'frontier': frontier,
             'clinical_reviews_block_area': False, 'no_inference_or_model_change': True}
    write(OUT / 'estado.json', state)
    return (BASE / 'identidade/CONCLUIDO.json').exists()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--watch', action='store_true')
    a = p.parse_args()
    deadline = time.monotonic() + 23 * 3600
    while True:
        if render() or not a.watch or time.monotonic() >= deadline:
            return
        time.sleep(60)


if __name__ == '__main__':
    main()

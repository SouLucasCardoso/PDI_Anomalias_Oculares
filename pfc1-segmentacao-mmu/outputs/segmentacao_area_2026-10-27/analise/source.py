"""Relatorio observacional da rodada congelada; nao treina nem escolhe pesos."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

import numpy as np

ROOT = Path(__file__).resolve().parent
MIRROR = ROOT / 'outputs/segmentacao_area_2026-10-27'
OUT = MIRROR / 'analise'
MODES = {'clean': 'Escala original', 'zoom3': 'Zoom 3×',
         'oblique': 'Oblíqua simulada', 'glasses': 'Óculos simulados'}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.part')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    temporary.replace(path)


def validation_queries(manifest):
    rows = manifest['val']
    identity = lambda row: (row['subject'], row['side'])
    eligible = {identity(r) for r in rows if r['session'] == 1} & {
        identity(r) for r in rows if r['session'] == 2}
    rows = [r for r in rows if identity(r) in eligible]
    queries = [r for r in rows if r['session'] == 2]
    people = sorted({r['subject'] for r in rows})
    labels = np.array([people.index(r['subject']) for r in queries])
    return queries, people, labels


def measure(scores, labels, valid, threshold):
    scores = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(labels)
    valid = np.asarray(valid, dtype=bool)
    if (scores.ndim != 2 or len(scores) == 0 or scores.shape[1] < 2
            or labels.shape != (len(scores),) or valid.shape != labels.shape
            or not np.issubdtype(labels.dtype, np.integer)
            or not np.isfinite(scores).all() or (labels < 0).any()
            or (labels >= scores.shape[1]).any()):
        raise ValueError('Matriz de reconhecimento invalida')
    genuine = scores[np.arange(len(scores)), labels]
    correct = (scores.argmax(1) == labels) & valid
    accepted = (genuine >= threshold) & valid
    imp = np.ones_like(scores, dtype=bool)
    imp[np.arange(len(scores)), labels] = False
    false = ((scores >= threshold) & valid[:, None] & imp).sum(1)
    counts = {'correct': int(correct.sum()), 'accepted': int(accepted.sum()),
              'joint': int((correct & accepted).sum()), 'false_accepts': int(false.sum()),
              'queries': len(scores), 'impostors': len(scores) * (scores.shape[1] - 1),
              'extraction_failures': int((~valid).sum())}
    n, impostors = counts['queries'], counts['impostors']
    rates = {'rank1': counts['correct'] / n, 'tar': counts['accepted'] / n,
             'joint': counts['joint'] / n, 'fmr': counts['false_accepts'] / impostors}
    passed = (10 * counts['correct'] >= 9 * n and 10 * counts['accepted'] >= 9 * n
              and 100 * counts['false_accepts'] <= impostors)
    vectors = {'rank1': correct, 'tar': accepted, 'joint': correct & accepted,
               'fmr': false / (scores.shape[1] - 1)}
    return counts, rates, bool(passed), vectors


def paired_difference(original, candidate, subjects):
    """Candidato menos original, pontos percentuais; clusters de pessoas, galeria fixa."""
    subjects = np.asarray(subjects)
    change = np.asarray(candidate, dtype=float) - np.asarray(original, dtype=float)
    if change.shape != subjects.shape or len(change) == 0:
        raise ValueError('Consultas nao pareadas')
    people = np.unique(subjects)
    sizes = np.array([(subjects == p).sum() for p in people])
    sums = np.array([change[subjects == p].sum() for p in people])
    draws = np.random.default_rng(127).integers(0, len(people), (5000, len(people)))
    bootstrap = 100 * sums[draws].sum(1) / sizes[draws].sum(1)
    return {'candidate_minus_original_pp': float(100 * change.mean()),
            'interval95_cluster_person_pp': np.quantile(bootstrap, [.025, .975]).tolist()}


def archive(source, target):
    if target.exists():
        if sha256(source) != sha256(target):
            raise ValueError('Arquivo arquivado divergente: ' + str(target))
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + '.part')
        shutil.copy2(source, temporary)
        temporary.replace(target)


def register():
    OUT.mkdir(exist_ok=True)
    protocol = json.loads((MIRROR / 'protocolo_rodada.json').read_text(encoding='utf-8-sig'))
    for name, expected in protocol['source_hashes'].items():
        if sha256(ROOT / name) != expected:
            raise ValueError('Fonte cientifica divergente: ' + name)
    analysis_protocol = OUT / 'protocolo_analise.json'
    source = sha256(Path(__file__))
    if analysis_protocol.exists():
        registered = json.loads(analysis_protocol.read_text(encoding='utf-8'))
        if (registered['source_sha256'] != source or
                registered['experiment_protocol_sha256'] != sha256(MIRROR / 'protocolo_rodada.json')):
            raise ValueError('Preservar analise registrada antes de mudar suas fontes')
    else:
        write_json(analysis_protocol, {'registered_utc': datetime.now(timezone.utc).isoformat(),
                   'source_sha256': source, 'experiment_protocol_sha256': sha256(MIRROR / 'protocolo_rodada.json'),
                   'paired_bootstrap': {'seed': 127, 'replicates': 5000, 'cluster': 'query person', 'gallery': 'fixed'},
                   'direction': 'candidate minus original, percentage points; positive FMR means worse',
                   'scope': 'Observational report only; no checkpoint, calibration, threshold or production change; validation only'})
        archive(Path(__file__), OUT / 'source.py')
    return protocol


def plot_history(history):
    os.environ.setdefault('MPLCONFIGDIR', str(Path(os.environ['TEMP']) / 'pfc-matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 4.7), layout='constrained')
    for mode, label in MODES.items():
        ax.plot([r['epoch'] for r in history], [100 * r['dice'][mode] for r in history],
                marker='.', label=label)
    ax.set(xlabel='Época concluída', ylabel='Dice macro da íris (%)', ylim=(0, 100),
           title='Validação: 1.652 imagens, quatro condições fixadas')
    ax.grid(alpha=.2)
    ax.legend(loc='lower right')
    fig.savefig(OUT / 'evolucao_segmentacao.png', dpi=180)
    plt.close(fig)


def audit_records(final):
    manifest_file = ROOT / 'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    train_protocol = json.loads((MIRROR / 'treino/protocolo.json').read_text(encoding='utf-8-sig'))
    if sha256(manifest_file) != train_protocol['provenance']['manifest_sha256']:
        raise ValueError('Manifesto alterado')
    queries, people, labels = validation_queries(json.loads(manifest_file.read_text(encoding='utf-8-sig')))
    if (len(queries), len(people)) != (482, 16):
        raise ValueError('Populacao diferente das 482 consultas/16 pessoas registradas')
    frozen = json.loads((ROOT / 'outputs/candidato_congelado_2026-10-21/CONGELADO.json').read_text())
    threshold = frozen['frozen_threshold']
    subjects = np.array([r['subject'] for r in queries])
    audit, vectors = [], {}
    for record in final['records']:
        folder = Path(record['folder'])
        key = f"{record['segmenter']}_{record['condition']}_{record['loss_percent']}"
        with np.load(folder / 'scores_finais.npz', allow_pickle=False) as saved:
            np.testing.assert_array_equal(labels, saved['labels'])
            if saved['scores'].shape != (482, 16):
                raise ValueError('Dimensoes da populacao alteradas')
            counts, rates, passed, per_query = measure(saved['scores'], labels, saved['valid'], threshold)
            np.testing.assert_array_equal(per_query['rank1'], saved['correct'])
            np.testing.assert_array_equal(per_query['tar'], saved['accepted'])
            for name in ('correct', 'accepted', 'false_accepts', 'queries', 'impostors'):
                if counts[name] != record['counts'][name]:
                    raise ValueError('Contagem divergente: ' + key + ' ' + name)
            if passed != record['passed'] or sha256(folder / 'scores_finais.npz') != record['scores_sha256']:
                raise ValueError('Decisao/checksum divergente: ' + key)
            vectors[(record['segmenter'], record['condition'], record['loss_percent'])] = per_query
        evidence = OUT / 'evidencias' / key
        names = {p.name for p in folder.glob('scores_*.npz')} | {
            'protocolo.json', 'CONCLUIDO.json', 'interventions.json'}
        for name in sorted(names):
            archive(folder / name, evidence / name)
        audit.append({'key': key, 'segmenter': record['segmenter'], 'condition': record['condition'],
                      'loss_percent': record['loss_percent'], 'counts': counts, 'rates': rates,
                      'passed': passed, 'scores_sha256': record['scores_sha256']})
    indexed = {(r['segmenter'], r['condition'], r['loss_percent']): r for r in audit}
    if len(indexed) != len(audit):
        raise ValueError('Condicao duplicada')
    eligible = indexed[('novo', 'original', 0)]['passed']
    if eligible != final['clean_identity_gate_passed']:
        raise ValueError('Aprovacao original divergente')
    if eligible:
        protocol = json.loads((MIRROR / 'protocolo_rodada.json').read_text(encoding='utf-8-sig'))
        losses = protocol['area_grid_loss_percent']
        decisions = []
        for condition in ('oclusao_superior', 'oclusao_inferior'):
            approved = [True] + [indexed[('novo', condition, loss)]['passed'] for loss in losses[1:]]
            decisions.append(approved)
            expected = final['frontier'][condition]
            if approved != expected['passed_by_registered_loss']:
                raise ValueError('Grade incompleta ou divergente')
        decisions.append(np.logical_and(*decisions).tolist())
        for condition, approved in zip(('oclusao_superior', 'oclusao_inferior', 'both_orientations'), decisions):
            minimum = None
            for loss, passed in zip(losses, approved):
                if not passed:
                    break
                minimum = 100 - loss
            if minimum != final['frontier'][condition]['nominal_minimum_on_tested_prefix_percent']:
                raise ValueError('Fronteira divergente')
    elif final['frontier']:
        raise ValueError('Candidato reprovado nao pode receber uma fronteira')
    comparisons = []
    for condition, level in (('original', 0), ('oclusao_superior', 10), ('oclusao_inferior', 10)):
        baseline = vectors[('original', condition, level)]
        candidate = vectors[('novo', condition, level)]
        comparisons.append({'condition': condition, 'loss_percent': level,
                            'paired': {m: paired_difference(baseline[m], candidate[m], subjects) for m in baseline}})
    with (OUT / 'identificacao_por_consulta.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.writer(stream)
        writer.writerow(['image', 'subject', 'side', 'segmenter', 'condition', 'loss_percent',
                         'rank1_correct', 'genuine_accepted', 'correct_and_accepted', 'false_accepts'])
        for (segmenter, condition, loss), per_query in vectors.items():
            for i, query in enumerate(queries):
                writer.writerow([Path(query['image']).name, query['subject'], query['side'], segmenter,
                                 condition, loss, int(per_query['rank1'][i]), int(per_query['tar'][i]),
                                 int(per_query['joint'][i]), int(round(15 * per_query['fmr'][i]))])
    return {'queries': len(queries), 'people': len(people), 'threshold': threshold,
            'records': audit, 'paired_comparisons': comparisons, 'all_failures_retained': True}


def render():
    register()
    histories = sorted((MIRROR / 'treino').glob('historico_ate_epoca_*.json'))
    history = json.loads(histories[-1].read_text(encoding='utf-8-sig'))
    plot_history(history)
    final_file = MIRROR / 'CONCLUIDO_RODADA.json'
    final = json.loads(final_file.read_text(encoding='utf-8-sig')) if final_file.exists() else None
    lines = ['# Segmentação e identificação — acompanhamento', '',
             'Atualizado em ' + datetime.now(timezone.utc).isoformat() + ' (UTC).', '',
             f"Última época concluída: **{history[-1]['epoch']}**. A seleção do candidato usa somente segmentação.", '',
             '![Evolução da validação](evolucao_segmentacao.png)', '',
             'Aumento sintético de escala, vista oblíqua e óculos. Esses resultados não medem doenças oculares.', '']
    if final is None:
        lines += ['**Treino/avaliação em andamento.** Ainda não há resultado de reconhecimento do candidato final ou novo mínimo de área.', '']
    elif final['status'] == 'completed_no_eligible_trained_candidate':
        lines += ['**Nenhum checkpoint treinado elegível.** Não foi atribuído novo mínimo de área.', '']
    else:
        checkpoint = MIRROR / 'treino' / f"candidato_epoca_{final['best_epoch']:02}.pt"
        if sha256(checkpoint) != final['checkpoint_sha256']:
            raise ValueError('Candidato final divergente')
        audit = audit_records(final)
        write_json(OUT / 'AUDITORIA_IDENTIFICACAO.json', audit)
        lines += [f"Candidato final: **época {final['best_epoch']}**; 482 consultas de 16 pessoas, candidatos do mesmo lado informado.", '',
                  '| Segmentador/condição | Rank-1 | TAR | Correto e aceito | FMR | Falhas | Critério registrado |',
                  '|---|---:|---:|---:|---:|---:|---|']
        for row in audit['records']:
            rates, counts = row['rates'], row['counts']
            label = f"{row['segmenter']} / {row['condition']} / perda {row['loss_percent']}%"
            lines.append(f"| {label} | {100*rates['rank1']:.2f}% | {100*rates['tar']:.2f}% | {100*rates['joint']:.2f}% | {100*rates['fmr']:.3f}% | {counts['extraction_failures']} | {'Passou' if row['passed'] else 'Não passou'} |")
        lines += ['', 'Critério: Rank-1 ≥ 90%, TAR ≥ 90% e FMR ≤ 1%, com contagens inteiras e todas as falhas no denominador. Acerto e aceitação simultâneos são mostrados separadamente; não alteram o critério registrado.', '',
                  'Diferenças pareadas: candidato menos original, em pontos percentuais. Intervalos de 95% por 5.000 reamostragens de pessoas, com galeria fixa. FMR positivo significa piora.', '',
                  '| Condição | Métrica | Diferença (pp) | Intervalo 95% (pp) |', '|---|---|---:|---:|']
        for row in audit['paired_comparisons']:
            for metric, delta in row['paired'].items():
                lo, hi = delta['interval95_cluster_person_pp']
                lines.append(f"| {row['condition']} {row['loss_percent']}% | {metric} | {delta['candidate_minus_original_pp']:+.2f} | [{lo:+.2f}, {hi:+.2f}] |")
        lines += ['', '**Área visível:**']
        if not final['clean_identity_gate_passed']:
            lines += ['', 'O candidato não passou no critério de reconhecimento sem oclusão. **Nenhum novo mínimo foi atribuído.**']
        else:
            for name, result in final['frontier'].items():
                lines.append(f"- {name}: mínimo nominal no prefixo da grade avaliada = {result['nominal_minimum_on_tested_prefix_percent']}%.")
        lines += ['', 'A área é relativa à íris visível originalmente anotada. A oclusão cinza é sintética. A validação já foi usada no desenvolvimento e não é confirmação cega. Os intervalos são descritivos de cada comparação e não validam simultaneamente uma fronteira de área. Não foi estimado percentual anatômico ou efeito causal de anomalias clínicas.', '']
    temporary = OUT / 'RELATORIO_ATUAL.md.part'
    temporary.write_text('\n'.join(lines), encoding='utf-8')
    temporary.replace(OUT / 'RELATORIO_ATUAL.md')
    write_json(OUT / 'estado_relatorio.json', {'updated_utc': datetime.now(timezone.utc).isoformat(),
               'epoch_completed': history[-1]['epoch'], 'pipeline_completed': final is not None,
               'final_sha256': sha256(final_file) if final else None,
               'report_sha256': sha256(OUT / 'RELATORIO_ATUAL.md')})
    return final is not None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--watch', action='store_true')
    args = parser.parse_args()
    deadline = time.monotonic() + 23 * 3600
    previous = None
    while True:
        files = sorted((MIRROR / 'treino').glob('historico_ate_epoca_*.json'))
        final = MIRROR / 'CONCLUIDO_RODADA.json'
        current = (files[-1].name, sha256(final) if final.exists() else None)
        if current != previous:
            if render():
                return
            previous = current
        if not args.watch or time.monotonic() >= deadline:
            return
        time.sleep(30)


if __name__ == '__main__':
    main()

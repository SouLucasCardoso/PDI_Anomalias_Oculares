"""Sensibilidade observacional: referencias de area definidas e indefinidas."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from analisar_rodada_segmentacao_area import measure, validation_queries
from analisar_sam3_area import area_frontier
from avaliar_prontidao_anomalias import identity_gate

ROOT = Path(__file__).resolve().parent
BASE = ROOT/'outputs/sam31_iris_adaptacao_2026-11-03'
AREA = BASE/'grade_area_ubipr'
OUT = BASE/'sensibilidade_referencia'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    temp = path.with_suffix(path.suffix+'.part')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    temp.replace(path)


def stratify(scores, labels, valid, reference_pixels, threshold, criteria):
    reference_pixels = np.asarray(reference_pixels)
    if (reference_pixels.shape != (len(scores),) or
            not np.issubdtype(reference_pixels.dtype, np.integer) or (reference_pixels < 0).any()):
        raise ValueError('Referencias nao alinhadas ou contagens invalidas')
    scores, labels, valid = np.asarray(scores), np.asarray(labels), np.asarray(valid)
    result = {}
    for name, selected in (('all_queries', np.ones(len(scores), bool)),
                           ('defined_reference', reference_pixels > 0),
                           ('undefined_reference', reference_pixels == 0)):
        if not selected.any():
            result[name] = {'counts': None, 'rates': None, 'passed': False}
            continue
        counts, rates, _, _ = measure(scores[selected], labels[selected], valid[selected], threshold)
        result[name] = {'counts': counts, 'rates': rates, 'passed': identity_gate(counts, criteria)}
    return result


def register():
    OUT.mkdir(exist_ok=True)
    area_final = read(AREA/'CONCLUIDO.json')
    if sha(AREA/'consultas.json') != area_final['artifacts_sha256']['consultas.json']:
        raise ValueError('Coorte de referencias mudou')
    binding = {'source_sha256': sha(Path(__file__)),
               'wrapper_sha256': sha(ROOT/'acompanhar_sensibilidade_area.py'),
               'cohort_sha256': sha(AREA/'consultas.json'),
               'criteria_sha256': sha(ROOT/'criterios_prontidao_anomalias.json'),
               'primary_analysis_protocol_sha256': sha(BASE/'analise_area/protocolo.json'),
               'flow_protocol_sha256': sha(ROOT/'outputs/prontidao_anomalias_2026-11-03/protocolo_fluxo.json'),
               'helpers': {n: sha(ROOT/n) for n in ('analisar_sam3_area.py', 'analisar_rodada_segmentacao_area.py', 'avaliar_prontidao_anomalias.py')}}
    if (OUT/'protocolo.json').exists():
        if read(OUT/'protocolo.json')['binding'] != binding:
            raise ValueError('Preservar analise de sensibilidade registrada')
    else:
        # Especificar os estratos e sua interpretacao ANTES dos escores do novo candidato.
        if (BASE/'identidade/novo_original_0.json').exists():
            raise ValueError('Escores do novo candidato ja existem; identificar nova analise como posterior')
        write(OUT/'protocolo.json', {'registered_utc': datetime.now(timezone.utc).isoformat(),
            'binding': binding, 'scope': 'Secondary descriptive sensitivity only; does not change primary experiment or selection',
            'primary_population': 'All482queries, all extraction failures retained',
            'strata': 'reference_pixels>0 versus reference_pixels==0; fixed from native annotations, not model predictions',
            'gates': 'Same frozen threshold and engineering criteria as primary; no subgroup calibration',
            'area_interpretation': 'Require both all-query and defined-reference prefixes for a conservative interpretable minimum; undefined-reference group never receives an area fraction',
            'minimum_scope': 'Descriptive registered grid, annotation-defined support, no anatomical/clinical or blind-validation claim',
            'uses_clinical_references': False, 'no_inference_or_training': True})
        (OUT/'source.py').write_bytes(Path(__file__).read_bytes())


def render():
    register()
    cohort = read(AREA/'consultas.json')
    manifest_file = ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    training = read(BASE/'protocolo.json')
    if sha(manifest_file) != training['frozen']['manifest_sha256']:
        raise ValueError('Manifesto mudou')
    queries, _, expected = validation_queries(read(manifest_file))
    if [Path(q['image']).name for q in queries] != [r['image'] for r in cohort]:
        raise ValueError('Ordem das consultas divergente')
    areas = np.array([r['reference_iris_pixels'] for r in cohort], dtype=np.int64)
    criteria = read(ROOT/'criterios_prontidao_anomalias.json')['identification_study']
    primary_file = BASE/'analise_area/AUDITORIA.json'
    primary = read(primary_file)
    flow = read(ROOT/'outputs/prontidao_anomalias_2026-11-03/protocolo_fluxo.json')
    primary_binding = read(BASE/'analise_area/protocolo.json')['binding']
    frozen_file = ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json'
    if (sha(frozen_file) != primary_binding['frozen_configuration_sha256'] or
            sha(ROOT/'criterios_prontidao_anomalias.json') != primary_binding['criteria_sha256']):
        raise ValueError('Limiar ou criterios diferentes da analise primaria')
    for name, checksum in primary_binding['sources'].items():
        if sha(ROOT/name) != checksum:
            raise ValueError('Analise primaria alterada')
    if primary['records']:
        selected = read(BASE/'CONCLUIDO.json')
        if selected['development_smoke_only'] or selected['checkpoint_sha256'] != primary['checkpoint_sha256']:
            raise ValueError('Candidato diverge da analise primaria')
    threshold = read(frozen_file)['frozen_threshold']
    rows, indexed = [], {'all_queries': {}, 'defined_reference': {}}
    for record in primary['records']:
        file = BASE/'identidade/evidencias'/record['key']/'scores_finais.npz'
        if sha(file) != record['evidence_sha256']['scores_finais.npz']:
            raise ValueError('Matriz difere da auditoria primaria')
        with np.load(file, allow_pickle=False) as saved:
            np.testing.assert_array_equal(expected, saved['labels'])
            groups = stratify(saved['scores'], saved['labels'], saved['valid'], areas, threshold, criteria)
        if groups['all_queries']['counts'] != record['counts'] or groups['all_queries']['passed'] != record['passed']:
            raise ValueError('Analise geral nao reproduz contagens/decisao primaria')
        rows.append({'key': record['key'], 'groups': groups})
        key = record['segmenter'], record['condition'], record['loss_percent']
        for group in indexed:
            indexed[group][key] = groups[group]
    frontiers = {group: area_frontier(records, flow['area_loss_grid']) for group, records in indexed.items()}
    minimum = None
    if all(f['minimum_assigned'] for f in frontiers.values()):
        minimum = max(f['orientations']['both_orientations']['minimum_on_complete_grid_percent'] for f in frontiers.values())
    state = {'updated_utc': datetime.now(timezone.utc).isoformat(), 'groups': {
        'all_queries': len(areas), 'defined_reference': int((areas > 0).sum()),
        'undefined_reference': int((areas == 0).sum())},
        'primary_audit_sha256': sha(primary_file), 'records': rows, 'frontiers': frontiers,
        'conservative_interpretable_minimum_percent': minimum,
        'undefined_reference_area_fraction': None,
        'primary_experiment_modified': False, 'clinical_reviews_required': False,
        'intervals_are_not_simultaneously_certifying_frontier': True}
    write(OUT/'estado.json', state)
    lines = ['# Sensibilidade às referências de área', '',
        'Análise secundária especificada antes dos escores do novo candidato. A regra original, o limiar e os pesos permanecem iguais.', '',
        f"São {len(areas)} consultas: **{int((areas > 0).sum())} com área anotada** e **{int((areas == 0).sum())} sem pixels anotados como íris**. Uma referência vazia não comprova ausência anatômica de íris.", '',
        'O resultado primário conserva todas as consultas. Esta análise separa os estratos, mantendo as falhas nos denominadores de cada um, para interpretar a quantidade de área efetivamente definida.', '']
    if not rows:
        lines += ['**Aguardando as matrizes auditadas do novo experimento. Nenhum mínimo atribuído.**', '']
    else:
        lines += ['| Condição | Grupo | Consultas | Rank-1 | TAR | Correto e aceito | FMR |',
                  '|---|---|---:|---:|---:|---:|---:|']
        for row in rows:
            for group, values in row['groups'].items():
                c, r = values['counts'], values['rates']
                if c:
                    lines.append(f"| {row['key']} | {group} | {c['queries']} | {100*r['rank1']:.2f}% | {100*r['tar']:.2f}% | {100*r['joint']:.2f}% | {100*r['fmr']:.3f}% |")
        lines += ['', f"Mínimo conservador interpretável na grade completa: **{str(minimum)+'%' if minimum is not None else 'ainda não estabelecido'}**.", '']
    lines += ['O grupo sem referência de íris recebe métricas de identificação descritivas, mas nenhuma fração de área. A interpretação conservadora exige aprovação do prefixo completo tanto no resultado geral quanto no grupo com referência definida, nas duas orientações.', '',
              'O grupo de dez consultas é pequeno. Não há calibração por grupo, exclusão do resultado original, promoção de checkpoint ou inferência clínica a partir desta análise.', '',
              '[Caracterização dos pixels da referência](../grade_area_ubipr/REFERENCIA_AREA.md).', '',
              '[Resultado primário e progresso do SAM3](../analise_area/RELATORIO_ATUAL.md).']
    temp = OUT/'RELATORIO_ATUAL.md.part'
    temp.write_text('\n'.join(lines), encoding='utf-8')
    temp.replace(OUT/'RELATORIO_ATUAL.md')
    return state


if __name__ == '__main__':
    print(json.dumps(render(), ensure_ascii=False, indent=2))

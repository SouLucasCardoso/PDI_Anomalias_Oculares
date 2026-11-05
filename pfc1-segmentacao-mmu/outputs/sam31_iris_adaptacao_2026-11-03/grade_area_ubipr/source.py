"""Caracteriza a area de referencia da grade registrada, sem inferencia ou novo minimo."""
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from analisar_rodada_segmentacao_area import validation_queries

ROOT = Path(__file__).resolve().parent
BASE = ROOT/'outputs/sam31_iris_adaptacao_2026-11-03'
DEFAULT = BASE/'grade_area_ubipr'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def distribution(values):
    if not len(values):
        return None
    return {'min': float(np.min(values)), 'p10': float(np.quantile(values, .1)),
            'median': float(np.median(values)), 'mean': float(np.mean(values)),
            'p90': float(np.quantile(values, .9)), 'max': float(np.max(values))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if any(args.out.iterdir()):
        raise ValueError('Preservar a caracterizacao existente; usar outra saida')
    manifest_file = ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    manifest = read(manifest_file)
    train_protocol = read(BASE/'protocolo.json')
    flow_file = ROOT/'outputs/prontidao_anomalias_2026-11-03/protocolo_fluxo.json'
    flow = read(flow_file)
    if sha(manifest_file) != train_protocol['frozen']['manifest_sha256']:
        raise ValueError('Manifesto diferente do treino SAM3')
    queries, people, _ = validation_queries(manifest)
    if (len(queries), len(people)) != (482, 16):
        raise ValueError('Populacao diferente das 482 consultas/16 pessoas')
    protocol = {'registered_utc': datetime.now(timezone.utc).isoformat(),
                'source_sha256': sha(Path(__file__)),
                'manifest_sha256': sha(manifest_file), 'flow_protocol_sha256': sha(flow_file),
                'helper_sha256': sha(ROOT/'analisar_rodada_segmentacao_area.py'),
                'queries': 482, 'people': 16, 'loss_grid_percent': flow['area_loss_grid'],
                'native_iris_value': 85, 'reference_resolution': 'native annotation pixels',
                'scope': 'Reference geometry only; all eligible validation queries, including empty annotations',
                'reference_is_not_full_anatomical_iris': True, 'no_model_inference': True,
                'no_test_image_or_annotation_access': True,
                'clinical_references_required': False, 'minimum_area_assigned': False}
    write(args.out/'protocolo.json', protocol)
    (args.out/'source.py').write_bytes(Path(__file__).read_bytes())
    rows = []
    for query in queries:
        photo = ROOT/'data/ubipr/single_eye'/Path(query['image']).name
        mask = ROOT/'data/ubipr/single_eye'/Path(query['mask']).name
        with Image.open(photo) as image, Image.open(mask) as target:
            if image.size != target.size:
                raise ValueError('Dimensoes divergentes: '+photo.name)
            width, height = image.size
            values = np.asarray(target.convert('L'))
        if not set(np.unique(values)).issubset({0, 85, 170, 255}):
            raise ValueError('Classes nativas inesperadas: '+mask.name)
        count = int((values == 85).sum())
        rows.append({'image': photo.name, 'subject': query['subject'], 'side': query['side'],
                     'width': width, 'height': height, 'reference_iris_pixels': count,
                     'reference_fraction_of_photo': count/(width*height),
                     'image_sha256': sha(photo), 'mask_sha256': sha(mask)})
    # Verificacao real contra todas as intervencoes ja preservadas da rodada anterior.
    reference_root = ROOT/'outputs/segmentacao_area_2026-10-27/analise/evidencias'
    checks = []
    by_image = {r['image']: r for r in rows}
    for orientation in ('oclusao_superior', 'oclusao_inferior'):
        file = reference_root/('novo_'+orientation+'_10')/'interventions.json'
        previous = read(file)
        if len(previous) != 482 or {r['image'] for r in previous} != set(by_image):
            raise ValueError('Consultas diferentes na evidencia anterior')
        for record in previous:
            n = by_image[record['image']]['reference_iris_pixels']
            if n != record['reference_pixels'] or bool(n) != record['fraction_defined']:
                raise ValueError('Anotacao diverge da evidencia anterior')
            expected = round(n*.1)/n if n else 0.
            if not np.isclose(record['affected_fraction'], expected, rtol=0, atol=1e-14):
                raise ValueError('Quantidade de pixels oculta divergente')
        checks.append({'orientation': orientation, 'queries_checked': 482,
                       'previous_interventions_sha256': sha(file), 'all_reference_counts_and_rounding_match': True})
    defined = [r for r in rows if r['reference_iris_pixels']]
    counts = np.array([r['reference_iris_pixels'] for r in defined], dtype=np.int64)
    grid = []
    with (args.out/'grade_por_consulta.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['image', 'subject', 'side', 'loss_percent', 'nominal_retained_percent',
                         'reference_pixels', 'selected_occlusion_pixels', 'retained_pixels',
                         'actual_retained_percent', 'fraction_defined'])
        for loss in flow['area_loss_grid']:
            remaining = np.array([int(n)-round(int(n)*loss/100) for n in counts])
            actual = 100*remaining/counts if len(counts) else np.array([])
            grid.append({'loss_percent': loss, 'nominal_retained_percent': 100-loss,
                         'retained_native_pixels': distribution(remaining),
                         'actual_retained_percent': distribution(actual),
                         'max_absolute_rounding_error_percentage_points':
                         float(np.max(np.abs(actual-(100-loss)))) if len(actual) else None})
            for row in rows:
                n = row['reference_iris_pixels'];hidden = round(n*loss/100)
                writer.writerow([row['image'], row['subject'], row['side'], loss, 100-loss,
                                 n, hidden, n-hidden, 100*(n-hidden)/n if n else '', bool(n)])
    summary = {'queries': len(rows), 'people': len(people),
               'eyes': len({(r['subject'], r['side']) for r in rows}),
               'side_counts': {side: sum(r['side'] == side for r in rows) for side in ('L', 'R')},
               'empty_reference_queries_retained': len(rows)-len(defined),
               'native_reference_iris_pixels': distribution(counts),
               'reference_fraction_of_photo': distribution([r['reference_fraction_of_photo'] for r in rows]),
               'native_image_shapes': sorted({(r['width'], r['height']) for r in rows}),
               'grid': grid, 'previous_reference_checks': checks,
               'new_minimum_area_assigned': False, 'model_or_identity_performance_measured': False}
    write(args.out/'consultas.json', rows)
    write(args.out/'RESUMO.json', summary)
    lines = ['# Referência de área para o experimento UBIPr', '',
             'Esta caracterização descreve as anotações existentes. **Ainda não determina o mínimo necessário para identificação.**', '',
             f"São {len(rows)} consultas, {len(people)} pessoas e {summary['eyes']} olhos, com lado informado. Referências vazias mantidas: {len(rows)-len(defined)}.", '',
             'Os pixels são contados na resolução original da anotação. A fração é relativa à íris visível anotada em cada fotografia, sem reconstruir a parte escondida ou a íris anatômica inteira.', '',
             '| Área nominal preservada | Pixels preservados: mínimo | Mediana | Máximo |',
             '|---:|---:|---:|---:|']
    for row in grid:
        stats = row['retained_native_pixels']
        if stats:
            lines.append(f"| {row['nominal_retained_percent']}% | {stats['min']:.0f} | {stats['median']:g} | {stats['max']:.0f} |")
    lines += ['', 'Cada nível usa o mesmo número de pixels em oclusão superior e inferior; a posição desses pixels muda. Isso pode produzir efeitos diferentes no reconhecimento.', '',
              'A seleção de pixels usa arredondamento inteiro, conforme o protocolo. A planilha CSV conserva todas as consultas, quantidades e frações efetivas, inclusive referências vazias.', '',
              'As 482 contagens de referência e o arredondamento em perda de 10% foram reproduzidos nas duas orientações contra as evidências da rodada anterior, sem nova inferência.', '',
              'O mesmo percentual pode preservar quantidades diferentes de pixels entre fotografias. Estes números não medem resolução óptica, gravidade de doença ou reconhecimento com o novo SAM3.', '',
              '[Acompanhar o treino e o resultado biométrico](../analise_area/RELATORIO_ATUAL.md).']
    (args.out/'REFERENCIA_AREA.md').write_text('\n'.join(lines), encoding='utf-8')
    write(args.out/'CONCLUIDO.json', {'status': 'reference_geometry_characterized',
          'protocol_sha256': sha(args.out/'protocolo.json'),
          'artifacts_sha256': {p.name: sha(p) for p in args.out.iterdir() if p.is_file()},
          'queries': 482, 'loss_levels': len(grid), 'no_inference': True, 'minimum_area_assigned': False})
    print(json.dumps({'queries': len(rows), 'eyes': summary['eyes'],
                      'reference_iris_pixels': summary['native_reference_iris_pixels'],
                      'empty_references': len(rows)-len(defined), 'minimum_area_assigned': False}))


if __name__ == '__main__':
    main()

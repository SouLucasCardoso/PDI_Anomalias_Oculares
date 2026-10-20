"""Extrai a amostra oficial CatScreen e audita imagens/metadados sem treinar."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parent
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def records(content):
    """Le somente valores armazenados no XLSX; nao executa formulas/macros."""
    with zipfile.ZipFile(io.BytesIO(content)) as workbook:
        strings = []
        if 'xl/sharedStrings.xml' in workbook.namelist():
            strings = [''.join(t.text or '' for t in s.findall('.//m:t', NS))
                       for s in ET.fromstring(workbook.read('xl/sharedStrings.xml')).findall('m:si', NS)]
        rows = []
        sheet = ET.fromstring(workbook.read('xl/worksheets/sheet1.xml'))
        for row in sheet.findall('m:sheetData/m:row', NS):
            values = {}
            for cell in row:
                column = ''.join(c for c in cell.attrib['r'] if c.isalpha())
                kind = cell.attrib.get('t')
                value = cell.find('m:v', NS)
                if kind == 's' and value is not None:
                    values[column] = strings[int(value.text)]
                elif kind == 'inlineStr':
                    values[column] = ''.join(t.text or '' for t in cell.findall('.//m:t', NS))
                else:
                    values[column] = value.text if value is not None else ''
            rows.append(values)
        header = rows[0]
        return [{name: row.get(col, '') for col, name in header.items()} for row in rows[1:]]


def main():
    archive = ROOT / 'data/archives/catscreen-sample.zip'
    target = ROOT / 'data/catscreen'
    target.mkdir(parents=True, exist_ok=True)
    digest = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'archive_sha256': digest,
              'source': 'https://www.iab-rubric.org/resources/healthcare-datasets/catscreen',
              'release': 'public sample Data2025-main, not full dataset', 'tables': {}}
    manifest = []
    ids_by_split = {}
    with zipfile.ZipFile(archive) as bundle:
        bad = bundle.testzip()
        if bad:
            raise ValueError(f'CRC invalido: {bad}')
        for name in bundle.namelist():
            path = (target / name).resolve()
            if not path.is_relative_to(target.resolve()):
                raise ValueError('Caminho inseguro no ZIP')
        bundle.extractall(target)
        image_names = [n for n in bundle.namelist() if n.lower().endswith('.jpg')]
        by_name = {Path(n).name: n for n in image_names}
        if len(by_name) != len(image_names):
            raise ValueError('Nomes de imagem duplicados entre pastas')
        invalid_images = []
        for name in image_names:
            try:
                with Image.open(target / name) as im:
                    im.verify()
            except Exception:
                invalid_images.append(name)
        report['images'] = len(image_names)
        report['images_by_subset'] = dict(Counter(Path(n).parts[1] for n in image_names))
        report['invalid_images'] = invalid_images
        for name in bundle.namelist():
            if not name.endswith('.xlsx'):
                continue
            rows = records(bundle.read(name))
            missing = [r['filename'] for r in rows if r['filename'] not in by_name]
            label = Path(name).stem
            ids = {r['id'] for r in rows if r.get('id')}
            ids_by_split[label] = ids
            eye_counts = Counter((r['id'], r['eye_side']) for r in rows)
            report['tables'][label] = {
                'rows': len(rows), 'columns': list(rows[0]) if rows else [],
                'unique_metadata_ids': len(ids), 'missing_images': missing,
                'id_eye_groups_with_multiple_images': sum(n > 1 for n in eye_counts.values()),
                'diagnosis_counts_raw': dict(Counter(r['diagnosis'] for r in rows)),
                'eye_side_counts_raw': dict(Counter(r['eye_side'] for r in rows)),
            }
            for row in rows:
                manifest.append({'subset': Path(name).parts[1], 'source_split': label, **row,
                                 'image': str((target / by_name[row['filename']]).resolve())
                                 if row['filename'] in by_name else None})
        report['metadata_id_overlap_clean_splits'] = {
            f'{a}/{b}': len(ids_by_split[a] & ids_by_split[b])
            for a, b in [('train', 'val'), ('train', 'test'), ('val', 'test')]}
    report['biometric_eligibility'] = (
        'Nao confirmada: id e eye_side exigem dicionario dos autores; '
        'nao foi localizado campo de sessao ou pre/pos-cirurgia nas planilhas. '
        'Contagens por id nao comprovam capturas longitudinais independentes.')
    (target / 'manifesto.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (target / 'auditoria.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if invalid_images or any(t['missing_images'] for t in report['tables'].values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()

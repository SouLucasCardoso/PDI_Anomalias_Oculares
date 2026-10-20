"""Audita o deposito publico SLP-VLD v3 sem usar respostas VLM como alvo."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile

from PIL import Image
from auditar_catscreen import records

ROOT = Path(__file__).resolve().parent
GROUP = re.compile(r'^(P\d+)_(OD|OS)', re.IGNORECASE)


def main():
    base = ROOT / 'data/slpvld'
    base.mkdir(parents=True, exist_ok=True)
    archive = ROOT / 'data/archives/slp-vld-v3.zip'
    extracted = base / 'release'
    extracted.mkdir(exist_ok=True)
    report = {'utc': datetime.now(timezone.utc).isoformat(),
              'source': 'https://doi.org/10.6084/m9.figshare.32576697.v3',
              'license': 'CC BY 4.0', 'manifest_splits': {}}
    manifest, invalid, missing_metadata, missing_images = [], [], [], []
    hashes, duplicates = {}, []
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (extracted / member.filename).resolve()
            if not target.is_relative_to(extracted.resolve()):
                raise ValueError('Caminho inseguro')
            if member.is_dir():
                continue
            if not target.exists() or target.stat().st_size != member.file_size:
                bundle.extract(member, extracted)
        package = next(p for p in extracted.iterdir() if p.is_dir())
        report['jpeg_files_in_archive'] = sum(n.lower().endswith('.jpg') for n in bundle.namelist())
        for split, json_file, workbook in (
            ('development', 'training_dataset.json', 'training_validation_dataset_zhaohui/zhaohui_description.xlsx'),
            ('external', 'test_dataset.json', 'external_test_dataset_bijie/bijie_description.xlsx'),
        ):
            metadata_rows = records((package / workbook).read_bytes())
            metadata = {}
            for row in metadata_rows:
                name = Path(str(row.get('image_id', '')).replace('\\', '/')).stem.upper()
                if name:
                    if name in metadata and metadata[name].get('Diagnosis') != row.get('Diagnosis'):
                        raise ValueError('Rotulos divergentes em image_id')
                    metadata[name] = row
            vlm_records = json.loads((package / json_file).read_text(encoding='utf-8-sig'))
            paths = [name for record in vlm_records for name in record['images']]
            if len(paths) != len(set(paths)):
                raise ValueError('Imagens repetidas no JSON')
            selected = []
            for name in paths:
                image = (package / name).resolve()
                if not image.is_relative_to(package.resolve()) or not image.exists():
                    missing_images.append(name)
                    continue
                meta = metadata.get(image.stem.upper())
                if meta is None or not str(meta.get('Diagnosis', '')).strip():
                    missing_metadata.append(name)
                    continue
                match = GROUP.match(image.stem)
                if not match:
                    raise ValueError('Nome sem grupo anonimo P e lado OD/OS')
                with image.open('rb') as stream:
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                if digest in hashes:
                    duplicates.append([hashes[digest], name])
                hashes[digest] = name
                try:
                    with Image.open(image) as im:
                        size = list(im.size)
                        im.verify()
                except Exception:
                    size = None
                    invalid.append(name)
                diagnosis = str(meta['Diagnosis']).strip()
                selected.append({'image': str(image), 'subject': match[1].upper(), 'side': match[2].upper(),
                                 'source_split': split, 'diagnosis_raw': diagnosis,
                                 'label_binary': int(diagnosis.casefold() != 'normal eye'),
                                 'sha256': digest, 'size': size})
            ids = {r['subject'] for r in selected}
            report['manifest_splits'][split] = {
                'json_records': len(vlm_records), 'xlsx_rows_first_sheet': len(metadata_rows),
                'matched_images': len(selected), 'anonymous_filename_groups': len(ids),
                'diagnosis_counts': dict(Counter(r['diagnosis_raw'] for r in selected)),
                'binary_counts': dict(Counter(r['label_binary'] for r in selected)),
                'metadata_ID_nonempty_rows': sum(bool(r.get('ID')) for r in metadata_rows),
                'source': 'Diffuse Light first sheet only; narrower modalities excluded',
            }
            manifest.extend(selected)
        groups = {s: {r['subject'] for r in manifest if r['source_split'] == s} for s in ('development', 'external')}
        report['anonymous_group_overlap_between_sites'] = len(groups['development'] & groups['external'])
    with archive.open('rb') as stream:
        report['archive_md5'] = hashlib.file_digest(stream, 'md5').hexdigest()
    report['archive_md5_matches_source'] = report['archive_md5'] == '97b727e69ac07428e912457eb4bad527'
    report.update({'images': len(manifest), 'invalid_images': invalid,
                   'missing_images': missing_images, 'missing_metadata': missing_metadata,
                   'exact_duplicates': duplicates,
                   'group_definition': 'P#### prefix from anonymized filenames, consistent across eye/date; original patient mapping excluded by release',
                   'label_rule_candidate': 'Normal eye exact label vs other annotated conditions. Review clinical semantics before experiment.',
                   'paper_status': 'Dataset deposit; no associated peer-reviewed publication established in source record.'})
    for name, value in [('manifesto.json', manifest), ('auditoria.json', report)]:
        (base / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    summary = {k: v for k, v in report.items() if k != 'manifest_splits'}
    summary['manifest_splits'] = {k: {x: y for x, y in v.items() if x != 'diagnosis_counts'}
                                  for k, v in report['manifest_splits'].items()}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if invalid or missing_images or missing_metadata or not report['archive_md5_matches_source']:
        raise SystemExit('Auditoria com pendencias; nao iniciar treinamento clinico')


if __name__ == '__main__':
    main()

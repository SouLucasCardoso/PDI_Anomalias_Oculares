"""Audita imagens Mendeley e a selecao rotulada publicada em 2025."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

from PIL import Image
from auditar_catscreen import records

ROOT = Path(__file__).resolve().parent


def main():
    base = ROOT / 'data/nuclear'
    archive = ROOT / 'data/archives/nuclear-cataract-v2.zip'
    extracted = base / 'images'
    extracted.mkdir(parents=True, exist_ok=True)
    selected = records((base / 'NC_images_used_for_evaluation.xlsx').read_bytes())
    labels = {}
    for row in selected:
        if not row.get('Volunteer No.') or not row.get('Filename'):
            continue
        key = (int(float(row['Volunteer No.'])), row['Case'].upper(), row['Filename'].upper())
        grade = row['NC classification']
        if key in labels and labels[key] != grade:
            raise ValueError('Rotulos divergentes na selecao')
        labels[key] = grade
    manifest, invalid, seen, duplicates = [], [], {}, []
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            if not member.filename.lower().endswith('.jpg') or member.is_dir():
                continue
            target = (extracted / member.filename).resolve()
            if not target.is_relative_to(extracted.resolve()):
                raise ValueError('Caminho inseguro')
            if not target.exists() or target.stat().st_size != member.file_size:
                bundle.extract(member, extracted)
            parts = Path(member.filename).parts
            subject = next((int(x) for x in parts[:-1] if x.isdigit()), None)
            side = next((x.upper() for x in parts[:-1] if x.upper() in ('DER', 'IZQ')), None)
            key = (subject, side, target.stem.upper())
            with target.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if digest in seen:
                duplicates.append([seen[digest], member.filename])
            seen[digest] = member.filename
            try:
                with Image.open(target) as im:
                    size = list(im.size)
                    im.verify()
            except Exception:
                invalid.append(member.filename)
                size = None
            manifest.append({'image': str(target), 'patient_id': subject, 'side': side,
                             'filename': target.name, 'grade_nc_2025_selection': labels.get(key),
                             'sha256': digest, 'size': size})
    matched = [r for r in manifest if r['grade_nc_2025_selection'] is not None]
    with archive.open('rb') as stream:
        archive_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'version': 2,
              'source': 'https://doi.org/10.17632/6wv33nbcvv.2', 'license': 'CC BY 4.0',
              'label_source': 'https://github.com/ignatowicz-alicja/AI-Powered-Mobile-App-for-Nuclear-Cataract-Detection',
              'label_article': 'https://doi.org/10.3390/s25133954',
              'archive_sha256': archive_hash, 'images': len(manifest),
              'patients': len({r['patient_id'] for r in manifest if r['patient_id'] is not None}),
              'selected_label_rows': len(labels), 'matched_labeled_images': len(matched),
              'matched_patients': len({r['patient_id'] for r in matched}),
              'grade_counts_selection': dict(Counter(r['grade_nc_2025_selection'] for r in matched)),
              'invalid_images': invalid, 'exact_duplicates': duplicates,
              'warning': 'No healthy class established in acquired files. Do not convert severity 1 into healthy or mix controls from another sensor.',
              'original_full_labels_available': False}
    for name, value in [('manifesto.json', manifest), ('auditoria.json', report)]:
        (base / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if invalid or len(matched) != len(labels):
        raise SystemExit('Ha arquivos invalidos ou rotulos sem pareamento; revisar auditoria')


if __name__ == '__main__':
    main()

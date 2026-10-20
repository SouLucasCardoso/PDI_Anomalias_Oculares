"""Audita SLID publico sem inventar identidade, sessao ou mascara de iris."""
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parent


def main():
    destination = ROOT / 'data/slid'
    repository = destination / 'repository'
    archive = repository / 'Original_Slit-lamp_Images.zip'
    extracted = destination / 'images'
    extracted.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            if not member.filename.startswith('Original_Slit-lamp_Images/') or member.is_dir():
                continue
            target = (extracted / member.filename).resolve()
            if not target.is_relative_to(extracted.resolve()):
                raise ValueError('Caminho inseguro')
            if not target.exists() or target.stat().st_size != member.file_size:
                bundle.extract(member, extracted)
    annotations = defaultdict(list)
    with (repository / 'Annotations.csv').open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            annotations[row['filename']].append(row)
    manifest, invalid, seen, duplicates = [], [], {}, []
    for filename, rows in sorted(annotations.items()):
        image = extracted / 'Original_Slit-lamp_Images' / filename
        with image.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest in seen:
            duplicates.append([seen[digest], filename])
        seen[digest] = filename
        try:
            with Image.open(image) as im:
                size = list(im.size)
                im.verify()
        except Exception:
            invalid.append(filename)
            size = None
        lesions, regions = set(), set()
        for row in rows:
            attributes = json.loads(row['attributes'])
            lesion = attributes.get('lesion', '').strip()
            if lesion == 'Lens dislocation/Cataract':
                lesions.update(('Lens dislocation', 'Cataract'))
            elif lesion:
                lesions.add(lesion)
            if attributes.get('region'):
                regions.add(attributes['region'])
        manifest.append({'image': str(image.resolve()), 'filename': filename,
                         'lesions': sorted(lesions), 'regions': sorted(regions),
                         'label_binary': int(bool(lesions)), 'patient_id': None,
                         'side': None, 'session': None, 'sha256': digest, 'size': size})
    with archive.open('rb') as stream:
        archive_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    report = {'utc': datetime.now(timezone.utc).isoformat(),
              'source': 'https://github.com/xumingyu-hub/SLID',
              'article': 'https://doi.org/10.3389/fdgth.2025.1716501',
              'archive_sha256': archive_sha, 'images': len(manifest),
              'normal_no_annotated_lesion': sum(not r['lesions'] for r in manifest),
              'with_annotated_lesion': sum(bool(r['lesions']) for r in manifest),
              'labels_per_image': dict(Counter(x for r in manifest for x in r['lesions'])),
              'regions_per_image': dict(Counter(x for r in manifest for x in r['regions'])),
              'invalid_images': invalid, 'exact_duplicates': duplicates,
              'patient_ids_in_release': False, 'iris_reference_in_release': False,
              'use': 'Candidate external test with frozen classifier; not patient-disjoint internal training.',
              'license': 'Article CC BY; no separate dataset license found in repository. Do not redistribute.'}
    for name, value in [('manifesto.json', manifest), ('auditoria.json', report)]:
        (destination / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if invalid:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

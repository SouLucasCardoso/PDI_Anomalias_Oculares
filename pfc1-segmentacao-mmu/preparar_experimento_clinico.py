"""Prepara protocolo e manifesto clinico CatScreen sem treinar ou abrir escores de teste."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    source = ROOT / 'data/catscreen/manifesto.json'
    source_bytes = source.read_bytes()
    rows = [r for r in json.loads(source_bytes) if r['subset'] == 'Clean']
    splits = {}
    seen = {}
    for split in ('train', 'val', 'test'):
        selected = []
        for r in rows:
            if r['source_split'] != split:
                continue
            if r['diagnosis'] not in ('Normal', 'Cataract', 'Other'):
                raise ValueError('Diagnostico nao previsto')
            image = Path(r['image'])
            with image.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if digest in seen:
                raise ValueError(f'Imagem duplicada: {seen[digest]} / {image.name}')
            seen[digest] = image.name
            selected.append({'image': str(image), 'subject': r['id'], 'side': r['eye_side'],
                             'label': int(r['diagnosis'] != 'Normal'), 'diagnosis_raw': r['diagnosis'],
                             'source_split': split, 'sha256': digest})
        if not selected:
            raise ValueError('Particao vazia')
        splits[split] = selected
    ids = {k: {r['subject'] for r in v} for k, v in splits.items()}
    if any(ids[a] & ids[b] for a, b in [('train', 'val'), ('train', 'test'), ('val', 'test')]):
        raise ValueError('Vazamento de pessoas')
    out = ROOT / 'outputs/clinico_publico_2026-10-20'
    out.mkdir(parents=True, exist_ok=True)
    manifest_content = json.dumps(splits, ensure_ascii=False, indent=2).encode('utf-8')
    manifest_hash = hashlib.sha256(manifest_content).hexdigest()
    protocol_path = out / 'protocolo_pre_registrado.json'
    if protocol_path.exists():
        previous = json.loads(protocol_path.read_text(encoding='utf-8'))
        if previous['manifest_sha256'] != manifest_hash:
            raise ValueError('Manifesto mudou; usar nova versao do experimento')
        print('Protocolo existente preservado:', protocol_path)
        return
    protocol = {
        'registered_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'prepared_not_executed', 'dataset': 'CatScreen public sample Clean',
        'source': 'https://www.iab-rubric.org/resources/healthcare-datasets/catscreen',
        'source_manifest_sha256': hashlib.sha256(source_bytes).hexdigest(),
        'manifest_sha256': manifest_hash,
        'primary_task': 'Normal vs (Cataract or Other), using source labels; not specific diagnosis',
        'counts': {k: {'images': len(v), 'subjects': len(ids[k]),
                       'classes': dict(Counter(r['label'] for r in v)),
                       'diagnoses': dict(Counter(r['diagnosis_raw'] for r in v))} for k, v in splits.items()},
        'split': 'official split, metadata subject disjoint, no exact image duplicates',
        'primary_classifier': 'ResNet18 ImageNet frozen CNN + trained binary linear head',
        'branches': ['original', 'unet_iris_bbox_context', 'unet_iris_masked_same_bbox'],
        'segmentation': 'UBIPr U-Net selected on UBIPr validation, frozen before clinical extraction',
        'paired_control': 'same padded bbox for context and iris-mask branches; original is full image',
        'empty_masks': 'black masked image and full-frame bbox, no sample exclusion; report failures',
        'seeds': [42, 123, 2026], 'size': [224, 224],
        'selection': 'clinical validation only; no test-driven architecture, thresholds or preprocessing',
        'primary_metric': 'paired difference in test AUROC, masked minus original',
        'secondary_metrics': ['balanced_accuracy_at_0.5', 'sensitivity_at_0.5', 'specificity_at_0.5',
                              'macro_f1_at_0.5', 'confusion_matrix', 'mask_failure_rate'],
        'uncertainty': '5000 paired subject bootstrap replicates on fixed test predictions; exploratory sample',
        'external_candidate': 'SLID frozen test only, after label/terms/overlap audit; no patient ID available for cluster CI',
        'restrictions': ['no Noisy/Unlabelled in supervised main experiment',
                         'no mixing healthy controls across sensors to construct disease labels',
                         'no claim of clinical diagnosis or biometric identity performance',
                         'SLP-VLD eligibility may lead to a separately registered replacement before test scoring'],
    }
    (out / 'manifesto.json').write_bytes(manifest_content)
    protocol_path.write_text(json.dumps(protocol, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(protocol, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

"""Registra estudo clinico antes dos escores, com grupos conservadores e deduplicacao."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from sklearn.model_selection import StratifiedGroupKFold
from auditar_catscreen import records

ROOT = Path(__file__).resolve().parent


def main():
    source = ROOT / 'data/slpvld/manifesto.json'
    rows = json.loads(source.read_text(encoding='utf-8'))
    parents = {}
    def find(a):
        parents.setdefault(a, a)
        if parents[a] != a:
            parents[a] = find(parents[a])
        return parents[a]
    def union(a, b):
        a, b = find(a), find(b)
        parents[max(a, b)] = min(a, b)
    workbook = next((ROOT / 'data/slpvld/release').rglob('zhaohui_description.xlsx'))
    by_metadata = defaultdict(set)
    for row in records(workbook.read_bytes()):
        match = re.match(r'^(P\d+)_', Path(row['image_id']).stem, re.I)
        if match:
            prefix = match[1].upper()
            find(prefix)
            if row.get('ID'):
                by_metadata[row['ID']].add(prefix)
    for codes in by_metadata.values():
        codes = sorted(codes)
        for code in codes[1:]:
            union(codes[0], code)
    hashes = defaultdict(list)
    for row in rows:
        hashes[row['sha256']].append(row)
    keep, removed, conflicting = [], [], []
    for digest, matches in sorted(hashes.items()):
        if len({r['label_binary'] for r in matches}) > 1:
            conflicting.extend(matches)
            continue
        if len({r['source_split'] for r in matches}) > 1:
            raise ValueError('Duplicata entre desenvolvimento e teste externo')
        matches.sort(key=lambda r: r['image'])
        keep.append(matches[0])
        removed.extend(matches[1:])
    development = [dict(r, subject=find(r['subject'])) for r in keep if r['source_split'] == 'development']
    external = [dict(r, subject='external_' + r['subject']) for r in keep if r['source_split'] == 'external']
    development.sort(key=lambda r: r['image'])
    labels = [r['label_binary'] for r in development]
    groups = [r['subject'] for r in development]
    assignment = {}
    cv = StratifiedGroupKFold(n_splits=7, shuffle=True, random_state=42)
    for fold, (_, indexes) in enumerate(cv.split([[0]] * len(labels), labels, groups)):
        for i in indexes:
            assignment[int(i)] = 'test' if fold == 0 else ('val' if fold == 1 else 'train')
    splits = {s: [r for i, r in enumerate(development) if assignment[i] == s] for s in ('train', 'val', 'test')}
    splits['external_bijie'] = external
    ids = {s: {r['subject'] for r in v} for s, v in splits.items()}
    if any(ids[a] & ids[b] for a, b in [('train', 'val'), ('train', 'test'), ('val', 'test')]):
        raise ValueError('Vazamento de grupos')
    if any(len({r['label_binary'] for r in splits[s]}) < 2 for s in splits):
        raise ValueError('Particao sem ambas as classes')
    out = ROOT / 'outputs/clinico_slpvld_2026-10-20'
    out.mkdir(parents=True, exist_ok=True)
    content = json.dumps(splits, ensure_ascii=False, indent=2).encode('utf-8')
    digest = hashlib.sha256(content).hexdigest()
    target = out / 'protocolo_pre_registrado.json'
    if target.exists():
        if json.loads(target.read_text(encoding='utf-8'))['manifest_sha256'] != digest:
            raise ValueError('Manifesto diferente: usar nova versao')
        print('Protocolo existente preservado')
        return
    protocol = {
        'registered_utc': datetime.now(timezone.utc).isoformat(), 'status': 'prepared_not_executed',
        'dataset': 'SLP-VLD public v3', 'source': 'https://doi.org/10.6084/m9.figshare.32576697.v3',
        'license': 'CC BY 4.0', 'manifest_sha256': digest,
        'task': 'Exact source label Normal eye vs other annotated ocular conditions; not autonomous clinical diagnosis',
        'label_source': 'Diagnosis column in released XLSX, not VLM assistant responses',
        'grouping': 'Connected components of P#### filename prefixes sharing any metadata ID; all eyes/dates stay together',
        'original_prefixes': len(set(r['subject'] for r in rows if r['source_split'] == 'development')),
        'conservative_development_groups': len(set(groups)),
        'grouping_limitation': 'Original patient mapping excluded from release; independence beyond released identifiers not established',
        'exact_duplicate_rows_removed': len(removed), 'conflicting_duplicate_rows_excluded': len(conflicting),
        'split_rule': 'StratifiedGroupKFold(7, shuffle=True, random_state=42): fold0 test, fold1 validation, folds2-6 train; Bijie untouched external',
        'counts': {s: {'images': len(v), 'groups': len(ids[s]),
                      'classes': dict(Counter(r['label_binary'] for r in v))} for s, v in splits.items()},
        'segmentation': 'Frozen UBIPr U-Net selected only on UBIPr validation; record final checkpoint SHA before clinical extraction',
        'classifier': 'ResNet18 ImageNet IMAGENET1K_V1 frozen eval CNN and trained Linear(512,1) head',
        'branches': ['original', 'unet_iris_bbox_context', 'unet_iris_masked_same_bbox'],
        'preprocessing': 'bbox margin 25% of bbox width/height; masked and context branches share bbox; resize224 bilinear; ImageNet normalization',
        'empty_masks': 'Full-frame context bbox; masked image all black; count failure and retain sample',
        'head_training': {'seeds': [42, 123, 2026], 'optimizer': 'AdamW', 'learning_rate': 0.001,
                          'weight_decay': 0.0001, 'max_epochs': 100, 'patience': 15,
                          'batch': 'full training feature matrix',
                          'loss': 'BCEWithLogitsLoss(pos_weight=n_normal_train/n_altered_train)',
                          'selection': 'highest validation AUROC; ties keep earliest epoch',
                          'feature_standardization': 'no fitted standardization; frozen CNN ImageNet features'},
        'primary_prediction': 'Mean probability of the three seed heads, per branch; also report each seed',
        'primary_metric': 'Paired internal-test AUROC difference, masked minus original',
        'secondary_metrics': ['balanced_accuracy', 'sensitivity', 'specificity', 'macro_f1', 'confusion_matrix', 'mask_failure_rate'],
        'threshold': 0.5,
        'uncertainty': '5000 paired bootstrap replicates of conservative subject groups, fixed predictions; report discarded single-class replicates',
        'external': 'Bijie99 plus CatScreen Clean as separately labeled secondary domain; no fitting thresholds or preprocessing on external scores',
        'excluded_from_primary': ['SLID due to absent patient linkage and separate data-license uncertainty',
                                  'Nuclear Cataract severity-only selected subset', 'SLP VLM reports as predictive input'],
        'replacement_rationale': 'Larger public labeled cohort with normal controls and grouping, selected before any clinical test scores. Earlier CatScreen protocol not executed.',
    }
    (out / 'manifesto.json').write_bytes(content)
    target.write_text(json.dumps(protocol, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(protocol, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

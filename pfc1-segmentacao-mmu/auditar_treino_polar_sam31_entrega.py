"""Reconta a seleção e verifica os pesos congelados, sem inferência nem ajuste."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
import numpy as np
import torch

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def eligible(results, reference):
    clean = results['original']
    control = reference['original']
    return (clean['rank1'] >= control['rank1'] and clean['tar'] >= control['tar']
            and clean['far'] <= .01
            and all(results[c]['far'] <= reference[c]['far']
                    for c in ('oclusao_superior', 'oclusao_inferior'))
            and np.mean([v['joint_success'] for v in results.values()])
            > np.mean([v['joint_success'] for v in reference.values()]))


def key(results):
    return (float(np.mean([v['joint_success'] for v in results.values()])),
            min(v['joint_success'] for v in results.values()),
            float(np.mean([v['rank1'] for v in results.values()])))


def frozen_name(name):
    trainable = name.startswith(('backbone.layer4.', 'projection.'))
    buffer = name.endswith(('running_mean', 'running_var', 'num_batches_tracked'))
    return not trainable or buffer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', type=Path, required=True)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    protocol = read(run / 'protocolo.json')
    done = read(run / 'CONCLUIDO.json')
    history = read(run / 'historico.json')
    reference = read(run / 'BASELINE_ORIGINAL.json')
    assert done['status'] == 'concluido' and reference == done['baseline']
    assert [h['epoch'] for h in history] == list(range(done['epochs_completed'] + 1))
    manifest_file = ROOT / 'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    assert sha(manifest_file) == protocol['manifest_sha256']
    manifest = read(manifest_file)
    indices = protocol['training_subset_indices']
    assert len(indices) == len(set(indices)) == done['training_images'] == 1028
    training_people = {manifest['train'][i]['subject'] for i in indices}
    assert len(training_people) == protocol['counts']['train_people']
    assert not training_people & {r['subject'] for r in manifest['val']}
    assert not training_people & {r['subject'] for r in manifest['test']}
    for name, expected in protocol['sources_sha256'].items():
        assert sha(ROOT / name) == expected, name
    selected = None
    best = None
    decisions = []
    for record in history:
        results = record['results']
        assert all(v['queries'] == 482 for v in results.values())
        assert all(math.isfinite(v[k]) for v in results.values()
                   for k in ('rank1', 'tar', 'far', 'joint_success'))
        passes = bool(eligible(results, reference))
        assert passes == record['eligible']
        if passes and (best is None or key(results) > best):
            selected, best = record['epoch'], key(results)
        assert selected == record['selected_epoch']
        decisions.append({'epoch': record['epoch'], 'eligible_recounted': passes,
                          'selected_epoch_recounted': selected})
    assert selected == done['selected_epoch']
    assert (selected is not None) == done['eligible_gain']
    initial_file = ROOT / 'outputs/encoder_polar_2026-10-20/melhor_modelo.pt'
    assert sha(initial_file) == protocol['initial_checkpoint_sha256']
    original = torch.load(initial_file, map_location='cpu', weights_only=True)['model']
    last = torch.load(run / 'ultima_epoca.pt', map_location='cpu', weights_only=True)
    assert last['epoch'] == done['epochs_completed']
    checkpoints = [('last', last)]
    if selected is not None:
        assert sha(run / 'melhor_modelo.pt') == done['checkpoint_sha256']
        candidate = torch.load(run / 'melhor_modelo.pt', map_location='cpu', weights_only=True)
        assert candidate['epoch'] == selected and candidate['validation'] == done['results']
        checkpoints.append(('selected', candidate))
    else:
        assert not (run / 'melhor_modelo.pt').exists()
        assert done['results'] == reference
    checked = {}
    for label, checkpoint in checkpoints:
        state = checkpoint['model']
        assert list(state) == list(original)
        digest = hashlib.sha256()
        frozen = 0
        for name, value in state.items():
            assert torch.isfinite(value).all(), name
            if frozen_name(name):
                assert torch.equal(value, original[name]), name
                digest.update(name.encode())
                digest.update(value.contiguous().numpy().tobytes())
                frozen += 1
        assert digest.hexdigest() == done['frozen_parameters_sha256']
        checked[label] = {'frozen_tensors_bitwise_equal': frozen,
                          'frozen_sha256': digest.hexdigest()}
    result = {'status': 'verified', 'utc': datetime.now(timezone.utc).isoformat(),
              'selected_epoch': selected, 'selection_recounted': decisions,
              'all_validation_queries_retained': 482, 'train_images': len(indices),
              'train_people': len(training_people), 'train_validation_test_people_disjoint': True,
              'checkpoints_verified': checked, 'sources_unchanged': True,
              'test_inference_performed_by_this_audit': False,
              'recognizer_replaced': False,
              'inputs_sha256': {name: sha(run / name) for name in
                  ('protocolo.json', 'CONCLUIDO.json', 'historico.json', 'ultima_epoca.pt')},
              'auditor_sha256': sha(__file__)}
    output = run / 'analise'
    output.mkdir(exist_ok=True)
    (output / 'AUDITORIA_TREINO_FINAL.json').write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()

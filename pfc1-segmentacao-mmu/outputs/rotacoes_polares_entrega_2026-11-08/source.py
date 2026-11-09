"""Dois candidatos fixos de média de rotações; somente validação reutilizada."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, traceback
import numpy as np
import torch
from treinar_identidade_iris import IdentityEncoder
from avaliar_candidato_congelado import extract, global_scores, fuse, WEIGHTS
from avaliar_robustez_reconhecimento import load_splits, identity, metrics
from validar_lateralidade_informada import subset
from treinar_reconhecedor_entrega import ORDER, CONDITIONS, eligibility, selection_key
from rodada_reconhecedor_entrega import write, result_path

ROOT = Path(__file__).resolve().parent
OFFSETS = (0, 128, 256, 384)
ALPHAS = (.5, 1.)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', type=Path, required=True)
    p.add_argument('--reference-root', type=Path, required=True)
    a = p.parse_args()
    run = a.run_dir.resolve()
    run.mkdir(parents=True, exist_ok=False)
    reference = a.reference_root.resolve()
    checkpoint = ROOT / 'outputs/encoder_polar_2026-10-20/melhor_modelo.pt'
    assert sha(checkpoint) == WEIGHTS['polar'][1]
    frozen = ROOT / 'outputs/candidato_congelado_2026-10-21/CONGELADO.json'
    manifest = ROOT / 'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    config = json.loads(frozen.read_text())
    rows = load_splits(json.loads(manifest.read_text()))['val']
    files = {}
    for condition, level in CONDITIONS:
        suffix = '' if condition == 'original' else f'_{condition}_{level}'
        cache = reference / f'nearest/cache_confirmacao_val{suffix}_2026-10-21'
        for name in ('polar.npy', 'valid.npz'):
            f = cache / name
            files[str(f)] = sha(f)
        for name in ORDER:
            f = result_path(reference, 'nearest', condition, level) / f'scores_{name}.npz'
            files[str(f)] = sha(f)
    sources = {n: sha(ROOT / n) for n in ('avaliar_rotacoes_polares_entrega.py',
        'treinar_identidade_iris.py', 'avaliar_candidato_congelado.py',
        'avaliar_robustez_reconhecimento.py', 'normalizar_consulta.py')}
    protocol = {'registered_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Exploratory reused validation; no training or test inference',
        'offsets_columns': OFFSETS, 'raw_polar_score_alphas': ALPHAS,
        'method': 'Mean four unit embeddings then normalize; same rotations for enrollment and query. Change only global polar component. No texture completion, threshold or fusion calibration change.',
        'selection': 'Original reference: clean Rank1/TAR no lower, clean FMR<=1%, each occluded FMR no greater, mean joint higher. Max mean joint, worst joint, mean Rank1. No eligible=>retain reference.',
        'sources_sha256': sources, 'inputs_sha256': files,
        'checkpoint_sha256': sha(checkpoint), 'calibration_sha256': sha(frozen),
        'manifest_sha256': sha(manifest), 'validation_queries': 482,
        'torch': str(torch.__version__), 'automatic_replacement': False}
    write(run / 'protocolo.json', protocol)
    (run / 'source.py').write_bytes(Path(__file__).read_bytes())
    try:
        torch.set_num_threads(4)
        torch.backends.cudnn.benchmark = False
        device = torch.device('cuda')
        model = IdentityEncoder().to(device).eval()
        model.load_state_dict(torch.load(checkpoint, map_location='cpu', weights_only=True)['model'])
        ids = sorted({identity(r) for r in rows})
        baseline, results = {}, {str(alpha): {} for alpha in ALPHAS}
        for condition, level in CONDITIONS:
            components = []
            for name in ORDER:
                with np.load(result_path(reference, 'nearest', condition, level) / f'scores_{name}.npz') as z:
                    components.append({k: z[k].copy() for k in ('scores', 'labels', 'valid')})
            suffix = '' if condition == 'original' else f'_{condition}_{level}'
            cache = reference / f'nearest/cache_confirmacao_val{suffix}_2026-10-21'
            images = np.load(cache / 'polar.npy', mmap_mode='r')
            with np.load(cache / 'valid.npz') as z:
                valid = z['polar'].copy()
            features = []
            for offset in OFFSETS:
                write(run / 'estado.json', {'stage': 'extraindo', 'condition': condition,
                    'offset': offset, 'total_offsets': 4, 'utc': datetime.now(timezone.utc).isoformat()})
                value = extract(model, images if offset == 0 else np.roll(images, offset, axis=2), device)
                if offset == 0:
                    full, query_valid = global_scores(value, valid, rows)
                    scores, labels, _ = subset(full, rows, ids)
                    np.testing.assert_array_equal(labels, components[1]['labels'])
                    np.testing.assert_array_equal(query_valid, components[1]['valid'])
                    np.testing.assert_allclose(scores, components[1]['scores'], atol=1e-10, rtol=0)
                features.append(value.astype(np.float64))
            average = np.mean(features, axis=0)
            average /= np.maximum(np.linalg.norm(average, axis=1, keepdims=True), 1e-12)
            full, query_valid = global_scores(average, valid, rows)
            rotated, labels, _ = subset(full, rows, ids)
            np.savez_compressed(run / f'polar_rotated_{condition}.npz', scores=rotated,
                labels=labels, valid=query_valid)
            for alpha in (0.,) + ALPHAS:
                items = components.copy()
                if alpha:
                    replacement = components[1].copy()
                    replacement['scores'] = ((1-alpha)*components[1]['scores'] + alpha*rotated)
                    replacement['scores'][components[1]['scores'] <= -2] = -2
                    items[1] = replacement
                fused, fv = fuse(items, config['component_calibration_red_and_clahe'])
                m, correct, accepted = metrics(fused, labels, config['frozen_threshold'], fv)
                m['joint_success'] = float((correct & accepted).mean())
                assert m['queries'] == 482
                if alpha == 0:
                    baseline[condition] = m
                else:
                    results[str(alpha)][condition] = m
                np.savez_compressed(run / f'fusion_alpha{alpha}_{condition}.npz', scores=fused,
                    labels=labels, valid=fv, correct=correct, accepted=accepted)
            print(json.dumps({'condition': condition, 'results': {k:v[condition] for k,v in results.items()}}), flush=True)
        eligible = [k for k, value in results.items() if eligibility(value, baseline)]
        selected = max(eligible, key=lambda k: selection_key(results[k])) if eligible else None
        for name, expected in sources.items():
            assert sha(ROOT / name) == expected
        final = {'status': 'concluido', 'selected_alpha': selected,
            'eligible_gain': selected is not None, 'baseline': baseline, 'results': results,
            'test_inference': False, 'recognizer_replaced': False,
            'unrotated_reference_scores_reproduced': True}
        write(run / 'CONCLUIDO.json', final)
        lines = ['# Rotações polares na extração de características', '',
            f'Candidato elegível: {selected or "nenhum"}. Limiar e pesos históricos fixos.', '',
            '| Versão | Condição | Rank-1 | TAR | FMR | Correto e aceito |',
            '|---|---|---:|---:|---:|---:|']
        for name, data in {'reference':baseline, **results}.items():
            for condition, m in data.items():
                lines.append(f"| {name} | {condition} | {100*m['rank1']:.2f}% | {100*m['tar']:.2f}% | {100*m['far']:.3f}% | {100*m['joint_success']:.2f}% |")
        (run / 'RELATORIO_ATUAL.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
        write(run / 'estado.json', {'stage':'concluido', 'eligible_gain':selected is not None})
        print(json.dumps(final), flush=True)
    except Exception as error:
        write(run / 'estado.json', {'stage':'falha', 'error':str(error)})
        (run / 'ERRO.txt').write_text(traceback.format_exc(), encoding='utf-8')
        raise


if __name__ == '__main__':
    main()

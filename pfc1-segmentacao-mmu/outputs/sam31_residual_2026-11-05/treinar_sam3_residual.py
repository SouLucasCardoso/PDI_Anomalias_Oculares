"""Treina correcao residual RGB+SAM3.1, mantendo o adaptador-base congelado."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import importlib.metadata
import json
import math
import os
from pathlib import Path
import traceback

import cv2
import torch
from torch.utils.data import DataLoader

from perda_negativos_internos import checkpoint
from segmentador_sam3_iris import SAM_REVISION, iris_loss
from segmentador_sam3_residual import IrisSam3Residual, MODEL_TYPE, MODEL_CONFIG
from treinar_sam3_iris_adaptado import CachedEyes, evaluate, manifest, read_index, sha, specifications
from treinar_segmentacao_diversa import MODES, save_json
from treinar_segmentacao_ubipr import set_seed

ROOT = Path(__file__).resolve().parent
PARENT = ROOT / 'outputs/sam31_iris_adaptacao_2026-11-03'
PARENT_SHA = 'cf8a718e0160c14408d1533445ff611b00a79c75d2c0fd07fb7540150e59db99'
SOURCES = ('treinar_sam3_residual.py', 'segmentador_sam3_residual.py', 'avaliar_identidade_sam3_residual.py',
           'executar_sam3_residual.py', 'analisar_sam3_residual.py', 'executar_sam3_negativos_resiliente.py',
           'perda_negativos_internos.py', 'treinar_sam3_iris_adaptado.py', 'segmentador_sam3_iris.py',
           'treinar_segmentacao_diversa.py', 'treinar_segmentacao_ubipr.py', 'avaliar_sam31_diverso.py')
PACKAGES = ('torch', 'torchvision', 'sam3', 'numpy', 'pillow')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def cache_binding(cache, data, parent):
    """Reutiliza o cache fechado; nao o reconstrui nem muda sua semente."""
    frozen = parent['frozen']
    binding = read(cache / 'protocolo.json')
    completed = read(cache / 'CONCLUIDO.json')
    expected = specifications(data)
    if (binding['seed'] != 20261103 or binding['limit'] is not None or
            binding['manifest_sha256'] != frozen['manifest_sha256'] or
            binding['sources'] != frozen['sources'] or binding['sam_revision'] != SAM_REVISION or
            completed['count'] != len(expected) or sha(cache / 'index.jsonl') != completed['index_sha256']):
        raise ValueError('Cache anterior incompleto ou de outra origem')
    index = read_index(cache / 'index.jsonl')
    if len(index) != len(expected) or set(index) != {r['key'] for r in expected}:
        raise ValueError('Cobertura do cache divergente')
    if sha(cache / 'index.jsonl') != completed['index_sha256']:
        raise ValueError('Indice fechado foi modificado')
    return index, {'path': str(cache), 'cached_view_seed': 20261103,
                   'count': completed['count'], 'index_sha256': completed['index_sha256'],
                   'protocol_sha256': sha(cache / 'protocolo.json'),
                   'npz_hash_checked_on_every_read': True}


def compact(measured):
    return {m: {k: v for k, v in r.items() if k != 'records'} for m, r in measured.items()}


def model_payload(model, epoch, validation, protocol_sha, cache_sha):
    return {'model': {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
            'model_type': MODEL_TYPE, 'configuration': dict(MODEL_CONFIG),
            'sam_revision': SAM_REVISION, 'epoch': epoch, 'validation': validation,
            'training_protocol_sha256': protocol_sha, 'cache_index_sha256': cache_sha,
            'parent_checkpoint_sha256': PARENT_SHA}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'cache', 'mirror'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--epochs', type=int, default=24)
    parser.add_argument('--batch-size', type=int, default=8)
    parser.add_argument('--seed', type=int, default=20261105)
    args = parser.parse_args()
    if min(args.epochs, args.batch_size) < 1 or (args.limit is not None and args.limit < 1):
        raise ValueError('Parametros invalidos')
    out, mirror = args.run, args.mirror
    out.mkdir(parents=True, exist_ok=True)
    mirror.mkdir(parents=True, exist_ok=True)
    manifest_file, data = manifest()
    parent = read(PARENT / 'protocolo.json')
    final_parent = read(PARENT / 'CONCLUIDO.json')
    initial = PARENT / f'candidato_epoca_{final_parent["best_epoch"]:02}.pt'
    if final_parent['checkpoint_sha256'] != PARENT_SHA or sha(initial) != PARENT_SHA:
        raise ValueError('Pesos de inicializacao divergentes')
    if not (PARENT / 'identidade/CONCLUIDO.json').exists():
        raise ValueError('A comparacao anterior deve estar encerrada')
    if sha(manifest_file) != parent['frozen']['manifest_sha256']:
        raise ValueError('Manifesto alterado')
    for name, expected in parent['frozen']['sources'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('Fonte do cache alterada: ' + name)
    versions = {name: importlib.metadata.version(name) for name in PACKAGES}
    origin = json.loads(importlib.metadata.distribution('sam3').read_text('direct_url.json'))
    if versions != parent['frozen']['versions'] or origin != parent['frozen']['sam_origin']:
        raise ValueError('Manter ambiente compativel com o cache e o controle')
    sam = read(ROOT / 'outputs/sam31_atual_prompts_2026-11-03/protocolo.json')
    if sha(Path(sam['checkpoint'])) != parent['frozen']['sam_checkpoint_sha256']:
        raise ValueError('Checkpoint SAM3 oficial alterado')
    verification_file = ROOT / 'outputs/tecnologias_atuais_2026-11-05/VERIFICACAO_OFICIAL.json'
    verification = read(verification_file)
    if (verification['sam_code']['sha'] != SAM_REVISION or
            verification['sam_checkpoint']['revision'] != 'daa63191845a41281374e725f4c9e51c7a824460'):
        raise ValueError('Nova revisao oficial exige nova preparacao de ambiente/cache')
    if not (ROOT / 'outputs/sam31_negativos_internos_2026-11-04/fluxo/CONCLUIDO.json').exists():
        raise ValueError('Encerrar a rodada anterior antes de iniciar outra')
    index, reuse = cache_binding(args.cache, data, parent)
    configuration = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items() if k != 'prepare'}
    frozen = {'configuration': configuration, 'manifest_sha256': sha(manifest_file),
              'sources': {n: sha(ROOT / n) for n in SOURCES}, 'versions': versions,
              'sam_origin': origin, 'sam_checkpoint_sha256': sam['checkpoint_sha256'],
              'parent_checkpoint_sha256': PARENT_SHA, 'parent_protocol_sha256': sha(PARENT / 'protocolo.json'),
              'cache_reuse': reuse, 'official_latest_verification_sha256': sha(verification_file),
              'compatible_package_verification_sha256': sha(ROOT / 'outputs/tecnologias_atuais_2026-11-05/PACOTES_OFICIAIS.json')}
    protocol_file = mirror / 'protocolo.json'
    if protocol_file.exists():
        if read(protocol_file)['frozen'] != frozen:
            raise ValueError('Fontes, dados ou parametros mudaram: registrar outra rodada')
    else:
        if not args.prepare:
            raise ValueError('Registrar --prepare antes do treino')
        save_json(protocol_file, {
            'registered_utc': datetime.now(timezone.utc).isoformat(), 'frozen': frozen,
            'architecture': 'Frozen selected eight-channel RGB+SAM3 adapter plus independently trainable32-channel RGB+SAM3 residual U-Net. Frozen foundation, frozen base weights and BatchNorm. Residual classifier initialized to exactly zero; float32 logit correction=4*tanh(delta). Not full SAM3 finetuning.',
            'loss': 'Original boundary CE + iris Dice + 0.25 Tversky, FP0.7/FN0.3; no additional inner-negative penalty, no invented pupil labels. Unknown255 ignored. Optimize only correction parameters.',
            'selection': 'Include epoch0. Maximize minimum macroDice of four complete validation modes; clean >= epoch0clean-0.002; patience6. No identity or clinical labels select weights.',
            'optimization': {'optimizer': 'AdamW', 'lr': 1e-4, 'weight_decay': 1e-4,
                             'scheduler': 'CosineAnnealingLR', 'eta_min': 1e-5, 'grad_clip': 1,
                             'precision': 'BF16 forward, FP32 losses', 'fresh_optimizer': True,
                             'optimizer_order_and_bank_selection_seed': args.seed},
            'augmentation': 'Reuse original closed cache with native and diverse train banks, fixed seed20261103; four fixed validation modes. New seed selects only image order and existing bank, never regenerates cached images.',
            'baseline_guard': 'Fresh epoch0; difference <=0.001 Dice from parent in each mode. Zero correction preserves base logits exactly under same inputs/precision/batch; batch8 versus historical batch16 may have numerical differences.',
            'scope': 'Train/validation only. All cases retained; no new test or clinical inference in trainer. Human reviews may follow later.',
            'engineering_target_not_clinical_standard': {'all4_validation_macroDice': .90},
            'development_smoke_only': args.limit is not None})
        for name in SOURCES:
            (mirror / name).write_bytes((ROOT / name).read_bytes())
        (mirror / 'VERIFICACAO_OFICIAL.json').write_bytes(verification_file.read_bytes())
    if args.prepare:
        print('Protocolo registrado; cache fechado validado:', len(index), flush=True)
        return
    if (mirror / 'CONCLUIDO.json').exists():
        return
    with (mirror / 'execucao.log').open('a', encoding='utf-8', buffering=1) as log, redirect_stdout(log), redirect_stderr(log):
        try:
            protocol_sha = sha(protocol_file)
            cv2.setNumThreads(1)
            torch.set_num_threads(2)
            set_seed(args.seed)
            torch.backends.cudnn.benchmark = False
            if not torch.cuda.is_available():
                raise RuntimeError('GPU necessaria')
            if args.limit:
                data = {k: v[:args.limit] for k, v in data.items()}
            device = torch.device('cuda')
            model = IrisSam3Residual().to(device)
            model.initialize(torch.load(initial, map_location='cpu', weights_only=True)['model'])
            frozen_base = {k: v.detach().cpu().clone() for k, v in model.base.state_dict().items()}
            optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=1e-4, weight_decay=1e-4)
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, args.epochs, eta_min=1e-5)
            datasets = {m: CachedEyes(data['val'], 'val', m, args.cache, index, args.seed) for m in MODES}
            train = CachedEyes(data['train'], 'train', 'bank0', args.cache, index, args.seed)
            recovery = out / 'retomada.pt'
            save_json(out / 'status.json', {'stage': 'baseline_validation', 'pid': os.getpid(), 'epoch': 0})
            if recovery.exists():
                state = torch.load(recovery, map_location='cpu', weights_only=True)
                if state['protocol_sha256'] != protocol_sha or state['cache_index_sha256'] != reuse['index_sha256']:
                    raise ValueError('Retomada pertence a outro protocolo')
                model.load_state_dict(state['model'], strict=True)
                optimizer.load_state_dict(state['optimizer'])
                scheduler.load_state_dict(state['scheduler'])
                history, best_payload = state['history'], state['best_payload']
                best, stale, baseline = state['best'], state['stale'], state['baseline']
                next_epoch, completed, totals = state['next_epoch'], state['completed_batches'], state['totals']
            else:
                model.initialize(torch.load(initial, map_location='cpu', weights_only=True)['model'])
                model.eval()
                rgb, _, features, _ = next(iter(DataLoader(train, batch_size=args.batch_size, num_workers=0)))
                rgb, features = rgb.to(device), features.to(device)
                equivalence = {}
                with torch.inference_mode():
                    for precision in ('float32', 'bfloat16'):
                        with torch.autocast('cuda', dtype=torch.bfloat16, enabled=precision == 'bfloat16'):
                            expected = model.base(rgb, features).float()
                            actual = model(rgb, features)
                        if not torch.equal(actual, expected):
                            raise ValueError('Cabeca zero alterou logits de inicializacao: ' + precision)
                        equivalence[precision] = {'exact_logits': True, 'images': len(rgb)}
                save_json(mirror / 'ZERO_EQUIVALENCIA.json', equivalence)
                del rgb, features, actual, expected
                measured = {m: evaluate(model, d, device, args.batch_size, out) for m, d in datasets.items()}
                save_json(mirror / 'validacao_epoca_00.json', measured)
                measured = compact(measured)
                if not args.limit:
                    for m in MODES:
                        if abs(measured[m]['macro_dice'] - final_parent['validation'][m]['macro_dice']) > .001:
                            raise ValueError('Controle de epoca0 nao reproduziu o pai: ' + m)
                baseline = measured['clean']['macro_dice']
                best = min(r['macro_dice'] for r in measured.values())
                best_payload = model_payload(model, 0, measured, protocol_sha, reuse['index_sha256'])
                history = [{'epoch': 0, 'validation': measured, 'score': best}]
                stale, next_epoch, completed, totals = 0, 1, 0, [0., 0]

            def snapshot(epoch, batches, sums):
                checkpoint(recovery, {'model': model.state_dict(), 'optimizer': optimizer.state_dict(),
                           'scheduler': scheduler.state_dict(), 'history': history, 'best_payload': best_payload,
                           'best': best, 'stale': stale, 'baseline': baseline, 'next_epoch': epoch,
                           'completed_batches': batches, 'totals': list(sums),
                           'protocol_sha256': protocol_sha, 'cache_index_sha256': reuse['index_sha256']})

            if not recovery.exists():
                snapshot(next_epoch, completed, totals)
            for epoch in range(next_epoch, args.epochs + 1):
                if stale >= 6:
                    break
                train.epoch_index = epoch
                order = torch.randperm(len(train), generator=torch.Generator().manual_seed(args.seed + epoch)).tolist()
                loader = DataLoader(train, batch_size=args.batch_size, sampler=order[completed * args.batch_size:],
                                    num_workers=0, generator=torch.Generator().manual_seed(args.seed + epoch))
                save_json(out / 'status.json', {'stage': 'training', 'pid': os.getpid(), 'epoch': epoch,
                                              'best_epoch': best_payload['epoch']})
                model.train()
                batches = math.ceil(len(train) / args.batch_size)
                for step, (rgb, target, features, _) in enumerate(loader, completed + 1):
                    optimizer.zero_grad(set_to_none=True)
                    with torch.autocast('cuda', dtype=torch.bfloat16):
                        logits = model(rgb.to(device), features.to(device))
                    loss = iris_loss(logits, target.to(device))
                    if not torch.isfinite(loss):
                        raise FloatingPointError('Perda nao finita')
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1)
                    optimizer.step()
                    totals[0] += float(loss.detach()) * len(rgb)
                    totals[1] += len(rgb)
                    if step == completed + 1 or step % 25 == 0 or step == batches:
                        snapshot(epoch, step, totals)
                        save_json(out / 'progresso.json', {'stage': 'training', 'epoch': epoch, 'batch': step,
                                                         'batches': batches, 'loss': totals[0] / totals[1]})
                if any(not torch.equal(v.detach().cpu(), frozen_base[k]) for k, v in model.base.state_dict().items()):
                    raise ValueError('Pesos ou estatisticas do modelo-base foram alterados')
                measured = {m: evaluate(model, d, device, args.batch_size, out) for m, d in datasets.items()}
                save_json(mirror / f'validacao_epoca_{epoch:02}.json', measured)
                measured = compact(measured)
                score = min(r['macro_dice'] for r in measured.values())
                eligible = measured['clean']['macro_dice'] >= baseline - .002
                history.append({'epoch': epoch, 'validation': measured, 'score': score, 'eligible': eligible,
                                'train_loss': totals[0] / totals[1]})
                if eligible and score > best:
                    best, stale = score, 0
                    best_payload = model_payload(model, epoch, measured, protocol_sha, reuse['index_sha256'])
                else:
                    stale += 1
                scheduler.step()
                completed, totals = 0, [0., 0]
                snapshot(epoch + 1, 0, totals)
                save_json(out / 'historico.json', history)
                print(json.dumps({'epoch': epoch, 'score': score, 'best_epoch': best_payload['epoch'], 'stale': stale}), flush=True)
            # A melhor inferencia fica dentro da retomada atomica, sem pesos adiantados ao historico.
            canonical = out / 'melhor_modelo.pt'
            candidate = mirror / f'candidato_epoca_{best_payload["epoch"]:02}.pt'
            checkpoint(canonical, best_payload)
            checkpoint(candidate, best_payload)
            if sha(canonical) != sha(candidate):
                raise ValueError('Serializacao canonica e espelho divergentes')
            final = {'status': 'completed', 'best_epoch': best_payload['epoch'], 'checkpoint_sha256': sha(candidate),
                     'best_score': best, 'validation': best_payload['validation'], 'epochs_completed': len(history) - 1,
                     'parent_checkpoint_sha256': PARENT_SHA, 'base_weights_and_buffers_frozen_verified': True, 'improved_segmentation_selection': best_payload['epoch'] > 0,
                     'segmentation_engineering_target_passed': all(v['macro_dice'] >= .9 for v in best_payload['validation'].values()),
                     'trainable_parameters': sum(p.numel() for p in model.parameters() if p.requires_grad),
                     'frozen_parameters': sum(p.numel() for p in model.parameters() if not p.requires_grad),
                     'peak_cuda_allocated_bytes': torch.cuda.max_memory_allocated(),
                     'peak_cuda_reserved_bytes': torch.cuda.max_memory_reserved(),
                     'clinical_masks_reviewed': False, 'recognition_measured': False, 'test_inference': False,
                     'development_smoke_only': args.limit is not None}
            save_json(out / 'CONCLUIDO.json', final)
            save_json(mirror / 'CONCLUIDO.json', final)
            save_json(out / 'status.json', {'stage': 'completed', 'pid': os.getpid(), 'best_epoch': best_payload['epoch']})
        except BaseException as error:
            traceback.print_exc()
            save_json(out / 'status.json', {'stage': 'failed', 'pid': os.getpid(), 'error': repr(error)})
            raise


if __name__ == '__main__':
    main()

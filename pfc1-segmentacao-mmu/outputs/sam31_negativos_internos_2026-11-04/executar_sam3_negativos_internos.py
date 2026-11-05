"""Rodada finita retomavel: treino, identidade auditada e grade condicional de area."""
from datetime import datetime, timezone
import argparse
import ctypes
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
BASE = ROOT / 'outputs/sam31_negativos_internos_2026-11-04'
PARENT = ROOT / 'outputs/sam31_iris_adaptacao_2026-11-03'
FLOW = BASE / 'fluxo'
LOSSES = (0, 1, 2, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90)
FILES = ('executar_sam3_negativos_internos.py', 'analisar_sam3_negativos_internos.py',
         'acompanhar_prontidao_anomalias.py', 'avaliar_identidade_sam3_adaptado.py',
         'avaliar_clinica_sam3_adaptado.py', 'avaliar_prontidao_anomalias.py',
         'criterios_prontidao_anomalias.json', 'segmentador_sam3_iris.py',
         'avaliar_candidato_congelado.py', 'analisar_rodada_segmentacao_area.py',
         'analisar_sam3_area.py', 'analisar_sensibilidade_referencia_area.py')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.part')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    tmp.replace(path)


def register():
    FLOW.mkdir(parents=True, exist_ok=True)
    training = read(BASE / 'protocolo.json')
    run = Path(training['frozen']['configuration']['run'])
    cohort = PARENT / 'grade_area_ubipr/consultas.json'
    cohort_final = read(cohort.parent / 'CONCLUIDO.json')
    if sha(cohort) != cohort_final['artifacts_sha256']['consultas.json']:
        raise ValueError('Coorte de referencias de area alterada')
    binding = {'sources': {n: sha(ROOT / n) for n in FILES},
               'versions': {n: importlib.metadata.version(n) for n in ('torch', 'torchvision', 'numpy', 'pillow', 'sam3')},
               'area_loss_grid': list(LOSSES), 'training_protocol_sha256': sha(BASE / 'protocolo.json'),
               'cohort_sha256': sha(cohort), 'identity_temp': str(run.parent / 'pfc-s3-inner-id-20261104'),
               'frozen_sha256': sha(ROOT / 'outputs/candidato_congelado_2026-10-21/CONGELADO.json'),
               'criteria_sha256': sha(ROOT / 'criterios_prontidao_anomalias.json')}
    for n, digest in training['frozen']['sources'].items():
        if sha(ROOT / n) != digest:
            raise ValueError('Fonte do treino alterada: ' + n)
    file = FLOW / 'protocolo_fluxo.json'
    if file.exists():
        old = read(file)
        if any(old[k] != v for k, v in binding.items()):
            raise ValueError('Fluxo registrado mudou')
    else:
        write(file, {'registered_utc': datetime.now(timezone.utc).isoformat(), **binding,
                     'identity_gate_includes_joint_success': True,
                     'selection': 'Only four-mode segmentation selects checkpoint. If epoch0 wins, no duplicate identity run; report unchanged parent and stop.',
                     'controls': 'Reuse the three completed original-UNet controls ONLY after raw-score/source/runtime/label audit; preserve evidence and explicit reuse record. New candidate gets exclusive temp namespace.',
                     'minimum_rule': 'All482queries primary; additionally require defined-reference472 prefix. Complete registered grid in both orientations, no interpolation.',
                     'no_test_inference': True, 'clinical_references_not_used_for_checkpoint_selection': True,
                     'no_automatic_anomaly_inference': True})
        for n in FILES:
            (FLOW / n).write_bytes((ROOT / n).read_bytes())
        (FLOW / 'consultas.json').write_bytes(cohort.read_bytes())
    if sha(FLOW / 'consultas.json') != binding['cohort_sha256']:
        raise ValueError('Copia da coorte divergente')
    return training, read(file)


def reuse_controls():
    import analisar_sam3_area as analysis
    analysis.BASE, analysis.OUT = PARENT, PARENT / 'analise_area'
    analysis.FLOW = ROOT / 'outputs/prontidao_anomalias_2026-11-03'
    training, flow = analysis.register()
    audited = analysis.audit_identity(training, flow)
    expected = {r['key'] for r in audited['records'] if r['segmenter'] == 'original'}
    if expected != {'original_original_0', 'original_oclusao_superior_10', 'original_oclusao_inferior_10'}:
        raise ValueError('Controles completos ausentes')
    reused = {}
    for key in sorted(expected):
        source = PARENT / 'identidade'
        destination = BASE / 'identidade'
        for file in [source / (key + '.json'), *(source / 'evidencias' / key).iterdir()]:
            if not file.is_file():
                continue
            target = destination / file.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and sha(target) != sha(file):
                raise ValueError('Controle copiado divergente')
            if not target.exists():
                target.write_bytes(file.read_bytes())
        reused[key] = {'source_record': str(source / (key + '.json')),
                       'record_sha256': sha(source / (key + '.json')),
                       'evidence_sha256': next(r['evidence_sha256'] for r in audited['records'] if r['key'] == key)}
    write(FLOW / 'REUSO_CONTROLES.json', {'raw_scores_reaudited': True, 'same_runtime_and_source': True,
                                       'new_control_inference': False, 'records': reused})


def identity_worker():
    training, flow = register()
    if Path(os.environ['TEMP']).resolve() != Path(flow['identity_temp']).resolve():
        raise ValueError('Identidade exige diretorio temporario exclusivo desta rodada')
    final = read(BASE / 'CONCLUIDO.json')
    if final['development_smoke_only'] or not final['improved_segmentation_selection']:
        raise ValueError('Sem novo candidato elegivel para identidade')
    checkpoint = BASE / f'candidato_epoca_{final["best_epoch"]:02}.pt'
    if sha(checkpoint) != final['checkpoint_sha256']:
        raise ValueError('Checkpoint alterado')
    reuse_controls()
    import acompanhar_prontidao_anomalias as identity
    identity.BASE, identity.OUT = BASE, FLOW
    if list(identity.LOSSES) != flow['area_loss_grid']:
        raise ValueError('Grade de area divergente')
    with (FLOW / 'identidade.log').open('a', encoding='utf-8', buffering=1) as log:
        identity.identity_assessment(checkpoint, log)


def report():
    from analisar_sam3_negativos_internos import render
    render()


def supervise(command, log, env, stage):
    child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=log)
    try:
        while child.poll() is None:
            write(FLOW / 'supervisor.json', {'updated_utc': datetime.now(timezone.utc).isoformat(),
                  'stage': stage, 'supervisor_pid': os.getpid(), 'child_pid': child.pid,
                  'wake_request_active': True})
            report()
            time.sleep(30)
        if child.returncode:
            raise subprocess.CalledProcessError(child.returncode, command)
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=30)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--identity-worker', action='store_true')
    args = parser.parse_args()
    if args.identity_worker:
        identity_worker()
        return
    training, flow = register()
    if args.prepare:
        report()
        return
    if (FLOW / 'CONCLUIDO.json').exists():
        report()
        return
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.SetThreadExecutionState.argtypes = [ctypes.c_uint32]
    kernel.SetThreadExecutionState.restype = ctypes.c_uint32
    awake = False
    env = os.environ.copy()
    env['HF_HOME'] = (ROOT / 'data/hf-home.txt').read_text(encoding='utf-8-sig').strip()
    env['PYTHONIOENCODING'] = 'utf-8'
    env['MPLCONFIGDIR'] = str(Path(flow['identity_temp']).parent / 'pfc-matplotlib')
    with (FLOW / 'execucao.log').open('a', encoding='utf-8', buffering=1) as log:
        try:
            awake = bool(kernel.SetThreadExecutionState(0x80000001))
            if not awake:
                raise RuntimeError('Falha na solicitacao temporaria de energia')
            configuration = training['frozen']['configuration']
            if not (BASE / 'CONCLUIDO.json').exists():
                command = [sys.executable, '-u', str(ROOT / 'treinar_sam3_negativos_internos.py')]
                for k, v in configuration.items():
                    if v is not None:
                        command += ['--' + k.replace('_', '-'), str(v)]
                supervise(command, log, env, 'training')
            final = read(BASE / 'CONCLUIDO.json')
            if final['development_smoke_only']:
                raise ValueError('Smoke nao pode entrar no fluxo principal')
            if final['improved_segmentation_selection']:
                if not (BASE / 'identidade/CONCLUIDO.json').exists():
                    identity_temp = Path(flow['identity_temp'])
                    identity_temp.mkdir(parents=True, exist_ok=True)
                    identity_env = {**env, 'TEMP': str(identity_temp), 'TMP': str(identity_temp)}
                    supervise([sys.executable, '-u', str(Path(__file__).resolve()), '--identity-worker'],
                              log, identity_env, 'identity')
                reason = 'Training and registered identity/conditional-area pipeline completed'
            else:
                reason = 'Epoch0 selected: no segmentation improvement; unchanged parent identity results retained, no redundant identity or area inference'
            write(FLOW / 'CONCLUIDO.json', {'completed_utc': datetime.now(timezone.utc).isoformat(),
                  'reason': reason, 'new_candidate_evaluated': final['improved_segmentation_selection'],
                  'test_inference': False, 'clinical_effect_established': False, 'production_replaced': False})
            report()
        except BaseException as error:
            traceback.print_exc(file=log)
            write(FLOW / 'ERRO.json', {'utc': datetime.now(timezone.utc).isoformat(), 'error': repr(error)})
            raise
        finally:
            if awake:
                kernel.SetThreadExecutionState(0x80000000)
            write(FLOW / 'supervisor.json', {'updated_utc': datetime.now(timezone.utc).isoformat(),
                  'stage': 'stopped', 'supervisor_pid': os.getpid(), 'wake_request_active': False})


if __name__ == '__main__':
    main()

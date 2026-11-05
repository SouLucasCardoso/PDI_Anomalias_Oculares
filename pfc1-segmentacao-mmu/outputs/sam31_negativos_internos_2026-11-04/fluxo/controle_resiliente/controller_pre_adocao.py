"""Controle operacional externo: falhas do relatorio nao encerram os calculos registrados.

Nao altera os treinadores, perdas, avaliadores ou protocolos cientificos ativos.
"""
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
FLOW = BASE / 'fluxo'
CONTROL = FLOW / 'controle_resiliente'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.part')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    # Locks externos de curta duracao nao modificam o conteudo a ser gravado.
    for attempt in range(20):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(.25)


def register():
    training = read(BASE / 'protocolo.json')
    flow = read(FLOW / 'protocolo_fluxo.json')
    protected = dict(training['frozen']['sources'])
    for name, checksum in flow['sources'].items():
        if name in protected and protected[name] != checksum:
            raise ValueError('Proveniencia divergente: ' + name)
        protected[name] = checksum
    for name, checksum in protected.items():
        if sha(ROOT / name) != checksum:
            raise ValueError('Fonte cientifica registrada mudou: ' + name)
    if any(importlib.metadata.version(n) != version for n, version in flow['versions'].items()):
        raise ValueError('Ambiente registrado mudou')
    command = [sys.executable, '-u', str(ROOT / 'treinar_sam3_negativos_internos.py')]
    for name, value in training['frozen']['configuration'].items():
        if value is not None:
            command.extend(['--' + name.replace('_', '-'), str(value)])
    binding = {'controller_sha256': sha(Path(__file__)),
               'training_protocol_sha256': sha(BASE / 'protocolo.json'),
               'flow_protocol_sha256': sha(FLOW / 'protocolo_fluxo.json'),
               'protected_sources_unchanged': protected,
               'training_command': command,
               'identity_command': [sys.executable, '-u', str(ROOT / 'executar_sam3_negativos_internos.py'), '--identity-worker'],
               'report_command': [sys.executable, '-u', str(ROOT / 'analisar_sam3_negativos_internos.py')]}
    file = CONTROL / 'protocolo_operacional.json'
    if file.exists():
        if read(file)['binding'] != binding:
            raise ValueError('Registrar outro controle operacional antes de mudar esta entrada')
    else:
        CONTROL.mkdir(parents=True, exist_ok=True)
        (CONTROL / 'controller.py').write_bytes(Path(__file__).read_bytes())
        write(file, {'registered_utc': datetime.now(timezone.utc).isoformat(), 'binding': binding,
                     'reason': 'The previous supervisor terminated training when atomic replacement of its Markdown report raised WinError5. Reporting is now an independent child process; failures are recorded without terminating training or identity.',
                     'scope': 'External process/task orchestration only. Same scientific workers, CLI arguments, environment, cache, initialization, optimizer, checkpoint selection, recognition threshold and gates. No changes to registered sources or scientific protocols.',
                     'adoption': 'Task action may be updated while the existing instance runs; do not interrupt a healthy active training process.'})
    return training, flow, binding


def watch(child, publish, pause, notify):
    """O estado do filho cientifico determina o resultado; o observador e isolado."""
    while child.poll() is None:
        try:
            publish()
        except Exception as error:
            # Inclusive falhas de lancamento/gravação do observador sao operacionais.
            try:
                notify(error)
            except Exception:
                pass
        pause(2)
    return child.returncode


def stop_owned(child):
    if child.poll() is not None:
        return
    # Somente a arvore do processo criado por este controlador, incluindo o redirector do venv.
    subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), check=False)
    child.wait(timeout=30)


def run_phase(command, env, stage, work, log, report_command):
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=log, creationflags=flags)
    observer = None
    last_report = float('-inf')
    observer_start = None

    def notify(error):
        print(datetime.now(timezone.utc).isoformat(), 'observer_failure', repr(error), file=log, flush=True)

    def publish():
        nonlocal observer, last_report, observer_start
        now = time.monotonic()
        write(work / 'supervisor_resiliente.json', {'updated_utc': datetime.now(timezone.utc).isoformat(),
              'stage': stage, 'supervisor_pid': os.getpid(), 'worker_pid': child.pid,
              'wake_request_active': True, 'report_failure_does_not_stop_worker': True})
        if observer is not None:
            if observer.poll() is not None:
                if observer.returncode:
                    notify(RuntimeError(f'Observer exit code {observer.returncode}; scientific worker continues'))
                observer = None
            elif now - observer_start > 180:
                stop_owned(observer)
                notify(TimeoutError('Observer exceeded180seconds; scientific worker continues'))
                observer = None
        if observer is None and now - last_report >= 60:
            last_report = now
            observer = subprocess.Popen(report_command, cwd=ROOT, env=env, stdout=log, stderr=log, creationflags=flags)
            observer_start = now

    try:
        code = watch(child, publish, time.sleep, notify)
        if code:
            raise subprocess.CalledProcessError(code, command)
    finally:
        stop_owned(child)
        if observer is not None:
            try:
                observer.wait(timeout=30)
            except subprocess.TimeoutExpired:
                stop_owned(observer)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--register', action='store_true')
    args = parser.parse_args()
    training, flow, binding = register()
    if args.register:
        print('External control registered; all scientific sources unchanged', flush=True)
        return
    if (FLOW / 'CONCLUIDO.json').exists():
        return
    work = Path(training['frozen']['configuration']['run'])
    env = os.environ.copy()
    env['HF_HOME'] = (ROOT / 'data/hf-home.txt').read_text(encoding='utf-8-sig').strip()
    env['PYTHONIOENCODING'] = 'utf-8'
    env['MPLCONFIGDIR'] = str(Path(flow['identity_temp']).parent / 'pfc-matplotlib')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.SetThreadExecutionState.argtypes = [ctypes.c_uint32]
    kernel.SetThreadExecutionState.restype = ctypes.c_uint32
    awake = bool(kernel.SetThreadExecutionState(0x80000001))
    if not awake:
        raise RuntimeError('Falha na solicitacao temporaria de energia')
    with (work / 'controle_resiliente.log').open('a', encoding='utf-8', buffering=1) as log:
        try:
            if not (BASE / 'CONCLUIDO.json').exists():
                run_phase(binding['training_command'], env, 'training', work, log, binding['report_command'])
            final = read(BASE / 'CONCLUIDO.json')
            if final['development_smoke_only']:
                raise ValueError('Teste curto nao pode entrar no fluxo principal')
            improved = final['improved_segmentation_selection']
            if improved and not (BASE / 'identidade/CONCLUIDO.json').exists():
                temp = Path(flow['identity_temp'])
                temp.mkdir(parents=True, exist_ok=True)
                run_phase(binding['identity_command'], {**env, 'TEMP': str(temp), 'TMP': str(temp)},
                          'identity', work, log, binding['report_command'])
            write(FLOW / 'CONCLUIDO.json', {'completed_utc': datetime.now(timezone.utc).isoformat(),
                  'reason': 'Registered training and identity/conditional-area pipeline completed' if improved else
                            'Epoch0 selected: unchanged parent weights; no duplicate identity or area inference',
                  'new_candidate_evaluated': improved, 'test_inference': False,
                  'clinical_effect_established': False, 'production_replaced': False,
                  'external_operational_controller': str(CONTROL / 'protocolo_operacional.json')})
            try:
                subprocess.run(binding['report_command'], cwd=ROOT, env=env, stdout=log, stderr=log, check=True,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            except Exception:
                traceback.print_exc(file=log)
        except BaseException:
            traceback.print_exc(file=log)
            raise
        finally:
            kernel.SetThreadExecutionState(0x80000000)
            write(work / 'supervisor_resiliente.json', {'updated_utc': datetime.now(timezone.utc).isoformat(),
                  'stage': 'stopped', 'supervisor_pid': os.getpid(), 'wake_request_active': False})


if __name__ == '__main__':
    main()

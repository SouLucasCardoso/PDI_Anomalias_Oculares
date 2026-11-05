"""Supervisor externo ao protocolo cientifico; mantem vigilia apenas na avaliacao ativa."""
from datetime import datetime, timezone
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
CONTINUOUS = 0x80000000
SYSTEM_REQUIRED = 0x80000001


def pending_compute(base, readiness):
    if not (base/'CONCLUIDO.json').exists():
        return False
    if not (base/'identidade/CONCLUIDO.json').exists():
        return True
    if (base/'clinica/iris_anomaly/CONCLUIDO.json').exists():
        return False
    if readiness.exists():
        return bool(json.loads(readiness.read_text(encoding='utf-8'))['segmentation_pilot_ready'])
    return False


def supervise(spawn, set_power, pending, wait, notify):
    child = spawn()
    active = False
    try:
        while child.poll() is None:
            needed = bool(pending())
            if needed != active:
                if not set_power(SYSTEM_REQUIRED if needed else CONTINUOUS):
                    raise RuntimeError('Falha na solicitacao temporaria de energia')
                active = needed
                notify(child.pid, active)
            wait(2)
        notify(child.pid, False, child.returncode)
        return child.returncode
    finally:
        # Uma falha do supervisor nao pode deixar outro avaliador vivo para a proxima tentativa.
        try:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=15)
        finally:
            if active:
                set_power(CONTINUOUS)


def main():
    out = ROOT/'outputs/prontidao_anomalias_2026-11-03'
    base = ROOT/'outputs/sam31_iris_adaptacao_2026-11-03'
    temp = Path(os.environ['TEMP'])
    os.environ['HF_HOME'] = (ROOT/'data/hf-home.txt').read_text(encoding='utf-8-sig').strip()
    os.environ['MPLCONFIGDIR'] = str(temp/'pfc-matplotlib')
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.SetThreadExecutionState.argtypes = [ctypes.c_uint32]
    kernel.SetThreadExecutionState.restype = ctypes.c_uint32

    def notify(pid, awake, code=None):
        file = out/'supervisor_pos_treino.json'
        value = {'updated_utc': datetime.now(timezone.utc).isoformat(),
                 'supervisor_pid': os.getpid(), 'worker_pid': pid,
                 'wake_request_active': awake, 'worker_exit_code': code,
                 'scientific_worker_source_unchanged': True}
        temporary = file.with_suffix('.json.part')
        temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
        temporary.replace(file)

    with (out/'supervisor_pos_treino.log').open('a', encoding='utf-8', buffering=1) as log:
        return supervise(
            lambda: subprocess.Popen([sys.executable, '-u', str(ROOT/'acompanhar_prontidao_anomalias.py')],
                                     cwd=ROOT, stdout=log, stderr=log),
            kernel.SetThreadExecutionState,
            lambda: pending_compute(base, out/'estado.json'), time.sleep, notify)


if __name__ == '__main__':
    raise SystemExit(main())

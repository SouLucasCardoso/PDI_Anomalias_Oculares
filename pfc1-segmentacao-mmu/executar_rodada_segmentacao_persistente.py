"""Mantem a rodada registrada retomavel entre logins, sem mudar o experimento."""
from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
LAUNCH = ROOT / 'outputs/segmentacao_area_lancamento_2026-10-27.json'


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def inspect():
    launch = json.loads(LAUNCH.read_text(encoding='utf-8-sig'))
    mirror = Path(launch['mirror_directory'])
    run = Path(launch['run_root'])
    protocol = json.loads((mirror / 'protocolo_rodada.json').read_text(encoding='utf-8-sig'))
    for name, expected in protocol['source_hashes'].items():
        source = ROOT / name
        if source.parent.resolve() != ROOT or sha256(source) != expected:
            raise ValueError('Fonte registrada divergente: ' + name)
    config = protocol['configuration']
    if (Path(config['run_root']).resolve() != run.resolve()
            or (ROOT / config['mirror_root']).resolve() != mirror.resolve()
            or config['epochs'] != launch['epochs']
            or Path(launch['script']).resolve() != ROOT / 'avaliar_area_segmentador_diverso.py'):
        raise ValueError('Lancamento diverge do protocolo registrado')
    completed = mirror / 'CONCLUIDO_RODADA.json'
    final = json.loads(completed.read_text(encoding='utf-8-sig')) if completed.exists() else None
    if final and final['status'] not in ('completed', 'completed_no_eligible_trained_candidate'):
        raise ValueError('Estado de conclusao desconhecido')
    return launch, config, mirror, run, final


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    launch, config, mirror, run, final = inspect()
    if args.check_only:
        print(json.dumps({'sources_match': True, 'completed': final is not None,
                          'run_root': str(run), 'epochs': config['epochs']}))
        return 0
    with (mirror / 'supervisor.log').open('a', encoding='utf-8', buffering=1) as log:
        def record(event, **extra):
            log.write(json.dumps({'utc': datetime.now(timezone.utc).isoformat(),
                                  'event': event, **extra}) + '\n')
        if final:
            record('already_completed_no_restart')
            return 0
        # O Agendador usa IgnoreNew; este supervisor aguarda o processo filho.
        # A solicitacao temporaria impede apenas a suspensao por inatividade.
        # Suspensao manual, desligamento e configuracoes permanentes permanecem disponiveis.
        kernel = ctypes.windll.kernel32
        kernel.SetThreadExecutionState.argtypes = [ctypes.c_uint32]
        kernel.SetThreadExecutionState.restype = ctypes.c_uint32
        requested = bool(kernel.SetThreadExecutionState(0x80000001))
        record('starting_registered_pipeline', idle_sleep_request=requested)
        command = [sys.executable, '-u', launch['script'], '--run-root', str(run),
                   '--mirror-root', config['mirror_root'], '--baseline-dir', config['baseline_dir'],
                   '--epochs', str(config['epochs'])]
        try:
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            record('pipeline_exit', returncode=result.returncode)
            return result.returncode
        finally:
            if requested:
                kernel.SetThreadExecutionState(0x80000000)


if __name__ == '__main__':
    raise SystemExit(main())

"""Entrada sem janela para o relatorio observacional, com erros persistidos."""
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
import os
import sys
import traceback

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'outputs/segmentacao_area_2026-10-27/analise'


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    with (OUT / 'observador.log').open('a', encoding='utf-8', buffering=1) as log:
        with redirect_stdout(log), redirect_stderr(log):
            try:
                print(datetime.now(timezone.utc).isoformat(), 'observer_start', os.getpid(), flush=True)
                import analisar_rodada_segmentacao_area as report
                report.register()
                sys.argv = [str(ROOT / 'analisar_rodada_segmentacao_area.py'), '--watch']
                report.main()
                print(datetime.now(timezone.utc).isoformat(), 'observer_exit', flush=True)
            except BaseException:
                traceback.print_exc()
                raise

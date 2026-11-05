"""Entrada sem janela para o observador de area SAM3, com erros persistidos."""
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
import os
import sys
import traceback

ROOT = Path(__file__).resolve().parent

if __name__ == '__main__':
    out = ROOT / 'outputs/sam31_iris_adaptacao_2026-11-03/analise_area'
    out.mkdir(exist_ok=True)
    with (out / 'observador.log').open('a', encoding='utf-8', buffering=1) as log:
        with redirect_stdout(log), redirect_stderr(log):
            try:
                print(datetime.now(timezone.utc).isoformat(), 'observer_start', os.getpid(), flush=True)
                import analisar_sam3_area
                sys.argv = [str(ROOT / 'analisar_sam3_area.py'), '--watch']
                analisar_sam3_area.main()
                print(datetime.now(timezone.utc).isoformat(), 'observer_exit', flush=True)
            except BaseException:
                traceback.print_exc()
                raise

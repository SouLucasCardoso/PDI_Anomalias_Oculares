"""Entrada curta agendada, sem janela e sem uso de GPU."""
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import traceback

ROOT = Path(__file__).resolve().parent

if __name__ == '__main__':
    out = ROOT/'outputs/sam31_iris_adaptacao_2026-11-03/sensibilidade_referencia'
    out.mkdir(exist_ok=True)
    with (out/'observador.log').open('a', encoding='utf-8', buffering=1) as log:
        with redirect_stdout(log), redirect_stderr(log):
            try:
                import analisar_sensibilidade_referencia_area
                analisar_sensibilidade_referencia_area.render()
            except BaseException:
                traceback.print_exc()
                raise

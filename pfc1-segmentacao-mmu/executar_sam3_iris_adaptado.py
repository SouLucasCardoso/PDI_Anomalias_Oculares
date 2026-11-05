"""Supervisor local da rodada SAM3 supervisionada, retomavel no login."""
from pathlib import Path
import ctypes
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    mirror=ROOT/'outputs/sam31_iris_adaptacao_2026-11-03'
    if (mirror/'CONCLUIDO.json').exists():raise SystemExit(0)
    kernel=ctypes.windll.kernel32
    kernel.SetThreadExecutionState.argtypes=[ctypes.c_uint32]
    kernel.SetThreadExecutionState.restype=ctypes.c_uint32
    requested=bool(kernel.SetThreadExecutionState(0x80000001))
    os.environ['HF_HOME']=(ROOT/'data/hf-home.txt').read_text(encoding='utf-8-sig').strip()
    os.environ['PYTHONIOENCODING']='utf-8'
    temp=Path(os.environ['TEMP'])
    with (mirror/'supervisor.log').open('a',encoding='utf-8',buffering=1) as log:
        try:
            result=subprocess.run([sys.executable,'-u',str(ROOT/'treinar_sam3_iris_adaptado.py'),
                '--run',str(temp/'pfc-sam3-iris-adaptado-20261103'),
                '--cache',str(temp/'pfc-sam3-iris-cache-20261103'),
                '--mirror',str(mirror),'--wait-reference','--epochs','20','--batch-size','16'],
                cwd=ROOT,stdout=log,stderr=log)
            raise SystemExit(result.returncode)
        finally:
            if requested:kernel.SetThreadExecutionState(0x80000000)

"""Gera QA clinica em CPU para cada candidato elegivel da rodada ativa.

Termina com o treino ou apos12h; nao promove modelos nem altera treinamento.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent


def main():
    launch=json.loads((ROOT/'outputs/segmentacao_diversa_lancamento_2026-10-27.json').read_text(encoding='utf-8-sig'))
    runtime=Path(launch['runtime_directory']);mirror=Path(launch['mirror_directory'])
    started=time.monotonic();processed=set()
    while time.monotonic()-started < 12*3600:
        for checkpoint in sorted(mirror.glob('candidato_epoca_*.pt')):
            if checkpoint.name in processed:continue
            target=mirror/(checkpoint.stem+'_recortes')
            if (target/'comparacao.json').exists():processed.add(checkpoint.name);continue
            if target.exists():
                print(f'Saida incompleta preservada: {target}',flush=True)
                processed.add(checkpoint.name);continue
            command=[sys.executable,str(ROOT/'comparar_recortes_diversos.py'),'--checkpoint',str(checkpoint),'--output-dir',str(target)]
            result=subprocess.run(command,cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            print(json.dumps({'checkpoint':checkpoint.name,'returncode':result.returncode}),flush=True)
            processed.add(checkpoint.name)
        state_file=runtime/'status.json'
        if state_file.exists():
            try:state=json.loads(state_file.read_text(encoding='utf-8'))
            except (json.JSONDecodeError,PermissionError):time.sleep(10);continue
            if state['status'] in ('completed','failed'):
                # CONCLUIDO e copias sao escritas antes de status completed.
                print(json.dumps({'training_status':state['status'],'qa_processed':sorted(processed)}),flush=True)
                return
        time.sleep(20)
    print('Limite de12h do monitor atingido; treino nao foi interrompido.',flush=True)


if __name__=='__main__':main()

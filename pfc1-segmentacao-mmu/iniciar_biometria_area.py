"""Aguarda treino e piloto antes do experimento completo de area preservada."""
from pathlib import Path
import subprocess
import sys
import time
import json
from collections import Counter

ROOT = Path(__file__).resolve().parent

def main():
    out=ROOT/'outputs/biometria_area_completa_2026-10-20'
    out.mkdir(parents=True,exist_ok=True)
    counts={}
    for name,person in [('nuclear','patient_id'),('slpvld','subject')]:
        rows=json.loads((ROOT/f'data/{name}/manifesto.json').read_text(encoding='utf-8'))
        groups=Counter((r[person],r['side']) for r in rows)
        counts[name]={'images':len(rows),'eyes_with_multiple_images':sum(n>=2 for n in groups.values()),
                      'status':'eligibility audit only; dates, near duplicates, identity and mask quality require review'}
    (out/'triagem_clinica.json').write_text(json.dumps(counts,indent=2),encoding='utf-8')
    print(json.dumps(counts),flush=True)
    deadline=time.monotonic()+6*3600
    markers=[ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/metricas.json',
             ROOT/'outputs/biometria_area_piloto_2026-10-20/CONCLUIDO.json']
    print('Aguardando treino final e piloto; GPU reservada para o treino.',flush=True)
    while not all(p.exists() for p in markers):
        if time.monotonic()>deadline: raise TimeoutError('Dependencias nao concluidas em seis horas; verificar logs.')
        time.sleep(30)
    command=[sys.executable,'-u',str(ROOT/'avaliar_robustez_reconhecimento.py'),
             '--cnn-dir','outputs/cnn/ubipr_retreino_2026-10-20','--area-grid',
             '--device','cuda','--batch-size','6','--output-dir',str(out)]
    print('Iniciando experimento completo com checkpoint final.',flush=True)
    subprocess.run(command,cwd=ROOT,check=True)

if __name__=='__main__': main()

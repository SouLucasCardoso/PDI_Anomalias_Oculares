"""Interrompe apenas os dois processos deste experimento antes da inferencia."""
from datetime import datetime,timezone
import json
from pathlib import Path
import psutil

ROOT=Path(__file__).resolve().parent

def main():
    targets={'avaliar_identidade_nuclear.py','avaliar_area_nuclear_condicional.py'}
    stopped=[]
    for process in psutil.process_iter(['pid','name','cmdline']):
        try:
            if (process.info['name'] or '').lower() not in ('python.exe','pythonw.exe'): continue
            arguments=process.info['cmdline'] or []
            scripts=[Path(arg).name for arg in arguments[1:] if arg.lower().endswith('.py')]
            if scripts and scripts[0] in targets:
                if Path(process.cwd()).resolve()!=ROOT.resolve(): continue
                process.terminate(); stopped.append({'pid':process.pid,'script':scripts[0]})
        except (psutil.NoSuchProcess,psutil.AccessDenied): continue
    report={'status':'interrupted_after_calibration_image_quality_review_before_recognition',
        'utc':datetime.now(timezone.utc).isoformat(),'terminated_processes':stopped,
        'reason':'Initial calibration masks on slit-illumination Nuclear images often fragment into nonrepresentative patches; original-image identity and minimum-area inference not justified with current pipeline',
        'qa_image':'data/qa_biometria/nuclear/calibracao_inicial.png',
        'recognition_results_examined':False,'dataset_files_preserved':True,
        'next_step':'Audit segmentation suitability before enrolling a clinical dataset; do not impute missing or unreliable iris area'}
    for relative in ('nuclear_identidade_arcface_2026-10-20','nuclear_area_condicional_2026-10-20'):
        out=ROOT/'outputs'/relative
        if (out/'CONCLUIDO.json').exists(): raise RuntimeError('Unexpected completed recognition: review status before claiming pre-recognition stop')
        (out/'INTERROMPIDO_QA.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()

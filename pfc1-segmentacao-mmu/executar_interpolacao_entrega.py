"""Fila serial de GPU para tres interpolacoes val, sem ler resultados de teste."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--wait-run',type=Path,required=True);p.add_argument('--training-run',type=Path,required=True);p.add_argument('--reference-root',type=Path,required=True);p.add_argument('--hybrid-run',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    state=a.output_dir.parent/(a.output_dir.name+'_supervisor.json');assert not state.exists();file=ROOT/'avaliar_interpolacao_encoder_entrega.py';source=hashlib.sha256(file.read_bytes()).hexdigest()
    def stage(name,**kw):state.write_text(json.dumps({'stage':name,'pid':os.getpid(),'utc':datetime.now(timezone.utc).isoformat(),'source_sha256':source,**kw},indent=2),encoding='utf-8')
    stage('aguardando_gpu_livre',test_outcomes_read=False)
    while not (a.wait_run/'CONCLUIDO.json').exists():
        if datetime.now(timezone.utc)>=datetime.fromisoformat('2026-11-09T02:00:00+00:00'):stage('limite_horario');return
        time.sleep(5)
    assert hashlib.sha256(file.read_bytes()).hexdigest()==source;stage('validando')
    env=os.environ.copy();env['PYTHONUTF8']='1';env['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib')
    with (a.output_dir.parent/(a.output_dir.name+'_execucao.log')).open('w',encoding='utf-8') as log:
        result=subprocess.run([sys.executable,'-u',str(file),'--training-run',str(a.training_run),'--reference-root',str(a.reference_root),'--hybrid-run',str(a.hybrid_run),'--output-dir',str(a.output_dir)],cwd=ROOT.parent,env=env,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:stage('falha');raise RuntimeError('Ver log da interpolacao')
    r=json.loads((a.output_dir/'CONCLUIDO.json').read_text());stage('concluido',selected_alpha=r['selected_alpha'],exceeds_hybrid_validation=r['exceeds_hybrid_validation'])

if __name__=='__main__':main()

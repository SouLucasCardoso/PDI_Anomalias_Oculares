"""Aguarda a selecao validada, congela o candidato e executa toda a grade."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--training-run',type=Path,required=True);p.add_argument('--hybrid-run',type=Path,required=True);p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args()
    run=a.run_dir.resolve();training=a.training_run.resolve();hybrid=a.hybrid_run.resolve()
    statusfile=run.parent/(run.name+'_supervisor.json');assert not statusfile.exists()
    file=ROOT/'confirmar_reconhecedor_entrega.py';source=hashlib.sha256(file.read_bytes()).hexdigest()
    def status(stage,**extra):
        tmp=statusfile.with_suffix('.part');tmp.write_text(json.dumps({'stage':stage,'pid':os.getpid(),'utc':datetime.now(timezone.utc).isoformat(),'confirmation_source_sha256':source,**extra},indent=2),encoding='utf-8');tmp.replace(statusfile)
    try:
        status('aguardando_treino_e_auditoria')
        while not (training/'analise/AUDITORIA.json').exists():
            if (training/'supervisor.json').exists():
                previous=json.loads((training/'supervisor.json').read_text())
                if previous['stage']=='falha':raise RuntimeError('Treino ou auditoria falhou; nao ler teste')
            if datetime.now(timezone.utc)>=datetime.fromisoformat('2026-11-09T02:15:00+00:00'):raise RuntimeError('Limite de inicio da comparacao atingido')
            time.sleep(5)
        assert hashlib.sha256(file.read_bytes()).hexdigest()==source
        status('congelando_e_avaliando')
        env=os.environ.copy();env['PYTHONUTF8']='1';env['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib')
        with (run.parent/(run.name+'_execucao.log')).open('w',encoding='utf-8') as log:
            result=subprocess.run([sys.executable,'-u',str(file),'--training-run',str(training),'--hybrid-run',str(hybrid),'--run-dir',str(run)],cwd=ROOT.parent,env=env,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:raise RuntimeError('A comparacao falhou; verificar log sem alterar candidato congelado')
        if (run/'CONCLUIDO.json').exists():
            final=json.loads((run/'CONCLUIDO.json').read_text());status('concluido',comparison_gate_passed=final.get('comparison_gate_passed'),selected=final.get('selected'));print(json.dumps({k:v for k,v in final.items() if k!='records'}),flush=True)
        else:status('encerrado_pelo_limite_horario')
    except Exception as error:status('falha',error=str(error));raise

if __name__=='__main__':main()

"""Sequencia local independente do chat: aguarda comparacao, treina, audita."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
    tmp=path.with_suffix(path.suffix+'.part');tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8');tmp.replace(path)

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--reference-root',type=Path,required=True);a=p.parse_args()
    run=a.run_dir.resolve();reference=a.reference_root.resolve();run.mkdir(parents=True,exist_ok=True)
    file=run/'supervisor.json';assert not file.exists(),'Supervisor ja registrado'
    sources={name:sha(ROOT/name) for name in ('executar_reconhecedor_entrega.py','treinar_reconhecedor_entrega.py','analisar_reconhecedor_entrega.py')}
    write(run/'PLANO_EXECUCAO.json',{'registered_utc':datetime.now(timezone.utc).isoformat(),'sources_sha256':sources,
        'reference_root':str(reference),'sequence':['complete6paired_validation_conditions','train_max18epochs_earlystop5','audit_selected_vs_epoch0'],
        'no_automatic_replacement_or_test':True,'deadline_training_utc':'2026-11-09T02:00:00+00:00'})
    def status(stage,**kw):write(file,{'stage':stage,'pid':os.getpid(),'utc':datetime.now(timezone.utc).isoformat(),**kw})
    try:
        status('aguardando_comparacao_contorno');print('Aguardando as6condicoes da comparacao de contorno.',flush=True)
        while not (reference/'CONCLUIDO.json').exists():
            if datetime.now(timezone.utc)>=datetime.fromisoformat('2026-11-09T02:00:00+00:00'):raise RuntimeError('Limite de inicio do treino atingido')
            if (reference/'estado.json').exists() and time.time()-(reference/'estado.json').stat().st_mtime>1200:raise RuntimeError('Comparacao sem progresso ha20min; verificar processo antes de continuar')
            time.sleep(5)
        for name,expected in sources.items():assert sha(ROOT/name)==expected
        status('treinando');print('Comparacao concluida. Iniciando treino controlado.',flush=True)
        env=os.environ.copy();env['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib');env['PYTHONUTF8']='1'
        with (run/'execucao.log').open('w',encoding='utf-8') as log:
            result=subprocess.run([sys.executable,'-u',str(ROOT/'treinar_reconhecedor_entrega.py'),'--run-dir',str(run),'--reference-root',str(reference),'--epochs','18'],cwd=ROOT.parent,env=env,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:raise RuntimeError('Treinamento falhou; ver execucao.log e ERRO.txt')
        for name,expected in sources.items():assert sha(ROOT/name)==expected
        status('auditando')
        result=subprocess.run([sys.executable,'-u',str(ROOT/'analisar_reconhecedor_entrega.py'),'--run-dir',str(run)],cwd=ROOT.parent,env=env,capture_output=True,text=True,encoding='utf-8')
        (run/'auditoria_execucao.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
        if result.returncode:raise RuntimeError('Auditoria falhou; ver auditoria_execucao.log')
        final=json.loads((run/'CONCLUIDO.json').read_text());status('concluido',selected_epoch=final['selected_epoch'],eligible_gain=final['eligible_gain']);print(json.dumps(final),flush=True)
    except Exception as error:status('falha',error=str(error));(run/'ERRO_SUPERVISOR.txt').write_text(traceback.format_exc(),encoding='utf-8');raise

if __name__=='__main__':main()

"""Passa automaticamente do treino aprovado para grade13 e auditoria."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parent

def write(path,value):
    tmp=path.with_suffix('.part');tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8');tmp.replace(path)

def main():
    p=argparse.ArgumentParser();p.add_argument('--training-run',type=Path,required=True);p.add_argument('--confirmation-run',type=Path,required=True);a=p.parse_args();training=a.training_run.resolve();confirmation=a.confirmation_run.resolve()
    state=training/'FECHAMENTO.json';assert not state.exists()
    sources={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('executar_fechamento_polar_sam31.py','confirmar_polar_sam31_entrega.py','auditar_polar_sam31_entrega.py')}
    write(training/'PLANO_FECHAMENTO.json',{'registered_utc':datetime.now(timezone.utc).isoformat(),'sources_sha256':sources,'sequence':['waittraining','ifeligible_freezecandidate','complete13conditions','independentrecountandbootstrap'],
        'last_test_start_utc':'2026-11-09T00:30:00+00:00','test_stop_utc':'2026-11-09T02:10:00+00:00','no_automatic_model_or_article_replacement':True})
    def stage(name,**extra):write(state,{'stage':name,'pid':os.getpid(),'utc':datetime.now(timezone.utc).isoformat(),**extra})
    try:
        stage('aguardando_treino')
        while not (training/'CONCLUIDO.json').exists():
            if (training/'estado.json').exists():
                current=json.loads((training/'estado.json').read_text())
                if current['stage']=='falha':raise RuntimeError('Treino falhou; preservar referência e verificar ERRO.txt')
            if datetime.now(timezone.utc)>=datetime.fromisoformat('2026-11-09T00:30:00+00:00'):stage('sem_tempo_para_iniciar_grade_completa');return
            time.sleep(5)
        result=json.loads((training/'CONCLUIDO.json').read_text())
        if not result['eligible_gain']:
            history=json.loads((training/'historico.json').read_text());last=history[-1]
            lines=['# Fechamento da adaptação polar SAM3.1','',
                f"Treino encerrado após{result['epochs_completed']}épocas. Nenhum candidato cumpriu a regra registrada. **Reconhecedor original preservado; não foi iniciada nova inferência de teste.**",'',
                '| Versão | Condição | Rank-1 | TAR | FMR | Correto e aceito |','|---|---|---:|---:|---:|---:|']
            for name,records in (('Referência',result['baseline']),('Última época, reprovada',last['results'])):
                for condition,m in records.items():lines.append(f"| {name} | {condition} | {100*m['rank1']:.2f}% | {100*m['tar']:.2f}% | {100*m['far']:.3f}% | {100*m['joint_success']:.2f}% |")
            lines+=['','Todos os482casos de validação foram mantidos. A seleção não foi afrouxada após observar o resultado. Sem confirmação independente, estimativa clínica ou mínimo universal.']
            (training/'RELATORIO_ATUAL.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');stage('concluido_sem_candidato_aprovado');return
        for name,expected in sources.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected
        stage('avaliando_grade_completa',selected_epoch=result['selected_epoch']);env=os.environ.copy();env['PYTHONUTF8']='1';env['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib')
        with (training/'confirmacao_execucao.log').open('w',encoding='utf-8') as log:
            done=subprocess.run([sys.executable,'-u',str(ROOT/'confirmar_polar_sam31_entrega.py'),'--training-run',str(training),'--run-dir',str(confirmation)],cwd=ROOT.parent,env=env,stdout=log,stderr=subprocess.STDOUT)
        if done.returncode:raise RuntimeError('Falha na grade; ver confirmacao_execucao.log')
        if not (confirmation/'CONCLUIDO.json').exists():stage('grade_parcial_por_limite_horario');return
        stage('auditando_grade')
        with (training/'auditoria_grade_execucao.log').open('w',encoding='utf-8') as log:
            done=subprocess.run([sys.executable,'-u',str(ROOT/'auditar_polar_sam31_entrega.py'),'--run-dir',str(confirmation)],cwd=ROOT.parent,env=env,stdout=log,stderr=subprocess.STDOUT)
        if done.returncode:raise RuntimeError('Falha na auditoria; ver auditoria_grade_execucao.log')
        final=json.loads((confirmation/'CONCLUIDO.json').read_text());stage('concluido',comparison_gate_passed=final['comparison_gate_passed'],confirmation_run=str(confirmation));print(json.dumps({k:v for k,v in final.items() if k!='records'}),flush=True)
    except Exception as error:stage('falha',error=str(error));raise

if __name__=='__main__':main()

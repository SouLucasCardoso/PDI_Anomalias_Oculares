"""Espera a grade e o candidato e executa a auditoria, sem editar o artigo."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser();p.add_argument('--reference-run',type=Path,required=True)
    p.add_argument('--candidate-run',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    reference=a.reference_run.resolve();candidate=a.candidate_run.resolve();state=reference/'FECHAMENTO.json'
    assert not state.exists();sources={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('fechar_grade_densa_entrega.py','analisar_grade_densa_entrega.py')}
    (reference/'PLANO_FECHAMENTO.json').write_text(json.dumps({'registered_utc':datetime.now(timezone.utc).isoformat(),
        'sources_sha256':sources,'sequence':['waitreference63','waitcandidate63','independentrecountandfigures'],'automatic_article_or_model_replacement':False},indent=2),encoding='utf-8')
    def stage(name,**extra):state.write_text(json.dumps({'stage':name,'utc':datetime.now(timezone.utc).isoformat(),**extra},indent=2),encoding='utf-8')
    try:
        stage('aguardando_referencia_e_candidato')
        for run in (reference,candidate):
            while not (run/'CONCLUIDO.json').exists():
                current=json.loads((run/'estado.json').read_text())
                if current['stage']=='falha':raise RuntimeError('Execução falhou: '+str(run))
                if datetime.now(timezone.utc)>=datetime.fromisoformat('2026-11-09T02:50:00+00:00'):
                    stage('parcial_por_horario');return
                time.sleep(3)
        for n,expected in sources.items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==expected
        stage('auditando_grade_completa');env=os.environ.copy();env['PYTHONUTF8']='1';env['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib')
        with (reference/'auditoria_execucao.log').open('w',encoding='utf-8') as log:
            result=subprocess.run([sys.executable,'-u',str(ROOT/'analisar_grade_densa_entrega.py'),
                '--reference-run',str(reference),'--candidate-run',str(candidate),'--output-dir',str(a.output_dir.resolve())],env=env,cwd=ROOT.parent,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:raise RuntimeError('Auditoria falhou; ver auditoria_execucao.log')
        stage('concluido',output=str(a.output_dir.resolve()))
    except BaseException as error:stage('falha',error=str(error));raise


if __name__=='__main__':main()

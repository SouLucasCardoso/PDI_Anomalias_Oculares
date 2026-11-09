"""Comparacao pareada registrada, retomavel por condicao concluida."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,subprocess,sys,time
import numpy as np
from recorte_iris_sam31_alta_res import sha
ROOT=Path(__file__).resolve().parent
CONDITIONS=(('original',0),('oclusao_superior',10),('oclusao_inferior',10))

def write(path,value):
    tmp=path.with_suffix(path.suffix+'.part');tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8');tmp.replace(path)

def result_path(run,mode,condition,level):
    suffix='' if condition=='original' else f'_{condition}_{level}'
    return run/mode/'inferencia'/f'confirmacao_congelada_val{suffix}_2026-10-21'

def report(run,records):
    lines=['# Reconhecedor sob oclusoes — comparacao de desenvolvimento','',
        'Validação: 482 consultas,16 candidatos do mesmo lado; mesmos pesos, calibração e limiar. Sem nova inferência de teste.','',
        '| Contorno | Condição | Rank-1 | TAR | FMR | Correto e aceito |','|---|---|---:|---:|---:|---:|']
    for r in records:
        m=r['result'];lines.append(f"| {r['mode']} | {r['condition']} | {100*m['rank1']:.2f}% | {100*m['tar']:.2f}% | {100*m['far']:.3f}% | {100*m['joint_success']:.2f}% |")
    lines+=['','O resultado de segmentação não determina a decisão biométrica. O contorno novo só será candidato se preservar Rank-1/TAR limpos, melhorar a média do acerto e aceitação conjuntos nas três condições e não aumentar FMR nas oclusões. Para aprovação completa, FMR≤1% em todas as condições. Avaliação de desenvolvimento repetida, sem independência clínica.']
    (run/'RELATORIO_ATUAL.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');write(run/'resultados.json',records)

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args();run=a.run_dir.resolve();run.mkdir(parents=True,exist_ok=True)
    sources={n:sha(ROOT/n) for n in ('rodada_reconhecedor_entrega.py','avaliar_contorno_integrado.py','avaliar_candidato_congelado.py','avaliar_robustez_reconhecimento.py')}
    file=run/'protocolo.json'
    if file.exists():assert json.loads(file.read_text())['sources_sha256']==sources
    else:write(file,{'registered_utc':datetime.now(timezone.utc).isoformat(),'sources_sha256':sources,'conditions':CONDITIONS,'modes':['nearest','continuous'],
        'selection':'Preserve clean Rank1 and TAR, cleanFMR<=1%; mean joint across3 strictly higher and each occludedFMR<=fresh control; absolute release additionally all-conditionFMR<=1%. No test or clinical selection.',
        'deadline_local':'2026-11-08T23:15:00-03:00','models_and_threshold':'Historical frozen, unchanged','scope':'Validation development, not blind confirmation'})
    records=[];started=time.monotonic();report(run,records)
    for condition,level in CONDITIONS:
        for mode in ('nearest','continuous'):
            folder=result_path(run,mode,condition,level);done=folder/'CONCLUIDO.json'
            write(run/'estado.json',{'stage':'avaliando_contorno','mode':mode,'condition':condition,'completed':len(records),'total':6,'pid':os.getpid(),'elapsed_seconds':time.monotonic()-started,'utc':datetime.now(timezone.utc).isoformat()})
            if not done.exists():
                command=[sys.executable,'-u',str(ROOT/'avaliar_contorno_integrado.py'),'--output-root',str(run/mode/'inferencia'),'--mask-mode',mode,'--condition',condition,'--level',str(level)]
                with (run/f'{mode}_{condition}.log').open('w',encoding='utf-8') as log:
                    result=subprocess.run(command,cwd=ROOT.parent,stdout=log,stderr=subprocess.STDOUT)
                if result.returncode:raise RuntimeError(f'Falha em{mode}/{condition}; ver log da condição')
            data=json.loads(done.read_text());records.append({'mode':mode,'condition':condition,'level':level,'result':data['result']});report(run,records)
            print(json.dumps(records[-1]),flush=True)
    b={r['condition']:r['result'] for r in records if r['mode']=='nearest'};c={r['condition']:r['result'] for r in records if r['mode']=='continuous'}
    candidate=all(c['original'][k]>=b['original'][k] for k in ('rank1','tar')) and c['original']['far']<=.01
    candidate=candidate and np.mean([r['joint_success'] for r in c.values()])>np.mean([r['joint_success'] for r in b.values()]) and all(c[t]['far']<=b[t]['far'] for t in c if t!='original')
    final={'status':'concluido','candidate_eligible':bool(candidate),'absolute_fmr_target_all_conditions':all(r['far']<=.01 for r in c.values()),'records':records,'recognizer_replaced':False,'test_inference':False,'elapsed_seconds':time.monotonic()-started}
    write(run/'CONCLUIDO.json',final);write(run/'estado.json',{'stage':'concluido','completed':6,'total':6,'elapsed_seconds':time.monotonic()-started});print(json.dumps({k:v for k,v in final.items() if k!='records'}),flush=True)

if __name__=='__main__':main()

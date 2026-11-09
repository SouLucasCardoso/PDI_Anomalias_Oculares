"""Completa a referência congelada em todos os inteiros de perda de 1 a 31%."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, csv, json, os, platform, subprocess, sys, time, traceback
import numpy as np
from ensaio_entrega_oclusoes import digest, write, evaluate, PRIOR
from avaliar_robustez_reconhecimento import load_splits

ROOT=Path(__file__).resolve().parent
DIRECTIONS=('oclusao_superior','oclusao_inferior')
SCHEDULE=[('original',0)]+[(d,n) for n in range(1,32) for d in DIRECTIONS]


def report(run, records, complete=False):
    lines=['# Oclusões de 1% a 31% — referência congelada','',
        '**'+('CONCLUÍDO: 63 condições' if complete else f'EM EXECUÇÃO: {len(records)}/63 condições')+'**','',
        'Uma condição limpa e todos os percentuais inteiros nas posições superior e inferior. São 486 consultas e 7.290 pares impostores por condição, com galeria e limiar fixos. As referências vazias permanecem no total. A fração é relativa ao suporte originalmente anotado, não ao anel anatômico normativo.','',
        '| Oclusão | Posição | Suporte nominal | Rank-1 | TAR | Correto e aceito | FMR | Falhas |',
        '|---:|---|---:|---:|---:|---:|---:|---:|']
    ordered=sorted(records,key=lambda r:(r['loss_percent'],r['condition']))
    flat=[]
    for r in ordered:
        z=r['rates'];c=r['counts']
        lines.append(f"| {r['loss_percent']}% | {r['condition']} | {100-r['loss_percent']}% | {100*z['rank1']:.2f}% | {100*z['tar']:.2f}% | {100*z['joint']:.2f}% | {100*z['far']:.3f}% | {c['extraction_failures']} |")
        flat.append({'loss_percent':r['loss_percent'],'condition':r['condition'],
            'retained_percent':100-r['loss_percent'],**z,**{f'count_{k}':v for k,v in c.items()},'reused':r['reused']})
    lines+=['','Pesos, calibração e limiar históricos fixos. Todos os níveis são medidos mesmo após reprovação. Critérios marginais: Rank-1≥90%, TAR≥90%, FMR≤1%; correto e aceito é informado separadamente. Teste já exposto ao desenvolvimento, sem confirmação independente ou conclusão clínica.','',
        '[Estado](estado.json) · [Protocolo](protocolo.json) · [Resultados](resultados.json)']
    (run/'RELATORIO_ATUAL.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    write(run/'resultados.json',ordered)
    if flat:
        with (run/'resumo.csv').open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True)
    p.add_argument('--resume',action='store_true');a=p.parse_args();run=a.run_dir.resolve()
    run.mkdir(parents=True,exist_ok=a.resume)
    os.environ['HF_HOME']=(ROOT/'data/hf-home.txt').read_text(encoding='utf-8-sig').strip()
    os.environ['HF_HUB_OFFLINE']='1';os.environ['PYTHONUTF8']='1'
    os.environ['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib')
    import torch
    old=ROOT/'outputs/ensaio_oclusoes_2026-11-08'
    frozen_file=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json'
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    frozen=json.loads(frozen_file.read_text());model=json.loads((old/'FUSAO_CONGELADA.json').read_text())
    old_records=[r for r in json.loads((old/'resultados.json').read_text()) if r['model']=='historico']
    reusable={(r['condition'],r['loss_percent']):r for r in old_records};assert len(reusable)==13
    rows=load_splits(json.loads(manifest_file.read_text()))['test']
    subjects=np.array([r.subject for r in rows if r.session==2]);gi=[i for i,r in enumerate(rows) if r.session==1]
    assert len(subjects)==486 and len(np.unique(subjects))==16
    names=('rodada_grade_densa_1a31.py','ensaio_entrega_oclusoes.py','avaliar_candidato_congelado.py',
        'avaliar_robustez_reconhecimento.py','normalizar_consulta.py','textura_polar.py','preparar_polar_vermelho.py',
        'normalizacao_eliptica.py','treinar_segmentacao_ubipr.py')
    sources={n:digest(ROOT/n) for n in names}
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'schedule':SCHEDULE,
        'scope':'Complete exploratory dense grid; no new model, threshold or fusion selection',
        'source_sha256':sources,'frozen_sha256':digest(frozen_file),'manifest_sha256':digest(manifest_file),
        'old_results_sha256':digest(old/'resultados.json'),'reuse':'13 audited same-environment reference conditions; compute missing50 with unchanged official evaluator',
        'intervention':'Reference iris pixels only; gray128; exact rounded integer count; recompute mask and geometry; enrollment unchanged',
        'population':'All486queries incl6undefinedarea,16same-sidecandidates;7290impostorpairs;fixedgallery',
        'criteria':'Marginal90/90/1, joint separately; do not stop after a failure; do not infer universal or clinical minimum',
        'versions':{'python':platform.python_version(),'torch':str(torch.__version__),'numpy':np.__version__},
        'stop_utc':'2026-11-09T02:45:00+00:00','resume_supported':True,'automatic_model_replacement':False}
    if a.resume:
        previous=json.loads((run/'protocolo.json').read_text());assert previous['source_sha256']==sources
    else:
        write(run/'protocolo.json',protocol);(run/'source.py').write_bytes(Path(__file__).read_bytes())
    records=json.loads((run/'resultados.json').read_text()) if a.resume and (run/'resultados.json').exists() else []
    completed={(r['condition'],r['loss_percent']) for r in records};started=time.monotonic()
    def stage(name,**kw):write(run/'estado.json',{'stage':name,'pid':os.getpid(),
        'utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-started,
        'completed':len(records),'total':63,**kw})
    inference=run/'inferencia';inference.mkdir(exist_ok=True)
    guard=inference/'confirmacao_congelada_val_2026-10-21';guard.mkdir(exist_ok=True)
    if not (guard/'CONCLUIDO.json').exists():
        (guard/'CONCLUIDO.json').write_bytes((ROOT/'outputs/confirmacao_congelada_val_2026-10-21/CONCLUIDO.json').read_bytes())
    deadline=datetime.fromisoformat(protocol['stop_utc'])
    baseline_cache=old/'cache_confirmacao_test_2026-10-21'
    gallery={n:np.load(baseline_cache/f'{n}.npy',mmap_mode='r')[gi].copy() for n in ('rgb','native','polar','red')}
    try:
        report(run,records)
        # Establish all available anchors first, then missing integer levels.
        execution=[v for v in SCHEDULE if v in reusable]+[v for v in SCHEDULE if v not in reusable]
        for condition,level in execution:
            if (condition,level) in completed:continue
            while (run/'PAUSAR_PARA_REFINO').exists():
                stage('aguardando_refino_validacao');time.sleep(2)
                if datetime.now(timezone.utc)>=deadline:break
            if datetime.now(timezone.utc)>=deadline:
                stage('parcial_por_limite_horario');report(run,records);return
            suffix='' if condition=='original' else f'_{condition}_{level}'
            reuse=(condition,level) in reusable
            folder=(old/'inferencia' if reuse else inference)/f'confirmacao_congelada_test{suffix}_2026-10-21'
            stage('reutilizando' if reuse else 'inferindo',condition=condition,loss_percent=level)
            if reuse:
                for n,expected in reusable[(condition,level)]['component_scores_sha256'].items():
                    assert digest(folder/f'scores_{n}.npz')==expected
            elif not (folder/'CONCLUIDO.json').exists():
                if folder.exists() and any(folder.iterdir()):raise RuntimeError('Inferência parcial preservada: '+str(folder))
                with (run/f'inferencia_{condition}_{level}.log').open('w',encoding='utf-8') as log:
                    child=subprocess.run([sys.executable,'-u',str(ROOT/'avaliar_candidato_congelado.py'),
                        '--split','test','--condition',condition,'--level',str(level),'--output-root',str(inference)],
                        cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                if child.returncode:raise RuntimeError(f'Inferência falhou em {condition}/{level}; ver log')
            result,data=evaluate(folder,model,subjects,frozen['frozen_threshold'],PRIOR)
            assert result['counts']['queries']==486 and result['counts']['impostors']==7290
            with np.load(folder/'scores_finais.npz') as z:
                np.testing.assert_allclose(data['scores'],z['scores'],atol=1e-12,rtol=1e-12)
                for k in ('labels','valid','correct','accepted'):np.testing.assert_array_equal(data[k],z[k])
            if reuse:assert result['counts']==reusable[(condition,level)]['counts']
            cache=(old if reuse else run)/f'cache_confirmacao_test{suffix}_2026-10-21'
            for n,g in gallery.items():np.testing.assert_array_equal(np.load(cache/f'{n}.npy',mmap_mode='r')[gi],g)
            interventions=json.loads((folder/'interventions.json').read_text())
            fractions=[100*(1-r['affected_fraction']) for r in interventions if r['fraction_defined']]
            if level:assert len(interventions)==486 and len(fractions)==480
            result.update(condition=condition,loss_percent=level,reused=reuse,
                source_folder=str(folder),source_protocol_sha256=digest(folder/'protocolo.json'),
                actual_retained_min_mean_max=[min(fractions),float(np.mean(fractions)),max(fractions)] if fractions else [100.,100.,100.],
                defined_area_queries=480,undefined_area_queries_retained=6,gallery_byte_identical=True)
            path=run/f'scores_reference_{condition}_{level}.npz';np.savez_compressed(path,**data)
            result['scores_sha256']=digest(path);records.append(result);completed.add((condition,level));report(run,records)
            print(json.dumps({'condition':condition,'level':level,'completed':len(records),'counts':result['counts']}),flush=True)
        assert len(records)==63 and completed==set(SCHEDULE)
        for n,expected in sources.items():assert digest(ROOT/n)==expected
        write(run/'CONCLUIDO.json',{'status':'concluido','conditions':63,'new_conditions':50,
            'reused_conditions':13,'queries_per_condition':486,'impostors_per_condition':7290,
            'sources_unchanged':True,'model_replaced':False,'universal_minimum':None,
            'results_sha256':digest(run/'resultados.json'),'elapsed_seconds':time.monotonic()-started})
        report(run,records,True);stage('concluido')
    except BaseException as error:
        stage('falha',error=str(error));(run/'ERRO.txt').write_text(traceback.format_exc(),encoding='utf-8');raise


if __name__=='__main__':main()

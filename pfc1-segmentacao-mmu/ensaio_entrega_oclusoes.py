"""Ensaio completo de area para a entrega: fusao ajustada so na validacao.

Nao altera modelos, calibracao historica, fotografias ou fontes congeladas.
Todos os niveis sao avaliados mesmo depois de uma reprovacao.
"""
from __future__ import annotations
import argparse, hashlib, json, os, platform, subprocess, sys, time, traceback
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp, expit

ROOT=Path(__file__).resolve().parent
ORDER=('rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red')
LEVELS=(0,1,5,10,20,30,31)
PRIOR=np.array([1/8]*7+[1/16]*2)
LAMBDAS=(.01,.1,1.,10.)

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def write(path,value):
    path=Path(path);tmp=path.with_suffix(path.suffix+'.part')
    tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8');tmp.replace(path)

def load_components(folder,calibration):
    records=[]
    for name in ORDER:
        with np.load(folder/f'scores_{name}.npz',allow_pickle=False) as z:
            records.append({k:z[k] for k in ('scores','valid','labels')})
    labels=records[0]['labels']
    for r in records:np.testing.assert_array_equal(labels,r['labels'])
    params=calibration[0][:7]+[calibration[0][7],calibration[1][7]]
    for a,b in zip(calibration[0][:7],calibration[1][:7]):assert a==b
    x=np.stack([(r['scores']-p['mean'])/p['std'] for r,p in zip(records,params)],axis=-1)
    available=np.logical_and.reduce([r['scores']>-2 for r in records])
    valid=np.logical_and.reduce([r['valid'] for r in records])&available.any(1)
    return x,labels,valid,available

def score(x,w,valid,available):
    """Somente descritores, pesos congelados e galeria; identidade nao entra."""
    raw=x@w;out=np.full(raw.shape,-2.,dtype=np.float64)
    valid=valid.copy()
    for i in np.flatnonzero(valid):
        a=available[i]
        std=raw[i,a].std()
        if a.sum()<2 or std<1e-12:valid[i]=False;continue
        out[i,a]=expit(np.clip((raw[i,a]-raw[i,a].mean())/std,-30,30))
    return out,valid

def fit(x,y,valid,available,regularization):
    xx=x[valid].copy();yy=y[valid];aa=available[valid]
    def objective(w):
        logits=4*(xx@w);logits[~aa]=-1e6
        return float(np.mean(logsumexp(logits,axis=1)-logits[np.arange(len(yy)),yy])+regularization*np.sum((w-PRIOR)**2))
    result=minimize(objective,PRIOR,method='SLSQP',bounds=[(0,1)]*9,
                    constraints=[{'type':'eq','fun':lambda w:w.sum()-1}],
                    options={'maxiter':250,'ftol':1e-10})
    if not result.success:raise RuntimeError('Ajuste de fusao falhou: '+result.message)
    w=np.maximum(result.x,0);return w/w.sum()

def tune(run,frozen):
    from avaliar_robustez_reconhecimento import load_splits,operating_threshold,metrics
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text())
    queries=[r for r in load_splits(manifest)['val'] if r.session==2]
    subjects=np.array([r.subject for r in queries]);people=np.unique(subjects)
    # A atribuicao nao usa resultados, nomes dos olhos ou identidade de teste.
    folds=np.array([list(people).index(s)%4 for s in subjects])
    conditions=('original','oclusao_superior_10','oclusao_inferior_10')
    datasets=[];sources={}
    for condition in conditions:
        suffix='' if condition=='original' else '_'+condition
        folder=ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21'
        datasets.append(load_components(folder,frozen['component_calibration_red_and_clahe']))
        sources[condition]={f.name:digest(f) for f in folder.glob('scores_*.npz') if f.name!='scores_finais.npz'}
    x=np.concatenate([d[0] for d in datasets]);y=np.concatenate([d[1] for d in datasets])
    valid=np.concatenate([d[2] for d in datasets]);available=np.concatenate([d[3] for d in datasets])
    allfolds=np.tile(folds,3);n=len(queries);trials=[]
    baseline=[]
    for d in datasets:
        s,v=score(d[0],PRIOR,d[2],d[3]);baseline.append(float(((s.argmax(1)==d[1])&v).mean()))
    for reg in LAMBDAS:
        predictions=np.full(y.shape,-1)
        fold_weights=[]
        for f in range(4):
            train=allfolds!=f;held=~train
            w=fit(x[train],y[train],valid[train],available[train],reg);fold_weights.append(w.tolist())
            s,v=score(x[held],w,valid[held],available[held]);predictions[held]=np.where(v,s.argmax(1),-1)
        rates=[float((predictions[i*n:(i+1)*n]==datasets[i][1]).mean()) for i in range(3)]
        trials.append({'lambda':reg,'rank1_by_condition':rates,'mean_rank1':float(np.mean(rates)),'fold_weights':fold_weights})
    # Decisao predefinida: ganho fora da dobra no original e na media das tres condicoes.
    eligible=[t for t in trials if t['rank1_by_condition'][0]>baseline[0] and t['mean_rank1']>np.mean(baseline)]
    chosen=max(eligible,key=lambda t:(t['mean_rank1'],t['rank1_by_condition'][0],t['lambda'])) if eligible else None
    weights=fit(x,y,valid,available,chosen['lambda']) if chosen else PRIOR.copy()
    sx,sy,sv,sa=datasets[0];clean,cv=score(sx,weights,sv,sa)
    imp=np.ones(clean.shape,bool);imp[np.arange(n),sy]=False
    threshold=operating_threshold(np.where(cv[:,None],clean,-2)[imp],.01)
    measured,c,a=metrics(clean,sy,threshold,cv)
    model={'frozen_utc':datetime.now(timezone.utc).isoformat(),'order':ORDER,'weights':weights.tolist(),
           'selected_lambda':None if chosen is None else chosen['lambda'],'selection_used_test':False,
           'baseline_oof_rank1':baseline,'trials':trials,'threshold':threshold,
           'threshold_source':'Apenas impostores da validacao original; FMR empirica <=1%, limiar unico para todos os niveis de teste.',
           'clean_validation':measured|{'joint':float((c&a).mean())},'validation_sources_sha256':sources,
           'fold_query_people':{str(f):people[f::4].tolist() for f in range(4)},
           'component_calibration':frozen['component_calibration_red_and_clahe'],
           'limitations':'Validacao reutilizada historicamente; OOF de pesos nao constitui nova amostra cega. Calibracao historica e modelos mantidos.'}
    write(run/'FUSAO_CONGELADA.json',model)
    print('Fusao congelada ANTES do teste:',json.dumps({k:model[k] for k in ('weights','selected_lambda','baseline_oof_rank1','threshold','clean_validation')}),flush=True)
    return model

def evaluate(folder,model,subjects,threshold=None,weights=None):
    from avaliar_robustez_reconhecimento import metrics
    x,y,v,a=load_components(folder,model['component_calibration'])
    scores,valid=score(x,np.array(model['weights'] if weights is None else weights),v,a)
    threshold=model['threshold'] if threshold is None else threshold
    measured,c,ac=metrics(scores,y,threshold,valid)
    imp=np.ones(scores.shape,bool);imp[np.arange(len(y)),y]=False
    false=((scores>=threshold)&valid[:,None]&imp).sum(1)
    counts={'correct':int(c.sum()),'accepted':int(ac.sum()),'joint':int((c&ac).sum()),
            'false_accepts':int(false.sum()),'queries':len(y),'impostors':int(imp.sum()),'extraction_failures':int((~valid).sum())}
    people=np.unique(subjects);draws=np.random.default_rng(20261108).integers(0,len(people),(5000,len(people)))
    totals=np.array([[c[subjects==p].sum(),ac[subjects==p].sum(),(c&ac)[subjects==p].sum(),false[subjects==p].sum()] for p in people])[draws].sum(1)
    q=np.array([(subjects==p).sum() for p in people])[draws].sum(1)
    ci=np.quantile(100*totals/np.column_stack((q,q,q,15*q)),[.025,.975],axis=0)
    result={'rates':measured|{'joint':float((c&ac).mean())},'counts':counts,
            'interval95_cluster_person_pp':{k:ci[:,i].tolist() for i,k in enumerate(('rank1','tar','joint','fmr'))},
            'passed':10*counts['correct']>=9*len(y) and 10*counts['accepted']>=9*len(y) and 100*counts['false_accepts']<=counts['impostors']}
    return result,dict(scores=scores,labels=y,valid=valid,correct=c,accepted=ac)

def report(run,records,complete=False):
    import csv
    lines=['# Influência da área preservada — ensaio de 08/11/2026','',
           '**'+('CONCLUÍDO' if complete else 'EM EXECUÇÃO — resultados parciais')+'**','',
           'Área preservada = 100 × (1 − pixels ocluídos / pixels da íris originalmente anotada). Não é a fração do anel anatômico da ISO. Cadastro original; uma fotografia por consulta; 16 candidatos do mesmo lado. Todas as 486 consultas e falhas são mantidas. Teste reutilizado no histórico: análise exploratória, sem confirmação cega.','',
           '| Modelo | Posição | Oclusão | Área nominal | Rank-1 | TAR | Correto e aceito | FMR | Falhas | Critério |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---|']
    flat=[]
    for r in records:
        z=r['rates'];c=r['counts']
        lines.append(f"| {r['model']} | {r['condition']} | {r['loss_percent']}% | {100-r['loss_percent']}% | {100*z['rank1']:.2f}% | {100*z['tar']:.2f}% | {100*z['joint']:.2f}% | {100*z['far']:.3f}% | {c['extraction_failures']} | {'Passou' if r['passed'] else 'Não passou'} |")
        flat.append({'model':r['model'],'condition':r['condition'],'loss_percent':r['loss_percent'],'retained_percent':100-r['loss_percent'],**z,**{f'count_{k}':v for k,v in c.items()}})
    lines += ['', 'Critério nominal: Rank-1 ≥90%, TAR ≥90%, FMR ≤1%. O sucesso conjunto é informado separadamente. Os intervalos de 95% são descritivos por pessoa, com galeria fixa; não certificam simultaneamente toda a curva.','',
              'O limiar e os pesos de cada sistema permanecem fixos em todos os níveis. Todos os níveis registrados são executados, inclusive após falha. 30% e 31% de oclusão produzem 70% e 69% do suporte anotado, sem ensaio de conformidade ISO ou conclusão sobre doença.', '',
              '[Progresso detalhado](estado.json) · [Protocolo](protocolo.json) · [Fusão congelada](FUSAO_CONGELADA.json) · [Resultados completos](resultados.json)']
    (run/'RELATORIO_ATUAL.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    if flat:
        with (run/'resumo.csv').open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=flat[0].keys());w.writeheader();w.writerows(flat)
    write(run/'resultados.json',records)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-dir',type=Path,required=True);args=p.parse_args()
    run=args.run_dir.resolve();run.mkdir(parents=True,exist_ok=True)
    os.environ['HF_HOME']=(ROOT/'data/hf-home.txt').read_text(encoding='utf-8-sig').strip()
    os.environ['HF_HUB_OFFLINE']='1';os.environ['PYTHONUTF8']='1';os.environ['PYTHONUNBUFFERED']='1'
    os.environ['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib')
    import torch,scipy
    from avaliar_robustez_reconhecimento import load_splits,paired_ci
    frozen_path=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json'
    frozen=json.loads(frozen_path.read_text());started=time.monotonic()
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'levels_loss_percent':LEVELS,
        'conditions':['original','oclusao_superior','oclusao_inferior'],'complete_grid_even_after_failure':True,
        'population':'UBIPr, particoes por pessoa, treino sem pessoas de validacao/teste. 482 consultas de validacao e 486 de teste; uma fotografia; lado informado; 16 candidatos; galeria sessao1 original.',
        'intervention':'Somente pixels da iris anotada, cinza128, quantidade round(N*loss/100), ordem por linha superior/inferior. Exterior inalterado. Referencia nao entra na extracao. Segmentar e recalcular geometria a partir da foto alterada.',
        'area':'Fracao do suporte visivel originalmente anotado, NAO anel anatomico completo, fracao clinica, nem conformidade ISO. Referencias vazias mantidas e area indefinida.',
        'selection':'Fusao nao negativa no simplex, entropia cruzada com temperatura4 e regularizacao ao prior historico. 4dobras por pessoa da validacao, original/superior10/inferior10; lambda em [0.01,0.1,1,10]. Seleciona maior Rank1 medio OOF apenas se melhorar original e media; empate prefere maior lambda. Caso contrario prior. Reajusta pesos somente na validacao. Limiar de 1% FMR apenas na validacao original; congelar antes de ler teste.',
        'criteria':'Rank1>=90%,TAR>=90%,FMR<=1%; conjunto relatado. Nao afrouxar criterio apos observar dados. Comparar fusao historica e nova em TODOS os niveis.',
        'models':'Checkpoint U-Net historico como controle de identidade mais forte disponivel; nove descritores historicos. Nenhum treino/alteracao SAM ou atualizacao de ambiente durante comparacao.',
        'uncertainty':'5000 reamostragens por pessoa de consulta, seed20261108, galeria fixa, intervalos descritivos ponto a ponto e perdas pareadas; sem correcao simultanea.',
        'limitations':'Teste ja exposto no desenvolvimento historico e pretreino ArcIris com sobreposicao desconhecida. Nenhum minimo universal ou efeito causal de patologia.',
        'source_sha256':{n:digest(ROOT/n) for n in ('ensaio_entrega_oclusoes.py','avaliar_candidato_congelado.py','avaliar_robustez_reconhecimento.py','normalizar_consulta.py')},
        'frozen_historical_sha256':digest(frozen_path),
        'versions':{'python':platform.python_version(),'torch':torch.__version__,'numpy':np.__version__,'scipy':scipy.__version__},
        'iso_source':'https://www.iso.org/standard/54066.html; consulta08/11/2026, qualidade de imagem, nao garantia de identificacao.'}
    if (run/'protocolo.json').exists():
        old=json.loads((run/'protocolo.json').read_text())
        assert old['source_sha256']==protocol['source_sha256'],'Fontes mudaram; abrir nova rodada.'
    else:write(run/'protocolo.json',protocol)
    records=json.loads((run/'resultados.json').read_text()) if (run/'resultados.json').exists() else []
    def stage(name,**kw):
        state={'stage':name,'utc':datetime.now(timezone.utc).isoformat(),'pid':os.getpid(),'elapsed_seconds':time.monotonic()-started,**kw}
        write(run/'estado.json',state);print(json.dumps(state),flush=True)
    try:
        stage('ajustando_fusao_validacao')
        model=json.loads((run/'FUSAO_CONGELADA.json').read_text()) if (run/'FUSAO_CONGELADA.json').exists() else tune(run,frozen)
        model_hash=digest(run/'FUSAO_CONGELADA.json')
        rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['test']
        subjects=np.array([r.subject for r in rows if r.session==2]);assert len(subjects)==486
        inference=run/'inferencia';inference.mkdir(exist_ok=True)
        # Guarda original exigida pelo avaliador congelado; sua evidencia nao seleciona o novo modelo.
        replay=inference/'confirmacao_congelada_val_2026-10-21';replay.mkdir(exist_ok=True)
        replay_file=ROOT/'outputs/confirmacao_congelada_val_2026-10-21/CONCLUIDO.json'
        if not (replay/'CONCLUIDO.json').exists():(replay/'CONCLUIDO.json').write_bytes(replay_file.read_bytes())
        report(run,records)
        schedule=[('original',0)]+[(orientation,level) for level in LEVELS[1:] for orientation in ('oclusao_superior','oclusao_inferior')]
        baseline={}
        for condition,level in schedule:
            suffix='' if condition=='original' else f'_{condition}_{level}'
            folder=inference/f'confirmacao_congelada_test{suffix}_2026-10-21'
            stage('inferindo_grade',condition=condition,loss_percent=level,completed_conditions=len(records)//2,total_conditions=13)
            if not (folder/'CONCLUIDO.json').exists():
                if folder.exists() and any(folder.iterdir()):raise RuntimeError('Inferencia incompleta preservada: '+str(folder))
                command=[sys.executable,str(ROOT/'avaliar_candidato_congelado.py'),'--split','test','--condition',condition,'--level',str(level),'--output-root',str(inference)]
                subprocess.run(command,cwd=ROOT,check=True)
            assert digest(run/'FUSAO_CONGELADA.json')==model_hash
            for name,weights,threshold in [('historico',PRIOR,frozen['frozen_threshold']),('fusao_validacao',None,None)]:
                if any(r['model']==name and r['condition']==condition and r['loss_percent']==level for r in records):continue
                result,data=evaluate(folder,model,subjects,threshold,weights)
                if condition=='original':baseline[name]=data
                elif name not in baseline:
                    bfolder=inference/'confirmacao_congelada_test_2026-10-21';_,baseline[name]=evaluate(bfolder,model,subjects,threshold,weights)
                if condition!='original':result['paired_loss_rank1_pp95']=paired_ci(baseline[name]['correct'],data['correct'],subjects)
                area=json.loads((folder/'interventions.json').read_text())
                defined=[100*(1-r['affected_fraction']) for r in area if r['fraction_defined']]
                result.update(model=name,condition=condition,loss_percent=level,nominal_retained_percent=100-level,
                    actual_retained_percent_min_mean_max=[float(np.min(defined)),float(np.mean(defined)),float(np.max(defined))] if defined else ([100.,100.,100.] if level==0 else None),
                    defined_area_queries=len(defined) if level else None,undefined_area_queries=len(subjects)-len(defined) if level else None,
                    inference_protocol_sha256=digest(folder/'protocolo.json'),fusion_sha256=model_hash,
                    component_scores_sha256={n:digest(folder/f'scores_{n}.npz') for n in ORDER})
                records.append(result);np.savez_compressed(run/f'scores_{name}_{condition}_{level}.npz',**data)
                report(run,records)
            print('Condicao concluida:',condition,level,flush=True)
        frontier={}
        for name in ('historico','fusao_validacao'):
            for ori in ('oclusao_superior','oclusao_inferior'):
                relevant=[next(r for r in records if r['model']==name and r['loss_percent']==level and r['condition']==('original' if level==0 else ori)) for level in LEVELS]
                smallest=None
                for r in relevant:
                    if not r['passed']:break
                    smallest=100-r['loss_percent']
                frontier[name+'_'+ori]={'smallest_passing_retained_on_tested_prefix':smallest,'tested_loss_percent':LEVELS,'passed':[r['passed'] for r in relevant]}
        final={'status':'completed','conditions':13,'systems':2,'queries_per_condition':486,'records':records,'frontier':frontier,
               'anatomical_minimum':None,'universal_minimum':None,'clinical_effect':None,'independent_blind_test':False}
        write(run/'CONCLUIDO.json',final);report(run,records,True);stage('concluido',completed_conditions=13,total_conditions=13)
    except BaseException as error:
        stage('falhou',error=repr(error));traceback.print_exc();raise

if __name__=='__main__':main()

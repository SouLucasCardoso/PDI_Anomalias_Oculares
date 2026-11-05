"""Treino diverso -> verificacao de identidade -> curva de area na validacao.

Somente checkpoint final escolhido por Dice. Galeria, reconhecedores, fusao e
limiar congelados. Nao seleciona pesos pelo menor percentual observado.
"""
from __future__ import annotations
import argparse
from contextlib import redirect_stdout,redirect_stderr
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import numpy as np

ROOT=Path(__file__).resolve().parent
LOSSES=(0,1,2,5,10,20,30,40,50,60,70,80,90)
SOURCES=('avaliar_area_segmentador_diverso.py','treinar_segmentacao_area.py','treinar_segmentacao_diversa.py',
         'avaliar_candidato_congelado.py','avaliar_robustez_reconhecimento.py','comparar_recortes_diversos.py',
         'textura_polar.py','normalizacao_eliptica.py','normalizar_consulta.py','validar_lateralidade_informada.py')


def digest(path):
    import hashlib
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def write_json(path,value):
    temporary=path.with_suffix(path.suffix+'.part')
    temporary.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')
    for attempt in range(10):
        try:temporary.replace(path);return
        except PermissionError:
            if attempt==9:raise
            time.sleep(.2)


def criterion(correct,accepted,false_accepts,queries,impostors):
    return bool(queries>0 and impostors>0 and 10*correct>=9*queries and 10*accepted>=9*queries and 100*false_accepts<=impostors)


def prefix_minimum(losses,approved):
    if len(losses)!=len(approved) or not losses or losses[0]!=0 or list(losses)!=sorted(set(losses)):
        raise ValueError('Grade deve comecar em0 e crescer sem duplicatas')
    last=None
    for loss,passed in zip(losses,approved):
        if not passed:break
        last=100-loss
    return last


def inspect_scores(folder,subjects,threshold):
    from avaliar_robustez_reconhecimento import metrics
    with np.load(folder/'scores_finais.npz',allow_pickle=False) as z:
        scores,labels,valid=z['scores'],z['labels'],z['valid']
        measured,correct,accepted=metrics(scores,labels,threshold,valid)
        np.testing.assert_array_equal(z['correct'],correct);np.testing.assert_array_equal(z['accepted'],accepted)
    n,candidates=scores.shape
    if len(subjects)!=n:raise ValueError('Populacao de consultas divergente')
    mask=np.ones_like(scores,dtype=bool);mask[np.arange(n),labels]=False
    false=((scores>=threshold)&valid[:,None]&mask).sum(1)
    counts={'correct':int(correct.sum()),'accepted':int(accepted.sum()),'false_accepts':int(false.sum()),'queries':n,'impostors':n*(candidates-1)}
    passed=criterion(**counts)
    people=np.unique(subjects);q=np.array([(subjects==s).sum() for s in people])
    sums=np.array([[correct[subjects==s].sum(),accepted[subjects==s].sum(),false[subjects==s].sum()] for s in people])
    draws=np.random.default_rng(127).integers(0,len(people),(5000,len(people)))
    totals=sums[draws].sum(1);den=q[draws].sum(1)
    rates=totals/np.column_stack((den,den,den*(candidates-1)))
    intervals={k:np.quantile(rates[:,i],[.025,.975]).tolist() for i,k in enumerate(('rank1','tar','fmr'))}
    return {'metrics':measured,'counts':counts,'passed':passed,'intervals95_cluster_person':intervals,
            'scores_sha256':digest(folder/'scores_finais.npz'),'folder':str(folder)}


def preflight():
    from avaliar_candidato_congelado import WEIGHTS
    for name,(folder,expected) in WEIGHTS.items():
        file=ROOT/'outputs'/folder/'melhor_modelo.pt'
        if digest(file)!=expected:raise ValueError('Reconhecedor ausente ou divergente: '+name)
    base=ROOT/'data/modelos/cvrl_arciris'
    arc=next(base.rglob('ResNet100_154000.pt'))
    if digest(arc)!='466014be7723eb0b1a741dcff5a0c8ae51d1918818a6b021952f9c4ccd443f8f':raise ValueError('ArcIris divergente')
    if digest(base/'modules/network.py')!='de7f0cb796ebf4be02818c704d7e3afa0047dc09719b131b37cb8c26c42dd327':raise ValueError('Codigo ArcIris divergente')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-root',type=Path,required=True);p.add_argument('--mirror-root',type=Path,required=True)
    p.add_argument('--baseline-dir',type=Path,required=True);p.add_argument('--epochs',type=int,default=30)
    p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
    run=a.run_root;mirror=a.mirror_root
    os.environ['HF_HOME']=(ROOT/'data/hf-home.txt').read_text(encoding='utf-8-sig').strip()
    os.environ['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib')
    os.environ['PYTHONIOENCODING']='utf-8';os.environ['PYTHONUNBUFFERED']='1'
    run.mkdir(parents=True,exist_ok=True);mirror.mkdir(parents=True,exist_ok=True)
    protocol_file=mirror/'protocolo_rodada.json'
    sources={name:digest(ROOT/name) for name in SOURCES}
    if not protocol_file.exists():
        if not a.prepare_only:raise ValueError('Preparar e registrar protocolo antes da execucao')
        preflight()
        protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'source_hashes':sources,
                  'configuration':{'run_root':str(run),'mirror_root':str(mirror),'baseline_dir':str(a.baseline_dir),'epochs':a.epochs},
                  'main_objective':'Estimate smallest observed visible iris area supporting identification under controlled false matching',
                  'population':'Original subject-disjoint UBIPr segmentation train/validation; identity uses fixed session1 gallery and session2 queries, one image, supplied side, all failures retained',
                  'checkpoint_selection':'Final best epoch by segmentation validation ONLY; no recognition-guided checkpoint search',
                  'threshold_and_identity':'All original identity weights, component calibration, normalization and frozen threshold unchanged',
                  'controls':'Original and new segmenter on clean/upper10/lower10, all482 validation queries. Input resolution follows candidate training metadata.',
                  'area_grid_loss_percent':LOSSES,'area_grid_rule':'Only if candidate original passes Rank1>=90%,TAR>=90%,FMR<=1%; evaluate ALL registered levels both orientations, even after failure. Minimum is prefix on tested grid; no monotonic interpolation.',
                  'uncertainty':'5000 cluster bootstraps by query person, fixed gallery. Reused development validation, not independent confirmation.',
                  'area_definition':'Fraction of originally annotated visible iris pixels, not whole anatomical iris, disease severity or percent of a diagnosed lesion',
                  'intervention':'Gray128 at exact rounded annotated iris pixel count; reference used only for intervention and area measurement, never extraction. Segmentation recalculated on altered photograph.',
                  'clinical_scope':'SLP-VLD normal/anomaly cases qualitative, no clinical percentage without reviewed masks and repeated-session same-eye controls',
                  'test_inference':False,'automatic_production_replacement':False}
        write_json(protocol_file,protocol)
    else:
        protocol=json.loads(protocol_file.read_text(encoding='utf-8'))
        configuration={'run_root':str(run),'mirror_root':str(mirror),'baseline_dir':str(a.baseline_dir),'epochs':a.epochs}
        if sources!=protocol['source_hashes'] or configuration!=protocol['configuration']:
            raise ValueError('Fontes ou parametros mudaram apos registro; preservar protocolo e abrir outra rodada')
    if a.prepare_only:
        print(json.dumps({'status':'prepared','protocol':str(protocol_file)}));return
    with (mirror/'execucao.log').open('a',encoding='utf-8',buffering=1) as log,redirect_stdout(log),redirect_stderr(log):
        try:
            def stage(name,**extra):
                write_json(run/'estado_rodada.json',{'stage':name,'pid':os.getpid(),'utc':datetime.now(timezone.utc).isoformat(),**extra})
                print(name,extra,flush=True)
            def command(args):
                print('Executando:',args,flush=True)
                subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,stdout=log,stderr=log,check=True)
            stage('training');train=run/'training';train_mirror=mirror/'treino'
            if not (train/'CONCLUIDO.json').exists():
                args=[ROOT/'treinar_segmentacao_area.py','--output-dir',train,'--mirror-dir',train_mirror,
                      '--baseline-dir',a.baseline_dir,'--epochs',a.epochs,'--batch-size',16,'--save-every',25]
                if (train/'retomada.pt').exists():args+=['--resume']
                command(args)
            completion=json.loads((train/'CONCLUIDO.json').read_text());checkpoint=train/'melhor_modelo.pt'
            if digest(checkpoint)!=completion['checkpoint_sha256']:raise ValueError('Checkpoint final divergente')
            if completion['best_epoch']==0:
                final={'status':'completed_no_eligible_trained_candidate','best_epoch':0,'minimum_visible_area_percent':None,'recognition_gain_measured':False}
                write_json(run/'CONCLUIDO.json',final);write_json(mirror/'CONCLUIDO_RODADA.json',final);stage('completed',result=final);return
            stage('clinical_qualitative');qa=mirror/f'recortes_epoca_{completion["best_epoch"]:02}'
            if not (qa/'comparacao.json').exists():command([ROOT/'comparar_recortes_diversos.py','--checkpoint',checkpoint,'--output-dir',qa])
            stage('recognition_validation');preflight()
            from avaliar_robustez_reconhecimento import load_splits
            manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text())
            rows=load_splits(manifest)['val'];subjects=np.array([r.subject for r in rows if r.session==2])
            frozen=json.loads((ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json').read_text());threshold=frozen['frozen_threshold']
            records=[]
            def evaluate(custom,condition,level):
                key=('novo' if custom else 'original')+'_'+condition+'_'+str(level)
                parent=run/'recognition'/key;parent.mkdir(parents=True,exist_ok=True)
                suffix='' if condition=='original' else f'_{condition}_{level}'
                if custom:suffix+='_segmentador_'+digest(checkpoint)[:12]
                stem=f'confirmacao_congelada_val{suffix}_2026-10-21'
                completed=sorted(parent.glob('attempt_*/'+stem+'/CONCLUIDO.json'))
                if completed:folder=completed[-1].parent
                else:
                    number=1
                    while (parent/f'attempt_{number:03}').exists():number+=1
                    attempt=parent/f'attempt_{number:03}';attempt.mkdir()
                    args=[ROOT/'avaliar_candidato_congelado.py','--split','val','--condition',condition,'--level',level,'--output-root',attempt]
                    if custom:args+=['--segmenter',checkpoint]
                    stage('recognition_validation',condition=key);command(args);folder=attempt/stem
                current=inspect_scores(folder,subjects,threshold)
                area=json.loads((folder/'interventions.json').read_text())
                defined=[100*(1-r['affected_fraction']) for r in area if r['fraction_defined']]
                current.update(segmenter='novo' if custom else 'original',condition=condition,loss_percent=level,
                               nominal_visible_area_percent=100-level,actual_visible_area_mean_percent=float(np.mean(defined)) if defined else (100. if level==0 else None),
                               defined_area_queries=len(defined) if level else None)
                records.append(current);write_json(run/'resultados_parciais.json',records)
                write_json(mirror/f'resultado_{key}.json',current)
                return current
            controls={}
            for custom in (False,True):
                for condition,level in (('original',0),('oclusao_superior',10),('oclusao_inferior',10)):
                    controls[(custom,condition,level)]=evaluate(custom,condition,level)
            eligible=controls[(True,'original',0)]['passed'];frontier={}
            if eligible:
                for condition in ('oclusao_superior','oclusao_inferior'):
                    decisions=[True]
                    for loss in LOSSES[1:]:
                        result=controls[(True,condition,10)] if loss==10 else evaluate(True,condition,loss)
                        decisions.append(result['passed'])
                    frontier[condition]={'nominal_minimum_on_tested_prefix_percent':prefix_minimum(list(LOSSES),decisions),'passed_by_registered_loss':decisions}
                common=np.logical_and(frontier['oclusao_superior']['passed_by_registered_loss'],frontier['oclusao_inferior']['passed_by_registered_loss']).tolist()
                frontier['both_orientations']={'nominal_minimum_on_tested_prefix_percent':prefix_minimum(list(LOSSES),common)}
            final={'status':'completed','best_epoch':completion['best_epoch'],'checkpoint_sha256':digest(checkpoint),
                   'clean_identity_gate_passed':eligible,'records':records,'frontier':frontier,
                   'minimum_not_determined_reason':None if eligible else 'Original candidate fails identification/acceptance/false-match gate; no area minimum assigned',
                   'test_inference':False,'clinical_anatomical_minimum':None,'production_candidate_replaced':False,
                   'limitations':protocol['uncertainty']+' '+protocol['area_definition']}
            write_json(run/'CONCLUIDO.json',final);write_json(mirror/'CONCLUIDO_RODADA.json',final);stage('completed')
        except BaseException as error:
            traceback.print_exc();write_json(run/'estado_rodada.json',{'stage':'failed','error':repr(error),'pid':os.getpid(),'utc':datetime.now(timezone.utc).isoformat()})
            raise


if __name__=='__main__':main()

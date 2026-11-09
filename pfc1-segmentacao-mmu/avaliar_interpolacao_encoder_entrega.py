"""Tres interpolacoes fixas entre encoder inicial e ultima epoca de treino.

Usa somente validacao; nenhum resultado da grade de teste entra na escolha.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os
import numpy as np
import torch
from torch.torch_version import TorchVersion
from reconhecedor_resnet50 import Encoder
from treinar_reconhecedor_entrega import ROOT,ORDER,CONDITIONS,eligibility,selection_key
from avaliar_candidato_congelado import extract,global_scores,fuse,WEIGHTS
from avaliar_robustez_reconhecimento import load_splits,identity,metrics
from validar_lateralidade_informada import subset
from rodada_reconhecedor_entrega import write,result_path
from recorte_iris_sam31_alta_res import sha

ALPHAS=(.25,.5,.75)

def interpolate(initial,adapted,alpha):
    if not 0<=alpha<=1:raise ValueError('Alpha fora de0..1')
    result={}
    for name,value in initial.items():
        other=adapted[name]
        if torch.equal(value,other):result[name]=value.clone();continue
        if not name.startswith(('backbone.layer4.','projection.')) or not value.is_floating_point():raise ValueError('Alteracao fora dos parametros autorizados')
        if any(t in name for t in ('running_mean','running_var','num_batches_tracked')):raise ValueError('Estatistica congelada alterada')
        result[name]=value*(1-alpha)+other*alpha
        if not torch.isfinite(result[name]).all():raise ValueError('Parametro nao finito')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--training-run',type=Path,required=True);p.add_argument('--reference-root',type=Path,required=True);p.add_argument('--hybrid-run',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    run=a.output_dir.resolve();run.mkdir(parents=True,exist_ok=False)
    initial_file=ROOT/'outputs/resnet50_nativo224_2026-10-21/melhor_modelo.pt';assert sha(initial_file)==WEIGHTS['native'][1]
    final_file=a.training_run/'ultima_epoca.pt';training=json.loads((a.training_run/'CONCLUIDO.json').read_text())
    frozen_file=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json';frozen=json.loads(frozen_file.read_text())
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Posthoc validation-only development after native adjustment failed fixed-threshold gate. Finite three-alpha grid fixed before computing scores. No new training, no test metric read or selection.',
        'alphas':ALPHAS,'source_sha256':sha(__file__),'initial_sha256':sha(initial_file),'last_sha256':sha(final_file),'frozen_calibration_sha256':sha(frozen_file),
        'training_result_sha256':sha(a.training_run/'CONCLUIDO.json'),'hybrid_validation_sha256':sha(a.hybrid_run/'CONCLUIDO.json'),
        'rule':'Same cleanRank1/TAR/FMR and occludedFMR guard as prior trial; maximize meanjoint,then worstjoint,then meanRank1; tie smalleralpha. Retain original if none. Compare chosen with hybrid using validation only before any new test inference.',
        'invariants':'Interpolate changed floating layer4/projection parameters only. Bitwise preserve every unchanged tensor and all normalization buffers. Keep all9component calibration and legacy threshold.'}
    write(run/'protocolo.json',protocol)
    initial=torch.load(initial_file,map_location='cpu',weights_only=True)
    with torch.serialization.safe_globals([TorchVersion]):last=torch.load(final_file,map_location='cpu',weights_only=True)
    os.environ['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib');torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda')
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());rows=load_splits(manifest)['val'];ids=sorted({identity(r) for r in rows});conditions={};threshold=frozen['frozen_threshold']
    for condition,level in CONDITIONS:
        folder=result_path(a.reference_root,'nearest',condition,level);suffix='' if condition=='original' else f'_{condition}_{level}'
        cache=a.reference_root/'nearest'/f'cache_confirmacao_val{suffix}_2026-10-21'
        with np.load(cache/'valid.npz') as z:valid=z['rgb'].copy()
        components=[]
        for name in ORDER:
            with np.load(folder/f'scores_{name}.npz',allow_pickle=False) as z:components.append({k:z[k].copy() for k in ('scores','valid','labels')})
        conditions[condition]=(np.load(cache/'native.npy',mmap_mode='r'),valid,components)
    baseline=training['baseline'];model=Encoder().to(device).eval();trials=[];best=None;bestkey=None;bestalpha=None;bestdata=None
    for alpha in ALPHAS:
        write(run/'estado.json',{'stage':'validando_interpolacao','alpha':alpha,'completed':len(trials),'total':3,'pid':os.getpid()})
        state=interpolate(initial['model'],last['model'],alpha);model.load_state_dict(state);results={};data={}
        for condition,(images,valid,components) in conditions.items():
            full,qvalid=global_scores(extract(model,images,device),valid,rows);scores,y,_=subset(full,rows,ids);np.testing.assert_array_equal(y,components[0]['labels'])
            items=components.copy();items[5]={'scores':scores,'valid':qvalid,'labels':y};fused,fv=fuse(items,frozen['component_calibration_red_and_clahe'])
            m,c,accepted=metrics(fused,y,threshold,fv);m.update(joint_success=float((c&accepted).mean()),threshold=threshold);results[condition]=m
            data[condition]=dict(scores=fused,labels=y,valid=fv,correct=c,accepted=accepted)
            np.savez_compressed(run/f'scores_alpha{alpha}_{condition}.npz',**data[condition])
        eligible=eligibility(results,baseline);key=selection_key(results);trials.append({'alpha':alpha,'eligible':eligible,'results':results})
        if eligible and (bestkey is None or key>bestkey):best=state;bestkey=key;bestalpha=alpha;bestdata=data
        write(run/'resultados_validacao.json',trials);print(json.dumps(trials[-1]),flush=True)
    results=baseline if best is None else next(t['results'] for t in trials if t['alpha']==bestalpha)
    config=json.loads(json.dumps(protocol));config['architecture']='resnet50_gem3_256'
    torch.save({'model':initial['model'] if best is None else best,'training_head':initial['training_head'],'epoch':last['epoch'],
        'selected_alpha':bestalpha,'validation':results,'configuration':config},run/'melhor_modelo.pt')
    _=torch.load(run/'melhor_modelo.pt',map_location='cpu',weights_only=True)
    if bestdata:
        for condition,d in bestdata.items():np.savez_compressed(run/f'scores_fusion_selected_{condition}.npz',**d)
    hybrid=json.loads((a.hybrid_run/'CONCLUIDO.json').read_text());hybrid_result=hybrid['results'][hybrid['selected_group']] if hybrid['selected_group'] else None
    exceeds=best is not None and (hybrid_result is None or bestkey>selection_key(hybrid_result))
    final={'status':'concluido','selected_alpha':bestalpha,'selected_epoch':last['epoch'],'eligible_gain':best is not None,'exceeds_hybrid_validation':bool(exceeds),
        'results':results,'baseline':baseline,'checkpoint_sha256':sha(run/'melhor_modelo.pt'),'test_inference':False,'new_training':False,'trials':trials}
    write(run/'CONCLUIDO.json',final);audit=run/'analise';audit.mkdir();write(audit/'AUDITORIA.json',{'kind':'Finite interpolation validation audit','source_sha256':sha(__file__),'protocol_sha256':sha(run/'protocolo.json'),
        'completed_sha256':sha(run/'CONCLUIDO.json'),'three_trials':len(trials),'only_validation':True,'no_test_outcome_input':True,'normalization_buffers_preserved_bitwise':True})
    lines=['# Interpolação do encoder — validação','',f'Alpha elegível selecionado: {bestalpha}. Supera o híbrido na validação: {exceeds}.','',
        '| Alpha | Condição | Rank-1 | TAR | FMR | Correto e aceito |','|---:|---|---:|---:|---:|---:|']
    for trial in trials:
        for condition,m in trial['results'].items():lines.append(f"| {trial['alpha']} | {condition} | {100*m['rank1']:.2f}% | {100*m['tar']:.2f}% | {100*m['far']:.3f}% | {100*m['joint_success']:.2f}% |")
    (run/'RELATORIO.md').write_text('\n'.join(lines),encoding='utf-8');write(run/'estado.json',{'stage':'concluido','selected_alpha':bestalpha,'exceeds_hybrid_validation':bool(exceeds)})

if __name__=='__main__':main()

"""Mistura limitada de escores das duas geometrias, selecionada so na validacao."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json
import numpy as np
from avaliar_candidato_congelado import fuse
from avaliar_robustez_reconhecimento import metrics
from treinar_reconhecedor_entrega import ORDER,CONDITIONS,eligibility,selection_key
from recorte_iris_sam31_alta_res import sha
from rodada_reconhecedor_entrega import write,result_path
ROOT=Path(__file__).resolve().parent
GEOMETRIC=('polar','spatial','transformer','arc_clahe','arc_red')
ALPHAS=(0.,.25,.5,.75,1.)

def blend_component(original,sam,alpha):
    if not 0<=alpha<=1:raise ValueError('Coeficiente fora de0..1')
    np.testing.assert_array_equal(original['labels'],sam['labels'])
    old=np.asarray(original['scores'],np.float64);new=np.asarray(sam['scores'],np.float64)
    available=(old>-2)&(new>-2)&original['valid'][:,None]&sam['valid'][:,None]
    mixed=old.copy();mixed[available]=(1-alpha)*old[available]+alpha*new[available]
    if not np.isfinite(mixed).all():raise ValueError('Escores nao finitos')
    # Nao excluir consulta nem descartar o controle quando SAM nao e disponivel.
    return {'scores':mixed,'valid':original['valid'].copy(),'labels':original['labels'].copy()}

def main():
    p=argparse.ArgumentParser();p.add_argument('--reference-root',type=Path,required=True);p.add_argument('--sam-run',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    assert (a.sam_run/'CONCLUIDO.json').exists()
    frozen_file=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json'
    inputs={}
    for condition,level in CONDITIONS:
        folder=result_path(a.reference_root,'nearest',condition,level)
        for name in ORDER:inputs[str((folder/f'scores_{name}.npz').resolve())]=sha(folder/f'scores_{name}.npz')
        for name in GEOMETRIC:inputs[str((a.sam_run/condition/f'scores_{name}.npz').resolve())]=sha(a.sam_run/condition/f'scores_{name}.npz')
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Validation-only exploratory development after direct SAM geometry validation, no test metric input',
        'alphas':ALPHAS,'selection_candidates':ALPHAS[1:-1],'geometric_components':GEOMETRIC,
        'rule':'Convex raw-score interpolation within5polar components, then existing9fusion/calibration/threshold. Keep original scores/validity whereSAM unavailable. Choose eligible alpha maximizing meanjoint,worstjoint,meanRank1; tie smalleralpha. Original retained if none eligible.',
        'eligibility':'CleanRank1/TAR>=control,cleanFMR<=1%;each10percentocclusionFMR<=control;mean3joint>control. Absolute all-conditionFMR<=1% separately.',
        'source_sha256':sha(__file__),'frozen_calibration_sha256':sha(frozen_file),'input_sha256':inputs,'sam_result_sha256':sha(a.sam_run/'CONCLUIDO.json')}
    write(out/'protocolo.json',protocol);(out/'source.py').write_bytes(Path(__file__).read_bytes())
    frozen=json.loads(frozen_file.read_text());threshold=frozen['frozen_threshold'];data={}
    for condition,level in CONDITIONS:
        folder=result_path(a.reference_root,'nearest',condition,level);old=[];new={}
        for name in ORDER:
            with np.load(folder/f'scores_{name}.npz',allow_pickle=False) as z:old.append({k:z[k].copy() for k in ('scores','valid','labels')})
        for name in GEOMETRIC:
            with np.load(a.sam_run/condition/f'scores_{name}.npz',allow_pickle=False) as z:new[name]={k:z[k].copy() for k in ('scores','valid','labels')}
        data[condition]=(old,new)
    trials=[];baseline=None;best=None
    for alpha in ALPHAS:
        results={}
        for condition,(old,new) in data.items():
            components=[blend_component(c,new[name],alpha) if name in GEOMETRIC else c for name,c in zip(ORDER,old)]
            scores,valid=fuse(components,frozen['component_calibration_red_and_clahe']);labels=old[0]['labels'];m,c,accepted=metrics(scores,labels,threshold,valid)
            m.update(joint_success=float((c&accepted).mean()),threshold=threshold);results[condition]=m
            np.savez_compressed(out/f'scores_alpha{alpha}_{condition}.npz',scores=scores,labels=labels,valid=valid,correct=c,accepted=accepted)
        if alpha==0:baseline=results
        eligible=alpha in ALPHAS[1:-1] and eligibility(results,baseline)
        trial={'alpha':alpha,'results':results,'eligible':eligible};trials.append(trial)
        if eligible and (best is None or (selection_key(results),-alpha)>(selection_key(best['results']),-best['alpha'])):best=trial
    final={'status':'concluido','selected_alpha':None if best is None else best['alpha'],'eligible_gain':best is not None,
        'results':baseline if best is None else best['results'],'baseline':baseline,'trials':trials,'threshold':threshold,
        'absolute_fmr_target_all_conditions':False if best is None else all(r['far']<=.01 for r in best['results'].values()),'test_inference':False,'recognizer_replaced':False}
    write(out/'CONCLUIDO.json',final)
    if best is not None:write(out/'CANDIDATO_VALIDACAO.json',{'frozen_utc':datetime.now(timezone.utc).isoformat(),'alpha':best['alpha'],'geometric_components':GEOMETRIC,'calibration_sha256':sha(frozen_file),'threshold':threshold,'selection_protocol_sha256':sha(out/'protocolo.json'),'selected_validation_results':best['results']})
    lines=['# Combinação das geometrias — validação','',f"Coeficiente selecionado: {final['selected_alpha']}. Ganho elegível: {final['eligible_gain']}.",'',
        '| Peso SAM | Condição | Rank-1 | TAR | FMR | Correto e aceito |','|---:|---|---:|---:|---:|---:|']
    for t in trials:
        for condition,m in t['results'].items():lines.append(f"| {t['alpha']} | {condition} | {100*m['rank1']:.2f}% | {100*m['tar']:.2f}% | {100*m['far']:.3f}% | {100*m['joint_success']:.2f}% |")
    lines+=['','Mesmos482denominadores, pesos globais e limiar. Busca limitada de desenvolvimento; sem nova inferência de teste, referência clínica ou substituição do controle.']
    (out/'RELATORIO.md').write_text('\n'.join(lines),encoding='utf-8');print(json.dumps({'selected_alpha':final['selected_alpha'],'eligible_gain':final['eligible_gain'],'results':final['results']}))

if __name__=='__main__':main()

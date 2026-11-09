"""Ablação de três grupos fixos de descritores usando escores já calculados."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json
import numpy as np
from avaliar_candidato_congelado import fuse
from avaliar_robustez_reconhecimento import metrics
from treinar_reconhecedor_entrega import eligibility,selection_key,ORDER,CONDITIONS
from rodada_reconhecedor_entrega import write,result_path
from recorte_iris_sam31_alta_res import sha
ROOT=Path(__file__).resolve().parent
GROUPS={'rgb_only':('rgb','r50','convnext','native'),'polar_only':('polar','spatial','transformer','arc_clahe','arc_red'),'native_only':('native',)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--reference-root',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    files={}
    for mode in ('nearest','continuous'):
        for condition,level in CONDITIONS:
            for name in ORDER:
                f=result_path(a.reference_root,mode,condition,level)/f'scores_{name}.npz';files[str(f.resolve())]=sha(f)
    frozen=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json'
    write(out/'protocolo.json',{'registered_utc':datetime.now(timezone.utc).isoformat(),'groups':GROUPS,'input_sha256':files,
        'source_sha256':sha(__file__),'frozen_calibration_sha256':sha(frozen),'scope':'Posthoc development validation ablation. Combined all-component results already examined; these3groups fixed before computing their results. No training or test inference.',
        'selection':'Same primary gate as encoder trial: cleanRank1/TAR no lower,cleanFMR<=1%,occludedFMR no higher,mean3joint higher; choose greatest meanjoint,tie worstjoint,tie meanRank1. No optimization of weights or threshold.'})
    config=json.loads(frozen.read_text());threshold=config['frozen_threshold'];baseline={};data={};results={}
    for condition,level in CONDITIONS:
        data[condition]={}
        for mode in ('nearest','continuous'):
            components=[]
            for name in ORDER:
                f=result_path(a.reference_root,mode,condition,level)/f'scores_{name}.npz'
                with np.load(f,allow_pickle=False) as z:components.append({k:z[k].copy() for k in ('scores','labels','valid')})
            data[condition][mode]=components
        scores,valid=fuse(data[condition]['nearest'],config['component_calibration_red_and_clahe']);labels=data[condition]['nearest'][0]['labels']
        m,c,accepted=metrics(scores,labels,threshold,valid);m['joint_success']=float((c&accepted).mean());baseline[condition]=m
        for group,names in GROUPS.items():
            chosen=[data[condition]['continuous' if name in names else 'nearest'][i] for i,name in enumerate(ORDER)]
            scores,valid=fuse(chosen,config['component_calibration_red_and_clahe']);m,c,accepted=metrics(scores,labels,threshold,valid);m['joint_success']=float((c&accepted).mean())
            results.setdefault(group,{})[condition]=m;np.savez_compressed(out/f'scores_{group}_{condition}.npz',scores=scores,labels=labels,valid=valid,correct=c,accepted=accepted)
    eligible=[name for name,r in results.items() if eligibility(r,baseline)]
    chosen=max(eligible,key=lambda name:selection_key(results[name])) if eligible else None
    final={'baseline':baseline,'results':results,'eligible':eligible,'selected_group':chosen,'recognizer_replaced':False,'test_inference':False}
    write(out/'CONCLUIDO.json',final)
    lines=['# Contorno por grupo de descritores','',f'Candidato elegível: {chosen or "nenhum"}. Ablação exploratória de validação; pesos e limiar históricos mantidos.','',
        '| Grupo | Condição | Rank-1 | TAR | FMR | Correto e aceito |','|---|---|---:|---:|---:|---:|']
    for name,record in {'nearest':baseline,**results}.items():
        for condition,r in record.items():lines.append(f"| {name} | {condition} | {100*r['rank1']:.2f}% | {100*r['tar']:.2f}% | {100*r['far']:.3f}% | {100*r['joint_success']:.2f}% |")
    (out/'RELATORIO.md').write_text('\n'.join(lines),encoding='utf-8');print(json.dumps(final),flush=True)

if __name__=='__main__':main()

"""Ablação individual dos cinco descritores polares; escolha só pela validação."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json
import numpy as np
from combinar_geometrias_sam31 import GEOMETRIC,blend_component
from treinar_reconhecedor_entrega import ORDER,CONDITIONS,eligibility,selection_key
from avaliar_candidato_congelado import fuse
from avaliar_robustez_reconhecimento import metrics
from recorte_iris_sam31_alta_res import sha
from rodada_reconhecedor_entrega import result_path,write
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--reference-root',type=Path,required=True);p.add_argument('--sam-run',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    calibration=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json';frozen=json.loads(calibration.read_text());threshold=frozen['frozen_threshold']
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Exploratory individual-component validation ablation after threegroup and commonalphatrials; no test input or coefficient fitting',
        'components':GEOMETRIC,'alpha':1.,'source_sha256':sha(__file__),'sam_result_sha256':sha(a.sam_run/'CONCLUIDO.json'),'calibration_sha256':sha(calibration),
        'rule':'For each component separately replace its oldgeometry score with SAMgeometry score; keep other8 unchanged. Same clean-preservation and FMR guard. Choose greatest meanjoint,worstjoint,meanRank1,lexicalname; keep control if none.'}
    write(out/'protocolo.json',protocol);(out/'source.py').write_bytes(Path(__file__).read_bytes());baseline={};results={};inputs={}
    for condition,level in CONDITIONS:
        folder=result_path(a.reference_root,'nearest',condition,level);old=[];sam={}
        for name in ORDER:
            file=folder/f'scores_{name}.npz';inputs[str(file.resolve())]=sha(file)
            with np.load(file,allow_pickle=False) as z:old.append({k:z[k].copy() for k in ('scores','valid','labels')})
        for name in GEOMETRIC:
            file=a.sam_run/condition/f'scores_{name}.npz';inputs[str(file.resolve())]=sha(file)
            with np.load(file,allow_pickle=False) as z:sam[name]={k:z[k].copy() for k in ('scores','valid','labels')}
        labels=old[0]['labels'];scores,valid=fuse(old,frozen['component_calibration_red_and_clahe']);m,c,accepted=metrics(scores,labels,threshold,valid);m.update(joint_success=float((c&accepted).mean()),threshold=threshold);baseline[condition]=m
        for name in GEOMETRIC:
            items=old.copy();items[ORDER.index(name)]=blend_component(old[ORDER.index(name)],sam[name],1.)
            scores,valid=fuse(items,frozen['component_calibration_red_and_clahe']);m,c,accepted=metrics(scores,labels,threshold,valid);m.update(joint_success=float((c&accepted).mean()),threshold=threshold);results.setdefault(name,{})[condition]=m
            np.savez_compressed(out/f'scores_{name}_{condition}.npz',scores=scores,labels=labels,valid=valid,correct=c,accepted=accepted)
    write(out/'ENTRADAS_SHA256.json',inputs);eligible=[name for name,r in results.items() if eligibility(r,baseline)];chosen=max(eligible,key=lambda name:(selection_key(results[name]),name)) if eligible else None
    final={'status':'concluido','baseline':baseline,'results':results,'eligible':eligible,'selected_component':chosen,'test_inference':False,'recognizer_replaced':False};write(out/'CONCLUIDO.json',final)
    if chosen:write(out/'CANDIDATO_VALIDACAO.json',{'frozen_utc':datetime.now(timezone.utc).isoformat(),'components':[chosen],'alpha':1.,'threshold':threshold,'calibration_sha256':sha(calibration),'protocol_sha256':sha(out/'protocolo.json'),'validation_results':results[chosen]})
    lines=['# Ablação individual da geometria SAM3.1','',f'Candidato elegível: {chosen}.','',
        '| Componente alterado | Condição | Rank-1 | TAR | FMR | Correto e aceito |','|---|---|---:|---:|---:|---:|']
    for name,rs in {'baseline':baseline,**results}.items():
        for condition,m in rs.items():lines.append(f"| {name} | {condition} | {100*m['rank1']:.2f}% | {100*m['tar']:.2f}% | {100*m['far']:.3f}% | {100*m['joint_success']:.2f}% |")
    (out/'RELATORIO.md').write_text('\n'.join(lines),encoding='utf-8');print(json.dumps({'eligible':eligible,'selected_component':chosen,'selected_results':None if chosen is None else results[chosen]}))

if __name__=='__main__':main()

"""Ablação de três grupos arquiteturais fixos para geometria SAM3.1."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json
import numpy as np
from combinar_geometrias_sam31 import blend_component,GEOMETRIC
from avaliar_candidato_congelado import fuse
from avaliar_robustez_reconhecimento import metrics
from treinar_reconhecedor_entrega import ORDER,CONDITIONS,eligibility,selection_key
from rodada_reconhecedor_entrega import result_path,write
from recorte_iris_sam31_alta_res import sha
ROOT=Path(__file__).resolve().parent
GROUPS={'arc_only':('arc_clahe','arc_red'),'learned_polar':('polar','spatial','transformer'),'spatial_only':('spatial',)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--reference-root',type=Path,required=True);p.add_argument('--sam-run',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    frozen_file=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json'
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Posthoc development validation ablation after all5geometrycomponents and common-alpha variants were evaluated. No test metric input or parameter fitting.',
        'groups':GROUPS,'alpha':1.,'rule':'Same fixed-threshold clean-preservation/FMR guard; choose eligible group by meanjoint,worstjoint,meanRank1,lexicalname. All482queries retained.',
        'source_sha256':sha(__file__),'blend_source_sha256':sha(ROOT/'combinar_geometrias_sam31.py'),'sam_result_sha256':sha(a.sam_run/'CONCLUIDO.json'),'calibration_sha256':sha(frozen_file)}
    write(out/'protocolo.json',protocol);(out/'source.py').write_bytes(Path(__file__).read_bytes())
    frozen=json.loads(frozen_file.read_text());threshold=frozen['frozen_threshold'];baseline={};results={};inputs={}
    for condition,level in CONDITIONS:
        old=[];sam={};folder=result_path(a.reference_root,'nearest',condition,level)
        for name in ORDER:
            file=folder/f'scores_{name}.npz';inputs[str(file.resolve())]=sha(file)
            with np.load(file,allow_pickle=False) as z:old.append({k:z[k].copy() for k in ('scores','valid','labels')})
        for name in GEOMETRIC:
            file=a.sam_run/condition/f'scores_{name}.npz';inputs[str(file.resolve())]=sha(file)
            with np.load(file,allow_pickle=False) as z:sam[name]={k:z[k].copy() for k in ('scores','valid','labels')}
        labels=old[0]['labels'];scores,valid=fuse(old,frozen['component_calibration_red_and_clahe']);m,c,accepted=metrics(scores,labels,threshold,valid);m.update(joint_success=float((c&accepted).mean()),threshold=threshold);baseline[condition]=m
        for group,names in GROUPS.items():
            items=[blend_component(c,sam[name],1.) if name in names else c for name,c in zip(ORDER,old)]
            scores,valid=fuse(items,frozen['component_calibration_red_and_clahe']);m,c,accepted=metrics(scores,labels,threshold,valid);m.update(joint_success=float((c&accepted).mean()),threshold=threshold);results.setdefault(group,{})[condition]=m
            np.savez_compressed(out/f'scores_{group}_{condition}.npz',scores=scores,valid=valid,labels=labels,correct=c,accepted=accepted)
    write(out/'ENTRADAS_SHA256.json',inputs)
    eligible=[name for name,r in results.items() if eligibility(r,baseline)];selected=max(eligible,key=lambda name:(selection_key(results[name]),name)) if eligible else None
    final={'status':'concluido','baseline':baseline,'results':results,'eligible':eligible,'selected_group':selected,'test_inference':False,'recognizer_replaced':False}
    write(out/'CONCLUIDO.json',final)
    if selected:write(out/'CANDIDATO_VALIDACAO.json',{'frozen_utc':datetime.now(timezone.utc).isoformat(),'selected_group':selected,'components':GROUPS[selected],'alpha':1.,'threshold':threshold,'protocol_sha256':sha(out/'protocolo.json'),'validation_results':results[selected]})
    lines=['# Geometria SAM3.1 por grupo — validação','',f'Candidato elegível: {selected}.','',
        '| Grupo | Condição | Rank-1 | TAR | FMR | Correto e aceito |','|---|---|---:|---:|---:|---:|']
    for name,r in {'baseline':baseline,**results}.items():
        for condition,m in r.items():lines.append(f"| {name} | {condition} | {100*m['rank1']:.2f}% | {100*m['tar']:.2f}% | {100*m['far']:.3f}% | {100*m['joint_success']:.2f}% |")
    (out/'RELATORIO.md').write_text('\n'.join(lines),encoding='utf-8');print(json.dumps(final))

if __name__=='__main__':main()

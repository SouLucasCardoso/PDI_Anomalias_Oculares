"""Misturas discretas pré-listadas, sem otimizar pesos nem recalibrar limiar."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
from avaliar_candidato_congelado import fuse
from avaliar_robustez_reconhecimento import metrics
from treinar_reconhecedor_entrega import ORDER,CONDITIONS,eligibility,selection_key
from rodada_reconhecedor_entrega import result_path,write
ROOT=Path(__file__).resolve().parent
GROUPS={'polar_only':('polar',),'native_only':('native',),'native_and_polar':('native','polar')}
ALPHAS=(.25,.5)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def blend(old,new,alpha):
    np.testing.assert_array_equal(old['labels'],new['labels'])
    np.testing.assert_array_equal(old['valid'],new['valid'])
    scores=(1-alpha)*old['scores']+alpha*new['scores']
    scores[old['scores']<=-2]=-2
    return {'scores':scores,'labels':old['labels'],'valid':old['valid']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True)
    p.add_argument('--validation-run',type=Path,required=True);a=p.parse_args();run=a.run_dir.resolve();run.mkdir(parents=True,exist_ok=False)
    validation=a.validation_run.resolve();assert (validation/'CONCLUIDO.json').exists()
    reference=ROOT/'outputs/reconhecedor_contorno_2026-11-08';frozen_file=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json';config=json.loads(frozen_file.read_text())
    inputs={};data={}
    for condition,level in CONDITIONS:
        old=[];new={}
        for name in ORDER:
            file=result_path(reference,'nearest',condition,level)/f'scores_{name}.npz';inputs[str(file)]=sha(file)
            with np.load(file) as z:old.append({k:z[k].copy() for k in ('scores','labels','valid')})
        for name in ('native','polar'):
            file=validation/condition/f'scores_{name}.npz';inputs[str(file)]=sha(file)
            with np.load(file) as z:new[name]={k:z[k].copy() for k in ('scores','labels','valid')}
        data[condition]=(old,new)
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sha(__file__),
        'groups':GROUPS,'alphas':ALPHAS,'input_sha256':inputs,'calibration_sha256':sha(frozen_file),
        'scope':'Additional reused-validation development after full-strength contour evaluation. Six fixed candidates; no fitting or test inference.',
        'selection':'Original relative gate unchanged: preserve clean Rank1/TAR,cleanFMR<=1%,occludedFMR no greater,mean3joint higher; max meanjoint,worstjoint,meanRank1.'}
    write(run/'protocolo.json',protocol);results={};baseline={}
    for condition,(old,new) in data.items():
        for group,names,alpha in [('reference',(),0.)]+[(g,n,a) for g,n in GROUPS.items() for a in ALPHAS]:
            items=[blend(old[i],new[n],alpha) if n in names else old[i] for i,n in enumerate(ORDER)]
            scores,valid=fuse(items,config['component_calibration_red_and_clahe']);labels=old[0]['labels']
            m,c,accepted=metrics(scores,labels,config['frozen_threshold'],valid);m['joint_success']=float((c&accepted).mean())
            key='reference' if group=='reference' else f'{group}_alpha{alpha}'
            if key=='reference':baseline[condition]=m
            else:results.setdefault(key,{})[condition]=m
            np.savez_compressed(run/f'fusion_{key}_{condition}.npz',scores=scores,labels=labels,valid=valid,correct=c,accepted=accepted)
    eligible=[n for n,v in results.items() if eligibility(v,baseline)];selected=max(eligible,key=lambda n:selection_key(results[n])) if eligible else None
    final={'status':'concluido','selected':selected,'eligible_gain':selected is not None,'results':results,'baseline':baseline,'test_inference':False,'recognizer_replaced':False}
    write(run/'CONCLUIDO.json',final)
    if selected:
        group,alpha=selected.rsplit('_alpha',1)
        write(run/'CANDIDATO_IDENTIDADE.json',{'frozen_utc':datetime.now(timezone.utc).isoformat(),'group':group,'components':GROUPS[group],
            'alpha':float(alpha),'spec':json.loads((validation/'protocolo.json').read_text())['segmentation_selection']['spec'],
            'threshold':config['frozen_threshold'],'validation':results[selected],
            'validation_protocol_sha256':sha(run/'protocolo.json'),'input_validation_run':str(validation)})
    lines=['# Misturas fixas do novo contorno','',f'Candidato elegível: **{selected or "nenhum"}**.','',
        '| Candidato | Condição | Rank-1 | TAR | FMR | Correto e aceito |','|---|---|---:|---:|---:|---:|']
    for name,record in {'reference':baseline,**results}.items():
        for condition,m in record.items():lines.append(f"| {name} | {condition} | {100*m['rank1']:.2f}% | {100*m['tar']:.2f}% | {100*m['far']:.3f}% | {100*m['joint_success']:.2f}% |")
    lines+=['','Sem ajuste do limiar ou descarte de consultas. Exploração adicional em validação reutilizada, sem confirmação independente.']
    (run/'RELATORIO_ATUAL.md').write_text('\n'.join(lines),encoding='utf-8');print(json.dumps(final),flush=True)


if __name__=='__main__':main()

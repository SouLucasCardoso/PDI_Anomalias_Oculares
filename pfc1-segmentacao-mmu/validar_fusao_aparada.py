"""Hipotese unica de fusao resistente a componentes extremos; validacao apenas."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
from validar_fusao_identidade_adaptada import ORDER,calibrate
ROOT=Path(__file__).resolve().parent


def trimmed_fuse(components,parameters):
    from normalizar_consulta import normalize
    available=np.logical_and.reduce([c['scores']>-2 for c in components])
    valid=np.logical_and.reduce([c['valid'] for c in components])&available.any(1)
    first,second=parameters
    z=[(components[j]['scores']-first[j]['mean'])/first[j]['std'] for j in range(7)]
    z.append(((components[7]['scores']-first[7]['mean'])/first[7]['std']+(components[8]['scores']-second[7]['mean'])/second[7]['std'])/2)
    # Each of eight recognizer groups contributes equally; ArcIris views stay one group.
    value=np.sort(np.stack(z),axis=0)[1:-1].mean(0)
    scores=1/(1+np.exp(-np.clip(value,-30,30)));scores[~available]=-2;scores[~valid]=-2
    return normalize(scores,valid)


def main():
    from avaliar_candidato_congelado import fuse
    from avaliar_robustez_reconhecimento import metrics,operating_threshold
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    out=a.output_root/'fusao_aparada_val_2026-10-21';out.mkdir(parents=True,exist_ok=False)
    protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Exploratory validation ONLY, no test inference or automatic promotion',
        hypothesis='A few extreme component scores can dominate the arithmetic fusion. One fixed alternative: drop smallest/largest of eight standardized recognizer group scores for EACH candidate, mean remaining six; preserve ArcIris CLAHE/red as one mean group. Logistic then unchanged query normalization.',
        controls='Original and robust segmenter branches, arithmetic original control versus trimmed candidate. Identical clean-only component normalization for both; separate thresholds calibrated once CLEAN FMR<=1%, applied unchanged upper/lower10%. No trim-count/weight search.',
        acceptance='All482 queries retained; single query photo, supplied side,16 candidates. Descriptive development results only. No query ground truth in fusion; identity labels used solely for clean calibration and evaluation.',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    results=[];sources={};calibrations={}
    for branch,tag in [('original',''),('robust','_segmentador_8f126141f4dd')]:
        grouped={}
        for condition,suffix in [('clean',''),('upper10','_oclusao_superior_10'),('lower10','_oclusao_inferior_10')]:
            folder=ROOT/'outputs'/f'confirmacao_congelada_val{suffix}{tag}_2026-10-21';components=[]
            for name in ORDER:
                file=folder/f'scores_{name}.npz';sources[str(file)]=hashlib.sha256(file.read_bytes()).hexdigest()
                with np.load(file) as z:components.append({k:z[k] for k in ('scores','labels','valid')})
            assert components[0]['scores'].shape==(482,16)
            for c in components:np.testing.assert_array_equal(c['labels'],components[0]['labels'])
            grouped[condition]=components
        parameters=calibrate(grouped['clean'])
        for mode,method in [('arithmetic',fuse),('trimmed',trimmed_fuse)]:
            data={}
            for condition,components in grouped.items():
                scores,valid=method(components,parameters);data[condition]=dict(scores=scores,valid=valid,labels=components[0]['labels'])
            clean=data['clean'];imp=np.ones_like(clean['scores'],bool);imp[np.arange(482),clean['labels']]=False
            threshold=operating_threshold(clean['scores'][imp&clean['valid'][:,None]&(clean['scores']>-2)])
            calibrations[f'{branch}_{mode}']=dict(component_normalization=parameters,threshold=threshold)
            for condition,c in data.items():
                r,correct,accepted=metrics(c['scores'],c['labels'],threshold,c['valid']);r.update(branch=branch,mode=mode,condition=condition,threshold=threshold,joint_success=float((correct&accepted).mean()))
                results.append(r);np.savez_compressed(out/f'scores_{branch}_{mode}_{condition}.npz',**c,correct=correct,accepted=accepted)
    final=dict(status='trimmed_fusion_validation_completed',results=results,calibrations=calibrations,source_sha256=sources,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(results,indent=2),flush=True)


if __name__=='__main__':main()

"""Avalia componente adaptado na fusao, calibrando so na validacao limpa."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent
ORDER=['rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red']

def calibrate(components):
    labels=components[0]['labels'];parameters=[]
    for c in components:
        np.testing.assert_array_equal(c['labels'],labels);imp=np.ones_like(c['scores'],bool);imp[np.arange(len(labels)),labels]=False;usable=imp&c['valid'][:,None]&(c['scores']>-2);mean=float(c['scores'][usable].mean());std=float(c['scores'][usable].std())
        if not np.isfinite(std) or std<=0:raise ValueError('Invalid calibration')
        parameters.append(dict(mean=mean,std=std))
    return [parameters[:7]+[parameters[7]],parameters[:7]+[parameters[8]]]

def main():
    from avaliar_candidato_congelado import fuse
    from avaliar_robustez_reconhecimento import operating_threshold,metrics
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'fusao_identidade_adaptada_val_2026-10-21'
    if not out.exists():
        out.mkdir(parents=True)
        protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Exploratory train/validation development ONLY; fixed strategies registered before adapted model results, no test inference or automatic replacement',
          'strategies':'Five controls/candidates: original frozen preprocessing+original RGB; original preprocessing others+unadapted RGB/new segmenter; original preprocessing others+adapted RGB/new segmenter; robust segmenter all+unadapted RGB; robust segmenter all+adapted RGB. Shared7components each1/8, ArcIris CLAHE/red half each of1/8, unchanged fixed fusion rule.',
          'calibration':'For EACH strategy compute component impostor mean/std once on CLEAN validation only, per-query normalization, threshold CLEAN empirical FMR<=1%. Apply exactly same parameters/threshold to upper/lower10%. No per-occlusion calibration, weight search or threshold search to hit target.',
          'selection':'Adapted checkpoint already selected solely by single-encoder clean/occluded validation rule; this fusion comparison never selects another epoch',
          'counts':'All482 queries,16 supplied-side candidates,15 impostors/query. Failures retained; no quality filter.',
          'limits':'Repeated validation, new distribution calibration control required; unknown external-pretraining identities. Single-photo inference even hybrid preprocessing. No minimum-area or independent-test claim.',
          'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    else:assert (out/'source.py').read_bytes()==Path(__file__).read_bytes()
    if (out/'CONCLUIDO.json').exists():raise ValueError('Preserve completed run')
    trained=a.output_root/'identidade_oclusao_segmentacao_2026-10-21'
    if not (trained/'CONCLUIDO.json').exists():print('Fusion protocol registered; rerun after training completion.',flush=True);return
    completed=json.loads((trained/'CONCLUIDO.json').read_text());assert hashlib.sha256((trained/'melhor_modelo.pt').read_bytes()).hexdigest()==completed['checkpoint_sha256']
    conditions={'clean':'','upper10':'_oclusao_superior_10','lower10':'_oclusao_inferior_10'};sources={};source_hashes={}
    def read(file):
        source_hashes[str(file)]=hashlib.sha256(file.read_bytes()).hexdigest()
        with np.load(file) as z:return {k:z[k] for k in ['scores','labels','valid']}
    for branch,tag in [('original',''),('robust','_segmentador_8f126141f4dd')]:
        sources[branch]={}
        for condition,suffix in conditions.items():
            folder=ROOT/'outputs'/f'confirmacao_congelada_val{suffix}{tag}_2026-10-21';sources[branch][condition]=[read(folder/f'scores_{name}.npz') for name in ORDER]
    adapted={name:read(trained/f'scores_melhor_{name}.npz') for name in conditions};baseline={name:read(trained/f'scores_baseline_{name}.npz') for name in conditions}
    for name in conditions:
        np.testing.assert_array_equal(baseline[name]['labels'],sources['robust'][name][0]['labels']);np.testing.assert_allclose(baseline[name]['scores'],sources['robust'][name][0]['scores'],atol=1e-7,rtol=0)
    strategies=[('original_control','original',None),('hybrid_unadapted_control','original',baseline),('hybrid_adapted','original',adapted),('robust_unadapted_control','robust',baseline),('robust_adapted','robust',adapted)];results=[];frozen_parameters={}
    for name,branch,replacement in strategies:
        grouped={condition:list(sources[branch][condition]) for condition in conditions}
        if replacement:
            for condition in conditions:grouped[condition][0]=replacement[condition]
        parameters=calibrate(grouped['clean']);data={}
        for condition,components in grouped.items():
            for c in components:np.testing.assert_array_equal(c['labels'],components[0]['labels'])
            scores,valid=fuse(components,parameters);data[condition]=dict(scores=scores,valid=valid,labels=components[0]['labels'])
        clean=data['clean'];imp=np.ones_like(clean['scores'],bool);imp[np.arange(len(clean['labels'])),clean['labels']]=False;threshold=operating_threshold(clean['scores'][imp&clean['valid'][:,None]&(clean['scores']>-2)])
        frozen_parameters[name]=dict(component_normalization=parameters,threshold=threshold)
        for condition,c in data.items():
            result,correct,accepted=metrics(c['scores'],c['labels'],threshold,c['valid']);result.update(strategy=name,condition=condition,threshold=threshold,joint_success=float((correct&accepted).mean()));results.append(result);np.savez_compressed(out/f'scores_{name}_{condition}.npz',**c,correct=correct,accepted=accepted)
    final=dict(status='adapted_identity_fusion_validation_completed',results=results,parameters=frozen_parameters,selected_identity_epoch=completed['best_epoch'],identity_checkpoint_sha256=completed['checkpoint_sha256'],source_sha256=source_hashes,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps({'status':final['status'],'results':results},indent=2),flush=True)

if __name__=='__main__':main()

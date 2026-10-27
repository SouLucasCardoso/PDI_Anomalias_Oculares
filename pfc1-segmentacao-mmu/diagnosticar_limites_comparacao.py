"""Diagnostico TRAIN: limites descritivos, sem promover modelos ou mudar limiares."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from avaliar_robustez_reconhecimento import metrics,operating_threshold

NAME='diagnostico_comparacao_treino_2026-10-23'
METHODS={'original':('encoder_polar_espacial_2026-10-23','baseline'),
         'top3':('adaptador_polar_top3_2026-10-23','selected'),
         'penalizacao':('adaptador_polar_fmr_2026-10-23','selected'),
         'espacial':('encoder_polar_espacial_2026-10-23','selected')}

def describe(scores,labels,valid,clean_threshold):
    scores=np.asarray(scores,np.float64);labels=np.asarray(labels);valid=np.asarray(valid,bool)
    n,k=scores.shape;mask=np.ones_like(scores,bool);mask[np.arange(n),labels]=False
    # Failed queries remain rejections and retain their denominator. No score filtering.
    effective=scores.copy();effective[~valid]=-2
    oracle_threshold=operating_threshold(effective[mask])
    actual,correct,accepted=metrics(scores,labels,clean_threshold,valid)
    oracle,_,_=metrics(scores,labels,oracle_threshold,valid)
    genuine=scores[np.arange(n),labels];wrong=np.where(mask,scores,-np.inf).max(1)
    return dict(queries=n,candidates=k,correct=int(correct.sum()),rank1=actual['rank1'],
        fixed_clean_threshold=clean_threshold,fixed_tar=actual['tar'],fixed_fmr=actual['far'],
        diagnostic_oracle_threshold=oracle_threshold,diagnostic_maximum_tar_at_fmr1=oracle['tar'],
        diagnostic_fmr=oracle['far'],diagnostic_accepted=round(oracle['tar']*n),
        target_acceptances=int(np.ceil(.9*n)),
        genuine_below_hardest_impostor=int(((genuine<wrong)&valid).sum()),
        genuine_tied_hardest_impostor=int(((genuine==wrong)&valid).sum()),
        extraction_failures=int((~valid).sum()),
        median_valid_margin=float(np.median((genuine-wrong)[valid])))

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();out=a.root/NAME
    out.mkdir(exist_ok=False);result={};inputs={};arrays={};monitor=None
    for method,(folder_name,prefix) in METHODS.items():
        folder=a.root/folder_name;protocol=json.loads((folder/'protocolo.json').read_text());done=json.loads((folder/'CONCLUIDO.json').read_text())
        people=sorted(protocol['monitor_people'])
        if monitor is None:monitor=people
        assert monitor==people and len(people)==16 and not set(people)&set(protocol['fit_people'])
        rows=json.loads((folder/'rows.json').read_text());queries=[r for r in rows if r['subject'] in people and r['session']==2]
        assert len(queries)==480
        if arrays:assert queries==reference_queries
        else:reference_queries=queries
        group=done['baseline_monitor' if prefix=='baseline' else 'selected_monitor'];result[method]={};arrays[method]={}
        threshold=group['clean']['threshold']
        for tag in ['clean','upper10','lower10']:
            path=folder/f'scores_{prefix}_{tag}.npz';inputs[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
            with np.load(path) as z:scores=z['scores'];labels=z['labels'];valid=z['valid'];correct=z['correct']
            assert scores.shape==(480,16)
            measured=describe(scores,labels,valid,threshold);assert measured['rank1']==group[tag]['rank1'] and measured['fixed_tar']==group[tag]['tar'] and measured['fixed_fmr']==group[tag]['far']
            result[method][tag]=measured;arrays[method][tag]=dict(correct=correct,labels=labels)
    overlap={}
    for tag in ['clean','upper10','lower10']:
        for method in arrays:np.testing.assert_array_equal(arrays[method][tag]['labels'],arrays['original'][tag]['labels'])
        x=arrays['top3'][tag]['correct'];y=arrays['espacial'][tag]['correct']
        overlap[tag]=dict(both_correct=int((x&y).sum()),only_top3_correct=int((x&~y).sum()),only_spatial_correct=int((y&~x).sum()),both_wrong=int((~x&~y).sum()),
            unattainable_per_query_oracle_union_rank1=float((x|y).mean()))
    report=dict(status='saved_train_scores_diagnosed',scope='16 reused TRAIN monitor people; labels used ONLY for descriptive diagnostic. Per-condition oracle thresholds and query-wise oracle union are NOT deployable calibration/fusion and NEVER promote a model. No VAL/test, training, new image inference, threshold replacement or weights search.',
        methods=result,top3_spatial_overlap=overlap,input_sha256=inputs,new_training=False,new_image_inference=False,candidate_promoted=False,production_threshold_changed=False)
    (out/'CONCLUIDO.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

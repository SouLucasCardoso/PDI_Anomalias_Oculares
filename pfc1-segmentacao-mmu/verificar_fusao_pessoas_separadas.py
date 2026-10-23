"""Confere separacao por pessoa, selecao interna e inferencia apos recarga."""
from pathlib import Path
import argparse,csv,hashlib,json,tempfile
import numpy as np
import torch
from treinar_fusao_pessoas_separadas import person_split,fuse,NAMES,CONDITIONS
ROOT=Path(__file__).resolve().parent


def main():
    from treinar_segmentacao_ubipr import Sample
    from treinar_identidade_iris import IdentityEncoder
    from avaliar_candidato_congelado import extract,global_scores,digest
    from avaliar_robustez_reconhecimento import identity,metrics,operating_threshold,paired_ci
    from validar_lateralidade_informada import subset
    from diagnosticar_erros_validacao import transitions
    import reconhecedor_resnet50,reconhecedor_convnext
    p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,required=True);a=p.parse_args();out=a.folder
    final=json.loads((out/'CONCLUIDO.json').read_text());protocol=json.loads((out/'protocolo.json').read_text())
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';assert digest(manifest_file)==protocol['manifest_sha256']
    manifest=json.loads(manifest_file.read_text());split=person_split(manifest['train']);assert split==protocol['split_people']==final['model']['split_people']
    assert digest(out/'source.py')==protocol['script_sha256']
    assert digest(out/'MODELO_FUSAO.json')==final['model_sha256']
    for group in split.values():assert not set(group)&{r['subject'] for r in manifest['val']}
    weights=np.array(json.loads((out/'MODELO_FUSAO.json').read_text())['weights']);np.testing.assert_allclose(weights.sum(),1,atol=1e-6)
    key=lambda r:f"{r['subject']}_{r['side']}"
    eligible={key(r) for r in manifest['val'] if r['session']==1}&{key(r) for r in manifest['val'] if r['session']==2}
    rows=[Sample(**r) for r in manifest['val'] if key(r) in eligible];queries=[r for r in rows if r.session==2]
    subjects=np.array([r.subject for r in queries]);ids=sorted({identity(r) for r in rows});classes=sorted(set(subjects));labels=np.array([classes.index(s) for s in subjects]);assert len(queries)==482
    def read(file):
        with np.load(file) as z:return {k:z[k] for k in z.files}
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    replay=[];hashes={};selected={}
    for name in NAMES:
        file=out/name/'melhor_modelo.pt';assert digest(file)==final['model']['checkpoint_sha256'][name];hashes[name]=digest(file)
        checkpoint=torch.load(file,map_location='cpu',weights_only=True)
        assert checkpoint['fit_people']==split['encoder_fit'] and checkpoint['monitor_people']==split['encoder_monitor'] and checkpoint['excluded_meta_people']==split['fusion_fit']
        assert checkpoint['initialization_sha256']==protocol['imagenet_sha256'][name]
        assert checkpoint['training_head']['weight'].shape==(protocol['counts']['fit_eye_classes'],256)
        expected_batches=4*(protocol['counts']['fit_eye_classes']//16)*checkpoint['epoch']
        imagenet_file=ROOT/'data/modelos/torch/hub/checkpoints'/dict(r18='resnet18-f37072fd.pth',r50='resnet50-11ad3fa6.pth',convnext='convnext_tiny-983f1562.pth')[name]
        assert digest(imagenet_file)==protocol['imagenet_sha256'][name]
        initial=torch.load(imagenet_file,map_location='cpu',weights_only=True)
        batch_counters=[int(value)-int(initial.get(key_state.removeprefix('backbone.'),0)) for key_state,value in checkpoint['model'].items() if key_state.endswith('num_batches_tracked')]
        assert batch_counters and all(value==expected_batches for value in batch_counters)
        del initial
        with (out/name/'historico.csv').open(encoding='utf-8',newline='') as stream:history=list(csv.DictReader(stream))
        best=max(history,key=lambda r:(float(r['clean_tar']),min(float(r[f'{condition}_tar']) for condition in CONDITIONS),float(r['clean_rank1'])))
        assert int(best['epoch'])==checkpoint['epoch']==final['encoders'][name]['best_epoch'];selected[name]=int(best['epoch'])
        model=IdentityEncoder() if name=='r18' else reconhecedor_resnet50.Encoder() if name=='r50' else reconhecedor_convnext.Encoder();model.load_state_dict(checkpoint['model']);model.to(device).eval()
        for condition,suffix in [('clean',''),('upper10','_oclusao_superior_10'),('lower10','_oclusao_inferior_10')]:
            folder=Path(tempfile.gettempdir())/f'cache_confirmacao_val{suffix}_2026-10-21';images=np.load(folder/'rgb.npy',mmap_mode='r')
            with np.load(folder/'valid.npz') as z:valid=z['rgb']
            if name=='convnext':images=np.stack([reconhecedor_convnext.contrast(image) for image in images])
            full,qvalid=global_scores(extract(model,images,device),valid,rows);scores,actual_labels,_=subset(full,rows,ids)
            saved=read(out/name/f'scores_val_{condition}.npz');np.testing.assert_array_equal(saved['labels'],labels);np.testing.assert_array_equal(actual_labels,labels);np.testing.assert_array_equal(saved['valid'],qvalid)
            difference=float(np.abs(saved['scores']-scores).max());np.testing.assert_array_equal(saved['scores'],scores)
            replay.append(dict(model=name,condition=condition,max_abs_score_difference=difference))
        del model
        if device.type=='cuda':torch.cuda.empty_cache()
    decisions={};records=[]
    for strategy,w in [('uniform',np.full(3,1/3)),('learned',weights)]:
        decisions[strategy]={};threshold=final['thresholds'][strategy]
        for condition in CONDITIONS:
            components=[read(out/name/f'scores_val_{condition}.npz') for name in NAMES]
            for c in components:np.testing.assert_array_equal(c['labels'],labels)
            scores,valid=fuse(components,w);saved=read(out/f'scores_{strategy}_{condition}.npz');np.testing.assert_array_equal(scores,saved['scores']);np.testing.assert_array_equal(valid,saved['valid'])
            result,correct,accepted=metrics(scores,labels,threshold,valid);np.testing.assert_array_equal(correct,saved['correct']);np.testing.assert_array_equal(accepted,saved['accepted'])
            reported=next(r for r in final['results'] if r['strategy']==strategy and r['condition']==condition)
            for metric in ['rank1','tar','far','extraction_failures','queries']:assert result[metric]==reported[metric]
            assert reported['threshold']==threshold
            if condition=='clean':
                imp=np.ones_like(scores,bool);imp[np.arange(482),labels]=False
                assert operating_threshold(scores[imp&valid[:,None]&(scores>-2)])==threshold
            decisions[strategy][condition]=dict(correct=correct,accepted=accepted)
    for condition,suffix in [('clean',''),('upper10','_oclusao_superior_10'),('lower10','_oclusao_inferior_10')]:
        original=read(ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21'/'scores_finais.npz');np.testing.assert_array_equal(original['labels'],labels)
        learned=decisions['learned'][condition]
        for control,base in [('uniform_same_three',decisions['uniform'][condition]),('original_eight_group_reference',original)]:
            records.append(dict(condition=condition,control=control,rank1_gain_pp=100*float((learned['correct'].astype(float)-base['correct']).mean()),rank1_gain_ci95_pp=paired_ci(learned['correct'],base['correct'],subjects),tar_gain_pp=100*float((learned['accepted'].astype(float)-base['accepted']).mean()),tar_gain_ci95_pp=paired_ci(learned['accepted'],base['accepted'],subjects),transitions=transitions(base['correct'],learned['correct'])))
    audit=dict(status='person_split_and_reload_verified',identity_fit_monitor_meta_disjoint=True,development_validation_disjoint=True,segmentation_seen_meta_people=True,batchnorm_counters_fit_only=True,
        selected_epochs=selected,checkpoint_sha256=hashes,replay=replay,records=records,test_inference=False,frozen_candidate_replaced=False,
        limitations='Only identity encoders have disjoint fit/monitor/meta people. Frozen segmentation saw these people. Three-model pilot differs from original8-group reference. Reused development validation. Bootstrap5000 person clusters, fixed gallery and thresholds, pointwise, no selection correction.',script_sha256=digest(Path(__file__)))
    (out/'VERIFICACAO_RELOAD.json').write_text(json.dumps(audit,indent=2),encoding='utf-8');print(json.dumps(dict(status=audit['status'],selected_epochs=selected,replay=replay,records=records),indent=2))


if __name__=='__main__':main()

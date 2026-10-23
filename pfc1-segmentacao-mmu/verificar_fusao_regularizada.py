"""Recarrega pesos JSON, reproduz escores e compara com controles pareados."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from treinar_fusao_regularizada import predict,ORDER
ROOT=Path(__file__).resolve().parent


def main():
    from avaliar_robustez_reconhecimento import metrics,paired_ci,operating_threshold
    from diagnosticar_erros_validacao import transitions
    p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,required=True);p.add_argument('--validation-only',action='store_true',help='Reproduce restored validation/model package without excluded train matrices/caches');a=p.parse_args();out=a.folder
    final=json.loads((out/'CONCLUIDO.json').read_text());model_file=out/'MODELO_FUSAO.json'
    assert hashlib.sha256(model_file.read_bytes()).hexdigest()==final['model_sha256']
    model=json.loads(model_file.read_text());weights=np.array(model['weights']);np.testing.assert_allclose(weights.sum(),1,atol=1e-6)
    # float32 softmax can sum slightly off1, accepted and preserved by predict.
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text())
    key=lambda r:f"{r['subject']}_{r['side']}"
    eligible={key(r) for r in manifest['val'] if r['session']==1}&{key(r) for r in manifest['val'] if r['session']==2}
    rows=[r for r in manifest['val'] if r['session']==2 and key(r) in eligible]
    subjects=np.array([r['subject'] for r in rows]);classes=sorted(set(subjects));labels=np.array([classes.index(s) for s in subjects]);assert len(rows)==482
    def read(file):
        with np.load(file) as z:return {k:z[k] for k in z.files}
    records=[];sources={}
    for condition,suffix in [('clean',''),('upper10','_oclusao_superior_10'),('lower10','_oclusao_inferior_10')]:
        folder=ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21'
        components=[read(folder/f'scores_{name}.npz') for name in ORDER]
        for c in components:np.testing.assert_array_equal(c['labels'],labels)
        for name in ORDER:sources[str(folder/f'scores_{name}.npz')]=hashlib.sha256((folder/f'scores_{name}.npz').read_bytes()).hexdigest()
        strategies={}
        for strategy,w in [('uniform_query_z',np.full(8,1/8)),('learned_query_z',weights)]:
            scores,valid=predict(components,w);saved=read(out/f'scores_{strategy}_{condition}.npz')
            np.testing.assert_array_equal(saved['labels'],labels);np.testing.assert_array_equal(valid,saved['valid']);np.testing.assert_array_equal(scores,saved['scores'])
            threshold=final['thresholds'][strategy]
            result,correct,accepted=metrics(scores,labels,threshold,valid)
            reported=next(r for r in final['results'] if r['strategy']==strategy and r['condition']==condition)
            for key_metric in ['rank1','tar','far','extraction_failures','queries']:assert result[key_metric]==reported[key_metric]
            assert reported['threshold']==threshold
            np.testing.assert_array_equal(correct,saved['correct']);np.testing.assert_array_equal(accepted,saved['accepted'])
            if condition=='clean':
                imp=np.ones_like(scores,bool);imp[np.arange(482),labels]=False
                assert operating_threshold(scores[imp&valid[:,None]&(scores>-2)])==threshold
            strategies[strategy]=dict(correct=correct,accepted=accepted,result=result)
        original=read(folder/'scores_finais.npz');np.testing.assert_array_equal(original['labels'],labels)
        learned=strategies['learned_query_z']
        for control in ['uniform_query_z','original_frozen']:
            base=strategies[control] if control!='original_frozen' else dict(correct=original['correct'],accepted=original['accepted'])
            records.append(dict(condition=condition,control=control,
                rank1_gain_pp=100*float((learned['correct'].astype(float)-base['correct']).mean()),
                rank1_gain_ci95_pp=paired_ci(learned['correct'],base['correct'],subjects),
                tar_gain_pp=100*float((learned['accepted'].astype(float)-base['accepted']).mean()),
                tar_gain_ci95_pp=paired_ci(learned['accepted'],base['accepted'],subjects),
                transitions=transitions(base['correct'],learned['correct'])))
    # Training artifacts identify exactly which outputs supplied fitting episodes.
    train_sources={}
    for condition in ([] if a.validation_only else ['clean','upper10','lower10']):
        for name in ORDER:
            file=out/condition/f'scores_{name}.npz';train_sources[str(file.relative_to(out))]=hashlib.sha256(file.read_bytes()).hexdigest()
    from avaliar_candidato_congelado import WEIGHTS,digest
    for _,(folder,expected) in WEIGHTS.items():assert digest(ROOT/'outputs'/folder/'melhor_modelo.pt')==expected
    train=manifest['train'];eligible_train={key(r) for r in train if r['session']==1}&{key(r) for r in train if r['session']==2}
    train=[r for r in train if key(r) in eligible_train];gi=np.array([i for i,r in enumerate(train) if r['session']==1])
    cache=out.parent.parent/'cache_fusao_regularizada_treino_2026-10-21'
    for condition in ([] if a.validation_only else ['upper10','lower10']):
        for name in ['rgb','native','polar','red']:
            clean=np.load(cache/'clean'/f'{name}.npy',mmap_mode='r');altered=np.load(cache/condition/f'{name}.npy',mmap_mode='r')
            for start in range(0,len(gi),64):np.testing.assert_array_equal(clean[gi[start:start+64]],altered[gi[start:start+64]])
            clean._mmap.close();altered._mmap.close()
        with np.load(cache/'clean'/'valid.npz') as clean,np.load(cache/condition/'valid.npz') as altered:
            for name in ['rgb','polar']:np.testing.assert_array_equal(clean[name][gi],altered[name][gi])
    audit=dict(status='regularized_fusion_reload_verified',score_max_abs_difference=0.,records=records,source_validation_sha256=sources,source_training_sha256=train_sources,
        frozen_encoder_hashes_unchanged=True,train_enrollment_inputs_and_validity_unchanged=None if a.validation_only else True,
        validation_only=a.validation_only,
        test_inference=False,frozen_candidate_replaced=False,uncertainty='5000 paired person-cluster bootstrap replicates, fixed gallery/threshold, pointwise descriptive intervals; no selection correction or independent confirmation',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/('VERIFICACAO_RESTAURADA.json' if a.validation_only else 'VERIFICACAO_RELOAD.json')).write_text(json.dumps(audit,indent=2),encoding='utf-8');print(json.dumps(dict(status=audit['status'],records=records),indent=2),flush=True)


if __name__=='__main__':main()

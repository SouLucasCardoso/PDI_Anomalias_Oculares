"""Reproduz ajuste regional, entradas de treino e decisoes do piloto."""
from pathlib import Path
from types import SimpleNamespace
import argparse,json
import numpy as np
from threadpoolctl import threadpool_limits
from piloto_destilacao_regional import ROOT,NAME,METHODS,sha,measure,threshold,compute_scores
from descritor_regional_aprendido import sectors,fit_ridge

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--cache-root',type=Path);a=p.parse_args();out=a.root/NAME
    protocol=json.loads((out/'protocolo.json').read_text());done=json.loads((out/'CONCLUIDO.json').read_text())
    assert sha(out/'source.py')==protocol['dependencies']['piloto_destilacao_regional.py']
    for n,h in protocol['dependencies'].items():assert sha(ROOT/n)==h
    assert sha(out/'model.npz')==done['model_sha256']
    maximum=0.
    for split in ['internal','monitor']:
        for method in METHODS:
            for tag,m in done['results'][split][method].items():
                with np.load(out/f'scores_{split}_{method}_{tag}.npz') as z:data={k:z[k] for k in ['scores','labels','valid','query_indices']};correct=z['correct'];accepted=z['accepted']
                actual,decisions=measure(data,done['thresholds'][method]);assert actual==m
                np.testing.assert_array_equal(correct,decisions['correct']);np.testing.assert_array_equal(accepted,decisions['accepted'])
                if split=='internal':assert tag=='clean' and threshold(data)==done['thresholds'][method]
    r=done['results']['monitor'];clean=all(r['fusion6']['clean'][k]>=r['global']['clean'][k] for k in ['rank1','tar']) and r['fusion6']['clean']['far']<=.01
    assert bool(clean)==done['clean_gate_passed']==done['occlusions_evaluated']
    gate=clean and all(r['fusion6'][tag]['far']<=.01 and all(r['fusion6'][tag][k]>r['global'][tag][k] for k in ['rank1','tar']) for tag in ['upper10','lower10'])
    assert bool(gate)==done['monitor_gate_passed'] and not any(done[k] for k in ['validation_inference','test_inference','candidate_replaced'])
    fit=set(protocol['fit_people']);internal=set(protocol['internal_people']);monitor=set(protocol['monitor_people']);assert len(fit)==151 and len(internal)==len(monitor)==16 and not fit&internal and not (fit|internal)&monitor
    if a.cache_root:
        for f,h in protocol['inputs'].items():assert sha(f)==h
        source=a.cache_root/'adaptador_polar_original_2026-10-23';cache=a.cache_root/'encoder_polar_espacial_2026-10-23';div=a.cache_root/'diversidade_oclusao_treino_2026-10-24'
        rows=[SimpleNamespace(**r) for r in json.loads((source/'rows.json').read_text())]
        with np.load(a.cache_root/'bloco_fmr_separado_2026-10-23'/'indices_ajuste.npz') as z:fi=z['fit'];ci=z['internal'];mi=z['monitor']
        assert all(rows[i].subject in fit for i in fi) and all(rows[i].subject in internal for i in ci) and all(rows[i].subject in monitor for i in mi)
        manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());assert not (fit|internal|monitor)&{r['subject'] for r in manifest['val']+manifest['test']}
        maps=np.load(cache/'cache_layer3.npy',mmap_mode='r');extra=np.load(div/'cache_diverso.npy',mmap_mode='r')
        with np.load(cache/'cache_indices.npz') as z:mapping=z['mapping'];valid=z['valid']
        with np.load(div/'cache_diverso_valid.npz') as z:ev=z['valid']
        with np.load(source/'cache_features.npz') as z:teacher=z['teacher'];base=z['base']
        x=np.empty((len(rows),3,8,256),np.float32)
        for start in range(0,len(rows),64):
            ii=np.arange(start,min(start+64,len(rows)))
            for j in range(3):x[ii,j]=sectors(maps[mapping[ii,j]])
        train=x[fi].copy();vv=valid[fi].copy();lookup={int(i):k for k,i in enumerate(fi)}
        for j,item in enumerate(protocol['augmentation_plan']):
            i=item['index'];assert rows[i].subject in fit and rows[i].session==2;k=lookup[i];view=1 if item['kind']=='upper' else 2
            train[k,view]=sectors(extra[j:j+1])[0];vv[k,view]=ev[j]
        assert int((~vv).sum())==done['fit_invalid_views']==10
        with np.load(out/'fit_evidence.npz') as z:
            for name,array in [('sectors',train),('teacher',teacher[fi]),('valid',vv),('fit_indices',fi)]:np.testing.assert_array_equal(array,z[name])
        with threadpool_limits(limits=4):
            refit=fit_ridge(train.reshape(-1,8,256),np.repeat(teacher[fi],3,axis=0),(vv*np.array([4.,1.,1.])).reshape(-1))
            with np.load(out/'model.npz') as z:
                for k,value in refit.items():np.testing.assert_array_equal(value,z[k])
            for split,ii in [('internal',ci),('monitor',mi)]:
                for tag,j in [('clean',0),('upper10',1),('lower10',2)]:
                    if tag not in done['results'][split]['global']:continue
                    data=compute_scores(x,valid,rows,ii,base,refit,j)
                    for method in METHODS:
                        with np.load(out/f'scores_{split}_{method}_{tag}.npz') as z:
                            for k,v in data[method].items():np.testing.assert_array_equal(v,z[k])
    record=dict(status='regional_distillation_audited',metrics_and_decisions_exact=True,clean_only_calibration=True,primary_prespecified=True,fit_reproduction_exact=bool(a.cache_root),score_reproduction_exact=bool(a.cache_root),clean_gate_passed=bool(clean),monitor_gate_passed=bool(gate),no_validation_or_test=True)
    (out/('AUDITORIA_REPRODUCAO.json' if a.cache_root else 'VERIFICACAO_RECUPERACAO.json')).write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record))

if __name__=='__main__':main()

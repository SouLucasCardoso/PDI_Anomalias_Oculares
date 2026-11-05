"""Recalcula todos os escores SAM3.1 a partir das mascaras preservadas."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from avaliar_sam31_diverso import metrics
from treinar_segmentacao_diversa import IGNORE
from treinar_segmentacao_ubipr import sha256


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args()
    folder=a.directory;protocol=json.loads((folder/'protocolo.json').read_text(encoding='utf-8'))
    result=json.loads((folder/'CONCLUIDO.json').read_text(encoding='utf-8'))
    records=list(csv.DictReader((folder/'metricas_por_imagem.csv').open(encoding='utf-8')))
    masks=np.load(folder/'mascaras.npz',allow_pickle=False)
    subjects=[r['subject'] for r in protocol['samples']]
    assert len(subjects)==len(set(subjects))==result['people']
    assert len(records)==len(subjects)*len(protocol['modes'])*2
    assert sha256(folder/'source.py')==protocol['script_sha256']
    seen=set()
    for row in records:
        person=subjects.index(int(row['subject']));mode=row['mode'];method=row['method']
        key=(person,mode,method);assert key not in seen;seen.add(key)
        target=masks[f'{person}_{mode}_target']
        pred=np.unpackbits(masks[f'{person}_{mode}_{method}'],count=target.size).reshape(target.shape).astype(bool)
        recalculated=metrics(pred,target==1,target!=IGNORE)
        for name in ('dice','iou','prediction_pixels','reference_pixels'):
            assert abs(float(row[name])-float(recalculated[name]))<1e-10,(key,name)
    differences={};rng=np.random.default_rng(protocol['seed'])
    for mode in protocol['modes']:
        per_method={m:np.array([float(next(r['dice'] for r in records if int(r['subject'])==s and r['mode']==mode and r['method']==m)) for s in subjects]) for m in ('unet','sam31_strict')}
        for m in per_method:
            assert abs(per_method[m].mean()-result['summary'][mode][m]['dice'])<1e-12
        delta=per_method['sam31_strict']-per_method['unet'];draws=rng.integers(0,len(delta),(5000,len(delta)))
        differences[mode]={'sam_minus_unet':float(delta.mean()),'paired_person_bootstrap95':np.quantile(delta[draws].mean(1),[.025,.975]).tolist()}
    for row in result['clinical_qualitative_only']:
        name=row['image'];shape=masks[name+'_shape'];count=int(np.prod(shape))
        for method,key in [('sam','sam_pixels'),('unet','unet_pixels')]:
            assert int(np.unpackbits(masks[name+'_'+method],count=count).sum())==row[key]
    audit={'status':'passed','paired_records_recalculated':len(records),'unique_people':len(subjects),
           'clinical_pixel_counts_recalculated':len(result['clinical_qualitative_only']),
           'paired_differences':differences,'bootstrap_warning':'Exploratory reused validation; resampling16people is not new independent evidence',
           'files_sha256':{name:sha256(folder/name) for name in ('protocolo.json','source.py','metricas_por_imagem.csv','mascaras.npz','CONCLUIDO.json')}}
    (folder/'AUDITORIA.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps(audit,indent=2))


if __name__=='__main__':main()

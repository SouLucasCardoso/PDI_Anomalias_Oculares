"""Rodada exploratoria: encoder treinado e oclusoes na referencia UBIPr."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import json
import time
import numpy as np
from PIL import Image
import torch

ROOT=Path(__file__).resolve().parent
CONDITIONS=[('oclusao_superior',i) for i in range(10,100,10)]+[('oclusao_inferior',i) for i in range(10,100,10)]

def main():
    torch.set_num_threads(4)
    from treinar_identidade_iris import IdentityEncoder
    from avaliar_dinov3_ubipr import masked_crop
    from avaliar_robustez_reconhecimento import load_splits,identity,make_gallery,perturb,metrics,paired_ci,write_csv
    from treinar_segmentacao_ubipr import decode_mask
    from relatar_area_preservada import minimum_fraction
    trained=ROOT/'outputs/identidade_arcface_ubipr_2026-10-20'
    if not (trained/'CONCLUIDO.json').exists(): raise RuntimeError('Final encoder checkpoint required')
    completion=json.loads((trained/'CONCLUIDO.json').read_text(encoding='utf-8'))
    checkpoint=trained/'melhor_modelo.pt'; digest=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    if digest!=completion['checkpoint_sha256']: raise ValueError('Checkpoint changed')
    state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    manifest=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    splits=load_splits(json.loads(manifest.read_text(encoding='utf-8')))
    out=ROOT/'outputs/area_encoder_ubipr_2026-10-20'; out.mkdir(parents=True,exist_ok=True)
    threshold=float(state['validation']['threshold'])
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),
        'round':'Exploratory follow-up; UBIPr test used in prior DINO analysis, not a newly untouched test',
        'selection':'Encoder checkpoint and threshold fixed from UBIPr validation before this evaluation',
        'checkpoint_sha256':digest,'best_epoch':completion['best_epoch'],'threshold':threshold,
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependencies_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['treinar_identidade_iris.py',
             'avaliar_robustez_reconhecimento.py','avaliar_dinov3_ubipr.py','treinar_segmentacao_ubipr.py','relatar_area_preservada.py']},
        'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
        'conditions':[['original',0]]+CONDITIONS,'identity':'subject+side',
        'gallery':'Original session1 centroid; fixed','queries':'session2',
        'preprocessing':'Reference iris mask fixed, black exterior, bbox25%, bilinear128x128, ImageNet normalization',
        'occlusion':'Exact annotated iris fraction replaced with gray128; outside iris unchanged',
        'failures':'Retain all queries; empty references reject; area undefined for empty masks',
        'minimum_rule':'Rank1>=90% and TAR>=90% at original validation-calibrated threshold, all larger fractions must pass; otherwise not determined',
        'uncertainty':'5000 paired person-cluster bootstrap replicates, fixed gallery and threshold',
        'clinical_labels':False,'counts':{k:{'images':len(rs),'people':len({r.subject for r in rs}),
             'eyes':len({identity(r) for r in rs}),'queries':sum(r.session==2 for r in rs)} for k,rs in splits.items()}}
    registration=out/'protocolo.json'
    if registration.exists(): raise ValueError('Preserve previous experiment; choose new output folder')
    registration.write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model=IdentityEncoder().to(device); model.load_state_dict(state['model']); model.eval(); del state
    mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None]
    std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None]

    def extract(rows,kind,level,name):
        arrays=[]; valid=[]; coverage=[]; pending=[]
        def flush():
            if not pending: return
            tensor=torch.from_numpy(np.stack(pending).transpose(0,3,1,2).copy()).to(device).float()/255
            with torch.inference_mode(),torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'):
                vector=model((tensor-mean)/std)
            arrays.append(torch.nn.functional.normalize(vector.float(),dim=1).cpu().numpy()); pending.clear()
        for row in rows:
            with Image.open(row.image) as im: image=im.convert('RGB')
            with Image.open(row.mask) as im: mask=decode_mask(im)==1
            altered,metadata=perturb(image,mask,kind,level)
            pending.append(np.asarray(masked_crop(altered,mask).resize((128,128),Image.Resampling.BILINEAR)))
            valid.append(bool(mask.any())); coverage.append(metadata['affected_fraction'])
            if len(pending)==128: flush()
        flush(); vectors=np.concatenate(arrays)
        if not np.isfinite(vectors).all(): raise FloatingPointError('Nonfinite embeddings')
        result={'features':vectors,'valid':np.array(valid),'coverage':np.array(coverage)}
        np.savez_compressed(out/f'embeddings_{name}.npz',**result)
        return result

    rows=splits['test']; original=extract(rows,'original',0,'test_original')
    gallery,ids,failed=make_gallery(original['features'],original['valid'],rows)
    qi=[i for i,r in enumerate(rows) if r.session==2]; queries=[rows[i] for i in qi]
    labels=np.array([ids.index(identity(r)) for r in queries]); subjects=np.array([r.subject for r in queries])
    def compare(features,valid):
        scores=(features@gallery.T).astype(np.float64)
        for eye in failed: scores[:,ids.index(eye)]=-2.
        measured,correct,accepted=metrics(scores,labels,threshold,valid)
        return measured,correct,accepted,scores
    base,bc,ba,scores=compare(original['features'][qi],original['valid'][qi])
    np.savez_compressed(out/'scores_original.npz',scores=scores,labels=labels,valid=original['valid'][qi],correct=bc,accepted=ba)
    summaries=[{'condition':'original','level':0,**base,'loss_rank1_pp':0.,'ci_low_pp':0.,'ci_high_pp':0.,
                'loss_tar_pp':0.,'tar_ci_low_pp':0.,'tar_ci_high_pp':0.,'coverage_mean_defined':0.}]
    write_csv(out/'resumo.csv',summaries); start=time.monotonic()
    print('Original '+json.dumps(base),flush=True)
    for kind,level in CONDITIONS:
        altered=extract(queries,kind,level,f'test_{kind}_{level}')
        measured,correct,accepted,scores=compare(altered['features'],altered['valid'])
        ci=paired_ci(bc,correct,subjects); tci=paired_ci(ba,accepted,subjects)
        summaries.append({'condition':kind,'level':level,**measured,
            'loss_rank1_pp':100*(base['rank1']-measured['rank1']),'ci_low_pp':ci[0],'ci_high_pp':ci[1],
            'loss_tar_pp':100*(base['tar']-measured['tar']),'tar_ci_low_pp':tci[0],'tar_ci_high_pp':tci[1],
            'coverage_mean_defined':float(altered['coverage'][altered['valid']].mean())})
        np.savez_compressed(out/f'scores_{kind}_{level}.npz',scores=scores,labels=labels,valid=altered['valid'],correct=correct,accepted=accepted)
        write_csv(out/'resumo.csv',summaries)
        print(f'{kind} {level}: '+json.dumps(measured)+f' | elapsed={time.monotonic()-start:.0f}s',flush=True)
    result={'status':'exploratory_follow_up_completed','conditions':len(summaries),'baseline':base,
        'minimum_reference_area_percent':{kind:minimum_fraction(base,[r for r in summaries if r['condition']==kind])
                                         for kind in ('oclusao_superior','oclusao_inferior')},
        'note':'Same operational criterion; tests previously examined under DINO, no fresh clinical or disease-causality claim'}
    (out/'area_minima.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (out/'CONCLUIDO.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__': main()

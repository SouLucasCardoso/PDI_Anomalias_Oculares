"""Teste clinico reservado, com reconhecedor e limiar congelados na validacao."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import torch
from matcher_hdbif_fft import prepare,distances,best_score

ROOT=Path(__file__).resolve().parent

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    torch.set_num_threads(2)
    out=ROOT/'outputs/hdbif_slpvld_teste_congelado_2026-10-20'
    out.mkdir(parents=True,exist_ok=True)
    source=ROOT/'data/modelos/cvrl_hdbif'; sys.path.insert(0,str(source))
    from modules.irisRecognition import irisRecognition
    from avaliar_robustez_reconhecimento import metrics
    validation=ROOT/'outputs/hdbif_slpvld_validacao_completa_2026-10-20/resultado.json'
    selection=ROOT/'outputs/hdbif_slpvld_ablacao_validacao_2026-10-20/resultado.json'
    selected=json.loads(selection.read_text(encoding='utf-8'))
    if selected['selected_on_validation']!='default_raw': raise ValueError('This frozen protocol requires default_raw')
    threshold=float(json.loads(validation.read_text(encoding='utf-8'))['threshold'])
    pilot=json.loads((ROOT/'outputs/hdbif_slpvld_validacao_piloto_2026-10-20/protocolo.json').read_text(encoding='utf-8'))
    manifest=ROOT/'outputs/biometria_clinica_triagem_2026-10-20/manifesto.json'
    rows=json.loads(manifest.read_text(encoding='utf-8'))['test']
    rows.sort(key=lambda r:(r['subject'],r['side'],r['role'],r['capture_date'],r['image']))
    config=pilot['config']
    weights=json.loads((source/'pesos.json').read_text(encoding='utf-8'))
    for item in weights['files']:
        if digest(source/item['path'])!=item['sha256']: raise ValueError('Model weight changed')
    for item in pilot['sources']['files']:
        if digest(source/item['path'])!=item['sha256']: raise ValueError('Upstream source changed')
    protocol={'task':'Held-out clinical test, original captures; no minimum-area estimate',
        'manifest_sha256':digest(manifest),'script_sha256':digest(Path(__file__)),
        'config':config,'weights':weights,'source_revision':pilot['sources']['revision'],
        'gallery':'First image on earliest date per eye; queries all strictly later dates',
        'identity':'anonymous subject + side; metadata ambiguities excluded upstream',
        'matcher':'FFT masked Hamming, +/-16 columns, no score normalization; equivalence verified against official matcher on all validation pairs',
        'matcher_sha256':digest(ROOT/'matcher_hdbif_fft.py'),
        'selected_variant':'default_raw','selection_result_sha256':digest(selection),
        'validation_result_sha256':digest(validation),'frozen_threshold':threshold,
        'failure_handling':'Retain all eye identities and queries; invalid enrollment or comparison score -2; failed queries reject',
        'quality_checks':'Finite circles, positive pupil radius smaller than iris radius; nonempty normalized mask',
        'calibration':'Frozen validation threshold, no recalibration or hyperparameter selection on test',
        'mask':'CVRL predicted mask, not clinical ground truth',
        'counts':{'images':len(rows),'people':len({r['subject'] for r in rows}),
                  'eyes':len({(r['subject'],r['side']) for r in rows})}}
    signature=hashlib.sha256(json.dumps(protocol,sort_keys=True).encode()).hexdigest()
    registration=out/'protocolo.json'
    if registration.exists():
        old=json.loads(registration.read_text(encoding='utf-8'))
        if old['signature']!=signature: raise ValueError('Protocol changed; use new output folder')
    else:
        registration.write_text(json.dumps(dict(protocol,signature=signature,
            registered_utc=datetime.now(timezone.utc).isoformat()),indent=2),encoding='utf-8')
    print(json.dumps(protocol['counts']),flush=True)
    model=irisRecognition(config)
    cache=out/'templates'; cache.mkdir(exist_ok=True)
    qa=ROOT/'data/qa_biometria/slpvld_teste_congelado'; qa.mkdir(parents=True,exist_ok=True)
    templates=[]; audits=[]; started=time.monotonic()
    for index,row in enumerate(rows):
        image_path=Path(row['image'])
        if digest(image_path)!=row['sha256']: raise ValueError('Dataset image changed')
        target=cache/(image_path.stem+'.npz'); record=None
        if target.exists():
            with np.load(target,allow_pickle=False) as saved:
                record=json.loads(str(saved['audit']))
                template=([saved['code']],saved['mask']) if record['valid'] else None
        else:
            with Image.open(image_path) as im: image=model.fix_image(im.convert('L'))
            pupil,iris=model.circApprox(image)
            valid=bool(np.isfinite(pupil).all() and np.isfinite(iris).all() and 0<pupil[2]<iris[2])
            reason=None; polar_mask=np.zeros((64,512),dtype=np.uint8); code=np.zeros((5,48,512),dtype=bool)
            if valid:
                mask=model.segment(image)
                polar,polar_mask=model.cartToPol_torch(image,mask,pupil,iris)
                valid=bool(np.any(polar_mask))
                if valid: code=model.extractCode(polar)[0]
                else: reason='empty_normalized_mask'
            else: reason='invalid_circle_parameters'
            template=([code],polar_mask) if valid else None
            record={'image':image_path.name,'subject':row['subject'],'side':row['side'],
                'role':row['role'],'valid':valid,'failure_reason':reason,
                'valid_polar_fraction':float((polar_mask>0).mean()),
                'pupil_circle':pupil.tolist(),'iris_circle':iris.tolist()}
            temporary=target.with_suffix('.part.npz')
            np.savez_compressed(temporary,code=code,mask=polar_mask,audit=json.dumps(record)); temporary.replace(target)
            # All samples saved for audit, without post-score exclusions.
            visual=image.convert('RGB'); draw=ImageDraw.Draw(visual)
            if np.isfinite(pupil).all() and np.isfinite(iris).all():
                for circle,color in [(pupil,'red'),(iris,'lime')]:
                    x,y,r=circle
                    if r>0: draw.ellipse((x-r,y-r,x+r,y+r),outline=color,width=3)
            visual.thumbnail((480,360)); visual.save(qa/(image_path.stem+'.jpg'),quality=85)
        templates.append(template); audits.append(record)
        if (index+1)%10==0:
            (out/'auditoria_parcial.json').write_text(json.dumps(audits,indent=2),encoding='utf-8')
            print(f'Templates {index+1}/{len(rows)}; {time.monotonic()-started:.0f}s',flush=True)
    ids=sorted({(r['subject'],r['side']) for r in rows})
    enrollments=[next(i for i,r in enumerate(rows) if (r['subject'],r['side'])==eye and r['role']=='gallery') for eye in ids]
    queries=[i for i,r in enumerate(rows) if r['role']=='query']
    labels=np.array([ids.index((rows[i]['subject'],rows[i]['side'])) for i in queries])
    scores=np.full((len(queries),len(ids)),-2.,dtype=np.float64)
    progress=out/'scores_parciais.npz'; done=0
    fft_templates=[prepare(t[0][0],t[1]) if t is not None else None for t in templates]
    if progress.exists():
        with np.load(progress) as saved: scores=saved['scores']; done=int(saved['done'])
    for qi in range(done,len(queries)):
        query=fft_templates[queries[qi]]
        for ei,index in enumerate(enrollments):
            gallery=fft_templates[index]
            if query is None or gallery is None: continue
            raw,_,_=distances(query,gallery)
            scores[qi,ei]=best_score(raw,16)
        temporary=progress.with_suffix('.part.npz')
        np.savez_compressed(temporary,scores=scores,done=qi+1); temporary.replace(progress)
        if (qi+1)%10==0: print(f'Comparacoes {qi+1}/{len(queries)}',flush=True)
    valid=np.array([templates[i] is not None for i in queries]) & (scores>=0).any(axis=1)
    impostor=np.ones_like(scores,dtype=bool); impostor[np.arange(len(labels)),labels]=False
    usable=impostor & (scores>=0)
    result,correct,accepted=metrics(scores,labels,threshold,valid)
    groups={}
    for label,name in [(0,'source_normal_eye'),(1,'source_other_conditions')]:
        selected=np.array([rows[i]['label_binary']==label for i in queries])
        groups[name]={'queries':int(selected.sum()),'rank1':float(correct[selected].mean()) if selected.any() else None,
                      'tar':float(accepted[selected].mean()) if selected.any() else None}
    report={'status':'held_out_test_completed_frozen_protocol','held_out_test_result':True,'minimum_area_estimated':False,
        'metrics':result,'threshold':threshold,'groups_observational':groups,
        'failed_images':sum(not r['valid'] for r in audits),
        'failed_enrollments':sum(templates[i] is None for i in enrollments),
        'unavailable_pair_comparisons':int((scores<0).sum()),
        'test_impostor_pairs_with_available_comparison':int(usable.sum()),
        'note':'Frozen validation-selected recognizer and threshold; no post-test exclusions or tuning. No clinical causal claim or minimum-area estimate.'}
    np.savez_compressed(out/'scores.npz',scores=scores,labels=labels,valid=valid,correct=correct,accepted=accepted)
    (out/'auditoria.json').write_text(json.dumps(audits,indent=2),encoding='utf-8')
    (out/'resultado.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (out/'CONCLUIDO.json').write_text(json.dumps({'images':len(rows),'queries':len(queries),'signature':signature},indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__': main()

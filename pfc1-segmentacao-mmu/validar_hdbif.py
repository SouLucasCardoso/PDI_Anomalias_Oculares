"""Piloto HDBIF apenas na validacao UBIPr, em CPU e sem selecionar hiperparametros."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
from PIL import Image
import torch

ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',choices=('ubipr','slpvld'),default='ubipr')
    args=parser.parse_args()
    torch.set_num_threads(2)
    source=ROOT/'data/modelos/cvrl_hdbif'
    sys.path.insert(0,str(source))
    from modules.irisRecognition import irisRecognition
    from avaliar_robustez_reconhecimento import load_splits, identity
    from treinar_segmentacao_ubipr import decode_mask
    out=ROOT/('outputs/hdbif_validacao_piloto_2026-10-20' if args.dataset=='ubipr' else 'outputs/hdbif_slpvld_validacao_piloto_2026-10-20')
    out.mkdir(parents=True,exist_ok=True)
    config={'cuda':False,'polar_height':64,'polar_width':512,
        'recog_filter_size':'17','recog_num_filters':'5','recog_max_shift':16,
        'recog_bsif_dir':str(source/'filters_pt/finetuned_bsif_eyetracker_data')+'/',
        'threshold_frac_avg_bits':0,'score_norm':False,
        'mask_model_path':str(source/'models/nestedsharedatrousresunet-006-0.028214-maskIoU-0.938446.pth'),
        'circle_model_path':str(source/'models/resnet18-027-0.008222-maskIoU-0.967159.pth')}
    provenance=json.loads((source/'fontes.json').read_text(encoding='utf-8'))
    weights=json.loads((source/'pesos.json').read_text(encoding='utf-8'))
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),
        'purpose':'CPU compatibility and validation-only pilot, not final recognition estimates',
        'config':config,'sources':provenance,'weights':weights,
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dataset':args.dataset,
        'selection':'First four eligible validation eye IDs; UBIPr first sample per session, SLP earliest gallery and latest query; test untouched',
        'mask':'UBIPr reference iris; SLP predicted CVRL mask, not reference. CVRL pretrained circle regressor; grayscale ISO640x480',
        'matcher':'Official exhaustive matchCodes, +/-16 polar columns, no score normalization',
        'training_overlap':'Public pretrained sources may overlap populations; independence not established',
        'checkpoint_difference':'Drive circle027 overrides absent source cfg circle1543'}
    if (out/'protocolo.json').exists(): raise ValueError('Pasta de piloto ja existe; preservar e usar nova versao')
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    model=irisRecognition(config)
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text(encoding='utf-8'))
    rows=load_splits(manifest)['val']; ids=sorted({identity(r) for r in rows})[:4]
    if args.dataset=='slpvld':
        clinical=json.loads((ROOT/'outputs/biometria_clinica_triagem_2026-10-20/manifesto.json').read_text(encoding='utf-8'))['val']
        ids=sorted({r['subject']+'_'+r['side'] for r in clinical})[:4]
        rows=[]
        for eye in ids:
            candidates=[r for r in clinical if r['subject']+'_'+r['side']==eye]
            gallery=next(r for r in candidates if r['role']=='gallery')
            query=max((r for r in candidates if r['role']=='query'),key=lambda r:r['capture_date'])
            rows.extend(SimpleNamespace(subject=r['subject'],side=r['side'],session=session,image=r['image'],mask=None) for session,r in [(1,gallery),(2,query)])
    templates={}; records=[]
    for eye in ids:
        for session in (1,2):
            row=next(r for r in rows if identity(r)==eye and r.session==session)
            with Image.open(row.image) as im: image=model.fix_image(im.convert('L'))
            if row.mask is None:
                mask=Image.fromarray(model.segment(image))
            else:
                with Image.open(row.mask) as im:
                    mask=Image.fromarray((decode_mask(im)==1).astype(np.uint8)*255)
                    mask=mask.resize(image.size,Image.Resampling.NEAREST)
            pupil,iris=model.circApprox(image)
            if not (np.isfinite(pupil).all() and np.isfinite(iris).all() and 0<pupil[2]<iris[2]):
                raise ValueError(f'Invalid circles {eye} session{session}')
            polar,valid=model.cartToPol_torch(image,mask,pupil,iris)
            if not np.any(valid): raise ValueError('Empty normalized reference mask')
            templates[eye,session]=(model.extractCode(polar),valid)
            records.append({'eye':eye,'session':session,'valid_polar_fraction':float((valid>0).mean()),
                            'pupil_circle':pupil.tolist(),'iris_circle':iris.tolist()})
            print(f'Normalizacao concluida: {eye} sessao{session}',flush=True)
    scores=[]
    for query in ids:
        line=[]
        for gallery in ids:
            cq,mq=templates[query,2]; cg,mg=templates[gallery,1]
            distance,shift=model.matchCodes(cq,cg,mq,mg)
            if not np.isfinite(distance) or distance<0: raise ValueError('Matching failed: no overlap')
            line.append(float(distance))
        scores.append(line)
    scores=np.asarray(scores); correct=scores.argmin(1)==np.arange(len(ids))
    result={'status':'validation_pilot_completed','scientific_final_result':False,'eyes':len(ids),
        'queries':len(ids),'rank1':float(correct.mean()),'distance_matrix':scores.tolist(),
        'normalization':records,'note':'No minimum-area claim; no calibration or hyperparameter search on these four queries.'}
    (out/'resultado.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__': main()

"""Controle de fase sobre faixas polares automaticas; apenas validacao."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,time
import numpy as np
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs/loggabor_polar_val_2026-10-20'

def main():
    from avaliar_robustez_reconhecimento import load_splits,identity,metrics,operating_threshold
    from matcher_hdbif_fft import prepare
    from comparador_hdbif_lote import gallery_batch,aggregate
    from loggabor_iris import encode,normalized_scores
    cache=ROOT/'data/cache_encoder_polar_2026-10-20'
    if not (cache/'val_valid.npy').exists():raise ValueError('Wait for complete polar validation preparation')
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Development validation-only phase baseline, no training or test/occlusion inference; not official OSIRIS',
        'filter':'One-sided angular Log-Gabor wavelength18pixels sigmaOnf0.5, two phase bits, row mean removed, low amplitude<1e-6 invalid',
        'mask':'Conservative reconstruction from neutral sentinel: grayscale!=127; genuine127pixels also rejected; erode3radial x5angular with angular wrap',
        'matching':'Masked Hamming FFT +/-16columns, minimum pair overlap10% of full bit canvas; normalized D=.5-(.5-raw)*sqrt(overlap/(.5*fullbits)); first/max/top3 enrollment',
        'calibration':'Separate validation empirical FMR<=1%, all eyes/queries retained; not independent confirmation',
        'critical_distinction':'Overlap10% is code-quality gate, NOT minimum anatomical iris area',
        'cache_sha256':{n:hashlib.sha256((cache/n).read_bytes()).hexdigest() for n in ['val_polar.npy','val_valid.npy']},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'dependencies_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['loggabor_iris.py','matcher_hdbif_fft.py','comparador_hdbif_lote.py']}}
    OUT.mkdir(exist_ok=True)
    if (OUT/'protocolo.json').exists():raise ValueError('Preserve previous output')
    (OUT/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(OUT/'source.py').write_bytes(Path(__file__).read_bytes())
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val']
    images=np.load(cache/'val_polar.npy',mmap_mode='r');available=np.load(cache/'val_valid.npy');ids=sorted({identity(r) for r in rows})
    gi=sorted([i for i,r in enumerate(rows) if r.session==1],key=lambda i:(identity(rows[i]),Path(rows[i].image).name));qi=[i for i,r in enumerate(rows) if r.session==2]
    groups=[[j for j,i in enumerate(gi) if identity(rows[i])==eye] for eye in ids];labels=np.array([ids.index(identity(rows[i])) for i in qi])
    templates=[]
    for i,image in enumerate(images):
        gray=image[:,:,0];code,mask=encode(gray,gray!=127)
        templates.append(prepare(code,mask) if available[i] and (mask>0).any() else None)
    blocks=[]
    positions=[j for j,i in enumerate(gi) if templates[i] is not None]
    for start in range(0,len(positions),16):
        part=positions[start:start+16];blocks.append((part,gallery_batch([templates[gi[p]] for p in part])))
    raw=np.full((len(qi),len(gi)),-2.,np.float64);started=time.monotonic()
    for index,i in enumerate(qi):
        if templates[i] is not None:
            for positions,batch in blocks:raw[index,positions]=normalized_scores(templates[i],batch)
        if (index+1)%50==0:print(f'LogGabor {index+1}/{len(qi)} {time.monotonic()-started:.0f}s',flush=True)
    results=[]
    for mode in ('first','max','top3'):
        scores=aggregate(raw,groups,mode);valid=np.array([templates[i] is not None for i in qi])&(scores>-2).any(1)
        imp=np.ones_like(scores,dtype=bool);imp[np.arange(len(labels)),labels]=False;usable=imp&valid[:,None]&(scores>-2)
        threshold=operating_threshold(scores[usable]) if usable.any() else 2.
        measured,correct,accepted=metrics(scores,labels,threshold,valid);measured.update(variant=mode,threshold=threshold,joint_success=float((correct&accepted).mean()));results.append(measured)
        np.savez_compressed(OUT/(mode+'.npz'),scores=scores,labels=labels,valid=valid,correct=correct,accepted=accepted);print(json.dumps(measured),flush=True)
    (OUT/'CONCLUIDO.json').write_text(json.dumps({'status':'development_phase_baseline_completed','results':results,'test_inference':False},indent=2),encoding='utf-8')

if __name__=='__main__':main()

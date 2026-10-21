"""Descritores intermediarios alinhados: controle espacial, sem novo treino."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np
import torch
from torch import nn
ROOT=Path(__file__).resolve().parent

def spatial_scores(query,gallery,max_shift):
    """B,C,H,W normalizados por local; deslocamento circular so no eixo angular."""
    candidates=[]
    for shift in range(-max_shift,max_shift+1):
        candidates.append(torch.einsum('bchw,gchw->bg',torch.roll(query,shift,dims=-1),gallery)/(query.shape[-2]*query.shape[-1]))
    return torch.stack(candidates).max(0).values

def main():
    from treinar_identidade_iris import IdentityEncoder
    from avaliar_robustez_reconhecimento import load_splits,identity,metrics,operating_threshold
    trained=ROOT/'outputs/encoder_polar_2026-10-20'
    assert (trained/'CONCLUIDO.json').exists(),'Wait for completed checkpoint selection'
    checkpoint=trained/'melhor_modelo.pt';out=ROOT/'outputs/espacial_polar_val_2026-10-20';out.mkdir(exist_ok=True)
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Exploratory validation only after polar training; no test/occlusion inference',
        'representation':'Frozen trained polar ResNet18 through layer3; subtract response to constant127 canvas; L2-normalize channels per spatial location',
        'gallery':'Mean local descriptors per eye across all valid session1 captures, renormalized per location; all session2 queries retained',
        'matching':'Mean spatial cosine, best angular shift0 or +/-2 feature columns; no radial shift',
        'calibration':'Separate validation empirical FMR<=1%; repeated development data, not independent confirmation',
        'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if (out/'protocolo.json').exists():raise ValueError('Preserve existing output')
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val']
    cache=ROOT/'data/cache_encoder_polar_2026-10-20';images=np.load(cache/'val_polar.npy',mmap_mode='r');valid=np.load(cache/'val_valid.npy')
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    encoder=IdentityEncoder();encoder.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
    extractor=nn.Sequential(*list(encoder.backbone.children())[:7]).to(device).eval();del encoder
    mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None];std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None]
    with torch.inference_mode():background=extractor((torch.full((1,3,64,512),127/255,device=device)-mean)/std)
    features=[]
    for start in range(0,len(images),32):
        x=torch.from_numpy(np.asarray(images[start:start+32]).transpose(0,3,1,2).copy()).to(device).float()/255
        with torch.inference_mode():f=nn.functional.normalize(extractor((x-mean)/std)-background,dim=1)
        features.append(f.cpu())
    features=torch.cat(features);ids=sorted({identity(r) for r in rows});qi=[i for i,r in enumerate(rows) if r.session==2];labels=np.array([ids.index(identity(rows[i])) for i in qi])
    prototypes=[];failed=[]
    for j,eye in enumerate(ids):
        gi=[i for i,r in enumerate(rows) if r.session==1 and identity(r)==eye and valid[i]]
        if gi:prototypes.append(nn.functional.normalize(features[gi].mean(0),dim=0))
        else:prototypes.append(torch.zeros_like(features[0]));failed.append(j)
    gallery=torch.stack(prototypes).to(device);results=[]
    for shift in (0,2):
        scores=[]
        for start in range(0,len(qi),32):
            with torch.inference_mode():value=spatial_scores(features[qi[start:start+32]].to(device),gallery,shift)
            scores.append(value.cpu().numpy())
        scores=np.concatenate(scores).astype(np.float64);scores[:,failed]=-2;qvalid=valid[qi]&(scores>-2).any(1)
        imp=np.ones_like(scores,dtype=bool);imp[np.arange(len(labels)),labels]=False;usable=imp&qvalid[:,None]&(scores>-2)
        threshold=operating_threshold(scores[usable]) if usable.any() else 2.
        measured,correct,accepted=metrics(scores,labels,threshold,qvalid);measured.update(angular_shift=shift,threshold=threshold,joint_success=float((correct&accepted).mean()));results.append(measured)
        np.savez_compressed(out/f'scores_shift{shift}.npz',scores=scores,labels=labels,valid=qvalid,correct=correct,accepted=accepted);print(json.dumps(measured),flush=True)
    (out/'CONCLUIDO.json').write_text(json.dumps({'status':'spatial_development_validation_completed','results':results,'test_inference':False},indent=2),encoding='utf-8')

if __name__=='__main__':main()

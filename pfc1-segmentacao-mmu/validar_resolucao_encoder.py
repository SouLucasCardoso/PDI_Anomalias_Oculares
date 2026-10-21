"""Controle pareado 128/256 do encoder congelado, galeria igual ao HDBIF val."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np
from PIL import Image
import torch
ROOT=Path(__file__).resolve().parent

def main():
    from treinar_identidade_iris import IdentityEncoder
    from treinar_segmentacao_ubipr import decode_mask
    from avaliar_dinov3_ubipr import masked_crop
    from avaliar_robustez_reconhecimento import load_splits,identity,metrics,operating_threshold
    torch.set_num_threads(4)
    out=ROOT/'outputs/melhoria_resolucao_encoder_val_2026-10-20'; out.mkdir(exist_ok=True)
    checkpoint=ROOT/'outputs/identidade_arcface_ubipr_2026-10-20/melhor_modelo.pt'
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val']
    ids=sorted({identity(r) for r in rows})
    gallery=[sorted([r for r in rows if identity(r)==eye and r.session==1],key=lambda r:Path(r.image).name)[0] for eye in ids]
    queries=[r for r in rows if r.session==2]; chosen=gallery+queries
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'purpose':'Development-only frozen encoder resolution ablation; no new test scores',
        'input_sizes':[128,256],'gallery':'First lexicographic session1 image per eye, same as HDBIF normalization experiment',
        'queries':len(queries),'eyes':len(ids),'people':len({r.subject for r in rows}),
        'preprocessing':'Reference iris mask, black outside, bbox margin25%, bilinear, ImageNet normalization',
        'calibration':'Each resolution on validation original; empirical impostor FMR<=1%; failures retained',
        'limitation':'Trained input128; inference256 is distribution shift and cannot restore absent texture; validation already used to select training checkpoint',
        'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if (out/'protocolo.json').exists(): raise ValueError('Preserve experiment; output already registered')
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model=IdentityEncoder().to(device).eval(); model.load_state_dict(state['model']); del state
    mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None]; std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None]
    crops=[]; valid=[]
    for r in chosen:
        image=Image.open(r.image).convert('RGB'); mask=decode_mask(Image.open(r.mask))==1
        crops.append(masked_crop(image,mask)); valid.append(bool(mask.any()))
    valid=np.array(valid); labels=np.array([ids.index(identity(r)) for r in queries]); results=[]
    for size in protocol['input_sizes']:
        vectors=[]
        for start in range(0,len(crops),64):
            images=np.stack([np.asarray(im.resize((size,size),Image.Resampling.BILINEAR)) for im in crops[start:start+64]])
            tensor=torch.from_numpy(images.transpose(0,3,1,2).copy()).to(device).float()/255
            with torch.inference_mode(),torch.autocast(device_type=device.type,dtype=torch.bfloat16,enabled=device.type=='cuda'):
                value=model((tensor-mean)/std)
            vectors.append(torch.nn.functional.normalize(value.float(),dim=1).cpu().numpy())
        vectors=np.concatenate(vectors); scores=(vectors[len(ids):]@vectors[:len(ids)].T).astype(np.float64)
        scores[:,~valid[:len(ids)]]=-2
        qvalid=valid[len(ids):]; imp=np.ones_like(scores,dtype=bool); imp[np.arange(len(labels)),labels]=False
        threshold=operating_threshold(scores[imp&qvalid[:,None]&(scores>-2)])
        measured,correct,accepted=metrics(scores,labels,threshold,qvalid)
        result={'input_size':size,'threshold':threshold,**measured,'joint_success':float((correct&accepted).mean()),'failed_gallery':int((~valid[:len(ids)]).sum())}
        results.append(result); np.savez_compressed(out/f'scores_{size}.npz',scores=scores,labels=labels,valid=qvalid,correct=correct,accepted=accepted)
        print(json.dumps(result),flush=True)
    (out/'CONCLUIDO.json').write_text(json.dumps({'status':'development_validation_completed','scientific_final_result':False,'results':results},indent=2),encoding='utf-8')

if __name__=='__main__': main()

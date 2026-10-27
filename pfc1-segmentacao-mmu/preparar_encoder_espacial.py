"""Cache FP32 ate layer3; S1 somente limpa, oclusoes nativas somente em S2."""
from pathlib import Path
import hashlib,json,time
import numpy as np
from PIL import Image
import torch
from torch.nn import functional as F
from encoder_polar_espacial import prefix_model,prefix_features
ROOT=Path(__file__).resolve().parent

def file_hash(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def prepare_cache(out,source,device):
    from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
    from treinar_identidade_iris import IdentityEncoder
    from avaliar_robustez_reconhecimento import perturb
    from textura_polar import prepare_texture
    protocol=json.loads((out/'protocolo.json').read_text());manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());rows=manifest['train'];n=len(rows);queries=np.array([i for i,r in enumerate(rows) if r['session']==2]);total=n+2*len(queries)
    assert n==7716 and len(queries)==2222 and total==12160
    with np.load(source/'cache_features.npz') as z:expected=z['base'];old_valid=z['valid'];teacher_valid=z['teacher_valid']
    encoder=IdentityEncoder().to(device).eval();encoder.load_state_dict(torch.load(ROOT/protocol['encoder_relative_path'],map_location='cpu',weights_only=True)['model']);prefix=prefix_model(encoder).to(device)
    unet=MulticlassUNet(8).to(device).eval();unet.load_state_dict(torch.load(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt',map_location='cpu',weights_only=True)['model'])
    cache=ROOT/'data/cache_encoder_polar_2026-10-20';images=np.load(cache/'train_polar.npy',mmap_mode='r');features=np.lib.format.open_memmap(out/'cache_layer3.npy',mode='w+',dtype=np.float32,shape=(total,256,4,32));mapping=np.repeat(np.arange(n)[:,None],3,axis=1);valid=np.repeat(teacher_valid[:,None],3,axis=1);start_time=time.monotonic();difference=0.
    for start in range(0,n,32):
        stop=min(start+32,n);values=prefix_features(prefix,images[start:stop],device);features[start:stop]=values
        with torch.inference_mode():
            x=encoder.backbone.layer4(torch.from_numpy(values).to(device));v=F.normalize(encoder.projection(F.adaptive_avg_pool2d(x,1).flatten(1)),dim=1).cpu().numpy()
        difference=max(difference,float(np.max(np.abs(v-expected[start:stop,0]))))
        if start%1280==0:print(json.dumps(dict(phase='cache_clean_prefix',photos=stop,total=n,seconds=time.monotonic()-start_time)),flush=True)
    assert difference<=1e-6
    for j,kind in [(1,'oclusao_superior'),(2,'oclusao_inferior')]:
        mapping[queries,j]=n+(j-1)*len(queries)+np.arange(len(queries))
        for start in range(0,len(queries),32):
            selected=queries[start:start+32];photos=[]
            for i in selected:
                r=rows[i]
                with Image.open(ROOT/'data/ubipr/single_eye'/Path(r['image']).name) as im:photo=im.convert('RGB')
                with Image.open(ROOT/'data/ubipr/single_eye'/Path(r['mask']).name) as im:reference=decode_mask(im)==1
                photos.append(perturb(photo,reference,kind,10)[0])
            x=torch.from_numpy(np.stack([np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for im in photos]).transpose(0,3,1,2).copy()).to(device)
            with torch.inference_mode():masks=unet(x).argmax(1).cpu().numpy()==1
            textures=[]
            for i,im,small in zip(selected,photos,masks):
                mask=np.asarray(Image.fromarray(small).resize(im.size,Image.Resampling.NEAREST),bool)
                try:texture=prepare_texture(np.asarray(im),mask)[0];valid[i,j]=True
                except ValueError:texture=np.full((64,512,3),127,np.uint8);valid[i,j]=False
                textures.append(texture)
            features[mapping[selected,j]]=prefix_features(prefix,np.stack(textures),device)
            if start%640==0:print(json.dumps(dict(phase=kind,queries=min(start+32,len(queries)),total=len(queries),seconds=time.monotonic()-start_time)),flush=True)
        np.testing.assert_array_equal(valid[queries,j],old_valid[queries,j])
    features.flush();del features;np.savez_compressed(out/'cache_indices.npz',mapping=mapping,valid=valid,queries=queries)
    final=dict(status='layer3_cache_completed',photos=n,native_query_photos=len(queries),feature_maps=total,dtype='float32',shape=[total,256,4,32],bytes=(out/'cache_layer3.npy').stat().st_size,sha256=file_hash(out/'cache_layer3.npy'),indices_sha256=file_hash(out/'cache_indices.npz'),maximum_clean_embedding_difference=difference,native_query_extraction_validity_matches_previous=True,clean_enrollment_only=True,seconds=time.monotonic()-start_time)
    (out/'CACHE_CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)

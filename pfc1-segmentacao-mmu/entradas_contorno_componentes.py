"""Entradas nativas e polares do candidato, com galeria reutilizável e fallback."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from contorno_componentes_iris import predict_mask
from treinar_segmentacao_ubipr import decode_mask
from avaliar_robustez_reconhecimento import perturb
from avaliar_dinov3_ubipr import masked_crop
from textura_polar import prepare_texture


def prepare(rows,condition,level,reference_cache,folder,model,spec,gallery=None,progress=None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False);n=len(rows)
    native=np.lib.format.open_memmap(folder/'native.npy',mode='w+',dtype=np.uint8,shape=(n,224,224,3))
    polar=np.lib.format.open_memmap(folder/'polar.npy',mode='w+',dtype=np.uint8,shape=(n,64,512,3))
    old_native=np.load(reference_cache/'native.npy',mmap_mode='r');old_polar=np.load(reference_cache/'polar.npy',mmap_mode='r')
    with np.load(reference_cache/'valid.npz') as z:rv=z['rgb'].copy();pv=z['polar'].copy()
    gi=[i for i,r in enumerate(rows) if r.session==1];count={'native_fallback':0,'polar_fallback':0};interventions=[]
    if gallery is not None:native[gi]=gallery['native'];polar[gi]=gallery['polar']
    for i,row in enumerate(rows):
        if gallery is not None and row.session==1:continue
        photo=Image.open(row.image).convert('RGB')
        if condition!='original' and row.session==2:
            reference=decode_mask(Image.open(row.mask))==1;photo,meta=perturb(photo,reference,condition,level)
            interventions.append({'row':i,'reference_pixels':int(reference.sum()),'fraction_defined':bool(reference.any()),'affected_fraction':meta['affected_fraction']})
        mask=predict_mask(model,photo,spec)
        if mask.any():native[i]=np.asarray(masked_crop(photo,mask).resize((224,224),Image.Resampling.BILINEAR))
        else:native[i]=old_native[i];count['native_fallback']+=1
        try:polar[i]=prepare_texture(np.asarray(photo),mask)[0]
        except ValueError:polar[i]=old_polar[i];count['polar_fallback']+=1
        if progress is not None and i%64==0:progress(i,n)
    native.flush();polar.flush();np.savez_compressed(folder/'valid.npz',rgb=rv,polar=pv)
    detail={'fallback_counts':count,'validity':'Retain original component availability; original failures are not removed or repaired. Invalid new masks/geometry use original cached input.',
        'interventions':interventions,'gallery_reused':gallery is not None}
    (folder/'AUDITORIA_ENTRADAS.json').write_text(json.dumps(detail,indent=2),encoding='utf-8')
    if gallery is None:gallery={'native':native[gi].copy(),'polar':polar[gi].copy()}
    else:
        np.testing.assert_array_equal(native[gi],gallery['native']);np.testing.assert_array_equal(polar[gi],gallery['polar'])
    return {'native':native,'polar':polar},rv,pv,gallery

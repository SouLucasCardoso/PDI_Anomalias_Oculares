"""Hamming mascarado em lote, equivalente ao comparador FFT de referencia."""
import numpy as np

def gallery_batch(templates):
    return {key:np.stack([t[key] for t in templates]).conj() for key in ('code','sum','mask')}

def scores_batch(query, gallery, max_shift=16):
    spectrum=(query['sum'][None]*gallery['mask']+query['mask'][None]*gallery['sum']
              -2*(query['code'][None]*gallery['code']).sum(axis=1)).sum(axis=1)
    overlap=np.rint(np.fft.irfft((query['mask'][None]*gallery['mask']).sum(axis=1),n=query['width'])).astype(np.int64)*query['filters']
    xor=np.rint(np.fft.irfft(spectrum,n=query['width'])).astype(np.int64)
    xor=np.clip(xor,0,overlap)
    raw=np.full(overlap.shape,np.inf)
    np.divide(xor,overlap,out=raw,where=overlap>0)
    indexes=np.arange(-max_shift,max_shift+1)%query['width']
    best=raw[:,indexes].min(axis=1)
    return np.where(np.isfinite(best),1-best,-2.)

def aggregate(scores, groups, mode):
    """Sentinela -2 indica falha; cossenos negativos continuam validos."""
    result=np.full((scores.shape[0],len(groups)),-2.,dtype=np.float64)
    for j,positions in enumerate(groups):
        block=scores[:,positions]
        if mode=='first': result[:,j]=block[:,0]
        elif mode=='max': result[:,j]=block.max(axis=1)
        elif mode=='top3':
            best=np.sort(block,axis=1)[:,-min(3,block.shape[1]):]
            valid=best>-2
            np.divide(np.where(valid,best,0).sum(1),valid.sum(1),out=result[:,j],where=valid.any(1))
        else: raise ValueError(mode)
    return result

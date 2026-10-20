"""Hamming mascarado para todas as rotacoes: correlacao circular exata via FFT.

Equivale ao matchCodes CVRL para uma escala de filtros; nao altera codificacao.
"""
import numpy as np

def prepare(code, mask):
    code=np.asarray(code,dtype=bool); mask=np.asarray(mask)>127.5
    if code.ndim!=3 or mask.ndim!=2 or code.shape[2]!=mask.shape[1]: raise ValueError('Invalid template dimensions')
    difference=mask.shape[0]-code.shape[1]
    if difference<0 or difference%2: raise ValueError('Invalid mask crop')
    radius=difference//2
    if radius: mask=mask[radius:-radius]
    code_fft=np.fft.rfft(code*mask[None],axis=-1)
    return {'code':code_fft,'sum':code_fft.sum(axis=0),'mask':np.fft.rfft(mask,axis=-1),
            'filters':code.shape[0],'width':code.shape[-1]}

def distances(query, gallery, typical_valid_pixels=20603):
    if query['code'].shape!=gallery['code'].shape: raise ValueError('Incompatible template dimensions')
    spectrum=(query['sum']*gallery['mask'].conj()+query['mask']*gallery['sum'].conj()
              -2*(query['code']*gallery['code'].conj()).sum(axis=0)).sum(axis=0)
    width=query['width']; filters=query['filters']
    xor=np.rint(np.fft.irfft(spectrum,n=width)).astype(np.int64)
    overlap=np.rint(np.fft.irfft((query['mask']*gallery['mask'].conj()).sum(axis=0),n=width)).astype(np.int64)*filters
    valid=overlap>0; raw=np.full(width,np.inf); normalized=np.full(width,np.inf)
    xor=np.clip(xor,0,overlap)
    raw[valid]=xor[valid]/overlap[valid]
    normalized[valid]=.5-(.5-raw[valid])*np.sqrt(overlap[valid]/(typical_valid_pixels*filters))
    return raw,normalized,overlap

def best_score(distances_by_shift, max_shift):
    width=len(distances_by_shift)
    indexes=np.arange(width) if max_shift is None else np.arange(-max_shift,max_shift+1)%width
    best=float(np.min(distances_by_shift[indexes]))
    return 1-best if np.isfinite(best) else -2.

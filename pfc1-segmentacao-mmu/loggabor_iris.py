"""Baseline local de fase Log-Gabor, nao implementacao oficial OSIRIS."""
import cv2
import numpy as np

def encode(gray,mask,wavelength=18.,sigma=.5):
    gray=np.asarray(gray,dtype=np.float64);mask=np.asarray(mask,dtype=bool)
    # Angular border wraps; radial border is outside the visible strip.
    padded=np.pad(mask.astype(np.uint8),((0,0),(2,2)),mode='wrap')
    valid=cv2.erode(padded,np.ones((3,5),np.uint8),borderType=cv2.BORDER_CONSTANT,borderValue=0)[:,2:-2]>0
    count=mask.sum(1,keepdims=True);mean=np.divide((gray*mask).sum(1,keepdims=True),count,out=np.zeros_like(count,dtype=float),where=count>0)
    signal=(gray-mean)*mask;freq=np.fft.fftfreq(gray.shape[1]);filt=np.zeros_like(freq);positive=freq>0
    filt[positive]=np.exp(-np.log(freq[positive]*wavelength)**2/(2*np.log(sigma)**2))
    response=np.fft.ifft(np.fft.fft(signal,axis=1)*filt[None],axis=1)
    valid &= np.abs(response)>1e-6
    return np.stack([response.real>0,response.imag>0]),valid.astype(np.uint8)*255

def normalized_scores(query,gallery,max_shift=16):
    spectrum=(query['sum'][None]*gallery['mask']+query['mask'][None]*gallery['sum']-2*(query['code'][None]*gallery['code']).sum(axis=1)).sum(axis=1)
    overlap=np.rint(np.fft.irfft((query['mask'][None]*gallery['mask']).sum(axis=1),n=query['width'])).astype(np.int64)*query['filters']
    xor=np.rint(np.fft.irfft(spectrum,n=query['width'])).astype(np.int64);xor=np.clip(xor,0,overlap)
    raw=np.full(overlap.shape,np.inf);np.divide(xor,overlap,out=raw,where=overlap>0)
    typical=.5*64*512*query['filters']
    distance=np.full(raw.shape,np.inf);usable=overlap>=.1*64*512*query['filters']
    distance[usable]=.5-(.5-raw[usable])*np.sqrt(overlap[usable]/typical)
    indexes=np.arange(-max_shift,max_shift+1)%query['width'];best=distance[:,indexes].min(1)
    return np.where(np.isfinite(best),1-best,-2.)

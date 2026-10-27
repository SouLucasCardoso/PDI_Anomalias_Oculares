"""Comparacao local fixa de mapas polares; nenhum rotulo participa do escore."""
import numpy as np

def unit(x):
    return x/np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-12)

def regions(maps,mean,std):
    x=(np.asarray(maps,np.float32)-mean[None,:,None,None])/std[None,:,None,None]
    assert x.shape[1:]==(256,4,32)
    # Four radial positions x eight angular bands, each pooling four columns.
    return unit(x.reshape(len(x),256,4,8,4).mean(-1).transpose(0,2,3,1).reshape(len(x),32,256))

def compare(query,gallery,keep=24):
    assert 1<=keep<=32 and query.shape[1:]==gallery.shape[1:]==(32,256)
    local=np.einsum('bpc,gpc->bgp',query,gallery,optimize=True)
    return np.sort(local,axis=-1)[...,-keep:].mean(-1,dtype=np.float64)

"""Destilacao regional ridge: oito descritores de identidade por foto.

Nao usa rotulos de consulta, referencias ou contrapartida limpa na inferencia.
"""
import numpy as np


def unit(x):
    return x/np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-12)


def sectors(maps):
    x=np.asarray(maps,np.float32)
    if x.ndim!=4 or x.shape[1:]!=(256,4,32):raise ValueError('Expected Nx256x4x32')
    return x.reshape(len(x),256,4,8,4).mean((2,4)).transpose(0,2,1)


def fit_ridge(x,target,weights,regularization=.01):
    """Weighted ridge in standardized coordinates; unpenalized intercept.

    Lambda scales by total view weight, fixed independently of monitor scores.
    """
    x=np.asarray(x,np.float64);y=np.asarray(target,np.float64);w=np.asarray(weights,np.float64)
    if x.ndim!=3 or y.shape!=(len(x),256) or w.shape!=(len(x),) or (w<0).any() or w.sum()<=0:raise ValueError('Invalid training arrays')
    mean=np.einsum('n,npc->pc',w,x)/w.sum()
    variance=np.einsum('n,npc->pc',w,(x-mean)**2)/w.sum();std=np.sqrt(np.maximum(variance,1e-8))
    ym=(y*w[:,None]).sum(0)/w.sum();coef=[]
    for j in range(8):
        z=(x[:,j]-mean[j])/std[j]
        gram=z.T@(w[:,None]*z)/w.sum()+regularization*np.eye(256)
        rhs=z.T@(w[:,None]*(y-ym))/w.sum()
        coef.append(np.linalg.solve(gram,rhs))
    return dict(mean=mean,std=std,coef=np.stack(coef),intercept=ym)


def transform(x,state):
    z=(np.asarray(x,np.float64)-state['mean'])/state['std']
    return unit(np.einsum('npc,pcd->npd',z,state['coef'],optimize=True)+state['intercept']).astype(np.float32)


def pair_scores(query,gallery,keep=6):
    if not 1<=keep<=8 or query.shape[1:]!=(8,256) or gallery.shape[1:]!=(8,256):raise ValueError('Expected eight regions')
    agreement=np.einsum('bpc,gpc->bgp',query,gallery,optimize=True)
    return np.sort(agreement,axis=-1)[...,-keep:].mean(-1,dtype=np.float64)


def eye_scores(query,gallery,groups,keep=6):
    pairs=pair_scores(query,gallery,keep)
    return np.stack([np.sort(pairs[:,g],axis=1)[:,-min(3,len(g)):].mean(1) for g in groups],axis=1)

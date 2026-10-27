"""Escala por consulta estimada sem o maior escore; nao usa rotulos."""
import numpy as np

def fuse_background(components,calibration):
    available=np.logical_and.reduce([c['scores']>-2 for c in components]);valid=np.logical_and.reduce([c['valid'] for c in components])&available.any(1)
    views=[]
    for j in range(2):views.append(np.mean([(c['scores']-p['mean'])/p['std'] for c,p in zip(components[:7]+[components[7+j]],calibration[j])],axis=0))
    raw=np.mean(views,axis=0);out=np.full_like(raw,-2.)
    for i in np.flatnonzero(valid):
        cols=np.flatnonzero(available[i]);values=raw[i,cols]
        if len(values)<3:valid[i]=False;continue
        background=np.delete(values,int(values.argmax()));std=float(background.std())
        if std<=1e-12:valid[i]=False;continue
        z=(values-background.mean())/std;out[i,cols]=1/(1+np.exp(-np.clip(z,-30,30)))
    return out,valid&(out>-2).any(1)

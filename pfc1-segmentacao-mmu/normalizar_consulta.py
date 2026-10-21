"""Normalizacao de escores por consulta individual, sem conhecer sua identidade."""
import numpy as np

def normalize(scores,valid):
    scores=np.asarray(scores,dtype=np.float64);valid=np.asarray(valid,dtype=bool)
    available=scores>-2;out=np.full_like(scores,-2.)
    for i in np.flatnonzero(valid):
        usable=available[i]
        if usable.sum()<2:continue
        values=scores[i,usable]
        # Inputs are logistic fixed-fusion scores; invert before standardizing.
        values=np.log(np.clip(values,1e-12,1-1e-12)/np.clip(1-values,1e-12,1))
        std=float(values.std())
        if std<=1e-12:continue
        z=(values-values.mean())/std
        out[i,usable]=1/(1+np.exp(-np.clip(z,-30,30)))
    return out,valid&(out>-2).any(1)

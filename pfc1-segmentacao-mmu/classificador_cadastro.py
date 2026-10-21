"""Classificador ridge ajustado somente em fotos conhecidas de cadastro."""
import numpy as np

def fit(features,labels,classes,alpha=1.):
    x=np.asarray(features,dtype=np.float64);labels=np.asarray(labels,dtype=int)
    if alpha<=0 or x.ndim!=2 or len(x)!=len(labels):raise ValueError('Invalid enrollment data')
    mean=x.mean(0);targets=np.eye(classes)[labels];prior=targets.mean(0)
    centered=x-mean;y=targets-prior
    dual=np.linalg.solve(centered@centered.T+alpha*np.eye(len(x)),y)
    weights=centered.T@dual
    return {'mean':mean,'weights':weights,'prior':prior}

def predict(features,state):
    return (np.asarray(features,dtype=np.float64)-state['mean'])@state['weights']+state['prior']

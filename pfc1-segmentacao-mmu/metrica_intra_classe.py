"""Transformacao linear ajustada exclusivamente em identidades de treino."""
import numpy as np

def fit(features, labels, shrinkage=.1):
    x=np.asarray(features,dtype=np.float64);labels=np.asarray(labels)
    if x.ndim!=2 or len(x)!=len(labels) or not np.isfinite(x).all():raise ValueError('Invalid training features')
    if not 0<shrinkage<=1:raise ValueError('Invalid shrinkage')
    mean=x.mean(0);residual=np.empty_like(x);degrees=0
    for eye in np.unique(labels):
        selected=labels==eye;residual[selected]=x[selected]-x[selected].mean(0)
        degrees+=int(selected.sum())-1
    if degrees<=0:raise ValueError('Need repeated captures per training identity')
    covariance=residual.T@residual/degrees;scale=float(np.trace(covariance)/x.shape[1])
    if scale<=0:raise ValueError('No within-class variation')
    covariance=(1-shrinkage)*covariance+shrinkage*scale*np.eye(x.shape[1])
    values,vectors=np.linalg.eigh(covariance)
    matrix=(vectors/np.sqrt(values)[None,:])@vectors.T
    return mean,matrix

def transform(features,mean,matrix):
    result=(np.asarray(features,dtype=np.float64)-mean)@matrix
    norms=np.linalg.norm(result,axis=1,keepdims=True)
    return result/np.maximum(norms,1e-12)

"""Remove vies por olho cadastrado usando apenas impostores do cadastro."""
import numpy as np

def fit(gallery_scores,gallery_labels,gallery_valid):
    scores=np.asarray(gallery_scores,dtype=np.float64);labels=np.asarray(gallery_labels);valid=np.asarray(gallery_valid,dtype=bool)
    means=[];stds=[];counts=[]
    for eye in range(scores.shape[1]):
        selected=valid&(labels!=eye)&(scores[:,eye]>-2)
        values=scores[selected,eye]
        if len(values)<2 or values.std()<=1e-6:raise ValueError('Insufficient enrollment impostor cohort')
        means.append(float(values.mean()));stds.append(float(values.std()));counts.append(len(values))
    return np.array(means),np.array(stds),np.array(counts)

def transform(scores,means,stds):
    scores=np.asarray(scores,dtype=np.float64);available=scores>-2
    z=(scores-means)/stds
    result=1/(1+np.exp(-np.clip(z,-30,30)));result[~available]=-2
    return result

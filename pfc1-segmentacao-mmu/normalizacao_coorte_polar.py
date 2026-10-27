"""Normalizacao simetrica de escores por coorte FIT de olhos diferentes."""
import numpy as np
from comparador_hdbif_lote import aggregate

def cohort_stats(vectors,valid,sides,cohort,cohort_valid,cohort_sides,groups):
    result=np.zeros((len(vectors),2),np.float64)
    for start in range(0,len(vectors),32):
        raw=(vectors[start:start+32]@cohort.T).astype(np.float64);raw[:,~cohort_valid]=-2
        scores=aggregate(raw,groups,'top3')
        for j in range(len(raw)):
            selected=scores[j,(cohort_sides==sides[start+j])&(scores[j]>-2)]
            if not valid[start+j]:result[start+j]=[0,1];continue
            if len(selected)<2:raise ValueError('Need at least two valid same-side cohort eyes')
            result[start+j]=[selected.mean(),max(selected.std(),.05)]
    return result

def symmetric_scores(query,gallery,query_stats,gallery_stats):
    raw=(query@gallery.T).astype(np.float64)
    return .5*((raw-query_stats[:,0,None])/query_stats[:,1,None]+(raw-gallery_stats[None,:,0])/gallery_stats[None,:,1])

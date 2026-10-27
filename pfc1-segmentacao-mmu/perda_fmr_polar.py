"""Referencia limpa FIT e penalizacao da cauda impostora, sem dados do monitor."""
import math
import numpy as np
import torch
from torch.nn import functional as F
from perda_top3_polar import top3_eye_scores

def fit_impostor_reference(scores,labels,valid):
    from avaliar_robustez_reconhecimento import operating_threshold
    scores=np.asarray(scores,dtype=np.float64);labels=np.asarray(labels);valid=np.asarray(valid,bool)
    impostor=np.ones_like(scores,bool);impostor[np.arange(len(labels)),labels]=False
    usable=impostor&valid[:,None]&(scores>-2)
    if not usable.any():raise ValueError('No valid FIT impostor comparison')
    return float(operating_threshold(scores[usable])),int(usable.sum())

def top3_absolute_loss(pred,labels,is_query,gallery,present,eye_sides,reference,scale=.1,genuine_margin=.05):
    if not bool(is_query.any()):return pred.sum()*0
    scores=top3_eye_scores(pred[is_query],gallery,present);labels=labels[is_query].long()
    genuine=scores.gather(-1,labels[:,None,None].expand(-1,3,1)).squeeze(-1)
    same=eye_sides[None,:]==eye_sides[labels,None];same.scatter_(1,labels[:,None],False)
    if not bool(same.any(1).all()):raise ValueError('No same-side negative')
    count=max(1,math.ceil(.01*int(same.sum(1).max())))
    tail=scores.masked_fill(~same[:,None,:],-torch.inf).topk(count,dim=-1).values;finite=torch.isfinite(tail)
    negative=F.relu((tail-reference)/scale).square().masked_fill(~finite,0).sum(-1)/finite.sum(-1).clamp_min(1)
    positive=F.relu((reference+genuine_margin-genuine)/scale).square()
    loss=negative+positive
    return (loss*loss.new_tensor([4.,1.,1.])).sum(1).mean()/6

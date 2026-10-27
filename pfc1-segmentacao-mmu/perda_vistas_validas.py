"""Perdas por vista: extracoes invalidas nao supervisionam identidade.

Denominador fixo 6 por foto: a remocao de uma vista nao aumenta o peso
das demais. Fotografias e falhas continuam nos denominadores da avaliacao.
"""
import math
import torch
from torch.nn import functional as F
from perda_top3_polar import top3_eye_scores
from treinar_encoder_polar_espacial import FeaturePairs


class ValidFeaturePairs(FeaturePairs):
    def __init__(self,features,mapping,teacher,indices,labels,queries,valid):
        super().__init__(features,mapping,teacher,indices,labels,queries)
        self.valid=valid

    def __getitem__(self,k):
        return (*super().__getitem__(k),torch.from_numpy(self.valid[self.indices[k]].copy()))


def reduce_views(loss,valid):
    if loss.ndim!=2 or loss.shape[1]!=3 or valid.shape!=loss.shape or valid.dtype!=torch.bool:
        raise ValueError('Expected Bx3 loss and boolean validity')
    if not len(loss):return loss.sum()*0
    return (loss.masked_fill(~valid,0)*loss.new_tensor([4.,1.,1.])).sum(1).mean()/6


def valid_losses(pred,teacher,labels,is_query,gallery,present,eye_sides,reference,valid):
    alignment=reduce_views(1-(pred*teacher[:,None]).sum(-1),valid)
    if not bool(is_query.any()):return alignment,pred.sum()*0,pred.sum()*0
    labels=labels[is_query].long();qvalid=valid[is_query]
    scores=top3_eye_scores(pred[is_query],gallery,present)
    genuine=scores.gather(-1,labels[:,None,None].expand(-1,3,1)).squeeze(-1)
    same=eye_sides[None,:]==eye_sides[labels,None];same.scatter_(1,labels[:,None],False)
    if not bool(same.any(1).all()):raise ValueError('Need same-side negative')
    impostors=scores.masked_fill(~same[:,None,:],-torch.inf)
    hardest=impostors.max(-1).values
    relative=reduce_views(F.softplus((hardest+.1-genuine)/.1),qvalid)
    count=max(1,math.ceil(.01*int(same.sum(1).max())))
    tail=impostors.topk(count,dim=-1).values;finite=torch.isfinite(tail)
    negative=F.relu((tail-reference)/.1).square().masked_fill(~finite,0).sum(-1)/finite.sum(-1).clamp_min(1)
    positive=F.relu((reference+.05-genuine)/.1).square()
    absolute=reduce_views(negative+positive,qvalid)
    return alignment,relative,absolute

"""Perda S2->prototipos S1 congelados, somente pessoas de ajuste."""
import torch
from torch.nn import functional as F

def session_identity_loss(pred,labels,is_query,prototypes,prototype_sides,temperature=.1):
    if not bool(is_query.any()):return pred.sum()*0
    query=pred[is_query];target=labels[is_query].long()
    logits=query@prototypes.detach().T/temperature
    same_side=prototype_sides[None,:]==prototype_sides[target,None]
    logits=logits.masked_fill(~same_side[:,None,:],-torch.inf)
    loss=F.cross_entropy(logits.flatten(0,1),target[:,None].expand(-1,3).flatten(),reduction='none').reshape(-1,3)
    return (loss*loss.new_tensor([4.,1.,1.])).sum(1).mean()/6

def selection_key(measured,cosines,baseline,epoch):
    from treinar_adaptador_polar_original import advancement
    return (bool(advancement(measured,baseline,epoch)),min(measured[t]['tar'] for t in ['upper10','lower10']),min(measured[t]['rank1'] for t in ['upper10','lower10']),-max(measured[t]['far'] for t in ['upper10','lower10']),sum(cosines[t] for t in ['upper10','lower10'])/2)

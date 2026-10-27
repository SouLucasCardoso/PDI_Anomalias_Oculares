"""Agregacao diferenciavel top3 por olho e margem para impostor mais dificil."""
import torch
from torch.nn import functional as F

def top3_eye_scores(query,gallery,present):
    if gallery.ndim!=3 or present.shape!=gallery.shape[:2] or not bool(present.any(1).all()):raise ValueError('Every eye needs valid enrollment')
    scores=(query@gallery.detach().flatten(0,1).T).reshape(*query.shape[:-1],*gallery.shape[:2])
    scores=scores.masked_fill(~present,-torch.inf);best=scores.topk(min(3,gallery.shape[1]),dim=-1).values
    finite=torch.isfinite(best)
    return best.masked_fill(~finite,0).sum(-1)/finite.sum(-1).clamp_min(1)

def top3_hard_negative_loss(pred,labels,is_query,gallery,present,eye_sides,margin=.1,temperature=.1):
    if not bool(is_query.any()):return pred.sum()*0
    query=pred[is_query];labels=labels[is_query].long();scores=top3_eye_scores(query,gallery,present)
    genuine=scores.gather(-1,labels[:,None,None].expand(-1,3,1)).squeeze(-1)
    same_side=eye_sides[None,:]==eye_sides[labels,None];same_side.scatter_(1,labels[:,None],False)
    if not bool(same_side.any(1).all()):raise ValueError('Need different same-side eye')
    negative=scores.masked_fill(~same_side[:,None,:],-torch.inf).max(-1).values
    loss=F.softplus((negative+margin-genuine)/temperature)
    return (loss*loss.new_tensor([4.,1.,1.])).sum(1).mean()/6

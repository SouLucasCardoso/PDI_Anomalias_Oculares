"""Negativos internos derivados SOMENTE das classes nativas; nao sao GT independente de pupila."""
import io
from pathlib import Path

import cv2
import numpy as np
import torch

from segmentador_sam3_iris import iris_loss


def inner_noniris(target):
    values=np.asarray(target)
    iris=(values==1).astype(np.uint8)
    padded=np.pad(iris,1)
    cv2.floodFill(padded,None,(0,0),2)
    return (padded[1:-1,1:-1]==0) & (values==0)


def inner_penalty(logits,target):
    known=np.stack([inner_noniris(t) for t in target.detach().cpu().numpy()])
    selected=torch.from_numpy(known).to(logits.device)
    count=selected.sum((1,2));active=count>0
    probability=logits.float().softmax(1)[:,1].clamp(max=1-1e-6)
    values=(-torch.log1p(-probability)*selected).sum((1,2))/count.clamp_min(1)
    return values[active].mean() if active.any() else logits.float().sum()*0


def supervised_loss(logits,target):
    return iris_loss(logits,target)+.5*inner_penalty(logits,target)


def checkpoint(path,state):
    # O contêiner em memória usa o mesmo prefixo ZIP, independente do nome do arquivo.
    stream=io.BytesIO();torch.save(state,stream)
    temporary=Path(path).with_suffix('.pt.part')
    temporary.write_bytes(stream.getvalue());temporary.replace(path)

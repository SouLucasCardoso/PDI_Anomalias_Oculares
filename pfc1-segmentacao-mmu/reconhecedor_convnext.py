"""ConvNeXt de identidade e contraste local, sem restauracao generativa."""
import cv2
import numpy as np
import torch
from torch import nn
from torchvision import models

class Encoder(nn.Module):
    def __init__(self):
        super().__init__();self.backbone=models.convnext_tiny(weights=None)
        self.backbone.classifier[2]=nn.Identity()
        self.projection=nn.Sequential(nn.Linear(768,256,bias=False),nn.BatchNorm1d(256))
    def forward(self,x):
        return nn.functional.normalize(self.projection(self.backbone(x)),dim=1)

def contrast(image):
    rgb=np.asarray(image,dtype=np.uint8);support=(rgb>0).any(2)
    lab=cv2.cvtColor(rgb,cv2.COLOR_RGB2LAB)
    lab[:,:,0]=cv2.createCLAHE(clipLimit=2.,tileGridSize=(8,8)).apply(lab[:,:,0])
    result=cv2.cvtColor(lab,cv2.COLOR_LAB2RGB);result[~support]=0
    return result

def prepare(images,target):
    output=np.lib.format.open_memmap(target,mode='w+',dtype=np.uint8,shape=images.shape)
    for i,image in enumerate(images):
        output[i]=contrast(image)
        if (i+1)%1000==0:print(f'CLAHE {target.name} {i+1}/{len(images)}',flush=True)
    output.flush();return output

def load(checkpoint,device='cpu'):
    state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    assert state['configuration']['architecture']=='convnext_tiny_contrast_256'
    model=Encoder();model.load_state_dict(state['model']);return model.to(device).eval(),state['configuration']

"""Forma eliptica auxiliar; centro/raio equivalente do localizador circular congelados."""
from pathlib import Path
import json
import cv2
import numpy as np
import torch
from torch import nn
from localizador_pupila import PupilLocator,encode_roi,refined_textures as circle_textures
from normalizacao_eliptica import ellipse_endpoints

ROOT=Path(__file__).resolve().parent

class EllipticShape(nn.Module):
    def __init__(self):
        super().__init__()
        self.shape=nn.Linear(4096,2)
        nn.init.zeros_(self.shape.weight);nn.init.zeros_(self.shape.bias)
    def forward(self,features):return .75*torch.tanh(self.shape(features.flatten(1)))

def encode_shape(ellipse):
    (_, _),(w,h),angle=ellipse
    if w>h:major,minor,theta=w,h,np.deg2rad(angle)
    else:major,minor,theta=h,w,np.deg2rad(angle+90)
    magnitude=.5*np.log(major/minor)
    return np.array([magnitude*np.cos(2*theta),magnitude*np.sin(2*theta)],np.float32)

def decode_shape(center,radius,shape):
    magnitude=float(np.linalg.norm(shape));theta=.5*np.arctan2(shape[1],shape[0])
    return (tuple(map(float,center)),(float(2*radius*np.exp(magnitude)),float(2*radius*np.exp(-magnitude))),float(np.rad2deg(theta)))

def contained(inner,outer):
    theta=np.arange(512)*2*np.pi/512;x,y=ellipse_endpoints(inner,theta)
    dx=x-outer[0][0];dy=y-outer[0][1];a=np.deg2rad(outer[2])
    u=np.cos(a)*dx+np.sin(a)*dy;v=-np.sin(a)*dx+np.cos(a)*dy
    return bool(np.all((u/(outer[1][0]/2))**2+(v/(outer[1][1]/2))**2<=1))

class EllipseLocator(nn.Module):
    def __init__(self,shape_file,device):
        super().__init__();self.circle=PupilLocator();self.shape_model=EllipticShape()
        file=ROOT/'outputs/localizador_pupila_2026-10-22/melhor_modelo.pt'
        self.circle.load_state_dict(torch.load(file,map_location='cpu',weights_only=True)['model'])
        value=json.loads(Path(shape_file).read_text())
        self.shape_model.load_state_dict({k:torch.tensor(v,dtype=torch.float32) for k,v in value['state'].items()})
        self.to(device).eval()

def refined_textures(rgb,mask,locator,device):
    # Circle control is exactly yesterday's inference, including its fixed guards.
    old,oldred,geometry,applied=circle_textures(rgb,mask,locator.circle,device)
    if not applied:return old,oldred,geometry,False
    encoded,(x0,y0,x1,y1)=encode_roi(rgb,mask)
    x=torch.from_numpy(encoded.transpose(2,0,1).copy()).to(device).float()[None]/255
    with torch.inference_mode():shape=locator.shape_model(locator.circle.features(x))[0].cpu().numpy()
    radius=geometry['pupil_ellipse'][1][0]/2
    pupil=decode_shape(geometry['pupil_ellipse'][0],radius,shape)
    if not np.isfinite(shape).all() or not contained(pupil,geometry['iris_ellipse']):
        return old,oldred,geometry,True
    theta=np.arange(512)*2*np.pi/512;t=np.arange(1,65)[:,None]/64
    ax,ay=ellipse_endpoints(pupil,theta);bx,by=ellipse_endpoints(geometry['iris_ellipse'],theta)
    mx=((1-t)*ax+t*bx).astype(np.float32);my=((1-t)*ay+t*by).astype(np.float32)
    support=cv2.remap(mask[y0:y1,x0:x1].astype(np.uint8),mx,my,cv2.INTER_NEAREST,borderMode=cv2.BORDER_CONSTANT,borderValue=0)>0
    if not support.any():return old,oldred,geometry,True
    region=rgb[y0:y1,x0:x1];gray=cv2.createCLAHE(clipLimit=2.,tileGridSize=(8,8)).apply(cv2.cvtColor(region,cv2.COLOR_RGB2GRAY))
    textures=[]
    for image in [gray,region[:,:,0]]:
        polar=cv2.remap(image,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE);polar[~support]=127;textures.append(np.repeat(polar[:,:,None],3,axis=2))
    geometry=dict(geometry,pupil_ellipse=pupil,pupil_source='train_only_ellipse_shape',polar_mask_fraction=float(support.mean()))
    return *textures,geometry,True

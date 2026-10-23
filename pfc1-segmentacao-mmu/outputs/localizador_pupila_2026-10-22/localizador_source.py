"""Localizador circular supervisionado por buracos da anotacao, nao anatomia validada."""
import cv2
import numpy as np
import torch
from torch import nn


class PupilLocator(nn.Module):
    def __init__(self):
        super().__init__()
        self.features=nn.Sequential(nn.Conv2d(4,16,3,padding=1),nn.GroupNorm(4,16),nn.ReLU(),nn.MaxPool2d(2),nn.Conv2d(16,32,3,padding=1),nn.GroupNorm(4,32),nn.ReLU(),nn.MaxPool2d(2),nn.Conv2d(32,64,3,padding=1),nn.ReLU(),nn.AdaptiveAvgPool2d((8,8)))
        self.head=nn.Sequential(nn.Flatten(),nn.Linear(4096,128),nn.ReLU(),nn.Linear(128,3))
        nn.init.zeros_(self.head[-1].weight)
        with torch.no_grad():self.head[-1].bias.copy_(torch.tensor([0.,0.,-1.68639895357]))
    def forward(self,x):
        value=self.head(self.features(x)).sigmoid()
        return value*value.new_tensor([1.,1.,.4])


def roi_bounds(mask):
    y,x=np.where(mask)
    if not len(x):raise ValueError('Empty iris')
    width=int(x.max()-x.min()+1);height=int(y.max()-y.min()+1)
    px=max(2,round(width*.5));py=max(2,round(height*.5))
    return max(0,int(x.min())-px),max(0,int(y.min())-py),min(mask.shape[1],int(x.max())+px+1),min(mask.shape[0],int(y.max())+py+1)


def pupil_target(reference):
    contours,hierarchy=cv2.findContours(reference.astype(np.uint8)*255,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_NONE)
    if hierarchy is None:return None
    outer=[i for i,p in enumerate(hierarchy[0,:,3]) if p<0 and len(contours[i])>=5]
    if not outer:return None
    oi=max(outer,key=lambda i:cv2.contourArea(contours[i]));iris=cv2.fitEllipse(contours[oi])
    holes=[i for i,p in enumerate(hierarchy[0,:,3]) if p==oi and len(contours[i])>=5 and cv2.contourArea(contours[i])>=max(4,.01*cv2.contourArea(contours[oi]))]
    if not holes:return None
    pupil=cv2.fitEllipse(contours[max(holes,key=lambda i:cv2.contourArea(contours[i]))])
    if max(pupil[1])>=.9*max(iris[1]) or np.linalg.norm(np.array(pupil[0])-iris[0])>=max(iris[1])/2:return None
    return float(pupil[0][0]),float(pupil[0][1]),float(np.sqrt(pupil[1][0]*pupil[1][1])/2)


def encode_roi(rgb,mask):
    x0,y0,x1,y1=roi_bounds(mask)
    color=cv2.resize(rgb[y0:y1,x0:x1],(64,64),interpolation=cv2.INTER_LINEAR)
    binary=cv2.resize(mask[y0:y1,x0:x1].astype(np.uint8)*255,(64,64),interpolation=cv2.INTER_NEAREST)
    return np.concatenate([color,binary[:,:,None]],axis=2),(x0,y0,x1,y1)


def decode_circle(value,bounds):
    x0,y0,x1,y1=bounds;w=x1-x0;h=y1-y0
    return float(x0+value[0]*w),float(y0+value[1]*h),float(value[2]*min(w,h))


def refined_textures(rgb,mask,locator,device):
    """Only legacy FALLBACK changes; mask, outer ellipse and ordinary holes unchanged."""
    from textura_polar import prepare_texture
    from preparar_polar_vermelho import red_texture
    from normalizacao_eliptica import ellipse_endpoints
    old,geometry=prepare_texture(rgb,mask)
    if geometry['pupil_source']!='circle_regressor_fallback':return old,red_texture(rgb,mask),geometry,False
    encoded,bounds=encode_roi(rgb,mask)
    with torch.inference_mode():value=locator(torch.from_numpy(encoded.transpose(2,0,1).copy()).to(device).float()[None]/255)[0].cpu().numpy()
    cx,cy,r=decode_circle(value,bounds);x0,y0,x1,y1=bounds
    center=np.array([cx-x0,cy-y0]);outer=geometry['iris_ellipse']
    # Fixed plausibility constraints, no validation threshold search.
    if not np.isfinite([cx,cy,r]).all() or r<1 or 2*r>=.9*max(outer[1]) or np.linalg.norm(center-outer[0])>=max(outer[1])/2:
        return old,red_texture(rgb,mask),geometry,False
    original_geometry=geometry;geometry=dict(geometry);geometry['pupil_ellipse']=((float(center[0]),float(center[1])),(2*r,2*r),0.);geometry['pupil_source']='train_only_cnn_circle'
    theta=np.arange(512)*2*np.pi/512;t=np.arange(1,65)[:,None]/64
    ax,ay=ellipse_endpoints(geometry['pupil_ellipse'],theta);bx,by=ellipse_endpoints(outer,theta)
    mx=((1-t)*ax+t*bx).astype(np.float32);my=((1-t)*ay+t*by).astype(np.float32)
    support=cv2.remap(mask[y0:y1,x0:x1].astype(np.uint8),mx,my,cv2.INTER_NEAREST,borderMode=cv2.BORDER_CONSTANT,borderValue=0)>0
    if not support.any():return old,red_texture(rgb,mask),original_geometry,False
    region=rgb[y0:y1,x0:x1];gray=cv2.createCLAHE(clipLimit=2.,tileGridSize=(8,8)).apply(cv2.cvtColor(region,cv2.COLOR_RGB2GRAY))
    results=[]
    for image in [gray,region[:,:,0]]:
        polar=cv2.remap(image,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE);polar[~support]=127;results.append(np.repeat(polar[:,:,None],3,axis=2))
    geometry['polar_mask_fraction']=float(support.mean())
    return *results,geometry,True

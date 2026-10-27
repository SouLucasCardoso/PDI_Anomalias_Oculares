"""Correção elíptica externa em coordenadas da fotografia, sem reconstruir pixels."""
import cv2
import numpy as np
import torch
from torch import nn

def outer_ellipse(mask):
    contours,hierarchy=cv2.findContours(np.asarray(mask,np.uint8)*255,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_NONE)
    if hierarchy is None:raise ValueError('Empty mask')
    candidates=[i for i,p in enumerate(hierarchy[0,:,3]) if p<0 and len(contours[i])>=5]
    if not candidates:raise ValueError('No outer contour')
    ellipse=cv2.fitEllipse(contours[max(candidates,key=lambda i:cv2.contourArea(contours[i]))])
    if not np.isfinite(np.r_[ellipse[0],ellipse[1],ellipse[2]]).all() or min(ellipse[1])<=0:raise ValueError('Invalid ellipse')
    return ellipse

def covariance(ellipse):
    angle=np.deg2rad(ellipse[2]);r=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
    return r@np.diag((np.asarray(ellipse[1],float)/2)**2)@r.T

def ellipse_vector(ellipse,width,height):
    """Affine-invariant package: center and log-axis shape in unit-image coordinates."""
    if min(width,height)<=0:raise ValueError('Invalid image dimensions')
    d=np.diag([1/width,1/height]);matrix=d@covariance(ellipse)@d
    values,vectors=np.linalg.eigh(matrix)
    if not np.isfinite(values).all() or min(values)<=0:raise ValueError('Nonpositive ellipse')
    minor,major=np.sqrt(values);theta=np.arctan2(vectors[1,1],vectors[0,1])
    magnitude=.5*np.log(major/minor)
    return np.array([ellipse[0][0]/width,ellipse[0][1]/height,np.log(np.sqrt(major*minor)),magnitude*np.cos(2*theta),magnitude*np.sin(2*theta)],np.float32)

def vector_ellipse(value,width,height):
    value=np.asarray(value,float)
    if value.shape!=(5,) or not np.isfinite(value).all():raise ValueError('Invalid ellipse vector')
    radius=np.exp(value[2]);magnitude=np.linalg.norm(value[3:]);theta=.5*np.arctan2(value[4],value[3])
    if radius<=0 or magnitude>3:raise ValueError('Implausible ellipse shape')
    a,b=radius*np.exp(magnitude),radius*np.exp(-magnitude)
    r=np.array([[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]])
    d=np.diag([width,height]);matrix=d@r@np.diag([a*a,b*b])@r.T@d
    values,vectors=np.linalg.eigh(matrix)
    if min(values)<=0:raise ValueError('Nonpositive decoded ellipse')
    angle=np.rad2deg(np.arctan2(vectors[1,1],vectors[0,1]))
    return ((float(value[0]*width),float(value[1]*height)),(float(2*np.sqrt(values[1])),float(2*np.sqrt(values[0]))),float(angle))

def segmentation_features(unet,x):
    """Exactly the frozen U-Net forward, exposing an existing intermediate tensor."""
    e1=unet.enc1(x);e2=unet.enc2(unet.pool(e1));e3=unet.enc3(unet.pool(e2))
    y=unet.dec3(torch.cat((unet.up3(unet.middle(unet.pool(e3))),e3),1))
    y=unet.dec2(torch.cat((unet.up2(y),e2),1))
    logits=unet.output(unet.dec1(torch.cat((unet.up1(y),e1),1)))
    return logits,nn.functional.adaptive_avg_pool2d(e3,(8,8)).flatten(1)

class OuterCorrection(nn.Module):
    def __init__(self):
        super().__init__();self.head=nn.Sequential(nn.Linear(2053,128),nn.ReLU(),nn.Linear(128,5))
        nn.init.zeros_(self.head[-1].weight);nn.init.zeros_(self.head[-1].bias)
    def forward(self,features,baseline):
        delta=torch.tanh(self.head(torch.cat((features,baseline),1)))
        return baseline+delta*delta.new_tensor([.25,.25,.7,.75,.75])

def refined_textures(rgb,mask,value):
    """Only the outer ellipse changes; original support, inner ellipse and crop stay."""
    from textura_polar import prepare_texture
    from preparar_polar_vermelho import red_texture
    from localizador_pupila import roi_bounds
    from normalizacao_eliptica import ellipse_endpoints
    from pupila_eliptica import contained
    old,geometry=prepare_texture(rgb,mask);oldred=red_texture(rgb,mask)
    h,w=mask.shape
    baseline=ellipse_vector(outer_ellipse(mask),w,h)
    if np.max(np.abs(np.asarray(value)-baseline))<1e-8:return old,oldred,geometry,False,'unchanged'
    x0,y0,x1,y1=roi_bounds(mask)
    try:
        native=vector_ellipse(value,w,h)
        proposed=((native[0][0]-x0,native[0][1]-y0),native[1],native[2])
        if not (0<native[0][0]<w and 0<native[0][1]<h and min(native[1])>=2 and max(native[1])<2*max(w,h)):raise ValueError('geometry_guard')
        if not contained(geometry['pupil_ellipse'],proposed):raise ValueError('pupil_not_contained')
        theta=np.arange(512)*2*np.pi/512;t=np.arange(1,65)[:,None]/64
        ax,ay=ellipse_endpoints(geometry['pupil_ellipse'],theta);bx,by=ellipse_endpoints(proposed,theta)
        mx=((1-t)*ax+t*bx).astype(np.float32);my=((1-t)*ay+t*by).astype(np.float32)
        support=cv2.remap(mask[y0:y1,x0:x1].astype(np.uint8),mx,my,cv2.INTER_NEAREST,borderMode=cv2.BORDER_CONSTANT,borderValue=0)>0
        if not support.any():raise ValueError('empty_polar_support')
    except ValueError as error:return old,oldred,geometry,False,str(error)
    region=rgb[y0:y1,x0:x1];gray=cv2.createCLAHE(clipLimit=2.,tileGridSize=(8,8)).apply(cv2.cvtColor(region,cv2.COLOR_RGB2GRAY))
    textures=[]
    for pixels in [gray,region[:,:,0]]:
        polar=cv2.remap(pixels,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE);polar[~support]=127;textures.append(np.repeat(polar[:,:,None],3,2))
    geometry=dict(geometry,iris_ellipse=proposed,outer_source='train_only_residual_outer_ellipse',polar_mask_fraction=float(support.mean()))
    return *textures,geometry,True,'applied'

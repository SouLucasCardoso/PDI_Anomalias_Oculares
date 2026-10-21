"""Faixa polar de textura: mascara automatica, contraste local, exterior neutro."""
import cv2
import numpy as np
from normalizacao_eliptica import normalize,ellipse_endpoints

def prepare_texture(rgb,mask):
    rgb=np.asarray(rgb,dtype=np.uint8);mask=np.asarray(mask,dtype=bool)
    y,x=np.where(mask)
    if not len(x):raise ValueError('Empty predicted iris')
    width=int(x.max()-x.min()+1);height=int(y.max()-y.min()+1)
    px=max(2,round(width*.5));py=max(2,round(height*.5))
    x0=max(0,int(x.min())-px);x1=min(rgb.shape[1],int(x.max())+px+1)
    y0=max(0,int(y.min())-py);y1=min(rgb.shape[0],int(y.max())+py+1)
    region=rgb[y0:y1,x0:x1];binary=mask[y0:y1,x0:x1].astype(np.uint8)*255
    gray=cv2.cvtColor(region,cv2.COLOR_RGB2GRAY)
    gray=cv2.createCLAHE(clipLimit=2.,tileGridSize=(8,8)).apply(gray)
    fallback=[float((x.min()+x.max())/2-x0),float((y.min()+y.max())/2-y0),max(1.,min(width,height)/8)]
    polar,geometry=normalize(gray,binary,fallback)
    theta=np.arange(512)*2*np.pi/512;t=np.arange(1,65)[:,None]/64
    ax,ay=ellipse_endpoints(geometry['pupil_ellipse'],theta);bx,by=ellipse_endpoints(geometry['iris_ellipse'],theta)
    mx=((1-t)*ax+t*bx).astype(np.float32);my=((1-t)*ay+t*by).astype(np.float32)
    pm=cv2.remap(binary,mx,my,cv2.INTER_NEAREST,borderMode=cv2.BORDER_CONSTANT,borderValue=0)>0
    if not pm.any():raise ValueError('No polar mask support')
    polar[~pm]=127
    geometry.update(native_iris_width=width,native_iris_height=height,fallback_definition='concentric mask-bbox center, radius min(mask width,height)/8; not anatomical reference')
    return np.repeat(polar[:,:,None],3,axis=2),geometry

def cyclic_roll(image,shift):
    return np.roll(image,int(shift),axis=1).copy()

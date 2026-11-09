"""Refino conservador de logits com a fotografia como guia, sem completar tecido."""
import cv2
import numpy as np
import torch
from PIL import Image

SPECS={'continuous':{'flip':False,'radius':0,'epsilon':0.},
       'flip_mean':{'flip':True,'radius':0,'epsilon':0.}}
for flip in (False,True):
    for radius in (2,4):
        for epsilon in (.001,.01):
            SPECS[f'{"flip_" if flip else ""}guided_r{radius}_e{epsilon}']={
                'flip':flip,'radius':radius,'epsilon':epsilon}


def guided_filter(guide,signal,radius,epsilon):
    guide=np.asarray(guide,np.float32);signal=np.asarray(signal,np.float32)
    def mean(x):return cv2.boxFilter(x,-1,(2*radius+1,2*radius+1),borderType=cv2.BORDER_REFLECT_101)
    mi,mp=mean(guide),mean(signal)
    variance=np.maximum(mean(guide*guide)-mi*mi,0.)
    a=(mean(guide*signal)-mi*mp)/(variance+epsilon)
    b=mp-a*mi
    return mean(a)*guide+mean(b)


def native_margins(original,flipped,size,clinical=False):
    w,h=(106,80) if clinical else (320,240);x0=(320-w)//2;y0=(240-h)//2
    def margin(z):
        m=z[1]-np.max(z[[0,2,3]],axis=0)
        return cv2.resize(m[y0:y0+h,x0:x0+w],size,interpolation=cv2.INTER_LINEAR)
    return margin(original),margin((original+flipped[...,::-1])*.5)


def cpu_margins(model,photo,clinical=False):
    w,h=(106,80) if clinical else (320,240);x0=(320-w)//2;y0=(240-h)//2
    canvas=np.full((240,320,3),128,np.uint8)
    canvas[y0:y0+h,x0:x0+w]=np.asarray(photo.resize((w,h),Image.Resampling.BILINEAR))
    def forward(arr):
        x=torch.from_numpy(arr.astype(np.float32).transpose(2,0,1).copy()/255)[None]
        with torch.inference_mode():return model(x)[0].numpy()
    return native_margins(forward(canvas),forward(canvas[:,::-1]),photo.size,clinical)


def refine_margin(photo,margin,spec):
    if not spec['radius']:return margin>0
    guide=cv2.cvtColor(np.asarray(photo),cv2.COLOR_RGB2GRAY).astype(np.float32)/255
    radius=max(1,round(spec['radius']*min(photo.size)/240))
    refined=guided_filter(guide,np.clip(margin,-10,10),radius,spec['epsilon'])
    # Only ambiguous boundary logits can change. No filling or topology target.
    result=np.where(np.abs(margin)<=1.,refined,margin)
    return result>0

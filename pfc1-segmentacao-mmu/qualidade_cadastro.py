"""Indicador proprio de nitidez do cadastro; nao e medida ISO/anatomica."""
import cv2
import numpy as np

def quality(image,native_width):
    rgb=np.asarray(image,dtype=np.uint8);gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY).astype(np.float64)
    mask=(rgb>0).any(2)&(rgb.max(2)<245)&(gray>=5)
    mask=cv2.erode(mask.astype(np.uint8),np.ones((3,3),np.uint8))>0
    if mask.sum()<16:return {'score':0.,'normalized_sharpness':0.,'usable_pixels':int(mask.sum()),'native_width':float(native_width)}
    lap=cv2.Laplacian(gray,cv2.CV_64F)
    sharpness=float(lap[mask].var()/(gray[mask].var()+1.))
    resolution=float(native_width)/(float(native_width)+128.)
    return {'score':sharpness*resolution,'normalized_sharpness':sharpness,'usable_pixels':int(mask.sum()),'native_width':float(native_width)}

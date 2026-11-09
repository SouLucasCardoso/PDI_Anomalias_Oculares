"""Cobertura subpixel da isocurva zero; RGB e máscara de avaliação intactos."""
import cv2,numpy as np
from PIL import Image
from recorte_iris_sam31_alta_res import crop_box


def subpixel_crop(photo,mask,margin,padding=.08):
    rgb=np.asarray(photo);mask=np.asarray(mask,bool);margin=np.asarray(margin,np.float32)
    if mask.shape!=rgb.shape[:2] or margin.shape!=mask.shape:raise ValueError('Dimensões incompatíveis')
    if not np.isfinite(margin).all():raise ValueError('Margem não finita')
    if not mask.any():return Image.fromarray(np.dstack((rgb,np.zeros(mask.shape,np.uint8)))),(0,0,photo.width,photo.height)
    gx=cv2.Sobel(margin,cv2.CV_32F,1,0,ksize=3,scale=.125)
    gy=cv2.Sobel(margin,cv2.CV_32F,0,1,ksize=3,scale=.125)
    distance=margin/np.maximum(np.hypot(gx,gy),1e-6)
    coverage=np.clip(.5+distance,0,1)
    kernel=np.ones((3,3),np.uint8)
    inner=cv2.erode(mask.astype(np.uint8),kernel).astype(bool)
    near=cv2.dilate(mask.astype(np.uint8),kernel).astype(bool)
    coverage[inner]=1.;coverage[~near]=0.
    coverage[(margin>0)&~mask]=0.  # Components or pupil pixels removed by the binary decision stay removed.
    alpha=np.rint(coverage*255).astype(np.uint8);box=crop_box(mask,padding)
    crop=Image.fromarray(np.dstack((rgb,alpha))).crop(box)
    x0,y0,x1,y1=box
    np.testing.assert_array_equal(np.asarray(crop)[...,:3],rgb[y0:y1,x0:x1])
    return crop,box

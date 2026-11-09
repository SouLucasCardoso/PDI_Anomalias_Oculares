"""Média fixa de margens de segmentação em resoluções distintas."""
import cv2,numpy as np,torch
from PIL import Image

SPECS={'continuous':{320:1.},'tenth640':{320:.9,640:.1},
    'quarter640':{320:.75,640:.25},'half640':{320:.5,640:.5},
    'native640':{640:1.},'pyramid':{256:1/3,320:1/3,384:1/3},
    'mean384':{320:.5,384:.5}}


def margin_at_size(model,photo,width,clinical=False):
    height=width*3//4
    w,h=(round(width*106/320),round(height*80/240)) if clinical else (width,height)
    x0=(width-w)//2;y0=(height-h)//2
    canvas=np.full((height,width,3),128,np.uint8)
    canvas[y0:y0+h,x0:x0+w]=np.asarray(photo.resize((w,h),Image.Resampling.BILINEAR))
    x=torch.from_numpy(canvas.astype(np.float32).transpose(2,0,1).copy()/255)[None]
    with torch.inference_mode():scores=model(x)[0].numpy()
    margin=(scores[1]-np.max(scores[[0,2,3]],axis=0))[y0:y0+h,x0:x0+w]
    native=cv2.resize(margin,photo.size,interpolation=cv2.INTER_LINEAR)
    nearest=np.asarray(Image.fromarray(margin>0).resize(photo.size,Image.Resampling.NEAREST),bool)
    return native,nearest


def combined_mask(bank,spec):
    total=None
    for width,weight in spec.items():
        value=bank[int(width)]*weight
        total=value if total is None else total+value
    return total>0


def predict_mask(model,photo,spec,clinical=False):
    bank={int(w):margin_at_size(model,photo,int(w),clinical)[0] for w in spec}
    return combined_mask(bank,spec)

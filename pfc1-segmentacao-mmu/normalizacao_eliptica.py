"""Aproximacao geometrica assistida por mascara; nao e anatomia de referencia."""
import cv2
import numpy as np

def ellipse_endpoints(ellipse,theta):
    (cx,cy),(width,height),angle=ellipse
    a,b=width/2,height/2
    if min(a,b)<=0:raise ValueError('Nonpositive ellipse axes')
    phi=theta-np.deg2rad(angle)
    radius=1/np.sqrt((np.cos(phi)/a)**2+(np.sin(phi)/b)**2)
    return cx+radius*np.cos(theta),cy+radius*np.sin(theta)

def normalize(image,mask,pupil_fallback):
    binary=(np.asarray(mask)>0).astype(np.uint8)*255
    contours,hierarchy=cv2.findContours(binary,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_NONE)
    if hierarchy is None:raise ValueError('Empty iris mask')
    parents=hierarchy[0,:,3];outer=[i for i,p in enumerate(parents) if p<0 and len(contours[i])>=5]
    if not outer:raise ValueError('No outer contour')
    oi=max(outer,key=lambda i:cv2.contourArea(contours[i]));iris=cv2.fitEllipse(contours[oi])
    holes=[i for i,p in enumerate(parents) if p==oi and len(contours[i])>=5]
    holes=[i for i in holes if cv2.contourArea(contours[i])>=max(4,.01*cv2.contourArea(contours[oi]))]
    pupil=None;origin='circle_regressor_fallback'
    if holes:
        candidate=cv2.fitEllipse(contours[max(holes,key=lambda i:cv2.contourArea(contours[i]))])
        if max(candidate[1])<.9*max(iris[1]) and np.linalg.norm(np.array(candidate[0])-iris[0])<max(iris[1])/2:
            pupil=candidate;origin='largest_enclosed_mask_hole'
    if pupil is None:
        x,y,r=map(float,pupil_fallback);pupil=((x,y),(2*r,2*r),0.)
    values=np.array([*iris[0],*iris[1],iris[2],*pupil[0],*pupil[1],pupil[2]])
    if not np.isfinite(values).all() or min(*iris[1],*pupil[1])<=0 or max(pupil[1])>=max(iris[1]):raise ValueError('Invalid fitted ellipses')
    theta=np.arange(512)*2*np.pi/512
    px,py=ellipse_endpoints(pupil,theta);ix,iy=ellipse_endpoints(iris,theta)
    t=np.arange(1,65)[:,None]/64
    x=((1-t)*px+t*ix).astype(np.float32);y=((1-t)*py+t*iy).astype(np.float32)
    polar=cv2.remap(np.asarray(image),x,y,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
    valid=cv2.remap(binary,x,y,cv2.INTER_NEAREST,borderMode=cv2.BORDER_CONSTANT,borderValue=0)
    return polar,{'iris_ellipse':iris,'pupil_ellipse':pupil,'pupil_source':origin,'polar_mask_fraction':float((valid>0).mean())}

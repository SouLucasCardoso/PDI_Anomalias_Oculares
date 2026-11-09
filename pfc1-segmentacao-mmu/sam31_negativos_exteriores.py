"""Prompts externos conservadores; pesos oficiais SAM3.1 permanecem intactos."""
import hashlib
import cv2,numpy as np
import recorte_iris_sam31_alta_res as original


class ExteriorSam31(original.Sam31HighResolution):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.cache={};self.exterior=None;self.positive_count=16;self.first=True
    def encode(self,photo):
        key=(photo.size,hashlib.sha256(photo.tobytes()).digest())
        if key in self.cache:self.features=self.cache[key];self.size=photo.size;return
        super().encode(photo)
        if len(self.cache)<3:self.cache[key]=self.features
    def predict(self,points,labels,box):
        negative=None
        if self.first:
            self.first=False;negative=self.exterior
            if len(negative):points=np.vstack((points,negative));labels=np.r_[labels,np.zeros(len(negative),np.int32)]
        logits,quality,presence=super().predict(points,labels,box)
        if negative is not None and len(negative):
            xy=np.rint(negative).astype(int);bad=(logits[:,xy[:,1],xy[:,0]]>0).any(1)
            # Discard whole candidates that violate supplied negatives; do not edit accepted contours.
            logits[bad]=-32.
        return logits,quality,presence
    def refine_variant(self,photo,seed,count):
        self.positive_count=count;self.first=True;x0,y0,x1,y1=original.crop_box(seed);local=seed[y0:y1,x0:x1]
        yy,xx=np.where(local);diam=max(np.ptp(xx)+1,np.ptp(yy)+1);radius=max(2,round(.04*diam))
        outside=cv2.distanceTransform((~local).astype(np.uint8),cv2.DIST_L2,5)
        safe=outside>=radius;n,lab,_,_=cv2.connectedComponentsWithStats(safe.astype(np.uint8),8)
        border_ids=set(np.r_[lab[0],lab[-1],lab[:,0],lab[:,-1]])-{0}
        ring=np.isin(lab,list(border_ids))&(outside<=2*radius)&safe
        sy,sx=np.where(ring);neg=[]
        if len(sx):
            angle=np.mod(np.arctan2(sy-np.median(yy),sx-np.median(xx)),2*np.pi)
            for sector in range(8):
                ids=np.flatnonzero((angle>=sector*np.pi/4)&(angle<(sector+1)*np.pi/4))
                if len(ids):j=ids[np.argmax(outside[sy[ids],sx[ids]])];neg.append((sx[j],sy[j]))
        self.exterior=np.array(neg,np.float32).reshape(-1,2)
        previous=original.automatic_points
        def denser(mask,count=8):return previous(mask,self.positive_count)
        original.automatic_points=denser
        try:
            mask,detail=super().refine(photo,seed)
            if len(self.exterior):
                xy=np.rint(self.exterior).astype(int)
                if mask[y0+xy[:,1],x0+xy[:,0]].any():raise ValueError('Restrição negativa exterior não respeitada')
            detail.update(exterior_negative_points_xy_in_roi=self.exterior.tolist(),positive_sector_count=count)
            return mask,detail
        finally:original.automatic_points=previous
    def close(self):self.cache={};super().close()

"""SAM3.1 apenas para limbo geometrico; suporte visivel continua o da U-Net.

Elipses definem coordenadas de amostragem, nao completam a mascara ou o tecido.
"""
import cv2,numpy as np
from recorte_iris_sam31_alta_res import Sam31HighResolution,crop_box,automatic_points,retain_prompt_components
from textura_polar import prepare_texture
from preparar_polar_vermelho import red_texture
from normalizacao_eliptica import ellipse_endpoints

def polar_with_outer(rgb,support,outer):
    original,old=prepare_texture(rgb,support)
    yy,xx=np.where(support);w=int(np.ptp(xx)+1);h=int(np.ptp(yy)+1)
    x0=max(0,int(xx.min())-max(2,round(w*.5)));y0=max(0,int(yy.min())-max(2,round(h*.5)))
    x1=min(rgb.shape[1],int(xx.max())+max(2,round(w*.5))+1);y1=min(rgb.shape[0],int(yy.max())+max(2,round(h*.5))+1)
    region=rgb[y0:y1,x0:x1];binary=support[y0:y1,x0:x1].astype(np.uint8)
    gray=cv2.createCLAHE(clipLimit=2.,tileGridSize=(8,8)).apply(cv2.cvtColor(region,cv2.COLOR_RGB2GRAY))
    theta=np.arange(512)*2*np.pi/512;t=np.arange(1,65)[:,None]/64
    px,py=ellipse_endpoints(old['pupil_ellipse'],theta);ix,iy=ellipse_endpoints(outer,theta)
    ix-=x0;iy-=y0
    mx=((1-t)*px+t*ix).astype(np.float32);my=((1-t)*py+t*iy).astype(np.float32)
    visible=cv2.remap(binary,mx,my,cv2.INTER_NEAREST,borderMode=cv2.BORDER_CONSTANT,borderValue=0)>0
    if not visible.any():raise ValueError('Sem suporte polar usando limboSAM')
    outputs=[]
    for channel in (gray,region[:,:,0]):
        band=cv2.remap(channel,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE);band[~visible]=127
        outputs.append(np.repeat(band[:,:,None],3,axis=2))
    geometry={'sam_outer_ellipse_global':outer,'original_geometry':old,'visible_fraction_in_estimated_grid':float(visible.mean()),
        'support_mask_changed':False,'photograph_reconstructed':False,'pupil_geometry_changed':False}
    return outputs[0],outputs[1],geometry

class Sam31OuterGeometry(Sam31HighResolution):
    def outer_ellipse(self,photo,seed):
        x0,y0,x1,y1=crop_box(seed,.6);local=seed[y0:y1,x0:x1]
        points=automatic_points(local);self.encode(photo.crop((x0,y0,x1,y1)))
        logits,quality,presence=self.predict(points,np.ones(len(points),np.int32),crop_box(local,.1));candidates=[]
        for i,(logit,q) in enumerate(zip(logits,quality)):
            mask=logit>0;coverage=float((mask&local).sum()/local.sum());ratio=float(mask.sum()/local.sum())
            pts=np.rint(points).astype(int);match=float(mask[pts[:,1],pts[:,0]].mean())
            eligible=coverage>=.8 and .5<=ratio<=4 and match>=.875 and presence>0
            candidates.append({'index':i,'model_score_not_measured_iou':float(q),'coverage':coverage,'ratio':ratio,'prompt_match':match,'eligible':eligible})
        valid=[c for c in candidates if c['eligible']]
        if not valid:raise ValueError('SAM sem candidato geometrico consistente')
        chosen=max(valid,key=lambda c:c['model_score_not_measured_iou'])
        mask=retain_prompt_components(logits[chosen['index']]>0,points)
        contours,_=cv2.findContours(mask.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
        contour=max(contours,key=cv2.contourArea)
        if len(contour)<5:raise ValueError('Contorno SAM insuficiente para geometria')
        center,axes,angle=cv2.fitEllipse(contour)
        ys,xs=np.where(local);diam=max(np.ptp(xs)+1,np.ptp(ys)+1)
        values=np.array([*center,*axes,angle])
        if not np.isfinite(values).all() or min(axes)<=0 or min(axes)/max(axes)<.35 or max(axes)>2.5*diam:
            raise ValueError('Elipse geometrica SAM fora dos limites registrados')
        if np.hypot(center[0]-np.median(xs),center[1]-np.median(ys))>.6*diam:raise ValueError('Centro SAM inconsistente com localizacao inicial')
        ellipse=((float(center[0]+x0),float(center[1]+y0)),tuple(map(float,axes)),float(angle));self.features=None
        return ellipse,{'roi':[x0,y0,x1,y1],'candidates':candidates,'selected_index':chosen['index'],'code_revision':self.audit['code_revision']}

    def polar(self,photo,support):
        # A falha original nao e excluida nem automaticamente transformada em sucesso.
        rgb=np.asarray(photo);old,old_geometry=prepare_texture(rgb,support)
        try:
            ellipse,detail=self.outer_ellipse(photo,support);band,red,geometry=polar_with_outer(rgb,support,ellipse)
            detail.update(geometry,status='sam_outer_geometry');return band,red,detail
        except ValueError as error:
            self.features=None
            return old,red_texture(rgb,support),{'status':'original_geometry_fallback','reason':str(error),'support_mask_changed':False}

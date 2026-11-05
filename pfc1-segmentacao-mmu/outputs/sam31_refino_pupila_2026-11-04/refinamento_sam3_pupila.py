"""Refinamentos experimentais, guiados apenas por previsoes; sem referencia na inferencia."""
import cv2
import numpy as np

GUARDS = {'minimum_score': .5, 'minimum_hull_area_fraction': .005,
          'maximum_hull_area_fraction': .65, 'minimum_inside_fraction': .9,
          'minimum_aspect': .2, 'maximum_aspect': 5., 'maximum_removed_iris_fraction': .5,
          'roi_padding': .25, 'minimum_roi_support_pixels': 16,
          'minimum_roi_overlap': .5, 'minimum_roi_area_ratio': .5, 'maximum_roi_area_ratio': 1.75}


def remove_pupil(iris, masks, scores):
    iris = np.asarray(iris, bool)
    masks, scores = np.asarray(masks, bool), np.asarray(scores, float)
    if masks.shape != (len(scores), *iris.shape) or not np.isfinite(scores).all():
        raise ValueError('Candidatos de pupila desalinhados ou nao finitos')
    pupil = np.zeros_like(iris);records=[];eligible=[]
    contours,_ = cv2.findContours(iris.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hull = np.zeros_like(iris, np.uint8)
    if contours:
        cv2.drawContours(hull, [cv2.convexHull(max(contours, key=cv2.contourArea))], -1, 1, -1)
    hull = hull.astype(bool);area = int(hull.sum())
    for i,(mask,score) in enumerate(zip(masks,scores)):
        n=int(mask.sum());reason=None
        fraction=n/area if area else None
        inside=float((mask & hull).sum()/n) if n else 0.
        removed=float((mask & iris).sum()/iris.sum()) if iris.any() else 0.
        y,x=np.where(mask);aspect=(int(x.max())-int(x.min())+1)/(int(y.max())-int(y.min())+1) if n else None
        if not area or not n:reason='empty_support_or_candidate'
        elif score<=GUARDS['minimum_score']:reason='low_predicted_score'
        elif not GUARDS['minimum_hull_area_fraction']<=fraction<=GUARDS['maximum_hull_area_fraction']:reason='implausible_area'
        elif inside<GUARDS['minimum_inside_fraction']:reason='outside_iris_hull'
        elif not GUARDS['minimum_aspect']<=aspect<=GUARDS['maximum_aspect']:reason='implausible_aspect'
        elif removed>GUARDS['maximum_removed_iris_fraction']:reason='would_remove_too_much_iris'
        records.append({'index':i,'predicted_score_not_measured_iou':float(score),'pixels':n,
                        'hull_fraction':fraction,'inside_fraction':inside,'removed_iris_fraction':removed,
                        'aspect':aspect,'rejected':reason})
        if reason is None:eligible.append(i)
    chosen=max(eligible,key=lambda i:(scores[i],-i)) if eligible else None
    if chosen is not None:pupil=masks[chosen].copy()
    result=iris & ~pupil
    assert not (result & ~iris).any()
    return result,pupil,{'chosen_index':chosen,'candidates':records,'fallback_unchanged':chosen is None}


def local_box(iris):
    contours,_=cv2.findContours(np.asarray(iris,np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if not contours or int(np.count_nonzero(iris))<GUARDS['minimum_roi_support_pixels']:return None
    x,y,w,h=cv2.boundingRect(max(contours,key=cv2.contourArea))
    pad=max(2,round(GUARDS['roi_padding']*max(w,h)));height,width=iris.shape
    box=max(0,x-pad),max(0,y-pad),min(width,x+w+pad),min(height,y+h+pad)
    return box if (box[2]-box[0])*(box[3]-box[1])<.9*width*height else None


def guard_roi(iris, proposal):
    iris,proposal=np.asarray(iris,bool),np.asarray(proposal,bool)
    if iris.shape!=proposal.shape:raise ValueError('ROI desalinhada')
    n=int(iris.sum());ratio=float(proposal.sum()/n) if n else 0.
    overlap=float((iris & proposal).sum()/n) if n else 0.
    accepted=bool(n and GUARDS['minimum_roi_area_ratio']<=ratio<=GUARDS['maximum_roi_area_ratio'] and
                  overlap>=GUARDS['minimum_roi_overlap'])
    return proposal.copy() if accepted else iris.copy(),{'accepted':accepted,'area_ratio':ratio,'original_overlap':overlap}


class Sam3PupilRefiner:
    def __init__(self, semantic_checkpoint, iris_checkpoint):
        import torch
        from sam3.model.sam3_image_processor import Sam3Processor
        from avaliar_sam31_diverso import load_detector
        from segmentador_sam3_iris import IrisSam3Adapter
        self.model,self.audit=load_detector(semantic_checkpoint,'cuda')
        self.processor=Sam3Processor(self.model,device='cuda',confidence_threshold=.5)
        self.head=IrisSam3Adapter().cuda().eval()
        self.head.load_state_dict(torch.load(iris_checkpoint,map_location='cpu',weights_only=True)['model'],strict=True)

    def infer(self, rgb):
        import torch
        from PIL import Image
        if rgb.shape!=(320,416,3) or rgb.dtype!=np.uint8:raise ValueError('Entrada registrada: RGB416x320 uint8')
        with torch.inference_mode():
            with torch.autocast('cuda',dtype=torch.bfloat16):
                state=self.processor.set_image(Image.fromarray(rgb))
            feature=state['backbone_out']['vision_features'].float().half().float()
            if feature.shape!=(1,256,72,72) or not torch.isfinite(feature).all():raise ValueError('Caracteristicas SAM3 invalidas')
            x=torch.from_numpy(rgb.astype(np.float32).transpose(2,0,1).copy()/255)[None].cuda()
            iris=self.head(x,feature).argmax(1)[0].cpu().numpy()==1
            with torch.autocast('cuda',dtype=torch.bfloat16):
                output=self.processor.set_text_prompt(prompt='pupil of the eye',state=state)
            masks=output['masks'][:,0].cpu().numpy().astype(bool)
            scores=output['scores'].float().cpu().numpy()
            refined,pupil,selection=remove_pupil(iris,masks,scores)
            del output,state,feature,x
        return {'iris':iris,'corrected':refined,'pupil':pupil,'semantic_masks':masks,'selection':selection}

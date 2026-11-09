"""Refino de contorno por pontos com os pesos oficiais SAM3.1.

Reutiliza estritamente o backbone e a cabeca interativa do checkpoint multiplex.
Nao utiliza diagnostico, mascara de referencia, elipse imposta ou textura gerada.
"""
from pathlib import Path
import gc,hashlib,json
import cv2
import numpy as np
from PIL import Image
import torch
from torch.nn import functional as F

ROOT=Path(__file__).resolve().parent
REVISION='f1647e8d0c1d280991f4d1b7d974c2704537fe66'
CHECKPOINT_REVISION='daa63191845a41281374e725f4c9e51c7a824460'

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def crop_box(mask,margin=.45):
    ys,xs=np.where(mask)
    if len(xs)<16:raise ValueError('Localizacao inicial insuficiente para refinar')
    h,w=mask.shape;pad=round(max(xs.max()-xs.min()+1,ys.max()-ys.min()+1)*margin)
    return max(0,int(xs.min())-pad),max(0,int(ys.min())-pad),min(w,int(xs.max())+1+pad),min(h,int(ys.max())+1+pad)

def automatic_points(mask,count=8):
    """Pontos internos por setores, sem inventar um centro anatomico."""
    distance=cv2.distanceTransform(mask.astype(np.uint8),cv2.DIST_L2,5)
    yy,xx=np.where(distance>max(1,float(distance.max())*.18))
    if not len(xx):raise ValueError('Mascara inicial sem interior confiavel')
    cx,cy=np.median(xx),np.median(yy)
    angle=np.mod(np.arctan2(yy-cy,xx-cx),2*np.pi)
    points=[]
    for i in range(count):
        eligible=(angle>=i*2*np.pi/count)&(angle<(i+1)*2*np.pi/count)
        if eligible.any():
            positions=np.flatnonzero(eligible);j=positions[np.argmax(distance[yy[positions],xx[positions]])]
            points.append((int(xx[j]),int(yy[j])))
    return np.array(points,np.float32)

def enclosed_pupil_seed(mask):
    """Somente buraco interno observado; nao rotula fundo aberto como pupila."""
    n,labels,stats,centers=cv2.connectedComponentsWithStats((~mask).astype(np.uint8),8)
    h,w=mask.shape;options=[]
    for i in range(1,n):
        x,y,bw,bh,area=stats[i]
        if x==0 or y==0 or x+bw==w or y+bh==h:continue
        if area>=max(9,.008*mask.sum()) and area<.5*mask.sum():options.append(i)
    if not options:return None
    i=max(options,key=lambda j:int(stats[j,4]))
    return labels==i

def retain_prompt_components(mask,points):
    """Descarta objetos desconectados que nao contêm nenhum ponto de iris."""
    n,labels,stats,_=cv2.connectedComponentsWithStats(mask.astype(np.uint8),8)
    if n<=1:return mask
    pts=np.rint(points).astype(int)
    ids=set(labels[pts[:,1],pts[:,0]])-{0}
    if not ids:raise ValueError('Nenhum componente corresponde aos pontos internos')
    return np.isin(labels,list(ids))

def dark_pupil_seed(photo,outer,coarse_iris):
    """Localizador conservador por intensidade; a forma final continua prevista pelo SAM."""
    gray=cv2.cvtColor(np.asarray(photo),cv2.COLOR_RGB2GRAY)
    yy,xx=np.where(outer)
    if not len(xx):return None
    cx,cy=float(np.median(xx)),float(np.median(yy));diam=max(np.ptp(xx)+1,np.ptp(yy)+1)
    distance=cv2.distanceTransform(outer.astype(np.uint8),cv2.DIST_L2,5)
    interior=outer&(distance>.06*diam)
    options=[]
    for threshold in (35,50,65,80):
        # Pontos escuros que a U-Net ja chama de iris podem ser criptas, nao pupila.
        n,labels,stats,centers=cv2.connectedComponentsWithStats((interior&~coarse_iris&(gray<threshold)).astype(np.uint8),8)
        for j in range(1,n):
            area=int(stats[j,4]);dx,dy=centers[j]-[cx,cy];offset=float(np.hypot(dx,dy)/diam)
            if .003*outer.sum()<=area<=.35*outer.sum() and offset<.22:
                options.append((offset-.5*np.sqrt(area/outer.sum()),labels==j))
    return min(options,key=lambda x:x[0])[1] if options else None

def antialiased_crop(photo,mask,padding=.08):
    """RGB nativo intacto; transicao alfa de apenas um pixel na exibicao."""
    if not mask.any():return Image.new('RGBA',(photo.width,photo.height))
    box=crop_box(mask,padding);rgb=np.asarray(photo)
    inner=cv2.distanceTransform(mask.astype(np.uint8),cv2.DIST_L2,3)
    outer=cv2.distanceTransform((~mask).astype(np.uint8),cv2.DIST_L2,3)
    alpha=np.rint(np.clip(.5+(inner-outer)/2,0,1)*255).astype(np.uint8)
    rgba=np.dstack((rgb,alpha));return Image.fromarray(rgba).crop(box)

class Sam31HighResolution:
    def __init__(self,device='cuda'):
        from sam3.model_builder import _create_multiplex_tri_backbone
        from sam3.model.vl_combiner import TriHeadVisionOnly
        from sam3.sam.prompt_encoder import PromptEncoder
        from sam3.sam.mask_decoder import MaskDecoder
        from sam3.sam.transformer import TwoWayTransformer
        import importlib.metadata
        origin=json.loads(importlib.metadata.distribution('sam3').read_text('direct_url.json'))
        if REVISION not in json.dumps(origin):raise ValueError('Revisao SAM3 diferente da verificada')
        registered=json.loads((ROOT/'outputs/sam31_atual_prompts_2026-11-03/protocolo.json').read_text())
        file=Path(registered['checkpoint'])
        if sha(file)!=registered['checkpoint_sha256']:raise ValueError('Checkpoint SAM3.1 alterado')
        state=torch.load(file,map_location='cpu',weights_only=True,mmap=True);state=state.get('model',state)
        self.backbone=TriHeadVisionOnly(visual=_create_multiplex_tri_backbone(),n_features=256,scalp=0)
        self.prompt=PromptEncoder(embed_dim=256,image_embedding_size=(72,72),input_image_size=(1008,1008),mask_in_chans=16)
        self.decoder=MaskDecoder(transformer_dim=256,transformer=TwoWayTransformer(depth=2,embedding_dim=256,mlp_dim=2048,num_heads=8),
            num_multimask_outputs=3,iou_head_depth=3,iou_head_hidden_dim=256,use_high_res_features=True,
            iou_prediction_use_sigmoid=False,pred_obj_scores=True,pred_obj_scores_mlp=True,use_multimask_token_for_obj_ptr=True,
            dynamic_multimask_via_stability=True,dynamic_multimask_stability_delta=.05,dynamic_multimask_stability_thresh=.98)
        used={}
        for name,module,prefix in [('backbone',self.backbone.vision_backbone,'detector.backbone.vision_backbone.'),
                 ('prompt',self.prompt,'tracker.model.interactive_sam_prompt_encoder.'),
                 ('decoder',self.decoder,'tracker.model.interactive_sam_mask_decoder.')]:
            weights={k.removeprefix(prefix):v for k,v in state.items() if k.startswith(prefix)}
            report=module.load_state_dict(weights,strict=True)
            used[name]={'tensors':len(weights),'missing':report.missing_keys,'unexpected':report.unexpected_keys}
        self.no_mem=state['tracker.model.interactivity_no_mem_embed'].clone().reshape(1,256,1,1)
        del state;gc.collect()
        self.device=torch.device(device)
        for module in (self.backbone,self.prompt,self.decoder):module.requires_grad_(False).eval().to(self.device)
        self.no_mem=self.no_mem.to(self.device)
        self.audit={'family':'SAM3.1','code_revision':REVISION,'checkpoint_revision':CHECKPOINT_REVISION,
                    'checkpoint_sha256':registered['checkpoint_sha256'],'strict_components':used,
                    'random_missing_weights_used':False,'image_encoder_resolution':1008,
                    'scope':'Official interactive image path only; no language, tracking, propagation or newly trained parameters.'}

    @torch.inference_mode()
    def encode(self,photo):
        pixels=np.asarray(photo.resize((1008,1008),Image.Resampling.BILINEAR)).copy()
        x=torch.from_numpy(pixels.transpose(2,0,1)).float()[None].to(self.device)/127.5-1
        with torch.autocast(self.device.type,dtype=torch.bfloat16,enabled=self.device.type=='cuda'):
            encoded=self.backbone.forward_image(x,need_sam3_out=False,need_interactive_out=True,need_propagation_out=False)['interactive']
            f=[v.tensors for v in encoded['backbone_fpn']]
            self.features=(f[-1]+self.no_mem,[self.decoder.conv_s0(f[0]),self.decoder.conv_s1(f[1])])
        self.size=photo.size

    @torch.inference_mode()
    def predict(self,points,labels,box):
        w,h=self.size;scale=np.array([1008/w,1008/h],np.float32)
        pts=torch.from_numpy(np.array(points,np.float32)*scale)[None].to(self.device)
        labs=torch.from_numpy(np.array(labels,np.int32))[None].to(self.device)
        b=torch.from_numpy(np.array(box,np.float32).reshape(2,2)*scale)[None].to(self.device)
        with torch.autocast(self.device.type,dtype=torch.bfloat16,enabled=self.device.type=='cuda'):
            sparse,dense=self.prompt(points=(pts,labs),boxes=b,masks=None)
            masks,scores,_,obj=self.decoder(image_embeddings=self.features[0],image_pe=self.prompt.get_dense_pe(),
                sparse_prompt_embeddings=sparse,dense_prompt_embeddings=dense,multimask_output=True,repeat_image=True,high_res_features=self.features[1])
            native=F.interpolate(masks.float(),(h,w),mode='bilinear',align_corners=False)[0].cpu().numpy()
        # Filtrar logits antes de decidir o rotulo evita ilhas da grade de decodificacao.
        # Suporte local <=2 pixels nativos; nao fecha lacunas nem impoe forma anatomica.
        sigma=min(2.,max(w,h)/1008*.7)
        native=np.stack([cv2.GaussianBlur(m,(0,0),sigmaX=sigma) for m in native])
        return native,scores[0].float().cpu().numpy(),float(obj.flatten()[0])

    def refine(self,photo,seed):
        if seed.shape!=(photo.height,photo.width):raise ValueError('Foto e mascara inicial incompatíveis')
        x0,y0,x1,y1=crop_box(seed);roi=photo.crop((x0,y0,x1,y1));local=seed[y0:y1,x0:x1]
        points=automatic_points(local);pupil=enclosed_pupil_seed(local)
        positive=len(points);labels=np.ones(positive,np.int32)
        box=crop_box(local,.08);self.encode(roi)
        logits,quality,presence=self.predict(points,labels,box)
        candidates=[]
        for i,(logit,q) in enumerate(zip(logits,quality)):
            mask=logit>0;intersection=int((mask&local).sum());coverage=intersection/max(1,int(local.sum()))
            ratio=float(mask.sum()/max(1,local.sum()))
            prompt_match=float(np.mean(mask[np.rint(points[:,1]).astype(int),np.rint(points[:,0]).astype(int)]==(labels>0)))
            eligible=coverage>=.5 and .35<=ratio<=4 and prompt_match>=.85
            value=float(q)+.1*coverage+.1*prompt_match if eligible else -1e6
            candidates.append({'index':i,'model_quality_not_measured_iou':float(q),'seed_coverage':coverage,
                               'area_ratio_to_seed':ratio,'prompt_match':prompt_match,'eligible':eligible,'selection_score':value})
        selected=max(candidates,key=lambda x:x['selection_score'])
        if not selected['eligible']:raise ValueError('Refino SAM3.1 sem candidato confiavel; preservar captura para revisão')
        prediction=retain_prompt_components(logits[selected['index']]>0,points)
        pupil_origin='enclosed_coarse_hole'
        if pupil is None:
            pupil=dark_pupil_seed(roi,prediction,local);pupil_origin='native_intensity_and_coarse_background_localizer'
        pupil_detail={'status':'no_enclosed_seed'}
        pupil_logits=None
        if pupil is not None:
            distance=cv2.distanceTransform(pupil.astype(np.uint8),cv2.DIST_L2,5)
            cy,cx=np.unravel_index(np.argmax(distance),distance.shape);center=np.array([[cx,cy]],np.float32)
            # Segunda codificacao local: a pupila deixa de ocupar poucos pixels do encoder.
            px0,py0,px1,py1=crop_box(pupil,.8)
            nearby=local[py0:py1,px0:px1]
            negative=automatic_points(nearby) if nearby.sum()>=16 else np.empty((0,2),np.float32)
            offset=np.array([px0,py0],np.float32)
            pupil_points=np.vstack((center-offset,negative));pupil_labels=np.r_[1,np.zeros(len(negative),np.int32)]
            self.encode(roi.crop((px0,py0,px1,py1)))
            pbox=np.array(crop_box(pupil,.1),np.float32)-np.tile(offset,2)
            zoom_logits,pquality,ppresence=self.predict(pupil_points,pupil_labels,pbox)
            plogits=np.full((3,*local.shape),-32.,np.float32)
            plogits[:,py0:py1,px0:px1]=zoom_logits
            pupil_points_global=pupil_points+offset
            pcandidates=[]
            for i,(logit,q) in enumerate(zip(plogits,pquality)):
                pm=logit>0;area=int(pm.sum());ratio=area/max(1,int(pupil.sum()))
                inside=float((pm&prediction).sum()/max(1,area))
                center_in=bool(pm[round(float(center[0,1])),round(float(center[0,0]))])
                ng=pupil_points_global[1:]
                negative_ok=not bool(pm[np.rint(ng[:,1]).astype(int),np.rint(ng[:,0]).astype(int)].any())
                maxratio=5 if pupil_origin=='enclosed_coarse_hole' else 15
                eligible=bool(center_in and negative_ok and .3<=ratio<=maxratio and inside>=.9 and area<.6*prediction.sum())
                pcandidates.append({'index':i,'model_quality_not_measured_iou':float(q),'area_ratio_to_seed':ratio,
                                    'inside_iris_fraction':inside,'negative_iris_points_respected':negative_ok,'eligible':eligible})
            valid=[v for v in pcandidates if v['eligible']]
            if valid:
                chosen=max(valid,key=lambda v:v['model_quality_not_measured_iou'])
                pupil_mask=retain_prompt_components(plogits[chosen['index']]>0,center)
                prediction &= ~pupil_mask
                pupil_detail={'status':'sam31_refined','seed_origin':pupil_origin,'selected_index':chosen['index'],'candidates':pcandidates,
                              'zoom_xyxy_in_roi':[px0,py0,px1,py1],
                              'points_xy_in_roi':pupil_points_global.tolist(),'point_labels':pupil_labels.tolist()}
            else:
                if pupil_origin=='enclosed_coarse_hole':prediction &= ~pupil
                pupil_detail={'status':'no_eligible_sam_pupil','seed_origin':pupil_origin,'candidates':pcandidates}
        prediction=retain_prompt_components(prediction,points)
        full=np.zeros(seed.shape,bool);full[y0:y1,x0:x1]=prediction
        self.features=None
        return full,{'roi_xyxy':[x0,y0,x1,y1],'points_xy_in_roi':points.tolist(),'point_labels':labels.tolist(),
                     'automatic_pupil_seed':pupil is not None,'pupil_refinement':pupil_detail,
                     'candidates':candidates,'selected_index':selected['index'],
                     'presence_logit':presence,'manual_or_reference_prompts':False,'morphological_hole_filling':False,
                     'forced_circle_or_ellipse':False,'rgb_texture_modified':False,
                     'disconnected_objects_without_iris_points_removed':True}

    def close(self):
        for module in (self.backbone,self.prompt,self.decoder):module.cpu()
        self.features=None
        if self.device.type=='cuda':torch.cuda.empty_cache()

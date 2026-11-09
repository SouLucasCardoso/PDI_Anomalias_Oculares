"""Seis consultas fixas de validacao, tres condicoes, sem ajuste por referencia."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json
import cv2,numpy as np,torch
from PIL import Image,ImageDraw,ImageFont,ImageOps
from geometria_polar_sam31 import Sam31OuterGeometry
from recorte_iris_sam31_alta_res import sha
from avaliar_robustez_reconhecimento import load_splits,perturb
from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
from textura_polar import prepare_texture
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();out=a.output_dir;out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(4);cv2.setNumThreads(1)
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());rows=load_splits(manifest)['val'];queries=[r for r in rows if r.session==2]
    people=sorted({r.subject for r in queries})[:6];selected=[next(r for r in sorted(queries,key=lambda r:r.image) if r.subject==s) for s in people]
    conditions=(('original',0),('oclusao_superior',10),('oclusao_inferior',10))
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Geometric feasibility pilot only, no identity metrics or clinical conclusions; keep all6preselected casesx3conditions',
        'selection':'First sorted session2image of first6sorted eligible validation people, before predictions',
        'rows':[r.image for r in selected],'conditions':conditions,'sources_sha256':{n:sha(ROOT/n) for n in ('piloto_geometria_sam31.py','geometria_polar_sam31.py','recorte_iris_sam31_alta_res.py')},
        'official_verification':{'date':'2026-11-08','github_head':'f1647e8d0c1d280991f4d1b7d974c2704537fe66','hf_revision':'daa63191845a41281374e725f4c9e51c7a824460',
            'github_api':'https://api.github.com/repos/facebookresearch/sam3/commits/main','hf_api':'https://huggingface.co/api/models/facebook/sam3.1'},
        'method':'Original nearest U-Net support and original pupil geometry unchanged. SAM3.1 interactive outer contour only defines limbus sampling ellipse. Native source pixels, no filling of mask or photograph. Failed geometry uses original; original empty support retained as failure.'}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    unet=MulticlassUNet(8).cuda().eval();unet.load_state_dict(torch.load(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt',map_location='cpu',weights_only=True)['model'])
    items=[]
    for row in selected:
        photo=Image.open(row.image).convert('RGB');reference=decode_mask(Image.open(row.mask))==1
        for condition,level in conditions:
            im=photo if condition=='original' else perturb(photo,reference,condition,level)[0]
            x=torch.from_numpy(np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32).transpose(2,0,1).copy()/255)[None].cuda()
            with torch.inference_mode():small=unet(x).argmax(1)[0].cpu().numpy()==1
            support=np.asarray(Image.fromarray(small).resize(im.size,Image.Resampling.NEAREST),bool)
            items.append((row,condition,im,support))
    del unet;torch.cuda.empty_cache();sam=Sam31OuterGeometry();records=[]
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
    for group in range(3):
        board=Image.new('RGB',(1480,70+6*210),'white');draw=ImageDraw.Draw(board)
        for col,title in enumerate(('Original e suporte','Limbo SAM geometrico','Polar anterior','Polar SAM')):draw.text((col*370+5,5),title,font=font,fill='black')
        for j,(row,condition,im,support) in enumerate(items[group*6:(group+1)*6]):
            y=55+j*210;draw.text((5,y-25),Path(row.image).stem+' '+condition,font=font,fill='black');rgb=np.asarray(im).copy();overlay=rgb.copy();overlay[support]=(.65*rgb[support]+.35*np.array([0,220,100])).astype(np.uint8)
            try:
                old,_=prepare_texture(rgb,support);new,red,detail=sam.polar(im,support)
                if detail['status']=='sam_outer_geometry':cv2.ellipse(rgb,detail['sam_outer_ellipse_global'],(255,0,0),2)
            except ValueError as error:old=new=Image.new('RGB',(512,64),'gray');detail={'status':'invalid_original_support','reason':str(error)}
            for col,panel in enumerate((Image.fromarray(overlay),Image.fromarray(rgb),Image.fromarray(old) if isinstance(old,np.ndarray) else old,Image.fromarray(new) if isinstance(new,np.ndarray) else new)):
                board.paste(ImageOps.pad(panel,(355,175),color='white'),(col*370+5,y))
            records.append({'image':Path(row.image).name,'condition':condition,'support_pixels':int(support.sum()),'detail':detail})
        board.save(out/f'comparacao_geometria_{group+1}.png')
    sam.close();result={'records':records,'strict_sam_audit':sam.audit,'identity_reevaluated':False,'clinical_gt_available':False,'sam_geometry_count':sum(r['detail']['status']=='sam_outer_geometry' for r in records)}
    (out/'CONCLUIDO.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ('records','strict_sam_audit')}))

if __name__=='__main__':main()

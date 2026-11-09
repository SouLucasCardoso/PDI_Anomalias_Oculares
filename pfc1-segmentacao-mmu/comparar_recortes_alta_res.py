"""Compara recortes reais anteriores com refino SAM3.1 interativo automatico."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,time
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageOps,ImageFont
import torch
from recorte_iris_sam31_alta_res import Sam31HighResolution,sha,antialiased_crop
from treinar_segmentacao_ubipr import MulticlassUNet
from segmentacao_clinica_escala import predict_clinical

ROOT=Path(__file__).resolve().parent
NAMES=('P0005_OD20241206.JPG','P0007_OS20250306.JPG','P0209_OD20250329.JPG',
       'P0564_OD20250526.JPG','P0114_OS20250417.JPG','P0803_OD20250112.JPG')

def mask_stats(mask):
    n,_,stats,_=cv2.connectedComponentsWithStats(mask.astype(np.uint8),8)
    return {'pixels':int(mask.sum()),'components':n-1,'components_ge_100px':int((stats[1:,4]>=100).sum())}

def composite(photo,mask):
    rgb=np.asarray(photo).copy();rgb[mask]=(.65*rgb[mask]+.35*np.array([0,220,100])).astype(np.uint8)
    return Image.fromarray(rgb)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--limit',type=int,default=6);p.add_argument('--device',default='cuda');a=p.parse_args()
    out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(2);cv2.setNumThreads(1)
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'images':NAMES[:a.limit],
        'method':'SAM3.1 official interactive neck/prompt/mask heads,1008encoder; automatic iris points from frozen U-Net coarse1/3, original RGB localizer fallback ifempty; separate zoomed pupil encoder from enclosedhole or conservative native-intensity locator, with nearby coarse-iris negative points; native bilinear logits and Gaussian sigma<=2 native pixels before threshold; discard disconnected objects lacking iris points before/after pupil subtraction; no holefilling or forcedellipse.',
        'selection':'Automatic model confidence and seed/prompt consistency, no clinical reference or diagnosis in inference.',
        'scope':'Clinical qualitative development only; segmentation/recognition metrics of frozen experiments unchanged. All six predetermined cases retained.',
        'sources_sha256':{n:sha(ROOT/n) for n in ('comparar_recortes_alta_res.py','recorte_iris_sam31_alta_res.py','segmentacao_clinica_escala.py')},
        'no_generative_editing':True,'no_texture_inpainting':True,'clinical_ground_truth_available':False}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    rows=json.loads((ROOT/'data/slpvld/manifesto.json').read_text(encoding='utf-8-sig'))
    rows=[next(r for r in rows if Path(r['image']).name==name) for name in NAMES[:a.limit]]
    photos=[Image.open(r['image']).convert('RGB') for r in rows]
    unet=MulticlassUNet(8).eval();file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    assert sha(file)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    unet.load_state_dict(torch.load(file,map_location='cpu',weights_only=True)['model'])
    seeds=predict_clinical(photos,unet,'cpu')
    previous=[s.copy() for s in seeds]
    # Sem localizacao1/3, tentar somente a localizacao RGB original; sem usar diagnostico.
    for i,(photo,mask) in enumerate(zip(photos,seeds)):
        if not mask.any():
            x=torch.from_numpy(np.asarray(photo.resize((320,240)),np.float32).transpose(2,0,1).copy()/255)[None]
            with torch.inference_mode():m=unet(x).argmax(1)[0].numpy()==1
            seeds[i]=np.asarray(Image.fromarray(m).resize(photo.size,Image.Resampling.NEAREST),bool)
    del unet
    print('Carregando cabeca interativa SAM3.1 estritamente...',flush=True)
    refiner=Sam31HighResolution(a.device)
    (out/'carregamento_estrito.json').write_text(json.dumps(refiner.audit,indent=2),encoding='utf-8')
    records=[];boards=[];start=time.monotonic()
    for row,photo,seed,old_mask in zip(rows,photos,seeds,previous):
        name=Path(row['image']).stem;folder=out/name;folder.mkdir()
        try:new,detail=refiner.refine(photo,seed);status='refined'
        except ValueError as error:new=seed;detail={'reason':str(error)};status='preserved_initial_failed_refinement'
        if not old_mask.any():
            Image.fromarray(new.astype(np.uint8)*255).save(folder/'mask_candidata_nao_aprovada.png')
            detail['empty_initial_requires_manual_localization_review']=True
            new=old_mask.copy();status='review_required_empty_initial'
        Image.fromarray(old_mask.astype(np.uint8)*255).save(folder/'mask_anterior.png')
        Image.fromarray(seed.astype(np.uint8)*255).save(folder/'mask_localizacao.png')
        Image.fromarray(new.astype(np.uint8)*255).save(folder/'mask_nativa.png')
        antialiased_crop(photo,new).save(folder/'recorte_nativo.png')
        raw=np.asarray(photo).copy();raw[~old_mask]=0
        old=Image.fromarray(raw)
        if old_mask.any():
            yy,xx=np.where(old_mask);old=old.crop((xx.min(),yy.min(),xx.max()+1,yy.max()+1))
        boards.append((name,photo,composite(photo,old_mask),composite(photo,new),old,antialiased_crop(photo,new)))
        record={'filename':Path(row['image']).name,'diagnosis_dataset_only':row['diagnosis_raw'],'status':status,
                'image_sha256':sha(row['image']),'previous':mask_stats(old_mask),'localizer':mask_stats(seed),'new':mask_stats(new),
                'details':detail,'native_mask_sha256':sha(folder/'mask_nativa.png'),'crop_sha256':sha(folder/'recorte_nativo.png')}
        records.append(record);(folder/'metadados.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
        print(json.dumps({'image':name,'status':status,'previous':record['previous'],'new':record['new'],'seconds':time.monotonic()-start}),flush=True)
    refiner.close()
    font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
    width,height=3000,80+len(boards)*430
    canvas=Image.new('RGB',(width,height),'white');draw=ImageDraw.Draw(canvas)
    for i,title in enumerate(('Original','Máscara anterior','SAM3.1 refinado','Recorte anterior','Recorte refinado')):
        draw.text((i*600+8,8),title,font=font(40),fill='black')
    for i,(name,*panels) in enumerate(boards):
        y=65+i*430;draw.text((8,y),name,font=font(30),fill='black')
        for j,panel in enumerate(panels):
            if panel.mode=='RGBA':
                bg=Image.new('RGBA',panel.size,'black');bg.alpha_composite(panel);panel=bg.convert('RGB')
            canvas.paste(ImageOps.pad(panel,(580,370),method=Image.Resampling.LANCZOS,color='white'),(j*600+8,y+40))
    canvas.save(out/'comparacao_antes_depois.png',dpi=(300,300))
    (out/'CONCLUIDO.json').write_text(json.dumps({'records':records,'clinical_dice':None,'recognition_reevaluated':False,
        'method_audit':refiner.audit,'figure_sha256':sha(out/'comparacao_antes_depois.png')},indent=2,ensure_ascii=False),encoding='utf-8')
    print('Comparacao concluida.',flush=True)

if __name__=='__main__':main()

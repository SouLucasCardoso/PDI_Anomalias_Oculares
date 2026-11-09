"""Recorte de foto local com contorno continuo, sem gerar ou retocar textura."""
from pathlib import Path
import argparse,json
import numpy as np
import torch
from PIL import Image,ImageOps,ImageDraw,ImageFont
from avaliar_contorno_continuo import continuous_mask
from recorte_iris_sam31_alta_res import Sam31HighResolution,antialiased_crop,sha
from treinar_segmentacao_ubipr import MulticlassUNet
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--image',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--clinical-scale',action='store_true',help='Controle historico1/3 para fotografia clinica ampliada')
    p.add_argument('--sam31-experimental',action='store_true',help='Refino interativo ilustrativo; inferior na validacao, nao aprovado para identificar')
    a=p.parse_args();a.output_dir.mkdir(parents=True,exist_ok=False);torch.set_num_threads(2)
    photo=Image.open(a.image).convert('RGB');model=MulticlassUNet(8).eval()
    checkpoint=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
    old,mask=continuous_mask(model,photo,a.clinical_scale);del model
    detail={'method':'continuous iris-vs-other-class logit margin interpolated before native threshold0','clinical_scale':a.clinical_scale}
    if a.sam31_experimental:
        sam=Sam31HighResolution()
        try:mask,refinement=sam.refine(photo,mask);detail.update(refinement);detail['model_audit']=sam.audit
        finally:sam.close()
    Image.fromarray(mask.astype(np.uint8)*255).save(a.output_dir/'mascara_nativa.png')
    antialiased_crop(photo,mask).save(a.output_dir/'recorte_nativo.png')
    canvas=Image.new('RGB',(1800,650),'white');draw=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',34)
    for col,(title,m) in enumerate((('Anterior: rotulo ampliado',old),('Novo: confianca interpolada',mask))):
        crop=antialiased_crop(photo,m);background=Image.new('RGBA',crop.size,'black');background.alpha_composite(crop)
        draw.text((col*900+12,12),title,font=font,fill='black');canvas.paste(ImageOps.pad(background.convert('RGB'),(880,580),method=Image.Resampling.LANCZOS),(col*900+10,60))
    canvas.save(a.output_dir/'comparacao.png')
    detail.update({'photo_sha256':sha(a.image),'unet_sha256':sha(checkpoint),'script_sha256':sha(__file__),
        'mask_sha256':sha(a.output_dir/'mascara_nativa.png'),'native_rgb_unchanged':True,'display_alpha_edge_only':True,
        'recognition_recalibrated':False,'manual_clinical_review_required':True})
    (a.output_dir/'proveniencia.json').write_text(json.dumps(detail,indent=2,ensure_ascii=False),encoding='utf-8')
    print(a.output_dir.resolve())

if __name__=='__main__':main()

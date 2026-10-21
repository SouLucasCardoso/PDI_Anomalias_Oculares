"""Prancha auditavel de quatro consultas reais, sem selecao por desempenho."""
from pathlib import Path
import argparse,hashlib,json,tempfile
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps
import torch
ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_robustez_reconhecimento import load_splits
    from treinar_segmentacao_ubipr import MulticlassUNet
    from avaliar_dinov3_ubipr import masked_crop
    from preparar_polar_vermelho import red_texture
    from textura_polar import prepare_texture
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True)
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val']
    valid=np.load(ROOT/'data/cache_identidade_automatica_2026-10-20/val_valid.npy');selected=[];seen=set()
    for i,r in enumerate(rows):
        if r.session==2 and valid[i] and r.subject not in seen:selected.append(i);seen.add(r.subject)
        if len(selected)==4:break
    checkpoint=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');torch.set_num_threads(4)
    model=MulticlassUNet(8).to(device).eval();model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
    font=lambda size:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',size)
    canvas=Image.new('RGB',(1800,1530),'#f3f5f7');draw=ImageDraw.Draw(canvas)
    draw.text((30,20),'Recortes reais de íris — estado do processamento em 21/10/2026',font=font(32),fill='#172333')
    draw.text((30,68),'UBIPr • quatro consultas da sessão 2 • pessoas distintas • seleção pela ordem do manifesto, sem usar escores',font=font(21),fill='#425369')
    xs=[30,385,740,1005,1270];widths=[335,335,245,245,500]
    headers=['Foto original','Máscara automática (verde)','Entrada RGB 128 × 128','Entrada RGB 224 × 224','Faixas polares 512 × 64']
    for x,h in zip(xs,headers):draw.text((x,112),h,font=font(21),fill='#172333')
    metadata=[]
    for n,i in enumerate(selected):
        r=rows[i];source=ROOT/'data/ubipr/single_eye'/Path(r.image).name
        with Image.open(source) as im:original=im.convert('RGB')
        x=torch.from_numpy((np.asarray(original.resize((320,240),Image.Resampling.BILINEAR),dtype=np.float32)/255).transpose(2,0,1).copy())[None].to(device)
        with torch.inference_mode():mask=model(x).argmax(1)[0].cpu().numpy()==1
        mask=np.asarray(Image.fromarray(mask).resize(original.size,Image.Resampling.NEAREST),dtype=bool);assert mask.any()
        rgb=np.asarray(original);overlay=rgb.copy();overlay[mask]=(.60*rgb[mask]+.40*np.array([0,255,70])).astype(np.uint8)
        crop=masked_crop(original,mask);c128=crop.resize((128,128),Image.Resampling.BILINEAR);c224=crop.resize((224,224),Image.Resampling.BILINEAR)
        polar,geometry=prepare_texture(rgb,mask);red=red_texture(rgb,mask)
        top=160+n*310
        draw.text((30,top),f'Amostra {n+1} — {source.name}',font=font(20),fill='#172333')
        for xx,w,img in zip(xs[:4],widths[:4],[original,Image.fromarray(overlay),c128,c224]):
            frame=ImageOps.pad(img,(w,235),method=Image.Resampling.BILINEAR,color='white');canvas.paste(frame,(xx,top+32))
        draw.text((1270,top+32),'Contraste local (CLAHE)',font=font(18),fill='#425369');canvas.paste(Image.fromarray(polar).resize((500,63)),(1270,top+61))
        draw.text((1270,top+145),'Canal vermelho, sem CLAHE',font=font(18),fill='#425369');canvas.paste(Image.fromarray(red).resize((500,63)),(1270,top+174))
        metadata.append({'manifest_index':i,'image':source.name,'subject':r.subject,'session':r.session,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'geometry':geometry})
    draw.text((30,1420),'Preto: exterior removido no recorte RGB. Cinza: suporte excluído nas faixas polares. Reflexos e oclusões naturais permanecem.',font=font(21),fill='#425369')
    draw.text((30,1454),'Ampliação apenas para exibição; recortes calculados diretamente do original. As amostras não demonstram acerto de identidade.',font=font(21),fill='#425369')
    name='AMOSTRAS_RECORTES_IRIS_2026-10-21';canvas.save(a.output_dir/(name+'.png'))
    audit={'selection':'First valid session2 image of first4 distinct subjects in validation manifest; no recognition scores used','segmentation_checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),'samples':metadata,'display':'RGB inputs128 and224 displayed at same panel size, polar resized only for layout; no synthetic texture, no reference masks'}
    (a.output_dir/(name+'.json')).write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding='utf-8');print(a.output_dir/(name+'.png'))

if __name__=='__main__':main()

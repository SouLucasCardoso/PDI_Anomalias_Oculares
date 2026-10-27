"""Prancha documental: rotulos Normal eye e alteracoes da iris, mesma base."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps
import torch
from treinar_segmentacao_ubipr import MulticlassUNet
from avaliar_dinov3_ubipr import masked_crop
from segmentacao_clinica_escala import predict_clinical
ROOT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,default=ROOT.parent/'Relatórios-de-Avanço');a=p.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True)
    rows=json.loads((ROOT/'data/slpvld/manifesto.json').read_text());selected=[];seen=set()
    for r in sorted(rows,key=lambda r:Path(r['image']).name):
        if r['diagnosis_raw']=='Normal eye' and r['source_split']=='development' and r['subject'] not in seen:
            selected.append(r);seen.add(r['subject'])
            if len(selected)==2:break
    for name in ['P0114_OS20250417.JPG','P0803_OD20250112.JPG']:selected.append(next(r for r in rows if Path(r['image']).name==name))
    assert len(selected)==4
    checkpoint=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';assert sha(checkpoint)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    torch.set_num_threads(4);device='cuda' if torch.cuda.is_available() else 'cpu';model=MulticlassUNet(8).to(device).eval();model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
    photos=[Image.open(r['image']).convert('RGB') for r in selected];x=torch.from_numpy(np.stack([np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for im in photos]).transpose(0,3,1,2).copy()).to(device)
    with torch.inference_mode():small=model(x).argmax(1).cpu().numpy()==1
    original=[np.asarray(Image.fromarray(m).resize(im.size,Image.Resampling.NEAREST),bool) for m,im in zip(small,photos)];scaled=predict_clinical(photos,model,device)
    font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
    canvas=Image.new('RGB',(1800,1330),'#f3f5f7');draw=ImageDraw.Draw(canvas)
    draw.text((25,20),'Recortes oculares: Normal eye e alterações da íris — SLP-VLD',font=font(31),fill='#172333')
    draw.text((25,65),'Rótulos da base; máscaras previstas pela mesma U-Net. Controle de escala sem trocar pesos. 27/10/2026.',font=font(21),fill='#425369')
    xs=[25,440,795,1050,1405];widths=[395,335,235,335,365]
    for x,title in zip(xs,['Foto original','Máscara original','Recorte original','Máscara: escala 1/3','Recorte: escala 1/3']):draw.text((x,112),title,font=font(21),fill='#172333')
    labels=['Normal eye (rótulo da base)','Normal eye (rótulo da base)','Cisto de íris + alterações corneanas (diagnóstico da base)','Laceração da íris + outras lesões (diagnóstico da base)'];records=[]
    for k,(r,im,m0,m1,label) in enumerate(zip(selected,photos,original,scaled,labels)):
        y=155+260*k;draw.text((25,y),Path(r['image']).name,font=font(19),fill='#172333');draw.text((440,y),label,font=font(20),fill='#172333')
        rgb=np.asarray(im);overlays=[]
        for mask in [m0,m1]:
            out=rgb.copy();out[mask]=(.6*rgb[mask]+.4*np.array([0,255,70])).astype(np.uint8);overlays.append(Image.fromarray(out))
        for x,w,img in zip(xs,widths,[im,overlays[0],masked_crop(im,m0),overlays[1],masked_crop(im,m1)]):canvas.paste(ImageOps.pad(img,(w,195),color='white'),(x,y+32))
        records.append(dict(filename=Path(r['image']).name,diagnosis_raw=r['diagnosis_raw'],image_sha256=sha(Path(r['image'])),mask_pixels_original=int(m0.sum()),mask_pixels_scale3=int(m1.sum()),image_pixels=m0.size,recognition_of_normal_controls_evaluated=False))
    draw.text((25,1220),'Verde: máscara automática; preto: exterior excluído. Recorte não vazio não comprova segmentação correta.',font=font(21),fill='#425369')
    draw.text((25,1252),'Normal eye é o rótulo do depósito, sem nova avaliação médica. Exemplos ilustrativos; não medem área anatômica perdida.',font=font(20),fill='#425369')
    draw.text((25,1284),'Fonte: Qian, H. (2026), SLP-VLD v3, CC BY 4.0. Sobreposições, recortes e composição: este projeto.',font=font(20),fill='#425369')
    name='COMPARACAO_RECORTES_NORMAL_ANOMALIA_2026-10-27';canvas.save(a.output_dir/(name+'.png'))
    audit=dict(date='2026-10-27',selection='First2 distinct development subjects labelled exactly Normal eye by filename; then fixed P0114 query and P0803 enrollment illustrating both improvement and failure. Not prevalence estimates or a matched clinical experiment.',source='https://doi.org/10.6084/m9.figshare.32576697.v3',attribution='Qian,Hulei(2026).SLP-VLD.v3.Figshare.CC BY4.0. Derived composition/crops/overlays by this project.',unet_sha256=sha(checkpoint),png_sha256=sha(a.output_dir/(name+'.png')),samples=records,clinical_anatomical_preserved_percent=None)
    (a.output_dir/(name+'.json')).write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding='utf-8');print(a.output_dir/(name+'.png'))
if __name__=='__main__':main()

"""Prancha de entradas reais: primeira captura valida por pessoa, sem escores."""
from pathlib import Path
import argparse,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,required=True);args=parser.parse_args()
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text())['train']
    old=ROOT/'data/cache_identidade_automatica_2026-10-20';a=np.load(old/'train_crops.npy',mmap_mode='r');valid=np.load(old/'train_valid.npy')
    b=np.load(args.output_root/'cache_resnet50_nativo224/train_crops.npy',mmap_mode='r');selected=[];seen=set()
    for i,row in enumerate(manifest):
        if valid[i] and row['subject'] not in seen:
            assert b[i].any(),'Native sample not prepared yet'
            selected.append(i);seen.add(row['subject'])
        if len(selected)==4:break
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
    canvas=Image.new('RGB',(512,1124),'white');draw=ImageDraw.Draw(canvas)
    draw.text((12,10),'Entradas reais de treino: mesmos arquivos originais',font=font,fill='black')
    draw.text((12,36),'128 px (ampliado só para exibir)',font=small,fill='black');draw.text((272,36),'224 px (recorte direto do original)',font=small,fill='black')
    metadata=[]
    for n,i in enumerate(selected):
        top=62+n*264;draw.text((12,top),Path(manifest[i]['image']).name,font=small,fill='black')
        canvas.paste(Image.fromarray(np.asarray(a[i])).resize((224,224),Image.Resampling.BICUBIC),(12,top+22));canvas.paste(Image.fromarray(np.asarray(b[i])),(272,top+22))
        metadata.append({'index':i,'image':Path(manifest[i]['image']).name,'subject':manifest[i]['subject']})
    out=args.output_root/'resnet50_nativo224_2026-10-21';canvas.save(out/'qa_recortes_nativos.png')
    (out/'qa_recortes_nativos.json').write_text(json.dumps({'selection':'First valid train image per first4 different subjects; no query or performance selection','examples':metadata,'display_only':'128px inputs bicubic enlarged to224 for equal display size; model128 inputs unchanged','native224':'Direct original RGB masked crop, no super-resolution'},indent=2),encoding='utf-8')
    print(out/'qa_recortes_nativos.png')

if __name__=='__main__':main()

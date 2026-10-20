"""Visualiza os circulos ja estimados no piloto; nao recalcula escores."""
from pathlib import Path
import argparse
import json
import sys
from types import SimpleNamespace
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import torch

ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',choices=('ubipr','slpvld'),default='ubipr')
    args=parser.parse_args()
    torch.set_num_threads(2)
    source=ROOT/'data/modelos/cvrl_hdbif'; sys.path.insert(0,str(source))
    from modules.irisRecognition import irisRecognition
    from avaliar_robustez_reconhecimento import load_splits,identity
    from treinar_segmentacao_ubipr import decode_mask
    folder=ROOT/('outputs/hdbif_validacao_piloto_2026-10-20' if args.dataset=='ubipr' else 'outputs/hdbif_slpvld_validacao_piloto_2026-10-20')
    protocol=json.loads((folder/'protocolo.json').read_text(encoding='utf-8'))
    results=json.loads((folder/'resultado.json').read_text(encoding='utf-8'))
    model=irisRecognition(protocol['config'])
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text(encoding='utf-8'))
    rows=load_splits(manifest)['val']
    if args.dataset=='slpvld':
        clinical=json.loads((ROOT/'outputs/biometria_clinica_triagem_2026-10-20/manifesto.json').read_text(encoding='utf-8'))['val']
        rows=[]
        for eye in sorted({r['eye'] for r in results['normalization']}):
            candidates=[r for r in clinical if r['subject']+'_'+r['side']==eye]
            gallery=next(r for r in candidates if r['role']=='gallery')
            query=max((r for r in candidates if r['role']=='query'),key=lambda r:r['capture_date'])
            rows.extend(SimpleNamespace(subject=r['subject'],side=r['side'],session=session,image=r['image'],mask=None) for session,r in [(1,gallery),(2,query)])
    canvas=Image.new('RGB',(800,4*390),'white'); pen=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    for i,record in enumerate(results['normalization']):
        row=next(r for r in rows if identity(r)==record['eye'] and r.session==record['session'])
        with Image.open(row.image) as im: image=model.fix_image(im.convert('L'))
        if row.mask is None:
            mask=Image.fromarray(model.segment(image))
        else:
            with Image.open(row.mask) as im:
                mask=Image.fromarray((decode_mask(im)==1).astype(np.uint8)*255).resize(image.size,Image.Resampling.NEAREST)
        pupil=np.asarray(record['pupil_circle']); iris=np.asarray(record['iris_circle'])
        polar,valid=model.cartToPol_torch(image,mask,pupil,iris)
        visual=image.convert('RGB'); draw=ImageDraw.Draw(visual)
        for circle,color in [(pupil,'red'),(iris,'lime')]:
            x,y,r=circle; draw.ellipse((x-r,y-r,x+r,y+r),outline=color,width=3)
        col=i%2; line=i//2; x=col*400; y=line*390
        pen.text((x+8,y+5),f"{record['eye']} session {record['session']}",font=font,fill='black')
        canvas.paste(visual.resize((384,288)),(x+8,y+30))
        strip=np.stack((polar,)*3,axis=-1); strip[valid==0]=[180,40,40]
        canvas.paste(Image.fromarray(strip).resize((384,48)),(x+8,y+325))
    out=ROOT/'data/qa_biometria'; out.mkdir(parents=True,exist_ok=True)
    canvas.save(out/f'hdbif_{args.dataset}_normalizacao_validacao.jpg',quality=92)
    print('Prancha salva; circulo interno vermelho, externo verde, pixels invalidos em vermelho na faixa polar.')

if __name__=='__main__': main()

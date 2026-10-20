"""Pranchas de todos os exemplos de validacao, sem selecionar por acerto."""
from pathlib import Path
import argparse
import json
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--wait',action='store_true')
    args=parser.parse_args()
    source=ROOT/'outputs/hdbif_slpvld_validacao_completa_2026-10-20/templates'
    records=json.loads((ROOT/'outputs/biometria_clinica_triagem_2026-10-20/manifesto.json').read_text(encoding='utf-8'))['val']
    records.sort(key=lambda r:(r['subject'],r['side'],r['capture_date'],r['image']))
    directory=ROOT/'data/qa_biometria/slpvld_validacao_completa'
    deadline=time.monotonic()+4*3600
    while not all((directory/(Path(r['image']).stem+'.jpg')).exists() for r in records):
        if not args.wait or time.monotonic()>deadline: raise RuntimeError('QA images not complete')
        time.sleep(15)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
    target=ROOT/'data/qa_biometria/slpvld_pranchas'; target.mkdir(parents=True,exist_ok=True)
    pages=[]
    for start in range(0,len(records),20):
        subset=records[start:start+20]
        board=Image.new('RGB',(1200,1286),'white'); draw=ImageDraw.Draw(board)
        page=start//20+1
        draw.text((8,8),f'VALIDACAO | pagina {page} | circulos previstos, sem referencia clinica',fill='black',font=font)
        for offset,row in enumerate(subset):
            name=Path(row['image']).stem
            with np.load(source/(name+'.npz'),allow_pickle=False) as saved: audit=json.loads(str(saved['audit']))
            x=(offset%4)*300; y=(offset//4)*250+36
            draw.text((x+5,y),name,font=font,fill='black')
            draw.text((x+5,y+17),f"{row['role']} | polar valido {100*audit['valid_polar_fraction']:.1f}%",font=font,fill='black')
            with Image.open(directory/(name+'.jpg')) as image:
                thumb=ImageOps.contain(image.convert('RGB'),(290,210))
                board.paste(thumb,(x+(300-thumb.width)//2,y+36))
        path=target/f'pagina_{page:02}.jpg'; board.save(path,quality=92)
        pages.append({'page':page,'files':[Path(r['image']).name for r in subset]})
    (target/'indice.json').write_text(json.dumps(pages,indent=2),encoding='utf-8')
    print(json.dumps({'pages':len(pages),'images':len(records),'directory':str(target)}),flush=True)

if __name__=='__main__': main()

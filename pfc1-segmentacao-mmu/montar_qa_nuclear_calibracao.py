"""Inspecao inicial de mascaras e entradas do encoder, somente calibracao."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parent

def main():
    rows=json.loads((ROOT/'outputs/nuclear_biometria_protocolo_2026-10-20/manifesto.json').read_text(encoding='utf-8'))['calibration']
    eyes=sorted({(r['patient_id'],r['side']) for r in rows})[:4]
    board=Image.new('RGB',(960,1200),'white'); draw=ImageDraw.Draw(board)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    for line,eye in enumerate(eyes):
        photos=[r for r in rows if (r['patient_id'],r['side'])==eye]
        selected=[next(r for r in photos if r['role']==role) for role in ('gallery','query')]
        for col,row in enumerate(selected):
            name=f"{row['patient_id']:03d}_{row['side']}_{Path(row['filename']).stem}"
            with np.load(ROOT/'data/cache/nuclear_identidade128'/(name+'.npz'),allow_pickle=False) as saved:
                rgb=saved['rgb']; mask=saved['mask']; crop=saved['crop']
            x=480*col; y=300*line
            draw.text((x+8,y+5),name+' | '+row['role'],font=font,fill='black')
            draw.text((x+8,y+26),f'Previsao: {mask.sum()} pixels | recorte a direita',font=font,fill='black')
            overlay=rgb.copy(); overlay[mask]=(.65*rgb[mask]+.35*np.array([0,255,0])).astype(np.uint8)
            board.paste(Image.fromarray(overlay).resize((320,240)),(x+4,y+52))
            board.paste(Image.fromarray(crop),(x+344,y+90))
    out=ROOT/'data/qa_biometria/nuclear'; out.mkdir(parents=True,exist_ok=True)
    board.save(out/'calibracao_inicial.png')
    print('Oito exemplos de calibracao, escolhidos por ordem de identificador, sem consultar escores.')

if __name__=='__main__': main()

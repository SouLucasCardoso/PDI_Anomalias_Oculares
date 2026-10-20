"""Sinaliza similaridade perceptual e gera prancha da validacao para inspecao."""
from collections import defaultdict
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parent

def dhash(image):
    a=np.asarray(image.convert('L').resize((9,8),Image.Resampling.LANCZOS))
    return int(''.join('1' if b else '0' for b in (a[:,1:]>a[:,:-1]).ravel()),2)

def main():
    folder=ROOT/'outputs/biometria_clinica_triagem_2026-10-20'
    splits=json.loads((folder/'manifesto.json').read_text(encoding='utf-8'))
    samples=[dict(r,split=s) for s,rs in splits.items() for r in rs]
    signatures=[]
    for i,row in enumerate(samples):
        with Image.open(row['image']) as image: signatures.append(dhash(image))
        if (i+1)%100==0: print(f'Imagens inspecionadas: {i+1}/{len(samples)}',flush=True)
    flagged=[]
    for i,a in enumerate(samples):
        for j in range(i):
            b=samples[j]; distance=(signatures[i]^signatures[j]).bit_count()
            if distance<=2:
                flagged.append({'a':Path(a['image']).name,'b':Path(b['image']).name,
                                'hamming_dhash':distance,'same_eye':(a['subject'],a['side'])==(b['subject'],b['side']),
                                'same_split':a['split']==b['split']})
    report={'images':len(samples),'dhash_candidate_pairs':len(flagged),
            'candidate_cross_split_pairs':sum(not r['same_split'] for r in flagged),
            'candidate_cross_eye_pairs':sum(not r['same_eye'] for r in flagged),
            'rule':'64-bit difference hash distance <=2; screening only, not proof of duplication; no automatic exclusions',
            'pairs':flagged}
    (folder/'similaridade_perceptual.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    groups=defaultdict(list)
    for r in splits['val']: groups[(r['subject'],r['side'])].append(r)
    # Only validation is viewed while protocol is being developed.
    keys=sorted(groups)[:6]; width=1000; cardheight=350
    board=Image.new('RGB',(width,len(keys)*cardheight),'white'); draw=ImageDraw.Draw(board)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    for index,key in enumerate(keys):
        rs=groups[key]; gallery=next(r for r in rs if r['role']=='gallery')
        query=max((r for r in rs if r['role']=='query'),key=lambda r:r['capture_date'])
        for col,row in enumerate((gallery,query)):
            x=col*500; y=index*cardheight
            with Image.open(row['image']) as im:
                thumb=ImageOps.contain(im.convert('RGB'),(490,260))
                board.paste(thumb,(x+(500-thumb.width)//2,y+70))
            label=f"{key[0]} {key[1]} | {row['role']} | {row['capture_date']}"
            draw.text((x+8,y+5),label,font=font,fill='black')
            diagnosis=row['diagnosis_raw']
            draw.text((x+8,y+30),diagnosis[:48],font=font,fill='black')
            draw.text((x+8,y+50),diagnosis[48:96],font=font,fill='black')
    target=ROOT/'data/qa_clinica'; target.mkdir(parents=True,exist_ok=True)
    board.save(target/'pares_validacao.jpg',quality=90)
    if flagged:
        lookup={Path(r['image']).name:r for r in samples}
        review=Image.new('RGB',(1000,320*len(flagged)),'white'); pen=ImageDraw.Draw(review)
        for i,pair in enumerate(flagged):
            for col,field in enumerate(('a','b')):
                row=lookup[pair[field]]; x=500*col; y=320*i
                with Image.open(row['image']) as im:
                    thumb=ImageOps.contain(im.convert('RGB'),(490,265))
                    review.paste(thumb,(x+(500-thumb.width)//2,y+50))
                pen.text((x+8,y+5),pair[field],font=font,fill='black')
                pen.text((x+8,y+26),'Audit only | dHash '+str(pair['hamming_dhash']),font=font,fill='black')
        review.save(target/'candidatos_duplicatas.jpg',quality=90)
    print(json.dumps({k:v for k,v in report.items() if k!='pairs'},indent=2),flush=True)

if __name__=='__main__': main()

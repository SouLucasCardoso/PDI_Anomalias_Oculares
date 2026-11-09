"""Mesmas seis fotografias e máscaras, com apresentação subpixel em tamanho nativo."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from PIL import Image,ImageDraw,ImageOps,ImageFont
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    run=ROOT/'outputs/sam31_matte_subpixel_2026-11-08';done=json.loads((run/'CONCLUIDO.json').read_text())
    assert done['status']=='concluido' and not done['recognition_mask_changed']
    rows=json.loads((ROOT/'data/slpvld/manifesto.json').read_text(encoding='utf-8-sig'));records=done['records'];assert len(records)==6
    font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
    for indices,name in (([0,1],'recortes_normais.png'),([2,3],'recortes_anomalias.png'),([4,5],'recortes_limites_clinicos.png')):
        canvas=Image.new('RGB',(2100,1040),'white');draw=ImageDraw.Draw(canvas)
        for x,title in zip((0,710,1420),('Fotografia original','SAM3.1 experimental','Recorte nativo subpixel')):draw.text((x+12,12),title,font=font(40),fill='black')
        for line,index in enumerate(indices):
            record=records[index];row=next(r for r in rows if Path(r['image']).name==record['image'])
            assert sha(row['image'])==record['photo_sha256'];folder=run/Path(record['image']).stem
            assert sha(folder/'mask_nativa.png')==record['mask_sha256'] and sha(folder/'recorte_subpixel.png')==record['crop_sha256']
            photo=Image.open(row['image']).convert('RGB');mask=np.asarray(Image.open(folder/'mask_nativa.png'))>0
            rgb=np.asarray(photo);overlay=rgb.copy();overlay[mask]=(.65*rgb[mask]+.35*np.array([0,220,100])).astype(np.uint8)
            crop=Image.open(folder/'recorte_subpixel.png').convert('RGBA');background=Image.new('RGBA',crop.size,'black');background.alpha_composite(crop)
            top=90+line*465;draw.text((12,top-38),Path(row['image']).stem,font=font(38),fill='black')
            display=background.convert('RGB') if mask.any() else Image.new('RGB',(680,400),'black')
            for x,item in zip((0,710,1420),(photo,Image.fromarray(overlay),display)):
                canvas.paste(ImageOps.pad(item,(680,400),method=Image.Resampling.LANCZOS,color='white'),(x+10,top+10))
            if not mask.any():
                draw.text((1770,top+175),'LOCALIZAÇÃO INSUFICIENTE',font=font(34),fill='white',anchor='mm')
                draw.text((1770,top+225),'Requer revisão da máscara',font=font(32),fill='white',anchor='mm')
        canvas.save(out/name,dpi=(300,300))
    provenance={'run':str(run),'run_protocol_sha256':sha(run/'protocolo.json'),'completion_sha256':sha(run/'CONCLUIDO.json'),
        'helper_sha256':sha(__file__),'method':'Display-only subpixel alpha; original RGB and all six previous binary masks identical.',
        'dataset_credit':'Qian (2026), SLP-VLD v3, CC BY4.0, same fixed cases as prior manuscript',
        'clinical_reference_masks_available':False,'recognition_reevaluated':False,
        'figure_sha256':{f.name:sha(f) for f in out.glob('*.png')}}
    (out/'PROVENIENCIA.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8');print(json.dumps(provenance))


if __name__=='__main__':main()

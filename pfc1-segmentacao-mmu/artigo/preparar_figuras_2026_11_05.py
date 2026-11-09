"""Figuras documentais reais; sem retoque de textura ou recalibracao."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps
import torch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from treinar_segmentacao_ubipr import MulticlassUNet
from segmentacao_clinica_escala import predict_clinical
from avaliar_dinov3_ubipr import masked_crop


def main():
    out=ROOT/'artigo/figuras_2026-11-05';out.mkdir(parents=True,exist_ok=True)
    rows=json.loads((ROOT/'data/slpvld/manifesto.json').read_text(encoding='utf-8-sig'))
    names=['P0005_OD20241206.JPG','P0007_OS20250306.JPG','P0209_OD20250329.JPG','P0564_OD20250526.JPG','P0114_OS20250417.JPG','P0803_OD20250112.JPG']
    rows=[next(r for r in rows if Path(r['image']).name==name) for name in names]
    photos=[Image.open(r['image']).convert('RGB') for r in rows]
    checkpoint=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert sha(checkpoint)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    torch.set_num_threads(2)
    model=MulticlassUNet(8).eval()
    model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
    masks=predict_clinical(photos,model,'cpu')
    expected={r['filename']:r['predicted_pixels'] for r in json.loads((ROOT/'outputs/casos_oculares_escala3_2026-10-27/areas_clinicas.json').read_text())}
    font=lambda size:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',size)
    records=[]
    def board(indices,filename):
        canvas=Image.new('RGB',(2100,1040),'white');draw=ImageDraw.Draw(canvas)
        for x,title in zip([0,710,1420],['Fotografia original','Região prevista de íris','Recorte automático']):draw.text((x+12,12),title,font=font(45),fill='black')
        for line,index in enumerate(indices):
            photo,mask,row=photos[index],masks[index],rows[index]
            rgb=np.asarray(photo);overlay=rgb.copy();overlay[mask]=(.65*rgb[mask]+.35*np.array([0,220,100])).astype(np.uint8)
            top=90+line*465
            draw.text((12,top-38),Path(row['image']).stem,font=font(38),fill='black')
            crop=masked_crop(photo,mask)
            for x,item in zip([0,710,1420],[photo,Image.fromarray(overlay),crop]):
                canvas.paste(ImageOps.pad(item,(680,400),method=Image.Resampling.LANCZOS,color='white'),(x+10,top+10))
        canvas.save(out/filename,dpi=(300,300))
    board([0,1],'recortes_normais.png')
    board([2,3],'recortes_anomalias.png')
    board([4,5],'recortes_limites_clinicos.png')
    for row,photo,mask in zip(rows,photos,masks):
        name=Path(row['image']).name
        records.append(dict(filename=name,diagnosis_raw=row['diagnosis_raw'],image_sha256=sha(row['image']),
                            predicted_pixels=int(mask.sum()),historical_predicted_pixels=expected.get(name),
                            historical_pixel_count_matches=int(mask.sum())==expected.get(name),
                            historical_pixel_delta=None if name not in expected else int(mask.sum())-expected[name],
                            mask_sha256=hashlib.sha256(np.packbits(mask).tobytes()).hexdigest()))
    (out/'PROVENIENCIA_FIGURAS.json').write_text(json.dumps(dict(
        selection='Visual documentary selection of well delimited available crops, plus explicit failure controls. Not a random sample, clinical Dice or recognition estimate.',
        method='Historical frozen U-Net, fixed clinical scale 1/3; native photo pixels, nearest mask remapping, display-only resizing, no generative processing or manual contour correction.',
        unet_sha256=sha(checkpoint),source='Qian H. SLP-VLD v3, 2026, doi:10.6084/m9.figshare.32576697.v3',
        license='CC BY 4.0',samples=records,files={p.name:sha(p) for p in out.glob('*.png')}),indent=2,ensure_ascii=False),encoding='utf-8')
    print('Figuras reais preparadas em CPU; diferencas de borda registradas, sem alterar metricas historicas.')


if __name__=='__main__':main()

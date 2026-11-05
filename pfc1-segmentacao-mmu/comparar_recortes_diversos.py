"""Prancha dos mesmos casos clinicos com um checkpoint da nova rodada.

Inspecao qualitativa apenas. Nao usa diagnosticos para orientar a mascara e
nao estima Dice ou melhora de identidade sem referencia clinica anotada.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from treinar_segmentacao_ubipr import MulticlassUNet, sha256
from avaliar_sam31_diverso import board

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    a=p.parse_args();a.output_dir.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(4)
    state=torch.load(a.checkpoint,map_location='cpu',weights_only=True)
    model=MulticlassUNet(8).eval();model.load_state_dict(state['model'],strict=True)
    config=state['configuration'];width=int(config['width']);height=int(config['height'])
    rows=json.loads((ROOT/'data/slpvld/manifesto.json').read_text(encoding='utf-8-sig'))
    reference=ROOT/'outputs/sam31_diverso_2026-10-27'
    masks=np.load(reference/'mascaras.npz',allow_pickle=False)
    names=['P0005_OD20241206.JPG','P0007_OS20250306.JPG','P0114_OS20250417.JPG','P0803_OD20250112.JPG']
    examples=[];records=[]
    for name in names:
        row=next(r for r in rows if Path(r['image']).name==name)
        with Image.open(row['image']) as im:photo=im.convert('RGB');photo.thumbnail((1200,1200))
        x=torch.from_numpy(np.asarray(photo.resize((width,height),Image.Resampling.BILINEAR),np.float32).transpose(2,0,1).copy()/255)[None]
        with torch.inference_mode():small=model(x).argmax(1)[0].numpy()==1
        candidate=np.asarray(Image.fromarray(small).resize(photo.size,Image.Resampling.NEAREST),bool)
        shape=tuple(int(v) for v in masks[name+'_shape'])
        if shape!=(photo.height,photo.width):raise ValueError('Preprocessamento clinico divergente')
        original=np.unpackbits(masks[name+'_unet'],count=int(np.prod(shape))).reshape(shape).astype(bool)
        examples.append((photo,original,candidate,name.split('_')[0]))
        records.append({'image':name,'diagnosis_raw':row['diagnosis_raw'],'candidate_pixels':int(candidate.sum()),
                        'original_pixels':int(original.sum()),'image_sha256':sha256(Path(row['image'])),
                        'reference_mask_available':False})
    board(examples,a.output_dir/'comparacao_clinica.png',
          'SLPVLD: U-Net original versus novo candidato; sem referencia clinica anotada', candidate_name='U-Net diversa')
    report={'checkpoint':str(a.checkpoint),'checkpoint_sha256':sha256(a.checkpoint),'epoch':state['epoch'],
            'input':[width,height],'cases':records,'qualitative_only':True,'recognition_measured':False,
            'figure_sha256':sha256(a.output_dir/'comparacao_clinica.png')}
    (a.output_dir/'comparacao.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(a.output_dir/'comparacao_clinica.png')


if __name__=='__main__':main()

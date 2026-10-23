"""QA real na validacao, selecao por ordem, sem escolher pelo Dice."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import torch
ROOT=Path(__file__).resolve().parent

def main():
    from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
    from avaliar_robustez_reconhecimento import perturb
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'qa_segmentacao_oclusao_2026-10-21';out.mkdir(parents=True,exist_ok=False)
    rows=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text())['val'];samples=[];seen=set()
    for r in rows:
        if r['session']!=2 or r['subject'] in seen:continue
        image_path=ROOT/'data/ubipr/single_eye'/Path(r['image']).name;mask_path=ROOT/'data/ubipr/single_eye'/Path(r['mask']).name
        with Image.open(image_path) as im:rgb=im.convert('RGB')
        with Image.open(mask_path) as im:mask=decode_mask(im)==1
        if not mask.any():continue
        altered,meta=perturb(rgb,mask,'oclusao_inferior',10);samples.append((r,rgb,altered,mask,meta));seen.add(r['subject'])
        if len(samples)==4:break
    torch.set_num_threads(4);models=[];checkpoints=[ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt',a.output_root/'segmentacao_oclusao_2026-10-21/melhor_modelo.pt']
    for checkpoint in checkpoints:
        model=MulticlassUNet(8).eval();model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model']);models.append(model)
    inputs=torch.from_numpy(np.stack([np.asarray(s[2].resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for s in samples]).transpose(0,3,1,2).copy())
    with torch.inference_mode():predictions=[model(inputs).argmax(1).numpy()==1 for model in models]
    font=lambda size:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',size)
    canvas=Image.new('RGB',(1640,1370),'#f3f5f7');draw=ImageDraw.Draw(canvas);draw.text((25,20),'Segmentação sob oclusão inferior de10% — exemplos reais de validação',font=font(29),fill='#172333')
    draw.text((25,66),'Primeiras consultas de quatro pessoas com anotação não vazia; sem seleção por Dice ou reconhecimento',font=font(21),fill='#425369')
    xs=[25,435,845,1255]
    for x,title in zip(xs,['Original','Foto com oclusão','U-Net original','U-Net ajustada']):draw.text((x,110),title,font=font(23),fill='#172333')
    metadata=[]
    for j,(r,original,altered,reference,meta) in enumerate(samples):
        y,x=np.where(reference);w=int(x.max()-x.min()+1);h=int(y.max()-y.min()+1);px=max(8,round(w*.8));py=max(8,round(h*.8));box=(max(0,int(x.min())-px),max(0,int(y.min())-py),min(original.width,int(x.max())+px+1),min(original.height,int(y.max())+py+1))
        row_images=[original,altered];case_dice=[]
        for predicted in predictions:
            mask=np.asarray(Image.fromarray(predicted[j]).resize(original.size,Image.Resampling.NEAREST),bool);overlay=np.asarray(altered).copy();overlay[mask]=(.55*overlay[mask]+.45*np.array([0,255,70])).astype(np.uint8);row_images.append(Image.fromarray(overlay));case_dice.append(float((2*(mask&reference).sum()+1e-6)/(mask.sum()+reference.sum()+1e-6)))
        top=155+j*285;draw.text((25,top),Path(r['image']).name,font=font(20),fill='#172333')
        for xx,img in zip(xs,row_images):canvas.paste(img.crop(box).resize((360,210),Image.Resampling.BILINEAR),(xx,top+30))
        for xx,dice in zip(xs[2:],case_dice):draw.text((xx,top+245),f'Dice deste caso: {100*dice:.2f}%',font=font(18),fill='#425369')
        metadata.append({'image':Path(r['image']).name,'subject':r['subject'],'native_case_dice_original_and_robust':case_dice,'display_box':box,'intervention':meta})
    draw.text((25,1310),'Zoom da anotação somente para exibição. A U-Net recebe a foto inteira reduzida a320×240, sem máscara de referência.',font=font(21),fill='#425369')
    canvas.save(out/'comparacao_mascaras.png');(out/'AUDITORIA.json').write_text(json.dumps({'selection':'First nonempty-reference session2 image per first4 different validation subjects; no Dice/recognition selection','samples':metadata,'checkpoint_sha256':[hashlib.sha256(p.read_bytes()).hexdigest() for p in checkpoints],'display_only':'Annotation bbox used only for visualization zoom; not inference','device':'CPU FP32, not population metric','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print(out/'comparacao_mascaras.png')

if __name__=='__main__':main()

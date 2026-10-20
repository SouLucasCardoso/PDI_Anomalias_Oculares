"""Exemplos reais e rastreáveis do recorte; seleção sem consultar escores."""
from pathlib import Path
import csv
import json
import numpy as np
from PIL import Image
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from treinar_segmentacao_ubipr import MulticlassUNet, decode_mask
from avaliar_dinov3_ubipr import masked_crop
from avaliar_robustez_reconhecimento import perturb

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'Relatórios-de-Avanço'

def main():
    torch.set_num_threads(4)
    with (ROOT/'outputs/biometria_area_completa_2026-10-20/manifesto_auditado.csv').open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    selected=[]; seen=set()
    for r in rows:
        if r['split']=='val' and r['session']=='2' and int(r['iris_pixels'])>0 and r['subject'] not in seen:
            selected.append(r); seen.add(r['subject'])
        if len(selected)==4: break
    model=MulticlassUNet(8).eval()
    checkpoint=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
    fig,axes=plt.subplots(len(selected),6,figsize=(18,10),facecolor='white')
    titles=['Imagem original','Máscara prevista\n(sobreposição verde)','Recorte automático\nU-Net','Recorte de referência\nentrada 128 × 128','Referência: 10% ocultos\nna parte superior','Referência: 40% ocultos\nna parte superior']
    provenance=[]
    for i,r in enumerate(selected):
        image=Image.open(r['image']).convert('RGB')
        ref=decode_mask(Image.open(r['mask']))==1
        small=np.asarray(image.resize((320,240),Image.Resampling.BILINEAR),dtype=np.float32)/255
        with torch.inference_mode():
            pred=model(torch.from_numpy(small.transpose(2,0,1).copy())[None]).argmax(1)[0].numpy()==1
        pred=np.asarray(Image.fromarray(pred).resize(image.size,Image.Resampling.NEAREST),dtype=bool)
        overlay=np.array(image).copy()
        overlay[pred]=(.55*overlay[pred]+.45*np.array([30,255,80])).astype(np.uint8)
        items=[image,overlay,masked_crop(image,pred),masked_crop(image,ref).resize((128,128),Image.Resampling.BILINEAR)]
        for level in (10,40):
            altered,_=perturb(image,ref,'oclusao_superior',level)
            items.append(masked_crop(altered,ref).resize((128,128),Image.Resampling.BILINEAR))
        dice=2*(pred&ref).sum()/max(1,pred.sum()+ref.sum())
        for j,item in enumerate(items):
            axes[i,j].imshow(item,interpolation='nearest'); axes[i,j].set_xticks([]); axes[i,j].set_yticks([])
            if i==0: axes[i,j].set_title(titles[j],fontsize=11,pad=12)
        axes[i,0].set_ylabel(f"{Path(r['image']).stem}\nDice deste exemplo: {dice:.3f}",fontsize=9)
        provenance.append({'image':r['image'],'reference_mask':r['mask'],'example_dice':float(dice)})
    fig.suptitle('Estado atual dos recortes de íris · exemplos reais UBIPr · 20/10/2026',fontsize=19,weight='bold',y=.985)
    fig.text(.5,.062,'U-Net: máscara inferida pelo modelo retreinado. Referência: anotação da base, usada na rodada do extrator de identidade.',ha='center',fontsize=11)
    fig.text(.5,.035,'Preto: região removida pela máscara. Cinza: oclusão simulada apenas na íris. Exemplos da validação, sem seleção por desempenho.',ha='center',fontsize=10)
    fig.tight_layout(rect=(.02,.09,1,.95))
    fig.savefig(OUT/'EXEMPLOS_REAIS_RECORTES_IRIS_2026-10-20.png',dpi=180)
    plt.close(fig)
    (OUT/'EXEMPLOS_REAIS_RECORTES_IRIS_2026-10-20.json').write_text(json.dumps({'selection':'First four distinct people in validation session2 with nonempty reference, manifest order; no score filtering','checkpoint':str(checkpoint),'examples':provenance},indent=2,ensure_ascii=False),encoding='utf-8')

if __name__=='__main__': main()

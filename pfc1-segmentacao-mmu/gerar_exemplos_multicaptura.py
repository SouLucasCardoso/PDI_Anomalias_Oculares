"""Exemplos reais do candidato automatico top3, sem escolher consultas por acerto."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs/cadastro_multicaptura_val_v2_2026-10-20'

def main():
    from avaliar_robustez_reconhecimento import load_splits,identity
    from avaliar_dinov3_ubipr import masked_crop
    from treinar_segmentacao_ubipr import MulticlassUNet
    torch.set_num_threads(4)
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val']
    gallery=sorted([r for r in rows if r.session==1],key=lambda r:(identity(r),Path(r.image).name))
    queries=[r for r in rows if r.session==2]; ids=sorted({identity(r) for r in rows})
    with np.load(OUT/'features_automatic.npz') as z: vectors=z['features']; valid=z['valid']
    with np.load(OUT/'neural_automatic_top3.npz') as z: scores=z['scores']; correct=z['correct']; accepted=z['accepted']
    selected=[]; seen=set()
    for qi,r in enumerate(queries):
        if r.subject not in seen: selected.append(qi); seen.add(r.subject)
        if len(selected)==4:break
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model=MulticlassUNet(8).to(device).eval()
    model.load_state_dict(torch.load(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt',map_location='cpu',weights_only=True)['model'])
    def crop(row):
        with Image.open(row.image) as im: image=im.convert('RGB')
        small=np.asarray(image.resize((320,240),Image.Resampling.BILINEAR),dtype=np.float32)/255
        with torch.inference_mode(): mask=model(torch.from_numpy(small.transpose(2,0,1).copy())[None].to(device)).argmax(1)[0].cpu().numpy()==1
        mask=np.asarray(Image.fromarray(mask).resize(image.size,Image.Resampling.NEAREST),dtype=bool)
        return image,masked_crop(image,mask).resize((128,128),Image.Resampling.BILINEAR)
    fig,axes=plt.subplots(4,5,figsize=(15,10)); records=[]
    for line,qi in enumerate(selected):
        row=queries[qi]; winner=ids[int(scores[qi].argmax())]
        positions=[i for i,r in enumerate(gallery) if identity(r)==winner and valid[i]]
        positions=sorted(positions,key=lambda i:float(vectors[len(gallery)+qi]@vectors[i]),reverse=True)[:3]
        original,cut=crop(row)
        items=[(original,'Consulta original\n'+Path(row.image).stem),(cut,'Recorte automático\nU-Net → encoder 128 × 128')]
        for rank,i in enumerate(positions,1):items.append((crop(gallery[i])[1],f'Cadastro {rank} do candidato\n'+Path(gallery[i].image).stem))
        for ax in axes[line]: ax.axis('off')
        for ax,(value,title) in zip(axes[line],items): ax.imshow(value,interpolation='nearest'); ax.set_title(title,fontsize=9)
        axes[line,0].text(0,-.08,f"Candidato: {winner} · Rank-1 {'correto' if correct[qi] else 'incorreto'}\nGenuíno {'aceito' if accepted[qi] else 'rejeitado'} no limiar",transform=axes[line,0].transAxes,fontsize=9,va='top')
        records.append({'query':Path(row.image).name,'query_eye':identity(row),'winning_eye':winner,'rank1_correct':bool(correct[qi]),'genuine_accepted':bool(accepted[qi]),'winning_enrollment_top3':[Path(gallery[i].image).name for i in positions]})
    fig.suptitle('Reconhecimento automático com múltiplos cadastros · validação UBIPr',fontsize=17,weight='bold')
    fig.text(.5,.015,'Primeira consulta de quatro pessoas distintas na ordem do manifesto, sem seleção por desempenho. Referências não corrigem as máscaras.',ha='center',fontsize=10)
    fig.tight_layout(rect=(0,.045,1,.95),h_pad=4)
    fig.savefig(OUT/'exemplos_multicaptura.png',dpi=160); plt.close(fig)
    (OUT/'exemplos_multicaptura.json').write_text(json.dumps(records,indent=2),encoding='utf-8')

if __name__=='__main__': main()

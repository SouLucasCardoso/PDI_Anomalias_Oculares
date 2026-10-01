"""Pranchas de casos testados: recortes reais e escores salvos, sem nova biometria."""
import csv
import json
from pathlib import Path
import numpy as np
from PIL import Image
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from avaliar_robustez_reconhecimento import ROOT, perturb
from avaliar_dinov3_ubipr import masked_crop
from treinar_segmentacao_ubipr import MulticlassUNet, decode_mask

OUT=ROOT/'outputs/robustez_reconhecimento_2026-10-01'
CASES=[('oclusao_superior',60,'Oclusão superior · 60% da área'),
       ('oclusao_inferior',60,'Oclusão inferior · 60% da área'),
       ('desfoque_iris',5,'Desfoque · sigma = 5% da largura'),
       ('contraste_iris',75,'Contraste · mistura com cinza de 75%')]


def read(name):
    with (OUT/name).open(encoding='utf-8-sig') as f: return list(csv.DictReader(f))


def main():
    torch.set_num_threads(4)
    records=[r for r in read('manifesto_auditado.csv') if r['split']=='test']
    queries=[r for r in records if r['session']=='2']
    ids=sorted({r['subject']+'_'+r['side'] for r in records if r['session']=='1'})
    summary=read('resumo.csv')
    base_summary=next(r for r in summary if r['branch']=='iris_unet' and r['condition']=='original')
    base=np.load(OUT/'scores_iris_unet_original.npz')
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model=MulticlassUNet(8).to(device).eval()
    checkpoint=ROOT/'outputs/cnn/ubipr_multiclasse_30ep_batch32/melhor_modelo.pt'
    model.load_state_dict(torch.load(checkpoint,map_location=device,weights_only=True)['model'])
    def segment(im):
        small=np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),dtype=np.float32)/255
        t=torch.from_numpy(small.transpose(2,0,1).copy())[None].to(device)
        with torch.inference_mode(): mask=model(t).argmax(1)[0].cpu().numpy()==1
        return np.asarray(Image.fromarray(mask).resize(im.size,Image.Resampling.NEAREST),dtype=bool)
    selected=[]; seen=set()
    for kind,level,title in CASES:
        with np.load(OUT/f'scores_iris_unet_{kind}_{level}.npz') as z: alt={k:z[k] for k in z.files}
        eligible=[i for i,r in enumerate(queries) if int(r['iris_pixels'])>0 and base['valid'][i] and alt['valid'][i]
                  and base['scores'][i].argmax()==base['labels'][i] and alt['scores'][i].argmax()!=alt['labels'][i]]
        unique=[i for i in eligible if queries[i]['subject'] not in seen]
        pool=unique or eligible
        if not pool: raise RuntimeError(f'Sem transicao elegivel: {kind}')
        pool.sort(key=lambda i:float(base['scores'][i,base['labels'][i]]-alt['scores'][i,alt['labels'][i]]))
        i=pool[len(pool)//2]; r=queries[i]; seen.add(r['subject'])
        with Image.open(r['image']) as im: original=im.convert('RGB')
        with Image.open(r['mask']) as m: ref=decode_mask(m)==1
        altered,_=perturb(original,ref,kind,level)
        pm0,pm1=segment(original),segment(altered)
        masks=[pm0,pm1]; pictures=[original,altered]
        scores0=base['scores'][i]; scores1=alt['scores'][i]; label=int(base['labels'][i])
        rank0=int(np.flatnonzero(np.argsort(-scores0,kind='stable')==label)[0])+1
        rank1=int(np.flatnonzero(np.argsort(-scores1,kind='stable')==label)[0])+1
        aggregate=next(x for x in summary if x['branch']=='iris_unet' and x['condition']==kind and int(x['level'])==level)
        case={'kind':kind,'level':level,'title':title,'image':Path(r['image']).name,
              'true_eye':ids[label],'predicted_before':ids[int(scores0.argmax())],'predicted_after':ids[int(scores1.argmax())],
              'rank_before':rank0,'rank_after':rank1,'genuine_before':float(scores0[label]),'genuine_after':float(scores1[label]),
              'genuine_drop':float(scores0[label]-scores1[label]),'transition_candidates':len(eligible),
              'cohort_rank1_before':float(base_summary['rank1']),'cohort_rank1_after':float(aggregate['rank1']),
              'cohort_loss_pp':float(aggregate['loss_rank1_pp'])}
        selected.append((case,pictures,masks))

    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11})
    headers=['Original + contorno U-Net','Recorte original','Alteração + contorno U-Net','Recorte após alteração','Efeito no reconhecimento']
    def draw_row(axes, item):
        c,pictures,masks=item
        for col,im,mask,overlay in [(0,pictures[0],masks[0],True),(1,pictures[0],masks[0],False),
                                  (2,pictures[1],masks[1],True),(3,pictures[1],masks[1],False)]:
            ax=axes[col]; ax.imshow(im if overlay else masked_crop(im,mask))
            if overlay and mask.any(): ax.contour(mask,levels=[.5],colors=['#00e5d0'],linewidths=1.)
            ax.axis('off')
        axes[0].text(0,-.10,c['image'],transform=axes[0].transAxes,fontsize=9,color='#475569')
        ax=axes[4]; ax.axis('off')
        number=lambda v:f'{v:.4f}'.replace('.',',')
        text=(f"OLHO CORRETO: {c['true_eye']}\n"
              f"Antes: posição {c['rank_before']} / 32  ·  ACERTO\n"
              f"Depois: posição {c['rank_after']} / 32  ·  ERRO\n"
              f"Escolhido depois: {c['predicted_after']}\n\n"
              f"Similaridade com o olho correto\n{number(c['genuine_before'])} → {number(c['genuine_after'])}\n"
              f"Queda do escore: {number(c['genuine_drop'])}\n\n"
              f"NA COORTE DE 486 CONSULTAS\nRank-1: {100*c['cohort_rank1_before']:.2f}% → {100*c['cohort_rank1_after']:.2f}%\n"
              f"Perda: {c['cohort_loss_pp']:.2f} pontos percentuais")
        ax.text(.02,.95,text,ha='left',va='top',transform=ax.transAxes,fontsize=10,linespacing=1.5,color='#203346')
    fig,axes=plt.subplots(4,5,figsize=(21,15),gridspec_kw={'width_ratios':[1,1,1,1,1.25]})
    for j,item in enumerate(selected):
        draw_row(axes[j],item)
        for k,header in enumerate(headers): axes[j,k].set_title(header,fontsize=11,pad=16)
        axes[j,0].text(0,1.23,item[0]['title'],transform=axes[j,0].transAxes,fontsize=13,fontweight='bold',color='#146b8c')
    fig.suptitle('Como as alterações prejudicaram o reconhecimento\nDINOv3 com recorte da U-Net · exemplos efetivamente testados no UBIPr',fontsize=21,y=.99)
    fig.text(.04,.015,'Contorno turquesa: máscara prevista. Recortes mostram a imagem usada antes do redimensionamento do DINOv3.\n'
             'Alterações sintéticas, não diagnósticos. Exemplos selecionados entre acerto → erro, próximos da mediana da queda de escore; não representam a frequência dos erros.\n'
             'A similaridade é um escore, não uma probabilidade. O percentual de perda à direita pertence à coorte completa, não a uma única imagem.',fontsize=11,color='#475569')
    fig.subplots_adjust(left=.025,right=.99,top=.89,bottom=.10,wspace=.12,hspace=.7)
    fig.savefig(OUT/'exemplos_recorte_perda_reconhecimento.png',dpi=160); plt.close(fig)
    for item in selected:
        fig,axes=plt.subplots(1,5,figsize=(21,4.6),gridspec_kw={'width_ratios':[1,1,1,1,1.25]})
        draw_row(axes,item)
        for ax,title in zip(axes,headers): ax.set_title(title,fontsize=11,pad=12)
        fig.suptitle(item[0]['title']+' · DINOv3 com recorte U-Net',fontsize=19,y=.99)
        fig.text(.025,.025,'Alteração sintética testada, sem diagnóstico. Caso ilustrativo de acerto → erro. Similaridade não é probabilidade; perda percentual refere-se à coorte.',fontsize=11)
        fig.subplots_adjust(left=.025,right=.99,top=.80,bottom=.15,wspace=.12)
        fig.savefig(OUT/f"exemplos_recorte_{item[0]['kind']}.png",dpi=170); plt.close(fig)
    (OUT/'exemplos_recorte_selecao.json').write_text(json.dumps([c for c,_,_ in selected],indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps([c for c,_,_ in selected],indent=2,ensure_ascii=False))


if __name__=='__main__': main()

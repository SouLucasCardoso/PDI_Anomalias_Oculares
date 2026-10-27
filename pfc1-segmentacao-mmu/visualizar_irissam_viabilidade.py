"""Figura de seis casos fixos do protocolo; contornos reais, sem imagens sinteticas."""
from pathlib import Path
import argparse,json
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from avaliar_irissam_ubipr import ROOT,NAME,metrics,affected_support
from treinar_segmentacao_ubipr import decode_mask
from avaliar_robustez_reconhecimento import perturb

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();folder=a.root/NAME
    protocol=json.loads((folder/'protocolo.json').read_text());fig,axes=plt.subplots(6,3,figsize=(12,17))
    with np.load(folder/'mascaras_empacotadas.npz') as masks:
        for row_index,(i,tag) in enumerate([(0,'clean'),(0,'upper10'),(0,'lower10'),(1,'clean'),(1,'upper10'),(1,'lower10')]):
            row=protocol['sample'][i]
            with Image.open(ROOT/'data/ubipr/single_eye'/row['image']) as im:photo=im.convert('RGB')
            with Image.open(ROOT/'data/ubipr/single_eye'/row['mask']) as im:truth=decode_mask(im)==1
            kind={'clean':'original','upper10':'oclusao_superior','lower10':'oclusao_inferior'}[tag];photo,_=perturb(photo,truth,kind,0 if tag=='clean' else 10);visible=truth&~affected_support(truth,tag)
            for col,method in enumerate([None,'unet','irissam_auto_unet_box']):
                ax=axes[row_index,col];ax.imshow(photo);ax.axis('off')
                if method is None:ax.set_title(f"{row['image']} | {tag}",fontsize=9)
                else:
                    shape=tuple(masks[f'{i:02}_{tag}_shape']);pred=np.unpackbits(masks[f'{i:02}_{tag}_{method}'],count=int(np.prod(shape))).reshape(shape).astype(bool)
                    if visible.any():ax.contour(visible,levels=[.5],colors=['lime'],linewidths=.8)
                    if pred.any() and not pred.all():ax.contour(pred,levels=[.5],colors=['cyan'],linewidths=.8)
                    title='U-Net atual' if method=='unet' else 'Iris-SAM + caixa U-Net';ax.set_title(f'{title} | Dice visivel {100*metrics(pred,visible)["dice"]:.2f}%',fontsize=9)
    fig.suptitle('Primeiras duas pessoas do protocolo, sem selecao por qualidade\nVerde: referencia visivel. Ciano: predicao. Oclusoes simuladas de 10%.',fontsize=12)
    fig.tight_layout(rect=(0,0,1,.96));target=folder/'comparacao_recortes_irissam.png';fig.savefig(target,dpi=140);plt.close(fig);print(target)
if __name__=='__main__':main()

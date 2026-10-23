"""Comparacao real antes/depois, selecao por arquivo, nao por ganho de acuracia."""
from pathlib import Path
import json,tempfile
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parent


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out=ROOT/'outputs/pupila_aprendida_val_2026-10-22';completed=json.loads((out/'CONCLUIDO.json').read_text())
    if completed['status']!='pupil_locator_identity_validation_completed':raise ValueError('Recognition evaluation not completed')
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());raw=manifest['val'];key=lambda r:f"{r['subject']}_{r['side']}"
    eligible={key(r) for r in raw if r['session']==1}&{key(r) for r in raw if r['session']==2};rows=[r for r in raw if key(r) in eligible];qi=[i for i,r in enumerate(rows) if r['session']==2];query_index={i:j for j,i in enumerate(qi)}
    with np.load(out/'changed_inputs_clean.npz') as z:indices=z['indices'];polars=z['polar']
    old=np.load(Path(tempfile.gettempdir())/'cache_confirmacao_val_2026-10-21/polar.npy',mmap_mode='r')
    with np.load(out/'scores_original_control_clean.npz') as z:before=z['correct']
    with np.load(out/'scores_new_fixed_clean.npz') as z:after=z['correct']
    positions={int(index):j for j,index in enumerate(indices)};selected=[];people=set()
    for i in sorted((int(i) for i in indices if rows[i]['session']==2),key=lambda i:Path(rows[i]['image']).name):
        if rows[i]['subject'] not in people:selected.append(i);people.add(rows[i]['subject'])
        if len(selected)==4:break
    fig,axes=plt.subplots(len(selected),3,figsize=(15,3*len(selected)),squeeze=False)
    for line,i in enumerate(selected):
        row=rows[i];q=query_index[i]
        with Image.open(ROOT/'data/ubipr/single_eye'/Path(row['image']).name) as image:rgb=np.asarray(image.convert('RGB'))
        titles=[Path(row['image']).name,f"Polar original | {'acerto' if before[q] else 'erro'}",f"Nova pupila, calibracao fixa | {'acerto' if after[q] else 'erro'}"]
        for col,(image,title) in enumerate(zip([rgb,old[i],polars[positions[i]]],titles)):
            axes[line,col].imshow(image);axes[line,col].set_title(title,fontsize=9);axes[line,col].axis('off')
    fig.suptitle('Primeiras quatro pessoas com pupila fallback, por ordem de arquivo\nTextura real reamostrada; sem geracao/restauracao. Exemplos nao selecionados por melhora.',fontsize=11)
    fig.tight_layout(rect=(0,0,1,.95));target=out/'qa_pupila_comparacao.png';fig.savefig(target,dpi=150);plt.close(fig)
    (out/'AMOSTRAS.json').write_text(json.dumps(dict(images=[Path(rows[i]['image']).name for i in selected],selection='First4distinct subjects among clean changed queries sorted by filename; no correctness/score selection',figure=target.name),indent=2),encoding='utf-8');print(target)


if __name__=='__main__':main()

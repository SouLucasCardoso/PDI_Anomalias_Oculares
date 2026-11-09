"""Escolhe um contorno por Dice de validação, antes de avaliar reconhecimento."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,traceback
import cv2,numpy as np,torch
from PIL import Image,ImageDraw,ImageOps,ImageFont
from contorno_guiado_iris import SPECS,cpu_margins,refine_margin
from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
from avaliar_robustez_reconhecimento import perturb
from recorte_iris_sam31_alta_res import antialiased_crop
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def visible_reference(reference,direction,level):
    out=reference.copy()
    if direction=='original':return out
    ys,xs=np.where(reference);order=np.lexsort((xs,ys if direction.endswith('superior') else -ys))
    take=order[:round(len(xs)*level/100)];out[ys[take],xs[take]]=False
    return out


def board(photo,masks,labels,path):
    canvas=Image.new('RGB',(1800,630),'white');draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
    for i,(mask,label) in enumerate(zip(masks,labels)):
        crop=antialiased_crop(photo,mask);black=Image.new('RGBA',crop.size,'black');black.alpha_composite(crop)
        panel=ImageOps.pad(black.convert('RGB'),(580,560),method=Image.Resampling.LANCZOS)
        canvas.paste(panel,(600*i+10,55));draw.text((600*i+12,12),label,font=font,fill='black')
        if not mask.any():draw.text((600*i+30,310),'SEM SUPORTE / REVISAR',font=font,fill='#ffb34b')
    canvas.save(path)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args()
    run=a.run_dir.resolve();run.mkdir(parents=True,exist_ok=False)
    rows_file=ROOT/'outputs/refino_recorte_validacao_2026-11-08/protocolo.json'
    rows=json.loads(rows_file.read_text())['rows'];assert len(rows)==78
    checkpoint=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    assert sha(checkpoint)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    sources={n:sha(ROOT/n) for n in ('contorno_guiado_iris.py','avaliar_refino_guiado_entrega.py','treinar_segmentacao_ubipr.py')}
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'specs':SPECS,
        'source_sha256':sources,'checkpoint_sha256':sha(checkpoint),'rows_sha256':sha(rows_file),
        'rows':rows,'conditions':[['original',0],['oclusao_superior',10],['oclusao_inferior',10]],
        'scope':'Repeated development segmentation validation; ground truth only defines intervention and evaluation, never extraction',
        'selection':'Require each of3meanDice no lower than continuous reference and mean3 strictly higher; choose greatest mean3 then clean. Noeligible=>retaincontinuous. Freeze before identity validation.',
        'method':'Original and horizontal-flip mean logits; native bilinear margin; optional gray-guided filter r2/r4 at240px,eps.001/.01,changeonly|margin|<=1. No geometry completion, texture edit or topology filling.',
        'primary_method_source':'https://people.csail.mit.edu/kaiming/eccv10/index.html',
        'clinical_policy':'Fixed6previouscases, no clinical ground truth. Previously empty support remains review-only; raw candidate preserved.'}
    (run/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    (run/'source.py').write_bytes(Path(__file__).read_bytes());torch.set_num_threads(2);cv2.setNumThreads(1)
    model=MulticlassUNet(8).eval();model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
    records=[];means={name:{} for name in SPECS};samples=[]
    def dice(a,b):return float((2*(a&b).sum()+1e-6)/(a.sum()+b.sum()+1e-6))
    try:
        for condition,level in protocol['conditions']:
            for i,row in enumerate(rows):
                original=Image.open(row['image']).convert('RGB');reference=decode_mask(Image.open(row['mask']))==1
                photo,_=perturb(original,reference,condition,level);truth=visible_reference(reference,condition,level)
                margins=cpu_margins(model,photo);scores={}
                for name,spec in SPECS.items():scores[name]=dice(refine_margin(photo,margins[int(spec['flip'])],spec),truth)
                records.append({'condition':condition,'image':Path(row['image']).name,'dice':scores})
                if i%13==0:
                    state={'stage':'segmentacao_validacao','condition':condition,'completed':len(records),'total':234}
                    (run/'estado.json').write_text(json.dumps(state),encoding='utf-8');print(json.dumps(state),flush=True)
            for name in SPECS:means[name][condition]=float(np.mean([r['dice'][name] for r in records if r['condition']==condition]))
        baseline=means['continuous']
        eligible=[n for n in SPECS if n!='continuous' and all(means[n][c]>=baseline[c] for c in baseline)
            and np.mean(list(means[n].values()))>np.mean(list(baseline.values()))]
        selected=max(eligible,key=lambda n:(np.mean(list(means[n].values())),means[n]['original'])) if eligible else 'continuous'
        selection={'frozen_utc':datetime.now(timezone.utc).isoformat(),'selected_method':selected,'spec':SPECS[selected],
            'segmentation_gain':selected!='continuous','baseline':baseline,'results':means,
            'checkpoint_sha256':sha(checkpoint),'method_sha256':sha(ROOT/'contorno_guiado_iris.py'),
            'identity_selection_performed':False,'test_inference':False}
        (run/'CANDIDATO_SEGMENTACAO.json').write_text(json.dumps(selection,indent=2),encoding='utf-8')
        for i,row in enumerate(rows[:3]):
            photo=Image.open(row['image']).convert('RGB');margins=cpu_margins(model,photo)
            small=cv2.resize(margins[0],(320,240),interpolation=cv2.INTER_LINEAR)>0
            old=np.asarray(Image.fromarray(small).resize(photo.size,Image.Resampling.NEAREST),bool)
            masks=[old,margins[0]>0,refine_margin(photo,margins[int(SPECS[selected]['flip'])],SPECS[selected])]
            board(photo,masks,['Rótulo ampliado','Confiança contínua',selected],run/f'validacao_{i+1}.png')
        from comparar_recortes_alta_res import NAMES
        clinical=json.loads((ROOT/'data/slpvld/manifesto.json').read_text(encoding='utf-8-sig'))
        clinical_records=[]
        for name in NAMES:
            row=next(r for r in clinical if Path(r['image']).name==name);photo=Image.open(row['image']).convert('RGB')
            margins=cpu_margins(model,photo,clinical=True);base=margins[0]>0
            candidate=refine_margin(photo,margins[int(SPECS[selected]['flip'])],SPECS[selected])
            folder=run/Path(name).stem;folder.mkdir();Image.fromarray(candidate.astype(np.uint8)*255).save(folder/'candidato_bruto.png')
            final=candidate if base.any() else base
            Image.fromarray(final.astype(np.uint8)*255).save(folder/'mascara_nativa.png')
            antialiased_crop(photo,final).save(folder/'recorte_nativo.png')
            board(photo,[base,candidate,final],['Anterior contínuo','Candidato bruto','Final / revisão se vazio'],folder/'comparacao.png')
            clinical_records.append({'image':name,'photo_sha256':sha(row['image']),'baseline_pixels':int(base.sum()),
                'candidate_pixels':int(candidate.sum()),'final_pixels':int(final.sum()),'native_rgb_unchanged':True,
                'review_required':True,'clinical_accuracy_measured':False})
        for n,expected in sources.items():assert sha(ROOT/n)==expected
        result={'status':'concluido','selected':selection,'records':records,'clinical':clinical_records,
            'recognizer_replaced':False,'clinical_accuracy_claimed':False}
        (run/'CONCLUIDO.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        lines=['# Refino do contorno por bordas e simetria','',f'Candidato selecionado por segmentação: **{selected}**. Reconhecimento ainda não validado.','',
            '| Método | Dice limpo | Dice perda superior10% | Dice perda inferior10% |','|---|---:|---:|---:|']
        for name,v in means.items():lines.append(f"| {name} | {100*v['original']:.3f}% | {100*v['oclusao_superior']:.3f}% | {100*v['oclusao_inferior']:.3f}% |")
        lines+=['','78 imagens, uma por lado das39pessoas, em3condições. O Dice ocluído considera somente a região anotada ainda visível. Referências nunca entram no extrator. Casos clínicos sem referência especializada permanecem ilustrativos e sujeitos a revisão.','',
            '[Método de filtragem guiada, He et al.](https://people.csail.mit.edu/kaiming/eccv10/index.html)']
        (run/'RELATORIO_ATUAL.md').write_text('\n'.join(lines),encoding='utf-8')
        (run/'estado.json').write_text(json.dumps({'stage':'concluido','selected':selected}),encoding='utf-8')
        print(json.dumps(selection),flush=True)
    except BaseException as error:
        (run/'ERRO.txt').write_text(traceback.format_exc(),encoding='utf-8');raise


if __name__=='__main__':main()

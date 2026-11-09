"""Seleção limitada de escalas apenas na validação de segmentação."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,traceback
import cv2,numpy as np,torch
from PIL import Image
from contorno_multiescala_iris import SPECS,margin_at_size,combined_mask
from avaliar_refino_guiado_entrega import visible_reference,board
from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
from avaliar_robustez_reconhecimento import perturb
from recorte_iris_sam31_alta_res import antialiased_crop
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args()
    run=a.run_dir.resolve();run.mkdir(parents=True,exist_ok=False)
    rows_file=ROOT/'outputs/refino_recorte_validacao_2026-11-08/protocolo.json'
    rows=json.loads(rows_file.read_text())['rows'];assert len(rows)==78
    checkpoint=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    assert sha(checkpoint)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    sources={n:sha(ROOT/n) for n in ('contorno_multiescala_iris.py','avaliar_contorno_multiescala_entrega.py',
        'avaliar_refino_guiado_entrega.py','treinar_segmentacao_ubipr.py')}
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'specs':SPECS,'rows':rows,
        'source_sha256':sources,'checkpoint_sha256':sha(checkpoint),'rows_sha256':sha(rows_file),
        'conditions':[['original',0],['oclusao_superior',10],['oclusao_inferior',10]],
        'scope':'Reused segmentation validation; no identity or test inference',
        'method':'Frozen same U-Net at256x192,320x240,384x288,640x480; fixed convex mixtures of native bilinear iris-vs-other logit margins. No morphology, filling, texture or geometry completion.',
        'selection':'Each3meanDice must be no worse than continuous, mean3 strictly better. Max mean3, tie clean. Otherwise continuous reference. Clinical examples cannot choose parameters.'}
    (run/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    (run/'source.py').write_bytes(Path(__file__).read_bytes());torch.set_num_threads(2);cv2.setNumThreads(1)
    model=MulticlassUNet(8).eval();model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
    records=[];means={n:{} for n in SPECS}
    def dice(a,b):return float((2*(a&b).sum()+1e-6)/(a.sum()+b.sum()+1e-6))
    try:
        for condition,level in protocol['conditions']:
            for i,row in enumerate(rows):
                photo=Image.open(row['image']).convert('RGB');reference=decode_mask(Image.open(row['mask']))==1
                photo,_=perturb(photo,reference,condition,level);truth=visible_reference(reference,condition,level)
                bank={w:margin_at_size(model,photo,w)[0] for w in (256,320,384,640)}
                values={name:dice(combined_mask(bank,spec),truth) for name,spec in SPECS.items()}
                records.append({'condition':condition,'image':Path(row['image']).name,'dice':values})
                if i%13==0:
                    state={'stage':'segmentacao_validacao','condition':condition,'completed':len(records),'total':234}
                    (run/'estado.json').write_text(json.dumps(state),encoding='utf-8');print(json.dumps(state),flush=True)
            for name in SPECS:means[name][condition]=float(np.mean([r['dice'][name] for r in records if r['condition']==condition]))
        previous=json.loads((ROOT/'outputs/refino_guiado_entrega_2026-11-08/CANDIDATO_SEGMENTACAO.json').read_text())['baseline']
        for c in previous:assert abs(means['continuous'][c]-previous[c])<1e-12
        baseline=means['continuous'];eligible=[n for n in SPECS if n!='continuous' and all(means[n][c]>=baseline[c] for c in baseline)
            and np.mean(list(means[n].values()))>np.mean(list(baseline.values()))]
        selected=max(eligible,key=lambda n:(np.mean(list(means[n].values())),means[n]['original'])) if eligible else 'continuous'
        selection={'frozen_utc':datetime.now(timezone.utc).isoformat(),'selected_method':selected,'spec':SPECS[selected],
            'algorithm_module':'contorno_multiescala_iris','segmentation_gain':selected!='continuous',
            'baseline':baseline,'results':means,'checkpoint_sha256':sha(checkpoint),
            'method_sha256':sha(ROOT/'contorno_multiescala_iris.py'),'identity_selection_performed':False,'test_inference':False}
        (run/'CANDIDATO_SEGMENTACAO.json').write_text(json.dumps(selection,indent=2),encoding='utf-8')
        for i,row in enumerate(rows[:3]):
            photo=Image.open(row['image']).convert('RGB');bank={}
            bank[320],old=margin_at_size(model,photo,320)
            for w in SPECS[selected]:
                if w!=320:bank[w]=margin_at_size(model,photo,w)[0]
            board(photo,[old,bank[320]>0,combined_mask(bank,SPECS[selected])],
                ['Rótulo ampliado','Confiança contínua',selected],run/f'validacao_{i+1}.png')
        from comparar_recortes_alta_res import NAMES
        clinical=json.loads((ROOT/'data/slpvld/manifesto.json').read_text(encoding='utf-8-sig'));clinical_records=[]
        for name in NAMES:
            row=next(r for r in clinical if Path(r['image']).name==name);photo=Image.open(row['image']).convert('RGB')
            bank={320:margin_at_size(model,photo,320,True)[0]}
            for w in SPECS[selected]:
                if w!=320:bank[w]=margin_at_size(model,photo,w,True)[0]
            base=bank[320]>0;candidate=combined_mask(bank,SPECS[selected]);final=candidate if base.any() else base
            folder=run/Path(name).stem;folder.mkdir()
            Image.fromarray(candidate.astype(np.uint8)*255).save(folder/'candidato_bruto.png')
            Image.fromarray(final.astype(np.uint8)*255).save(folder/'mascara_nativa.png');antialiased_crop(photo,final).save(folder/'recorte_nativo.png')
            board(photo,[base,candidate,final],['Anterior contínuo','Candidato bruto','Final / revisão se vazio'],folder/'comparacao.png')
            clinical_records.append({'image':name,'photo_sha256':sha(row['image']),'baseline_pixels':int(base.sum()),
                'candidate_pixels':int(candidate.sum()),'final_pixels':int(final.sum()),'review_required':True,
                'native_rgb_unchanged':True,'clinical_accuracy_measured':False})
        for n,expected in sources.items():assert sha(ROOT/n)==expected
        final={'status':'concluido','selected':selection,'records':records,'clinical':clinical_records,'recognizer_replaced':False}
        (run/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8')
        lines=['# Contorno multiescala','',f'Candidato: **{selected}**, selecionado por segmentação. Reconhecimento pendente.','',
            '| Método | Dice limpo | Dice superior10% | Dice inferior10% |','|---|---:|---:|---:|']
        for n,v in means.items():lines.append(f"| {n} | {100*v['original']:.3f}% | {100*v['oclusao_superior']:.3f}% | {100*v['oclusao_inferior']:.3f}% |")
        lines+=['','Mesmas 78 imagens em três condições; referência somente na intervenção e avaliação. Os seis casos clínicos são ilustrativos, sem Dice ou efeito clínico medido. Suporte previamente vazio fica pendente de revisão, com candidato bruto preservado.']
        (run/'RELATORIO_ATUAL.md').write_text('\n'.join(lines),encoding='utf-8')
        (run/'estado.json').write_text(json.dumps({'stage':'concluido','selected':selected}),encoding='utf-8');print(json.dumps(selection),flush=True)
    except BaseException:
        (run/'ERRO.txt').write_text(traceback.format_exc(),encoding='utf-8');raise


if __name__=='__main__':main()

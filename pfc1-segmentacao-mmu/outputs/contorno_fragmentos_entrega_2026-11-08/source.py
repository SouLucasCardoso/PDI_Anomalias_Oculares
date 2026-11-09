"""Ablação conservadora de fragmentos, com todos os casos de validação retidos."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,traceback
import cv2,numpy as np,torch
from PIL import Image
from contorno_componentes_iris import SPECS,filter_mask
from contorno_multiescala_iris import margin_at_size
from avaliar_refino_guiado_entrega import visible_reference,board
from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
from avaliar_robustez_reconhecimento import perturb
from recorte_iris_sam31_alta_res import antialiased_crop
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args()
    run=a.run_dir.resolve();run.mkdir(parents=True,exist_ok=False)
    rows_file=ROOT/'outputs/refino_recorte_validacao_2026-11-08/protocolo.json';rows=json.loads(rows_file.read_text())['rows'];assert len(rows)==78
    checkpoint=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    sources={n:sha(ROOT/n) for n in ('avaliar_fragmentos_contorno_entrega.py','contorno_componentes_iris.py','contorno_multiescala_iris.py','avaliar_refino_guiado_entrega.py')}
    assert sha(checkpoint)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'specs':SPECS,'rows':rows,
        'sources_sha256':sources,'checkpoint_sha256':sha(checkpoint),'rows_sha256':sha(rows_file),
        'conditions':[['original',0],['oclusao_superior',10],['oclusao_inferior',10]],
        'method':'Continuous native margin followed by optional 1pixelopening and/or remove connected components below fixed fraction of largest component. Anti-extensive: never add pixels or fill holes. No GT extraction.',
        'selection':'Require each3meanDice no lower than continuous and mean3 strictly better; max mean3, then clean. If none retain continuous. Identity not evaluated here.'}
    (run/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(run/'source.py').write_bytes(Path(__file__).read_bytes())
    torch.set_num_threads(2);cv2.setNumThreads(1);model=MulticlassUNet(8).eval();model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
    records=[];means={n:{} for n in SPECS}
    try:
        for condition,level in protocol['conditions']:
            for i,row in enumerate(rows):
                photo=Image.open(row['image']).convert('RGB');reference=decode_mask(Image.open(row['mask']))==1
                photo,_=perturb(photo,reference,condition,level);truth=visible_reference(reference,condition,level)
                margin,_=margin_at_size(model,photo,320);base=margin>0;values={}
                for name,spec in SPECS.items():
                    mask=filter_mask(base,spec);values[name]=float((2*(mask&truth).sum()+1e-6)/(mask.sum()+truth.sum()+1e-6))
                records.append({'condition':condition,'image':Path(row['image']).name,'dice':values})
                if i%13==0:(run/'estado.json').write_text(json.dumps({'stage':'segmentacao_validacao','completed':len(records),'total':234}),encoding='utf-8')
            for n in SPECS:means[n][condition]=float(np.mean([r['dice'][n] for r in records if r['condition']==condition]))
        baseline=means['continuous'];previous=json.loads((ROOT/'outputs/refino_guiado_entrega_2026-11-08/CANDIDATO_SEGMENTACAO.json').read_text())['baseline']
        for c in previous:assert abs(baseline[c]-previous[c])<1e-12
        eligible=[n for n in SPECS if n!='continuous' and all(means[n][c]>=baseline[c] for c in baseline) and np.mean(list(means[n].values()))>np.mean(list(baseline.values()))]
        selected=max(eligible,key=lambda n:(np.mean(list(means[n].values())),means[n]['original'])) if eligible else 'continuous'
        selection={'frozen_utc':datetime.now(timezone.utc).isoformat(),'selected_method':selected,'spec':SPECS[selected],
            'algorithm_module':'contorno_componentes_iris','segmentation_gain':selected!='continuous','baseline':baseline,'results':means,
            'checkpoint_sha256':sha(checkpoint),'method_sha256':sha(ROOT/'contorno_componentes_iris.py'),'identity_selection_performed':False,'test_inference':False}
        (run/'CANDIDATO_SEGMENTACAO.json').write_text(json.dumps(selection,indent=2),encoding='utf-8')
        for i,row in enumerate(rows[:3]):
            photo=Image.open(row['image']).convert('RGB');margin,old=margin_at_size(model,photo,320);mask=filter_mask(margin>0,SPECS[selected])
            board(photo,[old,margin>0,mask],['Rótulo ampliado','Confiança contínua',selected],run/f'validacao_{i+1}.png')
        from comparar_recortes_alta_res import NAMES
        clinical=json.loads((ROOT/'data/slpvld/manifesto.json').read_text(encoding='utf-8-sig'));clinical_records=[]
        for name in NAMES:
            row=next(r for r in clinical if Path(r['image']).name==name);photo=Image.open(row['image']).convert('RGB')
            margin,old=margin_at_size(model,photo,320,True);base=margin>0;mask=filter_mask(base,SPECS[selected]);folder=run/Path(name).stem;folder.mkdir()
            Image.fromarray(mask.astype(np.uint8)*255).save(folder/'mascara_nativa.png');antialiased_crop(photo,mask).save(folder/'recorte_nativo.png')
            board(photo,[old,base,mask],['Rótulo ampliado','Confiança contínua','Novo / revisão se vazio'],folder/'comparacao.png')
            clinical_records.append({'image':name,'photo_sha256':sha(row['image']),'baseline_pixels':int(base.sum()),'final_pixels':int(mask.sum()),
                'components_before':cv2.connectedComponents(base.astype(np.uint8),8)[0]-1,'components_after':cv2.connectedComponents(mask.astype(np.uint8),8)[0]-1,
                'no_added_pixels':True,'native_rgb_unchanged':True,'review_required':True,'clinical_accuracy_measured':False})
        for n,expected in sources.items():assert sha(ROOT/n)==expected
        result={'status':'concluido','selected':selection,'records':records,'clinical':clinical_records,'recognizer_replaced':False}
        (run/'CONCLUIDO.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        lines=['# Remoção conservadora de fragmentos','',f'Candidato: **{selected}**, selecionado por segmentação; reconhecimento pendente.','',
            '| Método | Dice limpo | Dice superior10% | Dice inferior10% |','|---|---:|---:|---:|']
        for n,v in means.items():lines.append(f"| {n} | {100*v['original']:.3f}% | {100*v['oclusao_superior']:.3f}% | {100*v['oclusao_inferior']:.3f}% |")
        lines+=['','234 avaliações, sem retirar falhas ou completar pixels de íris. O filtro também pode remover fragmentos reais: há validação limitada e revisão clínica pendente. Não se atribui ganho de identificação a uma máscara mais limpa.']
        (run/'RELATORIO_ATUAL.md').write_text('\n'.join(lines),encoding='utf-8');(run/'estado.json').write_text(json.dumps({'stage':'concluido','selected':selected}),encoding='utf-8')
        print(json.dumps(selection),flush=True)
    except BaseException:
        (run/'ERRO.txt').write_text(traceback.format_exc(),encoding='utf-8');raise


if __name__=='__main__':main()

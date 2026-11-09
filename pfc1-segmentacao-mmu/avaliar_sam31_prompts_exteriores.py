"""Dois prompts SAM3.1 predefinidos, com extensão condicional às oclusões."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,time,traceback
import cv2,numpy as np,torch
from PIL import Image
from sam31_negativos_exteriores import ExteriorSam31
from contorno_multiescala_iris import margin_at_size
from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
from avaliar_robustez_reconhecimento import perturb
from avaliar_refino_guiado_entrega import visible_reference,board
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--baseline-run',type=Path,required=True);a=p.parse_args()
    run=a.run_dir.resolve();run.mkdir(parents=True,exist_ok=False);pause=a.baseline_run.resolve()/'PAUSAR_PARA_REFINO'
    rows_file=ROOT/'outputs/refino_recorte_validacao_2026-11-08/protocolo.json';rows=json.loads(rows_file.read_text())['rows'];assert len(rows)==78
    vf=ROOT/'outputs/tecnologias_grade_densa_2026-11-08.json';versions=json.loads(vf.read_text(encoding='utf-8-sig'))
    assert versions['code_revision']=='f1647e8d0c1d280991f4d1b7d974c2704537fe66' and versions['checkpoint_revision']=='daa63191845a41281374e725f4c9e51c7a824460'
    sources={n:sha(ROOT/n) for n in ('avaliar_sam31_prompts_exteriores.py','sam31_negativos_exteriores.py','recorte_iris_sam31_alta_res.py','contorno_multiescala_iris.py')}
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'positive_counts':[16,24],'negative_points':'Up to8sectors in border-connected coarse-background band4%-8%ofpredicteddiameter; no reference prompts',
        'scope':'Reused segmentation validation only; no identity or test selection','rows':rows,'sources_sha256':sources,'official_versions':versions,
        'selection':'Choose greatest clean meanDice among2fixedprompts only if>=continuousbaseline; then fixedwinner alone evaluated on both10%occlusions. Require all3Dice no lower and mean3higher to recommend. Otherwise no promotion.',
        'fallback':'If prediction/negative constraints fail, retain original nearest coarse seed; count all78cases and report fallback. No texture or hole filling.',
        'stop_utc':'2026-11-09T01:45:00+00:00'}
    (run/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(run/'source.py').write_bytes(Path(__file__).read_bytes())
    def stage(name,**extra):(run/'estado.json').write_text(json.dumps({'stage':name,'utc':datetime.now(timezone.utc).isoformat(),**extra}),encoding='utf-8')
    owns=False;sam=None
    try:
        while pause.exists():stage('aguardando_outro_refino');time.sleep(2)
        pause.write_text('Ensaio curto SAM3.1; liberação automática no finally.',encoding='utf-8');owns=True
        while True:
            s=json.loads((a.baseline_run/'estado.json').read_text())
            if s['stage'] in ('aguardando_refino_validacao','concluido','falha','parcial_por_limite_horario'):break
            stage('aguardando_fronteira_segura_gpu');time.sleep(2)
        torch.set_num_threads(2);cv2.setNumThreads(1);unet=MulticlassUNet(8).eval()
        checkpoint=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';assert sha(checkpoint)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
        unet.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model']);stage('carregando_sam31');sam=ExteriorSam31('cuda')
        (run/'SAM_ESTRITO.json').write_text(json.dumps(sam.audit,indent=2),encoding='utf-8')
        records=[]
        def dice(m,t):return float((2*(m&t).sum()+1e-6)/(m.sum()+t.sum()+1e-6))
        def evaluate(condition,counts):
            for i,row in enumerate(rows):
                if datetime.now(timezone.utc)>=datetime.fromisoformat(protocol['stop_utc']):raise TimeoutError('Limite do ensaio SAM; referência preservada')
                photo=Image.open(row['image']).convert('RGB');reference=decode_mask(Image.open(row['mask']))==1
                level=0 if condition=='original' else 10;photo,_=perturb(photo,reference,condition,level);truth=visible_reference(reference,condition,level)
                margin,seed=margin_at_size(unet,photo,320);sam.cache={};result={'condition':condition,'image':Path(row['image']).name,'continuous':dice(margin>0,truth),'variants':{}}
                for count in counts:
                    status='sam31';detail={}
                    try:mask,detail=sam.refine_variant(photo,seed,count)
                    except ValueError as error:mask=seed;status='coarse_fallback';detail={'reason':str(error)}
                    folder=run/f'positive{count}'/condition;folder.mkdir(parents=True,exist_ok=True)
                    Image.fromarray(mask.astype(np.uint8)*255).save(folder/(Path(row['image']).stem+'.png'))
                    result['variants'][str(count)]={'dice':dice(mask,truth),'status':status,'detail':detail}
                records.append(result);sam.cache={};sam.features=None
                if i%6==0:stage('avaliando_prompts',condition=condition,completed=i+1,total=78);print(json.dumps({'condition':condition,'completed':i+1}),flush=True)
        evaluate('original',(16,24));clean=[r for r in records if r['condition']=='original'];baseline=float(np.mean([r['continuous'] for r in clean]))
        means={str(c):float(np.mean([r['variants'][str(c)]['dice'] for r in clean])) for c in (16,24)}
        eligible=[c for c in (16,24) if means[str(c)]>=baseline];selected=max(eligible,key=lambda c:means[str(c)]) if eligible else None
        summary={'original':{'baseline':baseline,**means}}
        if selected is not None:
            for condition in ('oclusao_superior','oclusao_inferior'):
                evaluate(condition,(selected,));rs=[r for r in records if r['condition']==condition]
                summary[condition]={'baseline':float(np.mean([r['continuous'] for r in rs])),str(selected):float(np.mean([r['variants'][str(selected)]['dice'] for r in rs]))}
        gate=bool(selected is not None and all(v[str(selected)]>=v['baseline'] for v in summary.values()) and np.mean([v[str(selected)]-v['baseline'] for v in summary.values()])>0)
        for n,expected in sources.items():assert sha(ROOT/n)==expected
        final={'status':'concluido','selected_clean':selected,'segmentation_gate_passed':gate,'summary':summary,'records':records,'recognizer_replaced':False,'clinical_accuracy_claimed':False}
        (run/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8')
        lines=['# SAM3.1 com pontos negativos exteriores','',f'Critério de segmentação aprovado: **{gate}**. Sem novo teste de reconhecimento ou alteração do aplicativo.','',
            '| Condição | Método | Dice médio | Fallbacks |','|---|---|---:|---:|']
        for condition,values in summary.items():
            rs=[r for r in records if r['condition']==condition]
            for name,value in values.items():
                fallback=0 if name=='baseline' else sum(r['variants'][name]['status']=='coarse_fallback' for r in rs)
                lines.append(f'| {condition} | {name} | {100*value:.3f}% | {fallback}/{len(rs)} |')
        lines+=['','Todas as imagens e falhas foram mantidas. As anotações definem somente a intervenção e o Dice, nunca os prompts. Fallbacks tornam esse procedimento híbrido; não se atribui o Dice somente ao SAM. Validação reutilizada, sem medida clínica.']
        (run/'RELATORIO_ATUAL.md').write_text('\n'.join(lines),encoding='utf-8');stage('concluido',segmentation_gate_passed=gate)
        print(json.dumps({'summary':summary,'gate':gate}),flush=True)
    except BaseException as error:
        stage('falha',error=str(error));(run/'ERRO.txt').write_text(traceback.format_exc(),encoding='utf-8');raise
    finally:
        if sam is not None:sam.close()
        if owns:pause.unlink(missing_ok=True)


if __name__=='__main__':main()

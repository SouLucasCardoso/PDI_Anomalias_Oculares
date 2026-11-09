"""Valida três grupos fixos do contorno selecionado antes de abrir novos testes."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,time,traceback
import cv2,numpy as np,torch
from entradas_contorno_componentes import prepare
from treinar_segmentacao_ubipr import MulticlassUNet
from treinar_identidade_iris import IdentityEncoder
from avaliar_candidato_congelado import extract,global_scores,fuse,WEIGHTS
from avaliar_robustez_reconhecimento import load_splits,identity,metrics
from validar_lateralidade_informada import subset
from treinar_reconhecedor_entrega import ORDER,CONDITIONS,eligibility,selection_key
from rodada_reconhecedor_entrega import result_path,write
import reconhecedor_resnet50
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
GROUPS={'polar_only':('polar',),'native_only':('native',),'native_and_polar':('native','polar')}


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True)
    p.add_argument('--segmentation-run',type=Path,required=True);p.add_argument('--baseline-run',type=Path,required=True);a=p.parse_args()
    run=a.run_dir.resolve();run.mkdir(parents=True,exist_ok=False);pause=a.baseline_run.resolve()/'PAUSAR_PARA_REFINO'
    selection_file=a.segmentation_run.resolve()/'CANDIDATO_SEGMENTACAO.json';selection=json.loads(selection_file.read_text());assert selection['segmentation_gain']
    assert selection['method_sha256']==sha(ROOT/'contorno_componentes_iris.py')
    manifest=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';rows=load_splits(json.loads(manifest.read_text()))['val']
    reference=ROOT/'outputs/reconhecedor_contorno_2026-11-08';frozen_file=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json'
    config=json.loads(frozen_file.read_text());threshold=config['frozen_threshold'];ids=sorted({identity(r) for r in rows})
    source_names=('validar_identidade_contorno_componentes.py','entradas_contorno_componentes.py',
        'contorno_componentes_iris.py','contorno_multiescala_iris.py','avaliar_candidato_congelado.py','avaliar_robustez_reconhecimento.py')
    sources={n:sha(ROOT/n) for n in source_names}
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'sources_sha256':sources,
        'selection_sha256':sha(selection_file),'segmentation_selection':selection,'groups':GROUPS,
        'threshold':threshold,'calibration_sha256':sha(frozen_file),'manifest_sha256':sha(manifest),
        'scope':'Reused validation only. Change only named native/polar components, original other inputs and frozen calibration. All482queries retained. No test or automatic promotion.',
        'selection':'Same relative gate: cleanRank1/TAR no lower,cleanFMR<=1%,eachoccludedFMR no greater,mean3joint strictlyhigher. Max meanjoint,worstjoint,meanRank1.',
        'new_input_policy':'Continuous native margin plus selected anti-extensive component filter; original component availability retained and original inputs fallback on failure.'}
    write(run/'protocolo.json',protocol);(run/'source.py').write_bytes(Path(__file__).read_bytes())
    def stage(name,**extra):write(run/'estado.json',{'stage':name,'utc':datetime.now(timezone.utc).isoformat(),'pid':os.getpid(),**extra})
    owns_pause=False
    try:
        torch.set_num_threads(2);cv2.setNumThreads(1);model=MulticlassUNet(8).eval()
        checkpoint=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';assert sha(checkpoint)==selection['checkpoint_sha256']
        model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model']);inputs={};gallery=None
        for condition,level in CONDITIONS:
            suffix='' if condition=='original' else f'_{condition}_{level}'
            cache=reference/f'nearest/cache_confirmacao_val{suffix}_2026-10-21'
            def progress(i,n):stage('preparando_cpu',condition=condition,completed=i,total=n)
            x,rv,pv,gallery=prepare(rows,condition,level,cache,run/condition,model,selection['spec'],gallery,progress)
            inputs[condition]=(x,rv,pv)
        del model
        stage('aguardando_gpu_segura');pause.write_text('Validação dos componentes; remover automaticamente no finally.',encoding='utf-8');owns_pause=True
        while True:
            state=json.loads((a.baseline_run/'estado.json').read_text())
            if state['stage'] in ('aguardando_refino_validacao','concluido','parcial_por_limite_horario','falha'):break
            time.sleep(2)
        device=torch.device('cuda');new={c:{} for c,_ in CONDITIONS}
        for name in ('polar','native'):
            file=ROOT/'outputs'/WEIGHTS[name][0]/'melhor_modelo.pt';assert sha(file)==WEIGHTS[name][1]
            if name=='polar':model=IdentityEncoder().to(device).eval();model.load_state_dict(torch.load(file,map_location='cpu',weights_only=True)['model'])
            else:model,_=reconhecedor_resnet50.load(file,device)
            for condition,_ in CONDITIONS:
                stage('extraindo_gpu',component=name,condition=condition)
                x,rv,pv=inputs[condition];full,valid=global_scores(extract(model,x[name],device),pv if name=='polar' else rv,rows)
                scores,labels,_=subset(full,rows,ids);new[condition][name]={'scores':scores,'labels':labels,'valid':valid}
                np.savez_compressed(run/condition/f'scores_{name}.npz',**new[condition][name])
            del model;torch.cuda.empty_cache()
        pause.unlink();owns_pause=False
        baseline={};results={n:{} for n in GROUPS}
        for condition,level in CONDITIONS:
            old=[]
            for name in ORDER:
                with np.load(result_path(reference,'nearest',condition,level)/f'scores_{name}.npz') as z:old.append({k:z[k].copy() for k in ('scores','labels','valid')})
            for name,data in new[condition].items():np.testing.assert_array_equal(data['labels'],old[ORDER.index(name)]['labels'])
            for group,names in {'reference':(),**GROUPS}.items():
                chosen=[new[condition][n] if n in names else old[i] for i,n in enumerate(ORDER)]
                scores,valid=fuse(chosen,config['component_calibration_red_and_clahe']);labels=old[0]['labels']
                m,c,accepted=metrics(scores,labels,threshold,valid);m['joint_success']=float((c&accepted).mean());assert m['queries']==482
                (baseline if group=='reference' else results[group])[condition]=m
                np.savez_compressed(run/f'fusion_{group}_{condition}.npz',scores=scores,labels=labels,valid=valid,correct=c,accepted=accepted)
        eligible=[n for n,r in results.items() if eligibility(r,baseline)];selected=max(eligible,key=lambda n:selection_key(results[n])) if eligible else None
        final={'status':'concluido','selected_group':selected,'eligible_gain':selected is not None,
            'baseline':baseline,'results':results,'test_inference':False,'recognizer_replaced':False}
        for n,expected in sources.items():assert sha(ROOT/n)==expected
        write(run/'CONCLUIDO.json',final)
        if selected:write(run/'CANDIDATO_IDENTIDADE.json',{'frozen_utc':datetime.now(timezone.utc).isoformat(),'group':selected,
            'components':GROUPS[selected],'spec':selection['spec'],'segmentation_selection_sha256':sha(selection_file),
            'validation_protocol_sha256':sha(run/'protocolo.json'),'threshold':threshold,'validation':results[selected]})
        lines=['# Identidade com remoção de fragmentos','',f'Candidato elegível: **{selected or "nenhum"}**.','',
            '| Grupo | Condição | Rank-1 | TAR | FMR | Correto e aceito |','|---|---|---:|---:|---:|---:|']
        for group,data in {'reference':baseline,**results}.items():
            for condition,m in data.items():lines.append(f"| {group} | {condition} | {100*m['rank1']:.2f}% | {100*m['tar']:.2f}% | {100*m['far']:.3f}% | {100*m['joint_success']:.2f}% |")
        lines+=['','Pesos e limiar fixos. Validação reutilizada no desenvolvimento, sem confirmação independente. Todas as 482 consultas e as falhas foram mantidas.']
        (run/'RELATORIO_ATUAL.md').write_text('\n'.join(lines),encoding='utf-8');stage('concluido',selected_group=selected);print(json.dumps(final),flush=True)
    except BaseException as error:
        stage('falha',error=str(error));(run/'ERRO.txt').write_text(traceback.format_exc(),encoding='utf-8');raise
    finally:
        if owns_pause:pause.unlink(missing_ok=True)


if __name__=='__main__':main()

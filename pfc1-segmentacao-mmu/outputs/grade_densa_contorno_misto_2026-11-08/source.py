"""Congela o candidato validado e compara todos os 63 cenários, sem novo ajuste."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,time,traceback
import cv2,numpy as np,torch
from PIL import Image
from contorno_componentes_iris import predict_mask
from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
from textura_polar import prepare_texture
from treinar_identidade_iris import IdentityEncoder
from avaliar_candidato_congelado import extract,global_scores,fuse,WEIGHTS
from avaliar_robustez_reconhecimento import perturb,load_splits,identity,metrics
from validar_lateralidade_informada import subset
from treinar_reconhecedor_entrega import ORDER
from rodada_reconhecedor_entrega import write
from misturar_contorno_componentes import blend
ROOT=Path(__file__).resolve().parent
SCHEDULE=[('original',0)]+[(d,n) for n in range(1,32) for d in ('oclusao_superior','oclusao_inferior')]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def measured(scores,labels,valid,threshold):
    m,c,a=metrics(scores,labels,threshold,valid);m['joint_success']=float((c&a).mean())
    imp=np.ones(scores.shape,bool);imp[np.arange(len(labels)),labels]=False
    false=((scores>=threshold)&valid[:,None]&imp).sum(1)
    counts={'queries':len(labels),'correct':int(c.sum()),'accepted':int(a.sum()),'joint':int((c&a).sum()),
        'false_accepts':int(false.sum()),'impostors':int(imp.sum()),'extraction_failures':int((~valid).sum())}
    return m,counts,np.column_stack((c,a,c&a,false)).astype(float)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True)
    p.add_argument('--baseline-run',type=Path,required=True);p.add_argument('--selection-run',type=Path,required=True);a=p.parse_args()
    run=a.run_dir.resolve();run.mkdir(parents=True,exist_ok=False);base=a.baseline_run.resolve()
    selection_file=a.selection_run.resolve()/'CANDIDATO_IDENTIDADE.json';selection=json.loads(selection_file.read_text())
    assert selection['components']==['polar'] and selection['alpha']==.5
    checkpoint=ROOT/'outputs/encoder_polar_2026-10-20/melhor_modelo.pt';assert sha(checkpoint)==WEIGHTS['polar'][1]
    frozen_file=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json';config=json.loads(frozen_file.read_text());threshold=config['frozen_threshold'];assert threshold==selection['threshold']
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_file.read_text());rows=load_splits(manifest)['test']
    qi=[i for i,r in enumerate(rows) if r.session==2];gi=[i for i,r in enumerate(rows) if r.session==1]
    subjects=np.array([rows[i].subject for i in qi]);people=np.unique(subjects);assert len(qi)==486 and len(people)==16
    assert not set(subjects)&{r['subject'] for r in manifest['train']}
    names=('confirmar_grade_densa_contorno.py','contorno_componentes_iris.py','contorno_multiescala_iris.py',
        'misturar_contorno_componentes.py','avaliar_candidato_congelado.py','avaliar_robustez_reconhecimento.py','normalizar_consulta.py','textura_polar.py')
    sources={n:sha(ROOT/n) for n in names};old=ROOT/'outputs/ensaio_oclusoes_2026-11-08'
    anchors={(r['condition'],r['loss_percent']) for r in json.loads((old/'resultados.json').read_text()) if r['model']=='historico'}
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sources,
        'selection_sha256':sha(selection_file),'selection':selection,'checkpoint_sha256':sha(checkpoint),
        'calibration_sha256':sha(frozen_file),'manifest_sha256':sha(manifest_file),'schedule':SCHEDULE,
        'comparison':'Change only polar raw score, half original plus half cleaned-contour; other8 scores, weights, calibration and threshold unchanged. Original component availability and all failures retained.',
        'gate':'CleanRank1/TAR no lower and cleanFMR<=1%; mean63joint higher; FMR no greater in every63condition. Report local gains separately. No model/app replacement.',
        'bootstrap':'Paired query-person5000draws seed20261108 fixedgallery, descriptive, data already exposed',
        'scope':'Repeated development, not blind test or clinical effect. No parameter selection using these63conditions.',
        'preparation_stop_utc':'2026-11-09T02:25:00+00:00','inference_stop_utc':'2026-11-09T02:45:00+00:00'}
    write(run/'protocolo.json',protocol);(run/'CANDIDATO_CONGELADO.json').write_bytes(selection_file.read_bytes());(run/'source.py').write_bytes(Path(__file__).read_bytes())
    def stage(name,**extra):write(run/'estado.json',{'stage':name,'utc':datetime.now(timezone.utc).isoformat(),'pid':os.getpid(),**extra})
    def paths(condition,level):
        suffix='' if condition=='original' else f'_{condition}_{level}';root=old if (condition,level) in anchors else base
        return root/f'cache_confirmacao_test{suffix}_2026-10-21',root/'inferencia'/f'confirmacao_congelada_test{suffix}_2026-10-21'
    try:
        torch.set_num_threads(2);cv2.setNumThreads(1);unet=MulticlassUNet(8).eval()
        unet_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';assert sha(unet_file)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
        unet.load_state_dict(torch.load(unet_file,map_location='cpu',weights_only=True)['model']);gallery=None;prepared=[]
        execution=[v for v in SCHEDULE if v in anchors]+[v for v in SCHEDULE if v not in anchors]
        for condition,level in execution:
            cache,folder=paths(condition,level)
            while not (folder/'scores_rgb.npz').exists():
                stage('aguardando_cache_referencia',condition=condition,loss_percent=level,prepared=len(prepared),total=63)
                if datetime.now(timezone.utc)>=datetime.fromisoformat(protocol['preparation_stop_utc']):stage('parcial_preparacao_por_horario',prepared=len(prepared));return
                time.sleep(2)
            out=run/f'{condition}_{level}';out.mkdir();images=np.lib.format.open_memmap(out/'polar.npy',mode='w+',dtype=np.uint8,shape=(len(rows),64,512,3))
            original=np.load(cache/'polar.npy',mmap_mode='r')
            with np.load(cache/'valid.npz') as z:pv=z['polar'].copy()
            if gallery is not None:images[gi]=gallery
            fallbacks=0
            for i,row in enumerate(rows):
                if gallery is not None and row.session==1:continue
                photo=Image.open(row.image).convert('RGB')
                if level and row.session==2:
                    reference=decode_mask(Image.open(row.mask))==1;photo,_=perturb(photo,reference,condition,level)
                mask=predict_mask(unet,photo,selection['spec'])
                try:images[i]=prepare_texture(np.asarray(photo),mask)[0]
                except ValueError:images[i]=original[i];fallbacks+=1
                if i%128==0:stage('preparando_cpu',condition=condition,loss_percent=level,row=i,rows=len(rows),prepared=len(prepared),total=63)
            images.flush();np.save(out/'valid.npy',pv)
            if gallery is None:gallery=images[gi].copy()
            else:np.testing.assert_array_equal(images[gi],gallery)
            write(out/'ENTRADAS_CONCLUIDAS.json',{'fallbacks':fallbacks,'original_validity_retained':True,'gallery_identical':True,'sha256':sha(out/'polar.npy')})
            prepared.append([condition,level]);write(run/'preparados.json',prepared)
        del unet
        while not (base/'CONCLUIDO.json').exists():
            stage('aguardando_grade_referencia',prepared=63)
            if datetime.now(timezone.utc)>=datetime.fromisoformat(protocol['inference_stop_utc']):stage('parcial_referencia_por_horario');return
            time.sleep(2)
        matte=ROOT/'outputs/sam31_matte_subpixel_2026-11-08'
        while (base/'PAUSAR_PARA_REFINO').exists():stage('aguardando_gpu_segura');time.sleep(2)
        reference_records=json.loads((base/'resultados.json').read_text());assert len(reference_records)==63
        device=torch.device('cuda');model=IdentityEncoder().to(device).eval();model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
        ids=sorted({identity(r) for r in rows});draws=np.random.default_rng(20261108).integers(0,len(people),(5000,len(people)))
        nq=np.array([(subjects==s).sum() for s in people]);den=nq[draws].sum(1);records=[]
        for condition,level in SCHEDULE:
            if datetime.now(timezone.utc)>=datetime.fromisoformat(protocol['inference_stop_utc']):stage('parcial_inferencia_por_horario',completed=len(records),total=63);return
            stage('inferindo_candidato',condition=condition,loss_percent=level,completed=len(records),total=63)
            out=run/f'{condition}_{level}';x=np.load(out/'polar.npy',mmap_mode='r');pv=np.load(out/'valid.npy')
            full,valid=global_scores(extract(model,x,device),pv,rows);scores,labels,_=subset(full,rows,ids);replacement={'scores':scores,'labels':labels,'valid':valid}
            _,folder=paths(condition,level);components=[]
            for name in ORDER:
                with np.load(folder/f'scores_{name}.npz') as z:components.append({k:z[k].copy() for k in ('scores','labels','valid')})
            old_scores,old_valid=fuse(components,config['component_calibration_red_and_clahe'])
            with np.load(base/f'scores_reference_{condition}_{level}.npz') as z:
                np.testing.assert_allclose(old_scores,z['scores'],atol=1e-12,rtol=1e-12);np.testing.assert_array_equal(old_valid,z['valid'])
            bm,bc,bvec=measured(old_scores,labels,old_valid,threshold)
            expected=next(r for r in reference_records if r['condition']==condition and r['loss_percent']==level);assert bc==expected['counts']
            items=components.copy();items[1]=blend(components[1],replacement,selection['alpha'])
            candidate_scores,candidate_valid=fuse(items,config['component_calibration_red_and_clahe']);cm,cc,cvec=measured(candidate_scores,labels,candidate_valid,threshold)
            assert cc['queries']==486 and cc['impostors']==7290
            delta=cvec-bvec;totals=np.array([delta[subjects==s].sum(0) for s in people])[draws].sum(1)
            ci=np.quantile(100*totals/np.column_stack((den,den,den,15*den)),[.025,.975],axis=0)
            np.savez_compressed(out/'scores_candidato.npz',scores=candidate_scores,labels=labels,valid=candidate_valid)
            np.savez_compressed(out/'scores_polar.npz',**replacement)
            records.append({'condition':condition,'level':level,'baseline':{'metrics':bm,'counts':bc},'candidate':{'metrics':cm,'counts':cc},
                'paired_gain95_pp':{n:ci[:,j].tolist() for j,n in enumerate(('rank1','tar','joint','fmr'))},'scores_sha256':sha(out/'scores_candidato.npz')})
            write(run/'resultados.json',records)
        clean=records[0];b=clean['baseline']['metrics'];c=clean['candidate']['metrics']
        gate=(c['rank1']>=b['rank1'] and c['tar']>=b['tar'] and c['far']<=.01
            and np.mean([r['candidate']['metrics']['joint_success'] for r in records])>np.mean([r['baseline']['metrics']['joint_success'] for r in records])
            and all(r['candidate']['metrics']['far']<=r['baseline']['metrics']['far'] for r in records))
        for n,expected in sources.items():assert sha(ROOT/n)==expected
        write(run/'CONCLUIDO.json',{'status':'concluido','conditions':63,'comparison_gate_passed':bool(gate),
            'recognizer_replaced':False,'independent_confirmation':False,'selection_sha256':sha(selection_file),'results_sha256':sha(run/'resultados.json')})
        lines=['# Comparação densa do contorno selecionado','',f'63 condições. Regra completa aprovada: **{bool(gate)}**. Sem substituição automática de modelo.','',
            '| Perda | Posição | Versão | Rank-1 | TAR | FMR | Correto e aceito |','|---:|---|---|---:|---:|---:|---:|']
        for r in records:
            for name in ('baseline','candidate'):
                m=r[name]['metrics'];lines.append(f"| {r['level']}% | {r['condition']} | {name} | {100*m['rank1']:.2f}% | {100*m['tar']:.2f}% | {100*m['far']:.3f}% | {100*m['joint_success']:.2f}% |")
        lines+=['','Validação e teste reutilizados no desenvolvimento. Intervalos pareados por pessoa são descritivos, sem correção da seleção ou comparações múltiplas. Suporte anotado não é anel normativo.']
        (run/'RELATORIO_ATUAL.md').write_text('\n'.join(lines),encoding='utf-8');stage('concluido',completed=63,total=63,comparison_gate_passed=bool(gate))
    except BaseException as error:
        stage('falha',error=str(error));(run/'ERRO.txt').write_text(traceback.format_exc(),encoding='utf-8');raise


if __name__=='__main__':main()

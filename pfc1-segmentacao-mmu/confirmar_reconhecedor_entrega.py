"""Congela o melhor candidato de validacao antes da comparacao exploratoria13niveis."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,os,time
import numpy as np
import torch
from avaliar_candidato_congelado import extract,global_scores,spatial,fuse,WEIGHTS
from avaliar_contorno_integrado import prepare_continuous
from avaliar_robustez_reconhecimento import load_splits,identity,metrics
from validar_lateralidade_informada import subset
from treinar_reconhecedor_entrega import ORDER,selection_key
from recorte_iris_sam31_alta_res import sha
from rodada_reconhecedor_entrega import write
from treinar_identidade_iris import IdentityEncoder
import reconhecedor_resnet50,reconhecedor_transformer_polar

ROOT=Path(__file__).resolve().parent
SCHEDULE=(('original',0),)+tuple((t,n) for n in (1,5,10,20,30,31) for t in ('oclusao_superior','oclusao_inferior'))

def load_components(folder):
    components=[]
    for name in ORDER:
        with np.load(folder/f'scores_{name}.npz',allow_pickle=False) as z:components.append({k:z[k].copy() for k in ('scores','valid','labels')})
    for c in components:np.testing.assert_array_equal(c['labels'],components[0]['labels'])
    return components

def measurements(scores,labels,valid,threshold,subjects):
    m,c,a=metrics(scores,labels,threshold,valid);m['joint_success']=float((c&a).mean())
    imp=np.ones(scores.shape,bool);imp[np.arange(len(c)),labels]=False
    counts={'correct':int(c.sum()),'accepted':int(a.sum()),'joint':int((c&a).sum()),'queries':len(c),
        'false_accepts':int(((scores>=threshold)&valid[:,None]&imp).sum()),'impostors':int(imp.sum()),'failures':int((~valid).sum())}
    return {'metrics':m,'counts':counts},c,a

def report(run,records,complete=False):
    lines=['# Comparação do candidato selecionado com o reconhecedor de referência','',
        '**'+('Concluída' if complete else 'Parcial — em execução')+'**. Candidato escolhido exclusivamente pela validação antes da nova inferência. Teste já exposto no histórico; comparação exploratória.','',
        '| Perda | Posição | Versão | Rank-1 | TAR | FMR | Correto e aceito |','|---:|---|---|---:|---:|---:|---:|']
    for r in records:
        for name in ('baseline','candidate'):
            m=r[name]['metrics'];lines.append(f"| {r['level']}% | {r['condition']} | {name} | {100*m['rank1']:.2f}% | {100*m['tar']:.2f}% | {100*m['far']:.3f}% | {100*m['joint_success']:.2f}% |")
    lines+=['','Mesma galeria, mesmos486denominadores e limiar histórico fixo. Baseline proveniente da rodada completa de08/11, cujo ambiente e fontes foram preservados; escores compartilhados reutilizados sem alteração. A fração removida refere-se ao suporte originalmente anotado, não ao anel anatômico da ISO nem à extensão de uma doença. Nenhum modelo do aplicativo foi substituído automaticamente.']
    (run/'RELATORIO_ATUAL.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');write(run/'resultados.json',records)

def main():
    p=argparse.ArgumentParser();p.add_argument('--training-run',type=Path,required=True);p.add_argument('--hybrid-run',type=Path,required=True);p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args()
    run=a.run_dir.resolve();run.mkdir(parents=True,exist_ok=False)
    t=json.loads((a.training_run/'CONCLUIDO.json').read_text());h=json.loads((a.hybrid_run/'CONCLUIDO.json').read_text())
    assert (a.training_run/'analise/AUDITORIA.json').exists()
    candidates={}
    if h['selected_group'] is not None:candidates['hybrid_polar']={'validation':h['results'][h['selected_group']],'kind':'hybrid','group':h['selected_group']}
    if t['eligible_gain']:candidates['native_adapted']={'validation':t['results'],'kind':'encoder','checkpoint':str((a.training_run/'melhor_modelo.pt').resolve()),'checkpoint_sha256':t['checkpoint_sha256']}
    # No new test file is opened until this deterministic validation-only decision is frozen.
    chosen=max(candidates,key=lambda name:(selection_key(candidates[name]['validation']),name)) if candidates else None
    selection={'frozen_utc':datetime.now(timezone.utc).isoformat(),'selected':chosen,'candidate':None if chosen is None else candidates[chosen],
        'rule':'Choose eligible validation candidate with greatest meanjoint,then worstjoint,then meanRank1; final tie lexicalname. No combination of candidates or test selection.',
        'training_result_sha256':sha(a.training_run/'CONCLUIDO.json'),'hybrid_result_sha256':sha(a.hybrid_run/'CONCLUIDO.json'),'available_candidates':candidates}
    write(run/'CANDIDATO_CONGELADO.json',selection)
    if chosen is None:
        write(run/'CONCLUIDO.json',{'status':'nenhum_candidato_elegivel','test_inference':False});report(run,[],True);return
    candidate=candidates[chosen]
    assert candidate.get('group','polar_only')=='polar_only','Only the predefined polar branch supported'
    baseline_root=ROOT/'outputs/ensaio_oclusoes_2026-11-08';frozen_file=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json';frozen=json.loads(frozen_file.read_text())
    old_protocol=json.loads((baseline_root/'protocolo.json').read_text())
    for name,expected in old_protocol['source_sha256'].items():assert sha(ROOT/name)==expected
    assert old_protocol['versions']['torch']==torch.__version__
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'selection_sha256':sha(run/'CANDIDATO_CONGELADO.json'),'schedule':SCHEDULE,
        'scope':'Exploratory repeated-test comparison, not independent confirmation. Never choose or retrain using this grid.',
        'frozen_calibration_sha256':sha(frozen_file),'historical_threshold':frozen['frozen_threshold'],'original_run_protocol_sha256':sha(baseline_root/'protocolo.json'),
        'source_sha256':sha(__file__),'dependencies_sha256':{name:sha(ROOT/name) for name in ('avaliar_candidato_congelado.py','avaliar_contorno_integrado.py','avaliar_robustez_reconhecimento.py','treinar_reconhecedor_entrega.py')},
        'manifest_sha256':sha(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'),
        'reuse':'Unchanged original components and native input caches from same-environment Nov08 baseline. Recompute only modified descriptors; independently reproduce baselinefusion and decisions from cached9scores before each comparison.',
        'comparison_gate':'CleanRank1/TAR no lower and cleanFMR<=1%; mean13joint improves; each13conditionFMR no higher than baseline. No automatic operational replacement.',
        'versions':{'torch':torch.__version__,'numpy':np.__version__},'deadline_utc':'2026-11-09T02:35:00+00:00'}
    write(run/'protocolo.json',protocol);(run/'source.py').write_bytes(Path(__file__).read_bytes())
    os.environ['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib');os.environ['HF_HUB_OFFLINE']='1'
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda')
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());rows=load_splits(manifest)['test'];ids=sorted({identity(r) for r in rows});subjects=np.array([r.subject for r in rows if r.session==2]);assert len(subjects)==486
    people=np.unique(subjects);draws=np.random.default_rng(20261108).integers(0,len(people),(5000,len(people)));records=[];report(run,records);started=time.monotonic()
    threshold=frozen['frozen_threshold'];calibration=frozen['component_calibration_red_and_clahe']
    for condition,level in SCHEDULE:
        if datetime.now(timezone.utc)>=datetime.fromisoformat(protocol['deadline_utc']):
            write(run/'estado.json',{'stage':'interrompido_pelo_limite_horario','completed':len(records),'total':13});return
        suffix='' if condition=='original' else f'_{condition}_{level}';name=f'{condition}_{level}'
        folder=run/name;folder.mkdir();write(run/'estado.json',{'stage':'avaliando','condition':condition,'level':level,'completed':len(records),'total':13,'pid':os.getpid()})
        original=baseline_root/'inferencia'/f'confirmacao_congelada_test{suffix}_2026-10-21';components=load_components(original)
        y=components[0]['labels'];baseline_scores,bvalid=fuse(components,calibration)
        with np.load(original/'scores_finais.npz',allow_pickle=False) as gold:
            np.testing.assert_array_equal(y,gold['labels']);np.testing.assert_array_equal(bvalid,gold['valid']);np.testing.assert_allclose(baseline_scores,gold['scores'],atol=1e-10,rtol=0)
            _,bc,ba=metrics(baseline_scores,y,threshold,bvalid);np.testing.assert_array_equal(bc,gold['correct']);np.testing.assert_array_equal(ba,gold['accepted'])
        metadata={'old_components_sha256':{f.name:sha(f) for f in original.glob('scores_*.npz')},'baseline_fusion_and_decisions_reproduced':True}
        if candidate['kind']=='encoder':
            cache=baseline_root/f'cache_confirmacao_test{suffix}_2026-10-21';x=np.load(cache/'native.npy',mmap_mode='r')
            metadata['cached_native_input_sha256']=sha(cache/'native.npy');metadata['cached_validity_sha256']=sha(cache/'valid.npz')
            with np.load(cache/'valid.npz') as z:valid=z['rgb']
            assert sha(candidate['checkpoint'])==candidate['checkpoint_sha256']
            model,_=reconhecedor_resnet50.load(candidate['checkpoint'],device)
            full,qvalid=global_scores(extract(model,x,device),valid,rows);scores,labels,_=subset(full,rows,ids);np.testing.assert_array_equal(labels,y)
            components[5]={'scores':scores,'valid':qvalid,'labels':y};del model;torch.cuda.empty_cache()
        else:
            images,rv,pv=prepare_continuous(rows,device,folder/'cache_continuo',condition,level)
            for descriptor in ('polar','transformer'):
                file=ROOT/'outputs'/WEIGHTS[descriptor][0]/'melhor_modelo.pt';assert sha(file)==WEIGHTS[descriptor][1]
                if descriptor=='polar':model=IdentityEncoder().to(device).eval();model.load_state_dict(torch.load(file,map_location='cpu',weights_only=True)['model'])
                else:model,_=reconhecedor_transformer_polar.load(file,device)
                full,qvalid=global_scores(extract(model,images['polar'],device),pv,rows);scores,labels,_=subset(full,rows,ids);np.testing.assert_array_equal(labels,y)
                components[ORDER.index(descriptor)]={'scores':scores,'valid':qvalid,'labels':y}
                if descriptor=='polar':
                    full,qvalid=spatial(model,images['polar'],pv,rows,device);scores,labels,_=subset(full,rows,ids);np.testing.assert_array_equal(labels,y)
                    components[ORDER.index('spatial')]={'scores':scores,'valid':qvalid,'labels':y}
                del model;torch.cuda.empty_cache()
            arc_base=ROOT/'data/modelos/cvrl_arciris';weights=next(arc_base.rglob('ResNet100_154000.pt'))
            assert sha(weights)=='466014be7723eb0b1a741dcff5a0c8ae51d1918818a6b021952f9c4ccd443f8f'
            assert sha(arc_base/'modules/network.py')=='de7f0cb796ebf4be02818c704d7e3afa0047dc09719b131b37cb8c26c42dd327'
            spec=importlib.util.spec_from_file_location('arciris_delivery_grid',arc_base/'modules/network.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            model=module.iresnet100();model.load_state_dict(torch.load(weights,map_location='cpu',weights_only=True));model.to(device).eval()
            for descriptor,key in (('arc_clahe','polar'),('arc_red','red')):
                full,qvalid=global_scores(extract(model,images[key],device,8,True),pv,rows,True);scores,labels,_=subset(full,rows,ids);np.testing.assert_array_equal(labels,y)
                components[ORDER.index(descriptor)]={'scores':scores,'valid':qvalid,'labels':y}
            del model;torch.cuda.empty_cache()
        scores,valid=fuse(components,calibration)
        b,bc,ba=measurements(baseline_scores,y,bvalid,threshold,subjects);c,cc,ca=measurements(scores,y,valid,threshold,subjects)
        np.savez_compressed(folder/'scores_candidato.npz',scores=scores,labels=y,valid=valid,correct=cc,accepted=ca)
        diff=np.column_stack((cc.astype(float)-bc,ca.astype(float)-ba,(cc&ca).astype(float)-(bc&ba)))
        totals=np.array([diff[subjects==person].sum(0) for person in people]);denom=np.array([(subjects==person).sum() for person in people])
        ci=np.quantile(100*totals[draws].sum(1)/denom[draws].sum(1)[:,None],[.025,.975],axis=0)
        record={'condition':condition,'level':level,'baseline':b,'candidate':c,'paired_gain_pp':(100*diff.mean(0)).tolist(),'descriptive_interval95_pp':ci.tolist(),'audit':metadata}
        records.append(record);write(folder/'resultado.json',record);report(run,records);print(json.dumps(record),flush=True)
    clean=records[0];eligible=all(clean['candidate']['metrics'][k]>=clean['baseline']['metrics'][k] for k in ('rank1','tar')) and clean['candidate']['metrics']['far']<=.01
    eligible=eligible and np.mean([r['candidate']['metrics']['joint_success'] for r in records])>np.mean([r['baseline']['metrics']['joint_success'] for r in records]) and all(r['candidate']['metrics']['far']<=r['baseline']['metrics']['far'] for r in records)
    assert sha(run/'CANDIDATO_CONGELADO.json')==protocol['selection_sha256'];assert sha(frozen_file)==protocol['frozen_calibration_sha256']
    for name,expected in protocol['dependencies_sha256'].items():assert sha(ROOT/name)==expected
    final={'status':'concluido','selected':chosen,'comparison_gate_passed':bool(eligible),'records':records,'recognizer_replaced':False,'independent_confirmation':False,'universal_minimum':None,'elapsed_seconds':time.monotonic()-started}
    write(run/'CONCLUIDO.json',final);report(run,records,True);write(run/'estado.json',{'stage':'concluido','completed':13,'total':13,'comparison_gate_passed':bool(eligible)});print(json.dumps({k:v for k,v in final.items() if k!='records'}),flush=True)

if __name__=='__main__':main()

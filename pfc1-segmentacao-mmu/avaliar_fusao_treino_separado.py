"""Avalia fusao fixa no TREINO; calibra apenas no grupo interno limpo."""
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone
import argparse,gc,importlib.util,json
import numpy as np
import torch
from avaliar_candidato_congelado import ROOT,WEIGHTS,prepare,extract,global_scores,spatial,fuse
from preparar_encoder_espacial import file_hash
from avaliar_robustez_reconhecimento import identity
from validar_lateralidade_informada import subset
from validar_fusao_identidade_adaptada import calibrate as calibrate_components
from treinar_bloco_fmr_separado import calibrate,measured
NAME='fusao_treino_calibracao_separada_2026-10-23'
ORDER=['rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red']
CONDITIONS=[('clean','original',0),('upper10','oclusao_superior',10),('lower10','oclusao_inferior',10)]

def main():
    from treinar_identidade_iris import IdentityEncoder
    import reconhecedor_resnet50,reconhecedor_convnext,reconhecedor_transformer_polar
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args();out=a.root/NAME;source=a.root/'bloco_fmr_separado_2026-10-23';sp=json.loads((source/'protocolo.json').read_text());sd=json.loads((source/'CONCLUIDO.json').read_text());arc=ROOT/'data/modelos/cvrl_arciris';aw=next(arc.rglob('ResNet100_154000.pt'));checkpoints={n:ROOT/'outputs'/folder/'melhor_modelo.pt' for n,(folder,h) in WEIGHTS.items()}
    if a.registrar:
        out.mkdir(exist_ok=False);protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='TRAIN-only integrated feasibility,16internalpeople clean calibration,16OLDmonitorpeople finalassessment. Encoders saw these historically. NEWfusionhypothesis AFTERfailedpolar/cohort pilots; reusedmonitor NOT independent. No fitting on monitor,noVAL/test.',
            strategies='ExactlyTWO: original8components+ORIGINALFP32polar vs same8+separated151FITadjustedFP32polar. All9fixedmodelweights/hash; NOcomponentweightsearch/drop/retraining/qualityfiltering. Existingfusion sevencomponentsweight1/8 plus ArcCLAHE/red each1/16,originalquerynormalization unchanged.',
            calibration='Eachstrategy componentimpostormean/std from INTERNALCLEANonly,then INTERNALCLEANthresholdtarget0.5%FMR,unchanged forallocclusionsandOLDmonitor. No OLDmonitorlabels in calibration. ALLqueries/failuresretained;onequeryphoto,suppliedside,16same-sideeyes;S1alwaysclean.',
            precision='OriginalpipelineBF16 CNNs/Transformer,FP32spatial/Arc;polarcomponentreusedFP32pairedscoresfromseparatedexperimentforBOTHstrategies. No precision search.',
            gate='Adapted OLDmonitorcleanRank1/TAR>=original and>=90%,FMR<=1%;BOTHocclusionRank1/TARstrictgainvsoriginal,FMR<=1%. Absoluteallconditions90%Rank1/TARandFMR<=1 separate. Diagnostic gate doesNOTautomaticallypromoteoropenVAL/test.',
            script_sha256=file_hash(Path(__file__)),source_protocol_sha256=file_hash(source/'protocolo.json'),source_completion_sha256=file_hash(source/'CONCLUIDO.json'),checkpoint_sha256={n:file_hash(f) for n,f in checkpoints.items()},arc_checkpoint_sha256=file_hash(aw),arc_source_sha256=file_hash(arc/'modules/network.py'),unet_sha256=file_hash(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'),dependencies_sha256={n:file_hash(ROOT/n) for n in ['avaliar_candidato_congelado.py','validar_fusao_identidade_adaptada.py','treinar_bloco_fmr_separado.py','textura_polar.py','preparar_polar_vermelho.py','normalizacao_eliptica.py','normalizar_consulta.py','validar_lateralidade_informada.py','reconhecedor_resnet50.py','reconhecedor_convnext.py','reconhecedor_transformer_polar.py']},external_pretraining_overlap_unknown=True)
        assert all(protocol['checkpoint_sha256'][n]==WEIGHTS[n][1] for n in WEIGHTS);assert protocol['arc_checkpoint_sha256']=='466014be7723eb0b1a741dcff5a0c8ae51d1918818a6b021952f9c4ccd443f8f';assert protocol['arc_source_sha256']=='de7f0cb796ebf4be02818c704d7e3afa0047dc09719b131b37cb8c26c42dd327'
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Fusao TREINO registrada antes das inferencias.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert not (out/'CONCLUIDO.json').exists() and file_hash(Path(__file__))==protocol['script_sha256'];assert file_hash(source/'protocolo.json')==protocol['source_protocol_sha256'] and file_hash(source/'CONCLUIDO.json')==protocol['source_completion_sha256']
    for n,h in protocol['dependencies_sha256'].items():assert file_hash(ROOT/n)==h
    for n,f in checkpoints.items():assert file_hash(f)==protocol['checkpoint_sha256'][n]
    assert file_hash(aw)==protocol['arc_checkpoint_sha256'] and file_hash(arc/'modules/network.py')==protocol['arc_source_sha256'];assert file_hash(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt')==protocol['unet_sha256']
    people=set(sp['internal_people']+sp['monitor_people']);all_rows=json.loads((source/'rows.json').read_text());rows=[]
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());native={Path(r['image']).name:r for r in manifest['train']}
    for r in all_rows:
        if r['subject'] in people:
            r=dict(native[Path(r['image']).name]);r['image']=str(ROOT/'data/ubipr/single_eye'/Path(r['image']).name);r['mask']=str(ROOT/'data/ubipr/single_eye'/Path(r['mask']).name);rows.append(SimpleNamespace(**r))
    subsets={split:np.array([i for i,r in enumerate(rows) if r.subject in set(sp[key])]) for split,key in [('internal','internal_people'),('monitor','monitor_people')]};assert len(people)==32 and not people&set(sp['fit_people'])
    (out/'rows.json').write_text(json.dumps([vars(r) for r in rows],indent=2),encoding='utf-8');torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');inputs={}
    def save(name,features,valid,arc_mode=False,spatial_mode=False,model=None,images=None):
        for split,ii in subsets.items():
            rr=[rows[i] for i in ii];ids=sorted({identity(r) for r in rr})
            full,available=spatial(model,images[ii],valid[ii],rr,device) if spatial_mode else global_scores(features[ii],valid[ii],rr,arc_mode)
            values,labels,_=subset(full,rr,ids);np.savez_compressed(out/f'component_{split}_{tag}_{name}.npz',scores=values,labels=labels,valid=available)
        print(json.dumps(dict(condition=tag,component=name,status='saved')),flush=True)
    for tag,kind,level in CONDITIONS:
        folder=a.root/(NAME+'_cache_'+tag)
        if (folder/'PREPROCESSADO.json').exists():
            images={k:np.load(folder/(k+'.npy'),mmap_mode='r') for k in ['rgb','native','polar','red']}
            with np.load(folder/'valid.npz') as z:rv=z['rgb'];pv=z['polar']
        else:
            images,rv,pv=prepare(rows,device,folder,kind,level);(folder/'PREPROCESSADO.json').write_text(json.dumps(dict(rows=len(rows),condition=tag,completed=True)),encoding='utf-8')
        for name in ['rgb','spatial','r50','convnext','native','transformer']:
            if all((out/f'component_{split}_{tag}_{name}.npz').exists() for split in subsets):continue
            if name in ['rgb','spatial']:
                model=IdentityEncoder().to(device).eval();model.load_state_dict(torch.load(checkpoints['polar' if name=='spatial' else name],map_location='cpu',weights_only=True)['model'])
            else:model,_={'r50':reconhecedor_resnet50,'native':reconhecedor_resnet50,'convnext':reconhecedor_convnext,'transformer':reconhecedor_transformer_polar}[name].load(checkpoints[name],device)
            inp=images['polar'] if name in ['spatial','transformer'] else images['native'] if name=='native' else images['rgb'];valid=pv if name in ['spatial','transformer'] else rv
            if name=='convnext':inp=np.stack([reconhecedor_convnext.contrast(i) for i in inp])
            if name=='spatial':save(name,None,valid,spatial_mode=True,model=model,images=inp)
            else:save(name,extract(model,inp,device),valid)
            del model;gc.collect();torch.cuda.empty_cache()
        if not all((out/f'component_{split}_{tag}_{name}.npz').exists() for split in subsets for name in ['arc_clahe','arc_red']):
            spec=importlib.util.spec_from_file_location('arciris_train_fixed',arc/'modules/network.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);model=module.iresnet100();model.load_state_dict(torch.load(aw,map_location='cpu',weights_only=True));model.to(device).eval()
            for name,key in [('arc_clahe','polar'),('arc_red','red')]:
                if not all((out/f'component_{split}_{tag}_{name}.npz').exists() for split in subsets):save(name,extract(model,images[key],device,8,True),pv,True)
            del model;gc.collect();torch.cuda.empty_cache()
        inputs[tag]={n:file_hash(folder/(n+'.npy')) for n in images};inputs[tag]['valid']=file_hash(folder/'valid.npz')
    results={};parameters={}
    for strategy,prefix in [('original','baseline'),('adapted','selected')]:
        calibration=None;threshold=None
        for split in ['internal','monitor']:
            for tag,_,_ in CONDITIONS:
                components=[]
                for name in ORDER:
                    file=source/f'scores_{prefix}_{split}_{tag}.npz' if name=='polar' else out/f'component_{split}_{tag}_{name}.npz'
                    with np.load(file) as z:components.append({k:z[k] for k in ['scores','labels','valid']})
                for c in components:np.testing.assert_array_equal(c['labels'],components[0]['labels'])
                if split=='internal' and tag=='clean':calibration=calibrate_components(components)
                values,validity=fuse(components,calibration);data=dict(scores=values,labels=components[0]['labels'],valid=validity)
                if split=='internal' and tag=='clean':threshold=calibrate(data)
                m,d=measured(data,threshold);results.setdefault(strategy,{}).setdefault(split,{})[tag]=m;np.savez_compressed(out/f'scores_{strategy}_{split}_{tag}.npz',**d)
        parameters[strategy]=dict(calibration=calibration,threshold=threshold)
    r=results['adapted']['monitor'];b=results['original']['monitor'];gate=all(r['clean'][k]>=max(.9,b['clean'][k]) for k in ['rank1','tar']) and all(r[t]['far']<=.01 for t,_,_ in CONDITIONS) and all(r[t][k]>b[t][k] for t in ['upper10','lower10'] for k in ['rank1','tar']);absolute=all(r[t]['rank1']>=.9 and r[t]['tar']>=.9 and r[t]['far']<=.01 for t,_,_ in CONDITIONS)
    done=dict(status='train_fusion_separated_calibration_completed',results=results,parameters=parameters,monitor_gate_passed=bool(gate),absolute_target_reached=bool(absolute),cached_input_sha256=inputs,query_images=1,informed_side=True,validation_inference=False,test_inference=False,candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(done,indent=2),encoding='utf-8');print(json.dumps(done),flush=True)
if __name__=='__main__':main()

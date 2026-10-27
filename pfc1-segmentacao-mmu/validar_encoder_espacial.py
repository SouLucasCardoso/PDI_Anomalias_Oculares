"""Validacao condicional do adaptador original; nunca abre o teste."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,tempfile
import numpy as np
import torch
from treinar_encoder_polar_espacial import ROOT,NAME
from adaptador_polar import pooled_features
from encoder_polar_espacial import SpatialTail,prefix_model,prefix_features
ORDER=['rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red']
SUFFIX={'clean':'','upper10':'_oclusao_superior_10','lower10':'_oclusao_inferior_10'}

def main():
    from avaliar_candidato_congelado import digest,WEIGHTS,global_scores,fuse
    from avaliar_robustez_reconhecimento import load_splits,identity,metrics,operating_threshold
    from validar_lateralidade_informada import subset
    from validar_fusao_identidade_adaptada import calibrate
    from treinar_identidade_iris import IdentityEncoder
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args();trained=a.output_root/NAME;out=a.output_root/(NAME.replace('_2026','_val_2026'))
    if a.registrar:
        out.mkdir(parents=True,exist_ok=False)
        protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='ONLYdevelopmentVALifTRAINmonitor passes. All482queries,onephoto,suppliedside,16candidateeyes,480cleanS1enrollment. No test or automatic replacement.',
            candidate='ONLYglobalpolarcomponent adapted; other8components use ORIGINALgeometry and frozenidentityweights. OriginalBF16control,originalFP32unadaptedcontrol,originalFP32adapted. NOoutergeometry/SAM. FP32batch32 throughout;145408rank8 corrections ONLYinside layer4, frozen earlierlayers/projection/normalizationstatistics.',
            calibration='One clean-only component calibration and empiricalFMR<=1%threshold per newmethod; unchanged forupper/lower10. OriginalBF16 uses original frozenparameters. Fixed8groupweights,no tuning/filtering.',
            gate='Adapted cleanRank1/TAR>=90%,FMR<=1%;BOTHocclusionRank1/TAR improve vs ORIGINALBF16 and FMR<=1%. Also reportFP32control. Absolute90%Rank1/TAR target separate. No automatictest/promotion/minimum.',
            script_sha256=digest(Path(__file__)),spatial_source_sha256=digest(ROOT/'encoder_polar_espacial.py'),training_protocol_sha256=digest(trained/'protocolo.json'))
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Validacao condicional registrada.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert protocol['script_sha256']==digest(Path(__file__)) and protocol['training_protocol_sha256']==digest(trained/'protocolo.json') and protocol['spatial_source_sha256']==digest(ROOT/'encoder_polar_espacial.py');assert not (out/'CONCLUIDO.json').exists()
    completed=json.loads((trained/'CONCLUIDO.json').read_text())
    if not completed['recognition_validation_gate_passed']:
        final=dict(status='spatial_encoder_monitor_failed_no_validation_inference',selected_epoch=completed['selected_epoch'],validation_identity_inference=False,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
        (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final));return
    assert digest(trained/'melhor_modelo.pt')==completed['checkpoint_sha256'];state=torch.load(trained/'melhor_modelo.pt',map_location='cpu',weights_only=True);torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device='cuda' if torch.cuda.is_available() else 'cpu'
    encoder=IdentityEncoder().to(device).eval();file=ROOT/'outputs'/WEIGHTS['polar'][0]/'melhor_modelo.pt';assert digest(file)==WEIGHTS['polar'][1];encoder.load_state_dict(torch.load(file,map_location='cpu',weights_only=True)['model']);tail=SpatialTail(encoder,state['rank']).to(device).eval();tail.load_adapters(state['adapters']);assert tail.frozen_digest()==state['frozen_sha256'];prefix=prefix_model(encoder).to(device)
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val'];assert len(rows)==962 and sum(r.session==2 for r in rows)==482
    assert not {r.subject for r in rows}&set(state['configuration']['fit_people']+state['configuration']['monitor_people']);ids=sorted({identity(r) for r in rows});groups={s:{} for s in ['original','fp32','adapted']};hashes={}
    for tag,suffix in SUFFIX.items():
        original=ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21';cache=Path(tempfile.gettempdir())/f'cache_confirmacao_val{suffix}_2026-10-21'
        for group in groups.values():group[tag]={}
        for name in ORDER:
            file=original/f'scores_{name}.npz';hashes[str(file)]=digest(file)
            with np.load(file) as z:c={k:z[k] for k in ['scores','labels','valid']}
            for group in groups.values():group[tag][name]=c
        with np.load(cache/'valid.npz') as z:valid=z['polar']
        images=np.load(cache/'polar.npy',mmap_mode='r');hashes[str(cache/'polar.npy')]=digest(cache/'polar.npy');hashes[str(cache/'valid.npz')]=digest(cache/'valid.npz');raw,base=pooled_features(encoder,images,device);adapted_parts=[]
        for start in range(0,len(images),32):
            values=prefix_features(prefix,images[start:start+32],device)
            with torch.inference_mode():adapted_parts.append(tail(torch.from_numpy(values).to(device)).cpu().numpy())
        adapted=np.concatenate(adapted_parts)
        for strategy,vectors in [('fp32',base),('adapted',adapted)]:
            full,qvalid=global_scores(vectors,valid,rows);scores,labels,_=subset(full,rows,ids);np.testing.assert_array_equal(labels,groups['original'][tag]['polar']['labels']);np.testing.assert_array_equal(qvalid,groups['original'][tag]['polar']['valid']);component=dict(scores=scores,labels=labels,valid=qvalid);groups[strategy][tag]['polar']=component;np.savez_compressed(out/f'polar_{strategy}_{tag}.npz',**component)
        print('Polar original/adaptado: '+tag,flush=True)
    frozen=json.loads((ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json').read_text());results={};parameters={}
    for strategy,group in groups.items():
        calibration=frozen['component_calibration_red_and_clahe'] if strategy=='original' else calibrate([group['clean'][n] for n in ORDER]);data={t:dict(zip(['scores','valid'],fuse([c[n] for n in ORDER],calibration))) for t,c in group.items()};labels=group['clean']['rgb']['labels'];c=data['clean'];imp=np.ones_like(c['scores'],bool);imp[np.arange(482),labels]=False;threshold=frozen['frozen_threshold'] if strategy=='original' else operating_threshold(c['scores'][imp&c['valid'][:,None]&(c['scores']>-2)]);parameters[strategy]=dict(calibration=calibration,threshold=threshold);results[strategy]={}
        for tag,c in data.items():
            r,correct,accepted=metrics(c['scores'],labels,threshold,c['valid']);r.update(correct=int(correct.sum()),accepted=int(accepted.sum()),threshold=threshold);results[strategy][tag]=r;np.savez_compressed(out/f'scores_{strategy}_{tag}.npz',**c,labels=labels,correct=correct,accepted=accepted)
            if strategy=='original':
                with np.load(ROOT/'outputs'/f'confirmacao_congelada_val{SUFFIX[tag]}_2026-10-21/scores_finais.npz') as z:np.testing.assert_allclose(c['scores'],z['scores'],rtol=0,atol=1e-12);np.testing.assert_array_equal(correct,z['correct']);np.testing.assert_array_equal(accepted,z['accepted'])
            print(json.dumps(dict(strategy=strategy,condition=tag,metrics=r)),flush=True)
    candidate=results['adapted'];control=results['original'];c=candidate['clean'];gate=c['rank1']>=.9 and c['tar']>=.9 and c['far']<=.01 and all(candidate[t][k]>control[t][k] for t in ['upper10','lower10'] for k in ['rank1','tar']) and all(candidate[t]['far']<=.01 for t in ['upper10','lower10'])
    final=dict(status='spatial_encoder_validation_completed',results=results,parameters=parameters,inputs_sha256=hashes,promotion_gate_passed=bool(gate),absolute_target_reached=all(r['rank1']>=.9 and r['tar']>=.9 and r['far']<=.01 for r in candidate.values()),validation_identity_inference=True,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in final.items() if k not in ['parameters','inputs_sha256']}),flush=True)
if __name__=='__main__':main()





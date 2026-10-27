"""Validação condicional de um único componente polar adaptado, sem teste."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,json,tempfile
import numpy as np
import torch
from adaptador_polar import PolarAdapter,pooled_features,apply_adapter
ROOT=Path(__file__).resolve().parent
ORDER=['rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red']
SUFFIX={'clean':'','upper10':'_oclusao_superior_10','lower10':'_oclusao_inferior_10'}

def main():
    from avaliar_candidato_congelado import digest,WEIGHTS,global_scores,fuse
    from avaliar_robustez_reconhecimento import load_splits,identity,metrics,operating_threshold
    from validar_lateralidade_informada import subset
    from validar_fusao_identidade_adaptada import calibrate
    from treinar_identidade_iris import IdentityEncoder
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args()
    trained=a.output_root/'adaptador_polar_cadastro_fixo_2026-10-23';out=a.output_root/'adaptador_polar_cadastro_fixo_val_2026-10-23';outer=a.output_root/'contorno_consistente_val_2026-10-23'
    if a.registrar:
        out.mkdir(parents=True,exist_ok=False)
        protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Conditional exploratory development-validation ONLY; no test inference, no automatic replacement. Fit/monitor selection completed before opening validation for adapter.',
            candidate='Replace ONLY polar GLOBAL component of prior outer-geometry fusion. Other8 raw score components fixed, equal8group weights unchanged. One query photo, supplied side,16same-side candidates,all482queries,480S1photos. Reconstruct identical corrected textures from saved changed-input cache; no clean counterpart at inference.',
            controls='Original frozen BF16 pipeline; outer-geometry+unadapted polar FP32 control; outer-geometry+adapted polar FP32. FP32batch32 frozen backbone/projection and FP32batch512adapter fixed before inference.',
            calibration='Original control uses original frozen parameters/threshold. Each other strategy calibrates component means/stds and threshold ONCE on CLEAN validation only, unchanged in both10%occlusions. No weight search or query filtering.',
            advancement='Adapted clean Rank1/TAR>=90%,FMR<=1%; both occluded Rank1/TAR improve vs original and FMR<=1%. Also report paired comparison with outer-FP32 control. Absolute target separately requires90%Rank1/TAR,FMR<=1 in all3conditions.',
            script_sha256=digest(Path(__file__)),adapter_source_sha256=digest(ROOT/'adaptador_polar.py'),training_protocol_sha256=digest(trained/'protocolo.json'),outer_completion_sha256=digest(outer/'CONCLUIDO.json'))
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Protocolo de validacao registrado antes da inferencia.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert protocol['script_sha256']==digest(Path(__file__)) and protocol['adapter_source_sha256']==digest(ROOT/'adaptador_polar.py') and protocol['training_protocol_sha256']==digest(trained/'protocolo.json')
    if (out/'CONCLUIDO.json').exists():raise ValueError('Preserve completed validation')
    completed=json.loads((trained/'CONCLUIDO.json').read_text())
    if not completed['recognition_validation_gate_passed']:
        final=dict(status='polar_adapter_monitor_gate_failed_no_validation_inference',training=completed,validation_identity_inference=False,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
        (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final));return
    assert digest(outer/'CONCLUIDO.json')==protocol['outer_completion_sha256']
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    checkpoint=trained/'melhor_modelo.pt';assert digest(checkpoint)==completed['checkpoint_sha256'];state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    adapter=PolarAdapter().to(device).eval();adapter.load_state_dict(state['model']);mean=state['raw_mean'].numpy();std=state['raw_std'].numpy()
    file=ROOT/'outputs'/WEIGHTS['polar'][0]/'melhor_modelo.pt';assert digest(file)==state['configuration']['polar_encoder_sha256']==WEIGHTS['polar'][1]
    encoder=IdentityEncoder().to(device).eval();encoder.load_state_dict(torch.load(file,map_location='cpu',weights_only=True)['model'])
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val'];assert len(rows)==962 and sum(r.session==2 for r in rows)==482
    assert not {r.subject for r in rows}&set(state['configuration']['fit_people']+state['configuration']['monitor_people'])
    ids=sorted({identity(r) for r in rows});groups={strategy:{} for strategy in ['original_control','outer_fp32_control','outer_adapted']};hashes={}
    for tag,suffix in SUFFIX.items():
        original=ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21';cache=Path(tempfile.gettempdir())/f'cache_confirmacao_val{suffix}_2026-10-21'
        for strategy in groups:groups[strategy][tag]={}
        for name in ORDER:
            file=original/f'scores_{name}.npz';hashes[str(file)]=digest(file)
            with np.load(file) as z:groups['original_control'][tag][name]={k:z[k] for k in ['scores','labels','valid']}
            file=outer/tag/f'scores_{name}.npz' if name in ['polar','spatial','transformer','arc_clahe','arc_red'] else original/f'scores_{name}.npz';hashes[str(file)]=digest(file)
            with np.load(file) as z:c={k:z[k] for k in ['scores','labels','valid']}
            for strategy in ['outer_fp32_control','outer_adapted']:groups[strategy][tag][name]=c
        images=np.array(np.load(cache/'polar.npy',mmap_mode='r'),copy=True)
        file=outer/tag/'changed_inputs.npz';hashes[str(file)]=digest(file)
        with np.load(file) as z:
            indices=z['indices'];assert len(indices)==len(set(indices.tolist())) and indices.min()>=0 and indices.max()<len(images)
            images[indices]=z['polar']
        with np.load(cache/'valid.npz') as z:valid=z['polar']
        raw,base=pooled_features(encoder,images,device);adapted=apply_adapter(adapter,raw,base,mean,std,device)
        folder=out/tag;folder.mkdir();np.savez_compressed(folder/'cache_features.npz',raw=raw,base=base,adapted=adapted,valid=valid)
        for strategy,vectors in [('outer_fp32_control',base),('outer_adapted',adapted)]:
            full,qvalid=global_scores(vectors,valid,rows);scores,labels,_=subset(full,rows,ids)
            np.testing.assert_array_equal(labels,groups['original_control'][tag]['polar']['labels']);np.testing.assert_array_equal(qvalid,groups['original_control'][tag]['polar']['valid'])
            component=dict(scores=scores,labels=labels,valid=qvalid);groups[strategy][tag]['polar']=component;np.savez_compressed(folder/f'polar_{strategy}.npz',**component)
        print(f'Componentes do adaptador: {tag}',flush=True)
    frozen=json.loads((ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json').read_text());results=[];parameters={}
    for strategy,group in groups.items():
        params=frozen['component_calibration_red_and_clahe'] if strategy=='original_control' else calibrate([group['clean'][n] for n in ORDER])
        data={tag:dict(zip(['scores','valid'],fuse([c[n] for n in ORDER],params))) for tag,c in group.items()};labels=group['clean']['rgb']['labels'];c=data['clean'];imp=np.ones_like(c['scores'],bool);imp[np.arange(482),labels]=False
        threshold=frozen['frozen_threshold'] if strategy=='original_control' else operating_threshold(c['scores'][imp&c['valid'][:,None]&(c['scores']>-2)])
        parameters[strategy]=dict(calibration=params,threshold=threshold)
        for tag,c in data.items():
            measured,correct,accepted=metrics(c['scores'],labels,threshold,c['valid']);measured.update(strategy=strategy,condition=tag,correct=int(correct.sum()),accepted=int(accepted.sum()),threshold=threshold);results.append(measured)
            np.savez_compressed(out/f'{strategy}_{tag}.npz',**c,labels=labels,correct=correct,accepted=accepted)
            with (out/f'{strategy}_{tag}.csv').open('w',newline='',encoding='utf-8') as stream:
                writer=csv.writer(stream);writer.writerow(['query','label','valid','correct','accepted']+[f'score_{j}' for j in range(16)])
                for i in range(482):writer.writerow([i,int(labels[i]),bool(c['valid'][i]),bool(correct[i]),bool(accepted[i])]+c['scores'][i].tolist())
            if strategy=='original_control':
                with np.load(ROOT/'outputs'/f'confirmacao_congelada_val{SUFFIX[tag]}_2026-10-21/scores_finais.npz') as z:np.testing.assert_allclose(c['scores'],z['scores'],rtol=0,atol=1e-12);np.testing.assert_array_equal(correct,z['correct']);np.testing.assert_array_equal(accepted,z['accepted'])
            print(json.dumps(measured),flush=True)
    baseline={r['condition']:r for r in results if r['strategy']=='original_control'};primary={r['condition']:r for r in results if r['strategy']=='outer_adapted'};c=primary['clean']
    gate=c['rank1']>=.9 and c['tar']>=.9 and c['far']<=.01 and all(primary[tag][m]>baseline[tag][m] for tag in ['upper10','lower10'] for m in ['rank1','tar']) and all(primary[tag]['far']<=.01 for tag in ['upper10','lower10'])
    absolute=all(r['rank1']>=.9 and r['tar']>=.9 and r['far']<=.01 for r in primary.values())
    final=dict(status='polar_adapter_identity_validation_completed',results=results,parameters=parameters,source_inputs_sha256=hashes,checkpoint_sha256=digest(checkpoint),promotion_gate_passed=bool(gate),absolute_target_reached=bool(absolute),validation_identity_inference=True,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in final.items() if k not in ['parameters','source_inputs_sha256']}),flush=True)

if __name__=='__main__':main()

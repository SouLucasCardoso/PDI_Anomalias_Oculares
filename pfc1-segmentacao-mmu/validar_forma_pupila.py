"""Troca apenas pupila fallback; pesos de identidade congelados, validacao apenas."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,importlib.util,json,tempfile
import numpy as np
from PIL import Image
import torch
from pupila_eliptica import EllipseLocator,refined_textures
ROOT=Path(__file__).resolve().parent


def main():
    from avaliar_candidato_congelado import WEIGHTS,digest,extract,global_scores,spatial,fuse
    from treinar_segmentacao_ubipr import Sample,MulticlassUNet,decode_mask
    from avaliar_robustez_reconhecimento import identity,metrics,operating_threshold,perturb
    from avaliar_dinov3_ubipr import masked_crop
    from validar_lateralidade_informada import subset
    from validar_fusao_identidade_adaptada import ORDER,calibrate
    from treinar_identidade_iris import IdentityEncoder
    import reconhecedor_transformer_polar
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    out=a.output_root/'forma_pupila_val_2026-10-23';out.mkdir(parents=True,exist_ok=True)
    if (out/'CONCLUIDO.json').exists():raise ValueError('Preserve completed run')
    protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Exploratory validation ONLY after locator selected on internal TRAIN monitor; no test inference or automatic promotion',
        intervention='Change ONLY shape of learned-circle fallback; frozen circle center/equivalent radius, outer ellipse, ordinary holes, masks, RGB/native and identity weights unchanged. Predicted ellipse must be contained at512angles; otherwise use learned circle. S1/S2 same transform; references only define artificial query occlusion.',
        controls='Four fixed strategies: original frozen control; yesterday circle with frozen calibration; ellipse with frozen calibration; ellipse with CLEAN-only calibration and empirical FMR<=1% threshold. Each strategy parameters unchanged upper/lower10%. No choice of strategy/weights/threshold using occlusion results.',
        gate='If selected shape does not beat isotropic zero-shape on internal monitor proxy loss, record gate failure and do NOT extract validation identity scores.',
        precision='Same original extraction: CNN/Transformer BF16batch128,spatialFP32batch32,ArcIrisFP32batch8. One original query photo, informed side,16 candidates,ALL482 queries/failures retained.',
        limits='Shape target is annotation-hole-derived ellipse proxy, not anatomical pupil ground truth; internal monitor seen by frozen U-Net. Reused development validation and external ArcIris pretraining overlap unknown. No minimum-area claim.',
        script_sha256=digest(Path(__file__)),locator_source_sha256=digest(ROOT/'pupila_eliptica.py'))
    if (out/'source.py').exists():assert (out/'source.py').read_bytes()==Path(__file__).read_bytes()
    else:
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    trained=a.output_root/'forma_pupila_2026-10-23'
    if not (trained/'CONCLUIDO.json').exists():print('Evaluation protocol registered. Training not completed.',flush=True);return
    training=json.loads((trained/'CONCLUIDO.json').read_text())
    if not training['recognition_validation_gate_passed']:
        (out/'CONCLUIDO.json').write_text(json.dumps(dict(status='pupil_monitor_gate_failed_no_identity_validation',training=training,test_inference=False,frozen_candidate_replaced=False,minimum_area=None),indent=2),encoding='utf-8');print('Gate failed; no identity validation inference.',flush=True);return
    checkpoint=trained/'melhor_forma.json';assert digest(checkpoint)==training['shape_sha256']
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');locator=EllipseLocator(checkpoint,device)
    unet_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';assert digest(unet_file)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    unet=MulticlassUNet(8).to(device).eval();unet.load_state_dict(torch.load(unet_file,map_location='cpu',weights_only=True)['model'])
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_file.read_text());raw=manifest['val'];key=lambda r:f"{r['subject']}_{r['side']}"
    eligible={key(r) for r in raw if r['session']==1}&{key(r) for r in raw if r['session']==2};rows=[Sample(**r) for r in raw if key(r) in eligible];ids=sorted({identity(r) for r in rows});gi=[i for i,r in enumerate(rows) if r.session==1];assert sum(r.session==2 for r in rows)==482
    originals={};modified={};changes=[];sources={};clean_gallery=None
    def read(file):
        sources[str(file)]=digest(file)
        with np.load(file) as z:return {k:z[k] for k in ['scores','labels','valid']}
    weights={name:ROOT/'outputs'/folder/'melhor_modelo.pt' for name,(folder,_) in WEIGHTS.items()}
    for name,file in weights.items():assert digest(file)==WEIGHTS[name][1]
    for condition,suffix,kind in [('clean','','original'),('upper10','_oclusao_superior_10','oclusao_superior'),('lower10','_oclusao_inferior_10','oclusao_inferior')]:
        folder=ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21';originals[condition]={name:read(folder/f'scores_{name}.npz') for name in ORDER};modified[condition]=dict(originals[condition])
        cache=Path(tempfile.gettempdir())/f'cache_confirmacao_val{suffix}_2026-10-21';rgb_cache=np.load(cache/'rgb.npy',mmap_mode='r');oldpolar=np.load(cache/'polar.npy',mmap_mode='r');oldred=np.load(cache/'red.npy',mmap_mode='r')
        polar=np.array(oldpolar,copy=True);red=np.array(oldred,copy=True)
        with np.load(cache/'valid.npz') as z:rv=z['rgb'];pv=z['polar']
        changed=[];details=[]
        for start in range(0,len(rows),32):
            photos=[]
            for row in rows[start:start+32]:
                with Image.open(ROOT/'data/ubipr/single_eye'/Path(row.image).name) as im:image=im.convert('RGB')
                if row.session==2 and kind!='original':
                    with Image.open(ROOT/'data/ubipr/single_eye'/Path(row.mask).name) as annotation:reference=decode_mask(annotation)==1
                    image,_=perturb(image,reference,kind,10)
                photos.append(image)
            x=torch.from_numpy(np.stack([np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for im in photos]).transpose(0,3,1,2).copy()).to(device)
            with torch.inference_mode():masks=unet(x).argmax(1).cpu().numpy()==1
            for offset,(im,small) in enumerate(zip(photos,masks)):
                i=start+offset;mask=np.asarray(Image.fromarray(small).resize(im.size,Image.Resampling.NEAREST),bool);assert bool(mask.any())==bool(rv[i])
                np.testing.assert_array_equal(np.asarray(masked_crop(im,mask).resize((128,128),Image.Resampling.BILINEAR)),rgb_cache[i])
                try:newpolar,newred,geometry,applied=refined_textures(np.asarray(im),mask,locator,device)
                except ValueError:
                    assert not pv[i];continue
                assert pv[i]
                if applied:
                    polar[i]=newpolar;red[i]=newred;changed.append(i);details.append(dict(image=Path(rows[i].image).name,session=rows[i].session,pupil_ellipse=geometry['pupil_ellipse'],polar_support=geometry['polar_mask_fraction']))
                else:
                    np.testing.assert_array_equal(newpolar,oldpolar[i]);np.testing.assert_array_equal(newred,oldred[i])
        if condition=='clean':clean_gallery=(polar[gi].copy(),red[gi].copy())
        else:
            np.testing.assert_array_equal(polar[gi],clean_gallery[0]);np.testing.assert_array_equal(red[gi],clean_gallery[1])
        np.savez_compressed(out/f'changed_inputs_{condition}.npz',indices=np.array(changed),polar=polar[changed],red=red[changed])
        changes.append(dict(condition=condition,changed_images=len(changed),changed_queries=sum(rows[i].session==2 for i in changed),details=details));print(json.dumps({k:v for k,v in changes[-1].items() if k!='details'}),flush=True)
        def save(name,result):
            full,valid=result;scores,labels,_=subset(full,rows,ids);data=dict(scores=scores,labels=labels,valid=valid);np.testing.assert_array_equal(labels,originals[condition][name]['labels']);np.testing.assert_array_equal(valid,originals[condition][name]['valid']);modified[condition][name]=data;np.savez_compressed(out/f'component_{name}_{condition}.npz',**data)
        model=IdentityEncoder().to(device).eval();model.load_state_dict(torch.load(weights['polar'],map_location='cpu',weights_only=True)['model']);save('polar',global_scores(extract(model,polar,device),pv,rows));save('spatial',spatial(model,polar,pv,rows,device));del model
        model,_=reconhecedor_transformer_polar.load(weights['transformer'],device);save('transformer',global_scores(extract(model,polar,device),pv,rows));del model
        arc=ROOT/'data/modelos/cvrl_arciris';file=next(arc.rglob('ResNet100_154000.pt'));assert digest(file)=='466014be7723eb0b1a741dcff5a0c8ae51d1918818a6b021952f9c4ccd443f8f';assert digest(arc/'modules/network.py')=='de7f0cb796ebf4be02818c704d7e3afa0047dc09719b131b37cb8c26c42dd327'
        spec=importlib.util.spec_from_file_location('arc_pupil_eval',arc/'modules/network.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);model=module.iresnet100();model.load_state_dict(torch.load(file,map_location='cpu',weights_only=True));model.to(device).eval()
        save('arc_clahe',global_scores(extract(model,polar,device,8,True),pv,rows,True));save('arc_red',global_scores(extract(model,red,device,8,True),pv,rows,True));del model
        if device.type=='cuda':torch.cuda.empty_cache()
    frozen=json.loads((ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json').read_text());results=[];parameters={}
    circle_control={}
    for condition in originals:
        circle_control[condition]=dict(originals[condition])
        for name in ['polar','spatial','transformer','arc_clahe','arc_red']:
            circle_control[condition][name]=read(ROOT/'outputs/pupila_aprendida_val_2026-10-22'/f'component_{name}_{condition}.npz')
    new_calibration=calibrate([modified['clean'][name] for name in ORDER])
    for strategy,group,calibration in [('original_control',originals,frozen['component_calibration_red_and_clahe']),('circle_fixed',circle_control,frozen['component_calibration_red_and_clahe']),('ellipse_fixed',modified,frozen['component_calibration_red_and_clahe']),('ellipse_clean_calibrated',modified,new_calibration)]:
        data={}
        for condition,components in group.items():
            scores,valid=fuse([components[name] for name in ORDER],calibration);data[condition]=dict(scores=scores,valid=valid,labels=components['rgb']['labels'])
        threshold=frozen['frozen_threshold']
        if strategy=='ellipse_clean_calibrated':
            clean=data['clean'];imp=np.ones_like(clean['scores'],bool);imp[np.arange(482),clean['labels']]=False;threshold=operating_threshold(clean['scores'][imp&clean['valid'][:,None]&(clean['scores']>-2)])
        parameters[strategy]=dict(component_calibration=calibration,threshold=threshold)
        for condition,c in data.items():
            result,correct,accepted=metrics(c['scores'],c['labels'],threshold,c['valid']);result.update(strategy=strategy,condition=condition,threshold=threshold,joint_success=float((correct&accepted).mean()));results.append(result);np.savez_compressed(out/f'scores_{strategy}_{condition}.npz',**c,correct=correct,accepted=accepted)
            if strategy=='circle_fixed':
                with np.load(ROOT/'outputs/pupila_aprendida_val_2026-10-22'/f'scores_new_fixed_{condition}.npz') as z:
                    np.testing.assert_array_equal(c['scores'],z['scores']);np.testing.assert_array_equal(correct,z['correct']);np.testing.assert_array_equal(accepted,z['accepted'])
            with (out/f'scores_{strategy}_{condition}.csv').open('w',encoding='utf-8',newline='') as stream:
                writer=csv.writer(stream);writer.writerow(['query','label','valid','correct','accepted']+[f'score_{i}' for i in range(16)])
                for i in range(482):writer.writerow([i,int(c['labels'][i]),bool(c['valid'][i]),bool(correct[i]),bool(accepted[i])]+c['scores'][i].tolist())
            if strategy=='original_control':
                suffix=dict(clean='',upper10='_oclusao_superior_10',lower10='_oclusao_inferior_10')[condition]
                with np.load(ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21/scores_finais.npz') as z:np.testing.assert_allclose(c['scores'],z['scores'],atol=1e-12,rtol=0);np.testing.assert_array_equal(correct,z['correct']);np.testing.assert_array_equal(accepted,z['accepted'])
    final=dict(status='pupil_shape_identity_validation_completed',results=results,parameters=parameters,changes=changes,source_sha256=sources,shape_checkpoint_sha256=digest(checkpoint),circle_checkpoint_sha256=training['circle_checkpoint_sha256'],test_inference=False,frozen_candidate_replaced=False,minimum_area=None,rgb_inputs_and_unmodified_polars_verified=True,enrollment_inputs_same_across_conditions=True)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(results,indent=2),flush=True)


if __name__=='__main__':main()

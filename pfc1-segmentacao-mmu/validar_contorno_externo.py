"""Validação biométrica condicional da correção externa; nenhum acesso ao teste."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,importlib.util,json,tempfile
import numpy as np
from PIL import Image
import torch
from contorno_externo import OuterCorrection,outer_ellipse,ellipse_vector,segmentation_features,refined_textures
ROOT=Path(__file__).resolve().parent
ORDER=['rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red']
CONDITIONS=[('clean','original',0),('upper10','oclusao_superior',10),('lower10','oclusao_inferior',10)]

def main():
    from avaliar_candidato_congelado import WEIGHTS,digest,extract,global_scores,spatial,fuse
    from avaliar_robustez_reconhecimento import load_splits,identity,perturb,metrics,operating_threshold
    from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
    from avaliar_dinov3_ubipr import masked_crop
    from validar_lateralidade_informada import subset
    from validar_fusao_identidade_adaptada import calibrate
    from treinar_identidade_iris import IdentityEncoder
    import reconhecedor_transformer_polar
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--registrar',action='store_true');p.add_argument('--training-name',default='contorno_externo_2026-10-23');p.add_argument('--experiment-name',default='contorno_externo_val_2026-10-23');a=p.parse_args()
    if any(Path(n).name!=n or n in ['.','..'] for n in [a.training_name,a.experiment_name]):raise ValueError('Single experiment folder names required')
    out=a.output_root/a.experiment_name;trained=a.output_root/a.training_name
    if a.registrar:
        out.mkdir(parents=True,exist_ok=False)
        protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Exploratory reused development validation ONLY, conditional on training geometry gate; no test inference or automatic promotion.',
            intervention='Only polar outer ellipse from whole-photo frozen-U-Net features and trained residual; fixed guards fallback to original. RGB/native crops, masks and inner ellipses unchanged. Gray/red textures recomputed from original or occluded query pixels. One photograph,side informed,16same-side candidates,all482queries and480S1images.',
            comparisons='Primary clean-only recalibration of component means/stds and threshold, applied unchanged to both10%occlusions; secondary old fixed calibration diagnostic. Same9components/equal8groups; no group or parameter search.',
            advancement='Clean Rank1/TAR>=90%,FMR<=1%; BOTH10%occlusions improve Rank1 and TAR vs reference and FMR<=1%. Separate absolute target flag requires Rank1/TAR>=90% and FMR<=1% in all3conditions. No promotion or test inference automatically.',
            training_experiment=a.training_name,training_protocol_sha256=digest(trained/'protocolo.json'),module_sha256=digest(ROOT/'contorno_externo.py'),script_sha256=digest(Path(__file__)),conditions=CONDITIONS)
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Protocolo biometrico registrado antes da inferencia de reconhecimento.');return
    protocol=json.loads((out/'protocolo.json').read_text('utf-8'));assert protocol['script_sha256']==digest(Path(__file__)) and protocol['module_sha256']==digest(ROOT/'contorno_externo.py') and protocol['training_protocol_sha256']==digest(trained/'protocolo.json')
    if (out/'CONCLUIDO.json').exists():raise ValueError('Preserve completed validation')
    training=json.loads((trained/'CONCLUIDO.json').read_text('utf-8'))
    if not training['recognition_validation_gate_passed']:
        result=dict(status='outer_geometry_gate_failed_no_identity_inference',training=training,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
        (out/'CONCLUIDO.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result));return
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    checkpoint=trained/'melhor_modelo.pt';assert digest(checkpoint)==training['checkpoint_sha256'];state=torch.load(checkpoint,map_location='cpu',weights_only=True)
    locator=OuterCorrection().to(device).eval();locator.load_state_dict(state['model']);mean=state['feature_mean'].to(device);std=state['feature_std'].to(device)
    unet_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';assert digest(unet_file)==state['configuration']['unet_sha256']
    unet=MulticlassUNet(8).to(device).eval();unet.load_state_dict(torch.load(unet_file,map_location='cpu',weights_only=True)['model'])
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());rows=load_splits(manifest)['val'];assert len(rows)==962 and sum(r.session==2 for r in rows)==482
    assert not {r.subject for r in rows}&set(state['configuration']['fit_people']+state['configuration']['monitor_people'])
    ids=sorted({identity(r) for r in rows});gi=[i for i,r in enumerate(rows) if r.session==1]
    frozen=json.loads((ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json').read_text());originals={};grouped={};changes=[];gallery=None;input_hashes={}
    for tag,kind,level in CONDITIONS:
        suffix='' if tag=='clean' else '_'+kind+'_10';old=ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21';cache=Path(tempfile.gettempdir())/f'cache_confirmacao_val{suffix}_2026-10-21'
        originals[tag]={}
        for name in ORDER:
            file=old/f'scores_{name}.npz';input_hashes[str(file)]=digest(file)
            with np.load(file) as z:originals[tag][name]={k:z[k] for k in ['scores','labels','valid']}
        grouped[tag]=dict(originals[tag]);polar=np.array(np.load(cache/'polar.npy',mmap_mode='r'),copy=True);red=np.array(np.load(cache/'red.npy',mmap_mode='r'),copy=True);rgb=np.load(cache/'rgb.npy',mmap_mode='r')
        with np.load(cache/'valid.npz') as z:rv=z['rgb'];pv=z['polar']
        details=[];counts={};changed=[]
        for start in range(0,len(rows),32):
            photos=[]
            for row in rows[start:start+32]:
                with Image.open(row.image) as im:image=im.convert('RGB')
                if row.session==2 and kind!='original':
                    with Image.open(row.mask) as im:reference=decode_mask(im)==1
                    image,_=perturb(image,reference,kind,level)
                photos.append(image)
            x=torch.from_numpy(np.stack([np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for im in photos]).transpose(0,3,1,2).copy()).to(device)
            with torch.inference_mode():logits,features=segmentation_features(unet,x)
            small=logits.argmax(1).cpu().numpy()==1;baselines=[];masks=[]
            for im,mask in zip(photos,small):
                mask=np.asarray(Image.fromarray(mask).resize(im.size,Image.Resampling.NEAREST),bool);masks.append(mask)
                try:b=ellipse_vector(outer_ellipse(mask),*im.size)
                except ValueError:b=np.zeros(5,np.float32)
                baselines.append(b)
            with torch.inference_mode():predictions=locator((features-mean)/std,torch.from_numpy(np.stack(baselines)).to(device)).cpu().numpy()
            for offset,(im,mask,value) in enumerate(zip(photos,masks,predictions)):
                i=start+offset
                np.testing.assert_array_equal(np.asarray(masked_crop(im,mask).resize((128,128),Image.Resampling.BILINEAR)),rgb[i])
                try:new,newred,geometry,applied,reason=refined_textures(np.asarray(im),mask,value)
                except ValueError:
                    assert not pv[i];counts['original_polar_invalid']=counts.get('original_polar_invalid',0)+1;continue
                assert pv[i];counts[reason]=counts.get(reason,0)+1
                if applied:
                    polar[i]=new;red[i]=newred;changed.append(i);details.append(dict(image=Path(rows[i].image).name,session=rows[i].session,baseline=baselines[offset].tolist(),predicted=value.tolist(),outer_roi=geometry['iris_ellipse']))
                else:
                    np.testing.assert_array_equal(new,polar[i]);np.testing.assert_array_equal(newred,red[i])
        if gallery is None:gallery=(polar[gi].copy(),red[gi].copy())
        else:np.testing.assert_array_equal(polar[gi],gallery[0]);np.testing.assert_array_equal(red[gi],gallery[1])
        folder=out/tag;folder.mkdir();np.savez_compressed(folder/'changed_inputs.npz',indices=np.array(changed),polar=polar[changed],red=red[changed])
        changes.append(dict(condition=tag,applied_images=len(changed),applied_queries=sum(rows[i].session==2 for i in changed),guards=counts,details=details));print(json.dumps({k:v for k,v in changes[-1].items() if k!='details'}),flush=True)
        def save(name,result):
            full,valid=result;scores,labels,_=subset(full,rows,ids);np.testing.assert_array_equal(labels,originals[tag][name]['labels']);np.testing.assert_array_equal(valid,originals[tag][name]['valid'])
            grouped[tag][name]=dict(scores=scores,valid=valid,labels=labels);np.savez_compressed(folder/f'scores_{name}.npz',**grouped[tag][name]);print(f'{tag}: {name}',flush=True)
        file=ROOT/'outputs'/WEIGHTS['polar'][0]/'melhor_modelo.pt';assert digest(file)==WEIGHTS['polar'][1]
        model=IdentityEncoder().to(device).eval();model.load_state_dict(torch.load(file,map_location='cpu',weights_only=True)['model']);save('polar',global_scores(extract(model,polar,device),pv,rows));save('spatial',spatial(model,polar,pv,rows,device));del model
        file=ROOT/'outputs'/WEIGHTS['transformer'][0]/'melhor_modelo.pt';assert digest(file)==WEIGHTS['transformer'][1]
        model,_=reconhecedor_transformer_polar.load(file,device);save('transformer',global_scores(extract(model,polar,device),pv,rows));del model
        arc=ROOT/'data/modelos/cvrl_arciris';file=next(arc.rglob('ResNet100_154000.pt'));assert digest(file)=='466014be7723eb0b1a741dcff5a0c8ae51d1918818a6b021952f9c4ccd443f8f'
        assert digest(arc/'modules/network.py')=='de7f0cb796ebf4be02818c704d7e3afa0047dc09719b131b37cb8c26c42dd327'
        spec=importlib.util.spec_from_file_location('arc_outer_contour',arc/'modules/network.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);model=module.iresnet100();model.load_state_dict(torch.load(file,map_location='cpu',weights_only=True));model.to(device).eval()
        save('arc_clahe',global_scores(extract(model,polar,device,8,True),pv,rows,True));save('arc_red',global_scores(extract(model,red,device,8,True),pv,rows,True));del model
        if device.type=='cuda':torch.cuda.empty_cache()
    calibration=calibrate([grouped['clean'][n] for n in ORDER]);results=[];parameters={};baseline={}
    for tag,c in originals.items():
        scores,valid=fuse([c[n] for n in ORDER],frozen['component_calibration_red_and_clahe']);baseline[tag]=metrics(scores,c['rgb']['labels'],frozen['frozen_threshold'],valid)[0]
    for strategy,params in [('outer_clean_calibrated',calibration),('outer_fixed_diagnostic',frozen['component_calibration_red_and_clahe'])]:
        data={tag:dict(zip(['scores','valid'],fuse([c[n] for n in ORDER],params))) for tag,c in grouped.items()}
        labels=grouped['clean']['rgb']['labels'];c=data['clean'];imp=np.ones_like(c['scores'],bool);imp[np.arange(482),labels]=False
        threshold=operating_threshold(c['scores'][imp&c['valid'][:,None]&(c['scores']>-2)]) if strategy=='outer_clean_calibrated' else frozen['frozen_threshold'];parameters[strategy]=dict(calibration=params,threshold=threshold)
        for tag,c in data.items():
            measured,correct,accepted=metrics(c['scores'],labels,threshold,c['valid']);measured.update(strategy=strategy,condition=tag,rank1_correct=int(correct.sum()),genuine_accepted=int(accepted.sum()),threshold=threshold);results.append(measured)
            np.savez_compressed(out/f'{strategy}_{tag}.npz',**c,labels=labels,correct=correct,accepted=accepted)
            with (out/f'{strategy}_{tag}.csv').open('w',newline='',encoding='utf-8') as stream:
                writer=csv.writer(stream);writer.writerow(['query','label','valid','correct','accepted']+[f'score_{i}' for i in range(16)])
                for i in range(482):writer.writerow([i,int(labels[i]),bool(c['valid'][i]),bool(correct[i]),bool(accepted[i])]+c['scores'][i].tolist())
            print(json.dumps(measured),flush=True)
    primary={r['condition']:r for r in results if r['strategy']=='outer_clean_calibrated'};clean=primary['clean']
    gate=clean['rank1']>=.9 and clean['tar']>=.9 and clean['far']<=.01 and all(primary[c][m]>baseline[c][m] for c in ['upper10','lower10'] for m in ['rank1','tar']) and all(primary[c]['far']<=.01 for c in ['upper10','lower10'])
    absolute=all(r['rank1']>=.9 and r['tar']>=.9 and r['far']<=.01 for r in primary.values())
    final=dict(status='outer_contour_identity_validation_completed',results=results,baseline=baseline,parameters=parameters,changes=changes,source_scores_sha256=input_hashes,checkpoint_sha256=digest(checkpoint),promotion_gate_passed=bool(gate),absolute_all_conditions_target_reached=bool(absolute),rgb_inputs_exact=True,enrollment_inputs_same_across_conditions=True,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in final.items() if k not in ['changes','parameters','source_scores_sha256']}),flush=True)

if __name__=='__main__':main()

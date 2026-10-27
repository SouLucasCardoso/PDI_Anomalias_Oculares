"""Piloto train-only: compensa mudanca de geometria sem alterar o encoder polar."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,json
import numpy as np
from PIL import Image
import torch
from treinar_identidade_residual import fit_residual,correct
ROOT=Path(__file__).resolve().parent

def apply_transport(features,changed,parameters):
    result=np.array(features,copy=True)
    indices=np.flatnonzero(changed)
    if len(indices):result[indices]=correct(features[indices],features[indices],parameters).astype(result.dtype)
    return result

def main():
    from avaliar_candidato_congelado import digest,WEIGHTS,extract,global_scores
    from treinar_segmentacao_ubipr import Sample,MulticlassUNet
    from treinar_identidade_iris import IdentityEncoder
    from avaliar_robustez_reconhecimento import identity,metrics,operating_threshold
    from validar_lateralidade_informada import subset
    from pupila_eliptica import EllipseLocator,refined_textures
    from textura_polar import prepare_texture
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);args=p.parse_args()
    out=args.output_root/'transporte_descritor_polar_2026-10-23';out.mkdir(parents=True,exist_ok=False)
    manifest_path=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_path.read_text());rows=[Sample(**r) for r in manifest['train']]
    previous=ROOT/'outputs/localizador_pupila_2026-10-22';split=json.loads((previous/'protocolo.json').read_text());monitor=set(split['monitor_people']);fit=set(split['fit_people'])
    assert not monitor&fit and {r.subject for r in rows}==monitor|fit
    assert not (monitor|fit)&{r['subject'] for r in manifest['val']}
    shape=ROOT/'outputs/forma_pupila_2026-10-23/melhor_forma.json';shape_training=json.loads((shape.parent/'CONCLUIDO.json').read_text())
    import hashlib
    shape_canonical=hashlib.sha256(shape.read_bytes().rstrip(b'\r\n')).hexdigest();assert shape_canonical==shape_training['shape_sha256']
    checkpoint=ROOT/'outputs'/WEIGHTS['polar'][0]/'melhor_modelo.pt';assert digest(checkpoint)==WEIGHTS['polar'][1]
    unet_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';assert digest(unet_file)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    cache=ROOT/'data/cache_encoder_polar_2026-10-20';audit=json.loads((cache/'train_auditoria.json').read_text())
    assert len(audit)==len(rows)==7716
    for row,old in zip(rows,audit):assert Path(row.image).name==old['image']
    protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='TRAIN-only descriptor-domain transport pilot. No validation/test inference, no new encoder training, no automatic promotion. Previously trained polar encoder and segmentation saw original training people including internal monitor. Shape selection also reused monitor; no independent generalization claim.',
        hypothesis='Frozen polar embeddings may shift under ellipse geometry. Fit a fixed residual map from new embedding to original same-photo teacher embedding, only on actual changed geometry for167fit people. Apply only changed geometry; ordinary images bit-identical.',
        method='Reuse fixed standardized weighted ridge fit_residual lambda1,uniform image weights,unpenalized offset;256input->256residual;L2(new embedding+predicted residual),cast to originalfloat32. No hyperparameter/weight search, no identities in regression targets.',
        monitor='All960photos/480S2queries of16internal monitor people,16same-side candidates. Original geometry,new ellipse geometry,transported geometry; clean condition ONLY. Failed extraction retained. One empirical FMR<=1% threshold per method on monitor, descriptive calibration. No artificial occlusion and no annotation masks used in this inference.',
        gate='Any later development validation permitted only if corrected mean same-photo cosine improves on CHANGED valid monitor photos AND all480query Rank1 and TAR are >= BOTH original and uncorrected ellipse values. No exception or rerun if fails. Improvement of teacher alignment alone is insufficient.',
        geometry='Recompute native masks ONLY259cached fallback images; assert old polar pixel-exact to original cache. Else reuse old polar and old embedding exactly. All identity weights frozen. Train mask validity/image order checked.',
        fit_people=sorted(fit),monitor_people=sorted(monitor),manifest_sha256=digest(manifest_path),encoder_sha256=digest(checkpoint),segmenter_sha256=digest(unet_file),shape_canonical_sha256=shape_canonical,
        script_sha256=digest(Path(__file__)),residual_source_sha256=digest(ROOT/'treinar_identidade_residual.py'),shape_source_sha256=digest(ROOT/'pupila_eliptica.py'),circle_sha256=digest(previous/'melhor_modelo.pt'),crop_audit_sha256=digest(cache/'train_auditoria.json'))
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    old_images=np.load(cache/'train_polar.npy',mmap_mode='r');valid=np.load(cache/'train_valid.npy');assert len(old_images)==7716 and np.array_equal(valid,np.array([r['valid'] for r in audit]))
    fallback=[i for i,r in enumerate(audit) if (r.get('geometry') or {}).get('pupil_source')=='circle_regressor_fallback'];assert len(fallback)==259
    locator=EllipseLocator(shape,device);unet=MulticlassUNet(8).to(device).eval();unet.load_state_dict(torch.load(unet_file,map_location='cpu',weights_only=True)['model'])
    changed=[];new_images=[]
    for start in range(0,len(fallback),32):
        indices=fallback[start:start+32];photos=[]
        for i in indices:
            with Image.open(ROOT/'data/ubipr/single_eye'/Path(rows[i].image).name) as im:photos.append(im.convert('RGB'))
        x=torch.from_numpy(np.stack([np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for im in photos]).transpose(0,3,1,2).copy()).to(device)
        with torch.inference_mode():masks=unet(x).argmax(1).cpu().numpy()==1
        for i,im,small in zip(indices,photos,masks):
            mask=np.asarray(Image.fromarray(small).resize(im.size,Image.Resampling.NEAREST),bool)
            original,_=prepare_texture(np.asarray(im),mask);np.testing.assert_array_equal(original,old_images[i])
            polar,_,_,applied=refined_textures(np.asarray(im),mask,locator,device)
            if applied and not np.array_equal(polar,original):changed.append(i);new_images.append(polar)
        print(json.dumps(dict(phase='geometry',processed=min(start+32,len(fallback)),total=len(fallback))),flush=True)
    del unet,locator
    encoder=IdentityEncoder().to(device).eval();encoder.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
    teacher=extract(encoder,old_images,device);student=teacher.copy();student[changed]=extract(encoder,np.stack(new_images),device)
    del encoder
    changed_flag=np.zeros(len(rows),bool);changed_flag[changed]=True
    fit_indices=np.array([i for i in changed if rows[i].subject in fit and valid[i]],int);monitor_indices=np.array([i for i in changed if rows[i].subject in monitor and valid[i]],int)
    assert len(fit_indices)>0 and len(monitor_indices)>0 and not set(fit_indices)&set(monitor_indices)
    parameters=fit_residual(student[fit_indices],teacher[fit_indices]-student[fit_indices],np.ones(len(fit_indices)),regularization=1.)
    transported=apply_transport(student,changed_flag,parameters);np.testing.assert_array_equal(transported[~changed_flag],teacher[~changed_flag])
    np.savez_compressed(out/'transporte.npz',**parameters)
    # Derived vectors allow independent replay; kept outside the protected workspace.
    np.savez_compressed(out/'cache_embeddings.npz',teacher=teacher,student=student,transported=transported,changed=changed_flag,valid=valid,fit_indices=fit_indices,monitor_changed_indices=monitor_indices)
    positions=[i for i,r in enumerate(rows) if r.subject in monitor];monitor_rows=[rows[i] for i in positions];ids=sorted({identity(r) for r in monitor_rows})
    results=[]
    for method,vectors in [('original',teacher),('ellipse',student),('transported',transported)]:
        full,qvalid=global_scores(vectors[positions],valid[positions],monitor_rows);scores,labels,_=subset(full,monitor_rows,ids)
        impostor=np.ones_like(scores,bool);impostor[np.arange(len(labels)),labels]=False;threshold=operating_threshold(scores[impostor&qvalid[:,None]&(scores>-2)])
        measured,correctness,accepted=metrics(scores,labels,threshold,qvalid);measured.update(method=method,threshold=threshold);results.append(measured)
        np.savez_compressed(out/f'scores_{method}.npz',scores=scores,labels=labels,valid=qvalid,correct=correctness,accepted=accepted)
    # Same-photo cosine is an alignment diagnostic, NOT identification accuracy.
    cosine=lambda features:np.sum(features[monitor_indices].astype(np.float64)*teacher[monitor_indices].astype(np.float64),axis=1)
    before=cosine(student);after=cosine(transported);monitor_scores={r['method']:r for r in results}
    gate=bool(after.mean()>before.mean() and all(monitor_scores['transported'][k]>=monitor_scores[method][k] for k in ['rank1','tar'] for method in ['original','ellipse']))
    drift_rows=[]
    for i in changed:
        drift_rows.append(dict(image=Path(rows[i].image).name,subject=rows[i].subject,role='monitor' if rows[i].subject in monitor else 'fit',session=rows[i].session,cosine_before=float(np.dot(student[i].astype(np.float64),teacher[i].astype(np.float64))),cosine_after=float(np.dot(transported[i].astype(np.float64),teacher[i].astype(np.float64)))))
    with (out/'alinhamento_por_imagem.csv').open('w',encoding='utf-8',newline='') as f:writer=csv.DictWriter(f,fieldnames=list(drift_rows[0]));writer.writeheader();writer.writerows(drift_rows)
    final=dict(status='train_only_polar_transport_completed',fit_changed_images=len(fit_indices),monitor_changed_images=len(monitor_indices),original_fallback_images=len(fallback),actual_changed_images=len(changed),monitor_queries=480,results=results,monitor_teacher_cosine_before=float(before.mean()),monitor_teacher_cosine_after=float(after.mean()),recognition_validation_gate_passed=gate,parameters_sha256=digest(out/'transporte.npz'),encoder_sha256_unchanged=digest(checkpoint)==protocol['encoder_sha256'],unchanged_images_exact=True,original_polar_fallback_inputs_exact=True,validation_identity_inference=False,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    assert digest(checkpoint)==protocol['encoder_sha256'] and all(r['queries']==480 for r in results)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()

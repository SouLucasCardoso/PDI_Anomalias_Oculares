"""Adapta apenas o ramo polar à geometria SAM3.1 com professor original.

Somente pessoas de treino; seleção contra a referência original na validação.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,collections,json,os,random,time,traceback
import cv2,numpy as np,torch
from PIL import Image
from torch import nn
from torch.utils.data import Dataset,DataLoader
from torchvision import transforms
from geometria_polar_sam31 import Sam31OuterGeometry
from recorte_iris_sam31_alta_res import sha
from treinar_segmentacao_ubipr import Sample,MulticlassUNet,decode_mask
from treinar_identidade_iris import IdentityEncoder,AngularHead
from reconhecedor_resnet50 import SessionBatches,supervised_contrastive
from avaliar_candidato_congelado import extract,global_scores,fuse,WEIGHTS
from avaliar_robustez_reconhecimento import load_splits,identity,perturb,metrics
from validar_lateralidade_informada import subset
from treinar_reconhecedor_entrega import ORDER,CONDITIONS,eligibility,selection_key,frozen_digest
from rodada_reconhecedor_entrega import result_path,write

ROOT=Path(__file__).resolve().parent
LEVELS=(1,5,10,20,30,31)

def choose_training(rows):
    groups=collections.defaultdict(list)
    for i,r in enumerate(rows):groups[(identity(r),r.session)].append(i)
    rng=np.random.default_rng(20261108);selected=[]
    for key,indices in sorted(groups.items()):selected.extend(int(i) for i in rng.choice(indices,min(2,len(indices)),replace=False))
    return sorted(selected)

def prepare_training(rows,run,device,stage):
    folder=run/'cache_treino';folder.mkdir();rng=np.random.default_rng(20261108);plan=rng.choice(LEVELS,(len(rows),2))
    write(folder/'PLANO.json',{'rows':[r.image for r in rows],'upper_lower_loss_percent':plan.tolist(),'seed':20261108})
    images=np.lib.format.open_memmap(folder/'polar.npy',mode='w+',dtype=np.uint8,shape=(3,len(rows),64,512,3));valid=np.zeros((3,len(rows)),bool);details=[]
    sam=Sam31OuterGeometry();write(run/'SAM_ESTRITO.json',sam.audit)
    unet=MulticlassUNet(8).to(device).eval();file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';assert sha(file)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    unet.load_state_dict(torch.load(file,map_location='cpu',weights_only=True)['model']);completed=0
    for start in range(0,len(rows),32):
        originals=[Image.open(r.image).convert('RGB') for r in rows[start:start+32]]
        references=[decode_mask(Image.open(r.mask))==1 for r in rows[start:start+32]]
        for view,condition in enumerate(('original','oclusao_superior','oclusao_inferior')):
            photos=[im if view==0 else perturb(im,reference,condition,int(plan[start+j,view-1]))[0] for j,(im,reference) in enumerate(zip(originals,references))]
            x=torch.from_numpy(np.stack([np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for im in photos]).transpose(0,3,1,2).copy()).to(device)
            with torch.inference_mode():masks=unet(x).argmax(1).cpu().numpy()==1
            for j,(photo,mask) in enumerate(zip(photos,masks)):
                i=start+j;support=np.asarray(Image.fromarray(mask).resize(photo.size,Image.Resampling.NEAREST),bool)
                try:band,_,detail=sam.polar(photo,support);images[view,i]=band;valid[view,i]=True
                except ValueError as error:images[view,i]=127;detail={'status':'invalid_original_support','reason':str(error)}
                details.append({'row':i,'condition':condition,'detail':detail});completed+=1
            stage('preparando_treino_sam31',completed=completed,total=3*len(rows))
        print(f'SAM training input {completed}/{3*len(rows)}',flush=True)
    images.flush();np.save(folder/'valid.npy',valid);write(folder/'GEOMETRIAS.json',details)
    write(folder/'CONCLUIDO.json',{'shape':list(images.shape),'valid_by_view':valid.sum(1).tolist(),'sha256':sha(folder/'polar.npy'),'plan_sha256':sha(folder/'PLANO.json')})
    sam.close();del unet;torch.cuda.empty_cache();return images,valid

class PolarPairs(Dataset):
    def __init__(self,images,valid,rows,labels,teacher,teacher_valid):
        self.images=images;self.valid=valid;self.rows=rows;self.labels=labels;self.teacher=teacher
        self.positions=np.flatnonzero(valid[0]&teacher_valid)
        self.transform=transforms.Compose([transforms.ToTensor(),transforms.ColorJitter(brightness=.05,contrast=.05),transforms.Normalize([.485,.456,.406],[.229,.224,.225])])
    def __len__(self):return len(self.positions)
    def __getitem__(self,index):
        i=int(self.positions[index]);u=random.random();view=0 if u<.5 else 1 if u<.75 else 2
        if not self.valid[view,i]:view=0
        image=np.roll(np.array(self.images[view,i],copy=True),random.randint(-8,8),axis=1)
        return self.transform(image),self.labels[identity(self.rows[i])],torch.from_numpy(self.teacher[i].copy())

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--reference-root',type=Path,required=True);p.add_argument('--geometry-run',type=Path,required=True);p.add_argument('--versions-json',type=Path,required=True);a=p.parse_args();run=a.run_dir.resolve();run.mkdir(parents=True,exist_ok=False)
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_file.read_text());alltrain=[Sample(**r) for r in manifest['train']];indices=choose_training(alltrain);train=[alltrain[i] for i in indices];val=load_splits(manifest)['val'];labels={eye:i for i,eye in enumerate(sorted({identity(r) for r in alltrain}))}
    assert not {r.subject for r in train}&{r.subject for r in val};assert not {r.subject for r in train}&{r['subject'] for r in manifest['test']}
    initial_file=ROOT/'outputs/encoder_polar_2026-10-20/melhor_modelo.pt';assert sha(initial_file)==WEIGHTS['polar'][1]
    oldcache=ROOT/'data/cache_encoder_polar_2026-10-20';old_inputs=oldcache/'train_polar.npy';old_valid=oldcache/'train_valid.npy'
    versions=json.loads(a.versions_json.read_text(encoding='utf-8-sig'));assert versions['code_revision']=='f1647e8d0c1d280991f4d1b7d974c2704537fe66' and versions['checkpoint_revision']=='daa63191845a41281374e725f4c9e51c7a824460'
    source_names=('treinar_polar_sam31_entrega.py','geometria_polar_sam31.py','recorte_iris_sam31_alta_res.py','avaliar_candidato_congelado.py','avaliar_robustez_reconhecimento.py','reconhecedor_resnet50.py','treinar_identidade_iris.py')
    sources={n:sha(ROOT/n) for n in source_names}
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Bounded supervised development; training people only; repeated validation selection, no test inference',
        'sources_sha256':sources,'manifest_sha256':sha(manifest_file),'initial_checkpoint_sha256':sha(initial_file),'teacher_input_sha256':sha(old_inputs),'teacher_valid_sha256':sha(old_valid),
        'training_subset_indices':indices,'selection_of_training_images':'RNG20261108,up to2photospertrain-eye-persession,noqualityoroutcomefilter',
        'counts':{'images':len(train),'train_people':len({r.subject for r in train}),'train_classes':len(labels),'validation_queries':sum(r.session==2 for r in val)},
        'input':'Only polar descriptor changes: original U-Net support/pupil, SAM3.1 outer ellipse; other8components retain original inputs/weights/calibration. FailedSAM uses originalgeometry. Invalidoriginalsupport retained in validation.',
        'train_augmentation':'Native annotated-iris-only upper/lower losses1,5,10,20,30,31; one draw per direction per photo. Rerun segmentation+SAM geometry. Sample50%clean25%upper25%lower;cyclicroll+/-8columns,jitter5%. No filled texture.',
        'teacher':'Original frozen polarencoder, clean original automatic polartrainingcache, samephoto; distillation target used only for training',
        'trainable':'Only ResNet18layer4,projection,angular366classhead; all earlier parameters and all BatchNormrunningstats frozen',
        'loss':'AngularCE margin0.3 scale30 +0.2SupCon temperature0.1 +1.0(1-cos(student,cleanoriginalteacher))',
        'optimizer':'AdamW layer4lr1e-5,projection/head5e-5,wd1e-4,cosine16epochs,clip5,BF16encoderFP32losses;16eyesx4captures,4roundsbalancedsessions',
        'selection':'Compare full9fusion against ORIGINAL reference, not against changed-inputepoch0. Require cleanRank1/TAR no lower,cleanFMR<=1%,occludedFMR each no greater,mean3joint higher. Max meanjoint,worstjoint,meanRank1. Epoch0included; noeligible=>keeporiginalsystem. Patience6afterepoch6,max16. All482queries retained.',
        'seed':20261108,'max_epochs':16,'patience':6,'deadline_utc':'2026-11-09T01:30:00+00:00','versions':{'torch':str(torch.__version__),'numpy':np.__version__},'official_sam_verification':versions,'automatic_replacement':False}
    write(run/'protocolo.json',protocol);(run/'source.py').write_bytes(Path(__file__).read_bytes());started=time.monotonic()
    def stage(name,**extra):write(run/'estado.json',{'stage':name,'utc':datetime.now(timezone.utc).isoformat(),'pid':os.getpid(),'elapsed_seconds':time.monotonic()-started,**extra})
    (run/'RELATORIO_ATUAL.md').write_text('# Adaptação polar SAM3.1\n\nEm execução. Consulte estado.json para preparação e treinamento. Nenhum candidato foi aprovado ainda.\n',encoding='utf-8')
    try:
        os.environ['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib');random.seed(20261108);np.random.seed(20261108);torch.manual_seed(20261108);torch.set_num_threads(4);cv2.setNumThreads(1);torch.backends.cudnn.benchmark=False;device=torch.device('cuda')
        stage('preparando_treino_sam31');images,valid=prepare_training(train,run,device,stage)
        initial=torch.load(initial_file,map_location='cpu',weights_only=True);assert initial['training_head']['weight'].shape==(len(labels),256)
        stage('calculando_professor');teacher=IdentityEncoder().to(device).eval();teacher.load_state_dict(initial['model'])
        clean=np.load(old_inputs,mmap_mode='r')[indices];teacher_features=extract(teacher,clean,device);teacher_valid=np.load(old_valid)[indices];np.save(run/'teacher.npy',teacher_features);del teacher,clean;torch.cuda.empty_cache()
        dataset=PolarPairs(images,valid,train,labels,teacher_features,teacher_valid);targets=np.array([labels[identity(train[i])] for i in dataset.positions]);sessions=np.array([train[i].session for i in dataset.positions]);sampler=SessionBatches(targets,sessions,seed=20261108);loader=DataLoader(dataset,batch_sampler=sampler,num_workers=0)
        write(run/'AUDITORIA_TREINO.json',{'retained':len(dataset),'excluded_invalid_training_pairs':len(train)-len(dataset),'class_order':labels,'teacher_sha256':sha(run/'teacher.npy')})
        model=IdentityEncoder().to(device);model.load_state_dict(initial['model']);model.requires_grad_(False);model.backbone.layer4.requires_grad_(True);model.projection.requires_grad_(True);head=AngularHead(len(labels)).to(device);head.load_state_dict(initial['training_head']);del initial
        frozen_hash=frozen_digest(model);parameters=list(model.backbone.layer4.parameters())+list(model.projection.parameters())+list(head.parameters())
        optimizer=torch.optim.AdamW([{'params':model.backbone.layer4.parameters(),'lr':1e-5},{'params':list(model.projection.parameters())+list(head.parameters()),'lr':5e-5}],weight_decay=1e-4);scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,T_max=16)
        config=json.loads((ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json').read_text());threshold=config['frozen_threshold'];conditions={};baseline={};ids=sorted({identity(r) for r in val})
        gprotocol=json.loads((a.geometry_run/'protocolo.json').read_text())
        for name,expected in gprotocol['sources_sha256'].items():assert sha(ROOT/name)==expected
        for condition,level in CONDITIONS:
            folder=result_path(a.reference_root,'nearest',condition,level);components=[]
            for name in ORDER:
                with np.load(folder/f'scores_{name}.npz',allow_pickle=False) as z:components.append({k:z[k].copy() for k in ('scores','valid','labels')})
            scores,fv=fuse(components,config['component_calibration_red_and_clahe']);m,c,accepted=metrics(scores,components[0]['labels'],threshold,fv);m.update(joint_success=float((c&accepted).mean()),threshold=threshold);baseline[condition]=m
            conditions[condition]=(np.load(a.geometry_run/condition/'polar.npy',mmap_mode='r'),np.load(a.geometry_run/condition/'valid.npy'),components)
        write(run/'BASELINE_ORIGINAL.json',baseline)
        def evaluate():
            model.eval();results={};data={};raw={}
            for condition,(x,pv,components) in conditions.items():
                full,qvalid=global_scores(extract(model,x,device),pv,val);scores,y,_=subset(full,val,ids);np.testing.assert_array_equal(y,components[0]['labels']);replacement={'scores':scores,'labels':y,'valid':qvalid};items=components.copy();items[1]=replacement
                fused,valid=fuse(items,config['component_calibration_red_and_clahe']);m,c,accepted=metrics(fused,y,threshold,valid);m.update(joint_success=float((c&accepted).mean()),threshold=threshold);results[condition]=m;data[condition]=dict(scores=fused,labels=y,valid=valid,correct=c,accepted=accepted);raw[condition]=replacement
            return results,data,raw
        history=[];bestkey=None;selected_epoch=None;stale=0;deadline=datetime.fromisoformat(protocol['deadline_utc'])
        for epoch in range(17):
            if epoch>0 and datetime.now(timezone.utc)>=deadline:break
            stage('treinando' if epoch else 'avaliando_epoca_zero',epoch=epoch,max_epochs=16,selected_epoch=selected_epoch);losses=[]
            if epoch:
                sampler.epoch=epoch-1;model.train();head.train()
                for module in model.modules():
                    if isinstance(module,nn.modules.batchnorm._BatchNorm):module.eval()
                for batch,(x,y,target) in enumerate(loader):
                    optimizer.zero_grad(set_to_none=True);x=x.to(device);y=y.to(device);target=target.to(device)
                    with torch.autocast('cuda',dtype=torch.bfloat16):features=model(x)
                    features=features.float();ce=nn.functional.cross_entropy(head(features,y),y);con=supervised_contrastive(features,y);distill=(1-(features*target).sum(1)).mean();loss=ce+.2*con+distill
                    if not torch.isfinite(loss):raise ValueError('Perda não finita')
                    loss.backward();nn.utils.clip_grad_norm_(parameters,5);optimizer.step();losses.append([float(ce.detach()),float(con.detach()),float(distill.detach())])
                    if batch%20==0:stage('treinando',epoch=epoch,max_epochs=16,batch=batch,batches=len(loader),selected_epoch=selected_epoch)
                scheduler.step()
            stage('validando',epoch=epoch,max_epochs=16,selected_epoch=selected_epoch);results,data,raw=evaluate();eligible=eligibility(results,baseline);key=selection_key(results)
            if eligible and (bestkey is None or key>bestkey):
                bestkey=key;selected_epoch=epoch;stale=0;metadata=json.loads(json.dumps(protocol));metadata.update(model='ResNet18 polar input3x64x512',dense_texture=False)
                temporary=run/'melhor_modelo.pt.part';torch.save({'model':model.state_dict(),'training_head':head.state_dict(),'epoch':epoch,'validation':results,'configuration':metadata},temporary);temporary.replace(run/'melhor_modelo.pt')
                for condition,d in data.items():np.savez_compressed(run/f'scores_fusion_selected_{condition}.npz',**d);np.savez_compressed(run/f'scores_polar_selected_{condition}.npz',**raw[condition])
            elif epoch:stale+=1
            record={'epoch':epoch,'eligible':eligible,'selected_epoch':selected_epoch,'loss_mean':np.mean(losses,axis=0).tolist() if losses else None,'results':results,'elapsed_seconds':time.monotonic()-started};history.append(record);write(run/'historico.json',history)
            assert frozen_digest(model)==frozen_hash,'Pesos ou estatísticas congeladas mudaram'
            torch.save({'model':model.state_dict(),'training_head':head.state_dict(),'epoch':epoch,'optimizer':optimizer.state_dict(),'scheduler':scheduler.state_dict(),'history':history,'selected_epoch':selected_epoch,'frozen_parameters_sha256':frozen_hash,'python_rng':random.getstate(),'torch_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all()},run/'ultima_epoca.pt')
            lines=['# Adaptação polar SAM3.1','',f'Época:{epoch}/16. Selecionada:{selected_epoch}. Controle original preservado.','',
                '| Condição | Rank-1 | TAR | FMR | Correto e aceito |','|---|---:|---:|---:|---:|']
            for condition,m in results.items():lines.append(f"| {condition} | {100*m['rank1']:.2f}% | {100*m['tar']:.2f}% | {100*m['far']:.3f}% | {100*m['joint_success']:.2f}% |")
            (run/'RELATORIO_ATUAL.md').write_text('\n'.join(lines),encoding='utf-8');print(json.dumps(record),flush=True)
            if epoch>=6 and stale>=6:break
        selected_results=baseline
        if selected_epoch is not None:
            selected=torch.load(run/'melhor_modelo.pt',map_location='cpu',weights_only=True);model.load_state_dict(selected['model']);selected_results,_,_=evaluate()
            for condition in selected_results:
                for key in ('rank1','tar','far','joint_success'):assert selected_results[condition][key]==selected['validation'][condition][key]
        final={'status':'concluido','selected_epoch':selected_epoch,'epochs_completed':history[-1]['epoch'],'eligible_gain':selected_epoch is not None,'baseline':baseline,'results':selected_results,
            'checkpoint_sha256':None if selected_epoch is None else sha(run/'melhor_modelo.pt'),'frozen_parameters_sha256':frozen_hash,'training_images':len(train),'retained_training_pairs':len(dataset),
            'test_inference':False,'recognizer_replaced':False,'elapsed_seconds':time.monotonic()-started,'retained_system':'original_reference' if selected_epoch is None else 'validation_candidate_pending_test'}
        for name,expected in sources.items():assert sha(ROOT/name)==expected
        write(run/'CONCLUIDO.json',final)
        if selected_epoch is not None:write(run/'CANDIDATO_VALIDACAO.json',{'frozen_utc':datetime.now(timezone.utc).isoformat(),'component':'polar','geometry':'sam31_outer_original_support_and_pupil','checkpoint_sha256':final['checkpoint_sha256'],'epoch':selected_epoch,'threshold':threshold,'validation_results':selected_results,'protocol_sha256':sha(run/'protocolo.json')})
        stage('concluido',selected_epoch=selected_epoch,eligible_gain=final['eligible_gain']);print(json.dumps(final),flush=True)
    except Exception as error:
        stage('falha',error=str(error));(run/'ERRO.txt').write_text(traceback.format_exc(),encoding='utf-8');raise

if __name__=='__main__':main()

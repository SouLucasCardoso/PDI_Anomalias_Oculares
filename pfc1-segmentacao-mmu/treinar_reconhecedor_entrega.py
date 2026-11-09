"""Ajuste controlado do encoder224 com oclusoes nativas e professor limpo.

Somente treino e validacao; todos os resultados do artigo permanecem preservados.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,hashlib,json,os,random,time,traceback
import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.utils.data import Dataset,DataLoader
from torchvision import transforms
from recorte_iris_sam31_alta_res import sha
from rodada_reconhecedor_entrega import result_path,write
from avaliar_candidato_congelado import extract,global_scores,fuse,WEIGHTS
from avaliar_robustez_reconhecimento import load_splits,identity,metrics,perturb
from validar_lateralidade_informada import subset
from reconhecedor_resnet50 import Encoder,SessionBatches,supervised_contrastive
from treinar_identidade_iris import AngularHead
from treinar_segmentacao_ubipr import Sample,MulticlassUNet,decode_mask
from avaliar_dinov3_ubipr import masked_crop

ROOT=Path(__file__).resolve().parent
LEVELS=(1,5,10,20,30,31)
CONDITIONS=(('original',0),('oclusao_superior',10),('oclusao_inferior',10))
ORDER=('rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red')

def crop_from_mask(photo,mask):
    native=np.asarray(Image.fromarray(mask).resize(photo.size,Image.Resampling.NEAREST),bool)
    return np.asarray(masked_crop(photo,native).resize((224,224),Image.Resampling.BILINEAR)),bool(native.any())

def prepare_training(rows,run,device,stage):
    folder=run/'cache_treino';folder.mkdir(exist_ok=True)
    done=folder/'CONCLUIDO.json'
    if done.exists():
        d=json.loads(done.read_text());assert d['rows']==[Path(r.image).name for r in rows]
        return np.load(folder/'recortes.npy',mmap_mode='r'),np.load(folder/'valid.npy')
    assert not (folder/'recortes.npy').exists(),'Cache incompleto: preservar e iniciar outro diretório'
    rng=np.random.default_rng(20261108);plan=rng.choice(LEVELS,(len(rows),2))
    write(folder/'plano.json',{'seed':20261108,'levels':LEVELS,'rows':[Path(r.image).name for r in rows],'upper_lower_levels':plan.tolist()})
    images=np.lib.format.open_memmap(folder/'recortes.npy',mode='w+',dtype=np.uint8,shape=(3,len(rows),224,224,3))
    valid=np.zeros((3,len(rows)),bool)
    model=MulticlassUNet(8).to(device).eval()
    model.load_state_dict(torch.load(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt',map_location='cpu',weights_only=True)['model'])
    for start in range(0,len(rows),16):
        photos=[];indices=[]
        for i,row in enumerate(rows[start:start+16],start):
            photo=Image.open(row.image).convert('RGB');reference=decode_mask(Image.open(row.mask))==1
            variants=[photo,perturb(photo,reference,'oclusao_superior',int(plan[i,0]))[0],perturb(photo,reference,'oclusao_inferior',int(plan[i,1]))[0]]
            for k,variant in enumerate(variants):photos.append(variant);indices.append((k,i))
        x=torch.from_numpy(np.stack([np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for im in photos]).transpose(0,3,1,2).copy()).to(device)
        with torch.inference_mode():masks=model(x).argmax(1).cpu().numpy()==1
        for (k,i),photo,mask in zip(indices,photos,masks):images[k,i],valid[k,i]=crop_from_mask(photo,mask)
        if start%256==0:stage('preparando_treino',prepared=min(start+16,len(rows)),total_images=len(rows));print(f'Native training crops {start}/{len(rows)}',flush=True)
    images.flush();np.save(folder/'valid.npy',valid)
    write(done,{'rows':[Path(r.image).name for r in rows],'shape':list(images.shape),'valid_by_view':valid.sum(1).tolist(),'cache_sha256':sha(folder/'recortes.npy'),'plan_sha256':sha(folder/'plano.json')})
    del model;torch.cuda.empty_cache();return images,valid

class OcclusionCrops(Dataset):
    def __init__(self,images,valid,rows,labels,teacher):
        self.images=images;self.valid=valid;self.rows=rows;self.labels=labels;self.teacher=teacher
        self.positions=np.flatnonzero(valid[0]);self.transform=transforms.Compose([
            transforms.ToTensor(),transforms.RandomRotation(5),transforms.ColorJitter(brightness=.05,contrast=.05),
            transforms.Normalize([.485,.456,.406],[.229,.224,.225])])
    def __len__(self):return len(self.positions)
    def __getitem__(self,index):
        i=int(self.positions[index]);u=random.random();view=0 if u<.5 else 1 if u<.75 else 2
        if not self.valid[view,i]:view=0
        photo=np.array(self.images[view,i],copy=True)
        return self.transform(photo),self.labels[identity(self.rows[i])],torch.from_numpy(self.teacher[i].copy())

def frozen_digest(model):
    trainable={n for n,p in model.named_parameters() if p.requires_grad}
    h=hashlib.sha256()
    for name,value in model.state_dict().items():
        if name not in trainable:h.update(name.encode());h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()

def eligibility(candidate,baseline):
    clean=all(candidate['original'][k]>=baseline['original'][k] for k in ('rank1','tar')) and candidate['original']['far']<=.01
    risk=all(candidate[t]['far']<=baseline[t]['far'] for t in candidate if t!='original')
    gain=np.mean([r['joint_success'] for r in candidate.values()])>np.mean([r['joint_success'] for r in baseline.values()])
    return bool(clean and risk and gain)

def selection_key(results):
    return (float(np.mean([r['joint_success'] for r in results.values()])),float(min(r['joint_success'] for r in results.values())),float(np.mean([r['rank1'] for r in results.values()])))

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--reference-root',type=Path,required=True)
    p.add_argument('--epochs',type=int,default=18);p.add_argument('--resume',action='store_true');a=p.parse_args();run=a.run_dir.resolve();run.mkdir(parents=True,exist_ok=True)
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_file.read_text())
    train=[Sample(**r) for r in manifest['train']];val=load_splits(manifest)['val'];labels={eye:i for i,eye in enumerate(sorted({identity(r) for r in train}))}
    assert not {r.subject for r in train}&{r.subject for r in val}
    assert not {r.subject for r in train}&{r['subject'] for r in manifest['test']}
    checkpoint=ROOT/'outputs/resnet50_nativo224_2026-10-21/melhor_modelo.pt';assert sha(checkpoint)==WEIGHTS['native'][1]
    unet=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';assert sha(unet)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    sources={n:sha(ROOT/n) for n in ('treinar_reconhecedor_entrega.py','avaliar_candidato_congelado.py','avaliar_robustez_reconhecimento.py','reconhecedor_resnet50.py','treinar_identidade_iris.py','treinar_segmentacao_ubipr.py','rodada_reconhecedor_entrega.py','validar_lateralidade_informada.py')}
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Train and validation only; repeatedly used validation, no blind confirmation, no clinical inference',
        'sources_sha256':sources,'manifest_sha256':sha(manifest_file),'initial_checkpoint_sha256':sha(checkpoint),'unet_sha256':sha(unet),
        'architecture':'resnet50_gem3_256','trainable':'Only layer4,projection,366-class angular head. All other parameters and all BatchNorm running statistics frozen.',
        'augmentation':'Native photograph iris-reference-only exact upper/lower occlusion, one independently drawn level1,5,10,20,30,31 per direction per training image; rerun frozen segmentation+geometry on altered image. Sampling50%clean25%upper25%lower; rotation5deg,brightness/contrast5%. No reconstruction or reference mask in extraction.',
        'teacher':'Initial frozen encoder clean automatic training crop; distillation only during training',
        'loss':'Angular CE margin0.3 scale30 +0.2 SupCon temperature0.1 +1.0 mean(1-cosine(student,clean teacher))',
        'optimizer':'AdamW layer4 lr3e-6 projection/head2e-5,wd1e-4,cosine18epochs,clip5; BF16 encoder,FP32 losses;16eyesx4captures,4rounds balanced sessions',
        'selection':'Epoch0 included. Full nine-component fusion; other8 components fixed fresh same-environment validation scores. Historical calibration and threshold fixed. Eligible only cleanRank1/TAR nondecrease, cleanFMR<=1%, occludedFMR each no greater than baseline, mean3conditionjoint strictly improves. Max meanjoint,tie worstjoint,tie meanRank1. Patience5 after epoch4. Absolute all-conditionFMR<=1% reported separately.',
        'counts':{'train_images':len(train),'train_people':len({r.subject for r in train}),'train_eyes':len(labels),'val_queries':sum(r.session==2 for r in val)},
        'levels':LEVELS,'conditions':CONDITIONS,'epochs':a.epochs,'patience':5,'seed':20261108,'deadline_utc':'2026-11-09T02:00:00+00:00',
        'secondary_analysis':'After fixed-threshold model selection only: compare epoch0 and selected with same max-of-three-validation-condition 1%FMR calibration rule; thresholds fixed across conditions; not used to select weights or assert blind performance.',
        'reference_root':str(a.reference_root.resolve()),'versions':{'torch':torch.__version__,'numpy':np.__version__},'automatic_replacement':False}
    if (run/'protocolo.json').exists():
        assert a.resume;old=json.loads((run/'protocolo.json').read_text());assert old['sources_sha256']==sources and old['epochs']==a.epochs
    else:write(run/'protocolo.json',protocol);(run/'source.py').write_bytes(Path(__file__).read_bytes())
    assert (a.reference_root/'CONCLUIDO.json').exists(),'A comparacao de contorno deve terminar antes do treino'
    started=time.monotonic()
    def stage(name,**extra):write(run/'estado.json',{'stage':name,'utc':datetime.now(timezone.utc).isoformat(),'pid':os.getpid(),'elapsed_seconds':time.monotonic()-started,**extra})
    try:
        os.environ['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib');torch.set_num_threads(4);torch.backends.cudnn.benchmark=False
        random.seed(20261108);np.random.seed(20261108);torch.manual_seed(20261108);device=torch.device('cuda');stage('preparando_treino')
        images,valid=prepare_training(train,run,device,stage)
        state=torch.load(checkpoint,map_location='cpu',weights_only=True)
        assert state['configuration']['manifest_sha256']==sha(manifest_file)
        assert state['training_head']['weight'].shape==(len(labels),256)
        teacher_file=run/'teacher.npy'
        if teacher_file.exists():teacher_features=np.load(teacher_file)
        else:
            stage('calculando_professor');teacher=Encoder().to(device).eval();teacher.load_state_dict(state['model'])
            teacher_features=extract(teacher,images[0],device);np.save(teacher_file,teacher_features);del teacher;torch.cuda.empty_cache()
        dataset=OcclusionCrops(images,valid,train,labels,teacher_features)
        targets=np.array([labels[identity(train[i])] for i in dataset.positions]);sessions=np.array([train[i].session for i in dataset.positions])
        sampler=SessionBatches(targets,sessions,seed=20261108);loader=DataLoader(dataset,batch_sampler=sampler,num_workers=0)
        model=Encoder().to(device);model.load_state_dict(state['model']);model.requires_grad_(False)
        model.backbone.layer4.requires_grad_(True);model.projection.requires_grad_(True)
        head=AngularHead(len(labels)).to(device);head.load_state_dict(state['training_head']);del state
        frozen_hash=frozen_digest(model);parameters=list(model.backbone.layer4.parameters())+list(model.projection.parameters())+list(head.parameters())
        optimizer=torch.optim.AdamW([{'params':model.backbone.layer4.parameters(),'lr':3e-6},{'params':list(model.projection.parameters())+list(head.parameters()),'lr':2e-5}],weight_decay=1e-4)
        scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,T_max=a.epochs)
        frozen=json.loads((ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json').read_text());threshold=frozen['frozen_threshold']
        ids=sorted({identity(r) for r in val});conditions={};references={}
        for condition,level in CONDITIONS:
            folder=result_path(a.reference_root,'nearest',condition,level)
            suffix='' if condition=='original' else f'_{condition}_{level}'
            cache=a.reference_root/'nearest'/f'cache_confirmacao_val{suffix}_2026-10-21'
            with np.load(cache/'valid.npz') as z:rv=z['rgb'].copy()
            components=[]
            for name in ORDER:
                with np.load(folder/f'scores_{name}.npz',allow_pickle=False) as z:components.append({k:z[k].copy() for k in ('scores','labels','valid')})
            conditions[condition]=(np.load(cache/'native.npy',mmap_mode='r'),rv,components)
            references[condition]={f.name:sha(f) for f in folder.glob('scores_*.npz')}
        write(run/'REFERENCIAS_VALIDACAO.json',references)
        def evaluate(epoch,save=False):
            model.eval();results={};data={}
            for condition,(x,rv,components) in conditions.items():
                full,qvalid=global_scores(extract(model,x,device),rv,val);scores,y,_=subset(full,val,ids)
                np.testing.assert_array_equal(y,components[0]['labels'])
                replacement={'scores':scores,'labels':y,'valid':qvalid};items=components.copy();items[5]=replacement
                fused,fv=fuse(items,frozen['component_calibration_red_and_clahe']);r,c,accepted=metrics(fused,y,threshold,fv)
                r.update(joint_success=float((c&accepted).mean()),threshold=threshold);results[condition]=r
                data[condition]=dict(scores=fused,labels=y,valid=fv,correct=c,accepted=accepted)
                if save:
                    np.savez_compressed(run/f'scores_native_selected_{condition}.npz',**replacement)
                    np.savez_compressed(run/f'scores_fusion_selected_{condition}.npz',**data[condition])
            return results,data
        history=[];baseline=None;bestkey=None;selected_epoch=0;stale=0;first_epoch=0
        if a.resume and (run/'ultima_epoca.pt').exists():
            resumed=torch.load(run/'ultima_epoca.pt',map_location='cpu',weights_only=True)
            model.load_state_dict(resumed['model']);head.load_state_dict(resumed['training_head']);optimizer.load_state_dict(resumed['optimizer']);scheduler.load_state_dict(resumed['scheduler'])
            history=resumed['history'];baseline=resumed['baseline'];bestkey=tuple(resumed['bestkey']);selected_epoch=resumed['selected_epoch'];stale=resumed['stale'];first_epoch=resumed['epoch']+1
            random.setstate(resumed['python_rng']);torch.set_rng_state(resumed['torch_rng']);torch.cuda.set_rng_state_all(resumed['cuda_rng'])
        deadline=datetime.fromisoformat(protocol['deadline_utc'])
        for epoch in range(first_epoch,a.epochs+1):
            if datetime.now(timezone.utc)>=deadline and epoch>0:break
            losses=[];stage('treinando' if epoch else 'avaliando_epoca_zero',epoch=epoch,max_epochs=a.epochs,selected_epoch=selected_epoch)
            if epoch:
                sampler.epoch=epoch-1;model.train();head.train()
                for m in model.modules():
                    if isinstance(m,nn.modules.batchnorm._BatchNorm):m.eval()
                for batch,(x,y,target) in enumerate(loader):
                    x=x.to(device);y=y.to(device);target=target.to(device);optimizer.zero_grad(set_to_none=True)
                    with torch.autocast('cuda',dtype=torch.bfloat16):features=model(x)
                    features=features.float();ce=nn.functional.cross_entropy(head(features,y),y)
                    con=supervised_contrastive(features,y);distill=(1-(features*target).sum(1)).mean();loss=ce+.2*con+distill
                    if not torch.isfinite(loss):raise ValueError('Perda nao finita')
                    loss.backward();nn.utils.clip_grad_norm_(parameters,5);optimizer.step();losses.append([float(ce.detach()),float(con.detach()),float(distill.detach())])
                    if batch%20==0:stage('treinando',epoch=epoch,max_epochs=a.epochs,batch=batch,batches=len(loader),selected_epoch=selected_epoch)
                scheduler.step()
            stage('validando',epoch=epoch,max_epochs=a.epochs,selected_epoch=selected_epoch)
            results,data=evaluate(epoch)
            if epoch==0:
                baseline=results;bestkey=selection_key(baseline);write(run/'BASELINE.json',baseline)
                for condition,d in data.items():np.savez_compressed(run/f'scores_fusion_baseline_{condition}.npz',**d)
            eligible=epoch>0 and eligibility(results,baseline);key=selection_key(results);chosen=epoch==0 or eligible and key>bestkey
            if chosen:bestkey=key;selected_epoch=epoch;stale=0
            elif epoch:stale+=1
            record={'epoch':epoch,'loss_mean':np.mean(losses,axis=0).tolist() if losses else None,'results':results,'eligible':eligible,'selected_epoch':selected_epoch,'elapsed_seconds':time.monotonic()-started}
            history.append(record);write(run/'historico.json',history)
            if chosen:
                config=dict(protocol);config['architecture']='resnet50_gem3_256'
                temporary=run/'melhor_modelo.pt.part';torch.save({'model':model.state_dict(),'training_head':head.state_dict(),'epoch':epoch,'validation':results,'configuration':config},temporary);temporary.replace(run/'melhor_modelo.pt')
                for condition,d in data.items():np.savez_compressed(run/f'scores_fusion_selected_{condition}.npz',**d)
            assert frozen_digest(model)==frozen_hash,'Parametros ou estatisticas congelados mudaram'
            temporary=run/'ultima_epoca.pt.part'
            torch.save({'model':model.state_dict(),'training_head':head.state_dict(),'optimizer':optimizer.state_dict(),'scheduler':scheduler.state_dict(),
                'epoch':epoch,'history':history,'baseline':baseline,'bestkey':bestkey,'selected_epoch':selected_epoch,'stale':stale,
                'python_rng':random.getstate(),'torch_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all()},temporary);temporary.replace(run/'ultima_epoca.pt')
            lines=['# Ajuste do reconhecedor sob oclusoes','',f'Época concluída: {epoch}/{a.epochs}. Época selecionada: {selected_epoch}.','',
                '| Condição | Rank-1 | TAR | FMR | Correto e aceito |','|---|---:|---:|---:|---:|']
            for condition,r in results.items():lines.append(f"| {condition} | {100*r['rank1']:.2f}% | {100*r['tar']:.2f}% | {100*r['far']:.3f}% | {100*r['joint_success']:.2f}% |")
            lines+=['','Resultados da época atual, seleção feita pelas regras do protocolo. Todas as482consultas são mantidas. Validação reutilizada no desenvolvimento; sem inferência clínica ou de teste.']
            (run/'RELATORIO_ATUAL.md').write_text('\n'.join(lines),encoding='utf-8');print(json.dumps(record),flush=True)
            if epoch>=4 and stale>=5:break
        chosen=torch.load(run/'melhor_modelo.pt',map_location='cpu',weights_only=True);model.load_state_dict(chosen['model']);results,_=evaluate(selected_epoch,True)
        final={'status':'concluido','selected_epoch':selected_epoch,'epochs_completed':history[-1]['epoch'],'baseline':baseline,'results':results,
            'eligible_gain':selected_epoch>0 and eligibility(results,baseline),'absolute_fmr_target_all_conditions':all(r['far']<=.01 for r in results.values()),
            'checkpoint_sha256':sha(run/'melhor_modelo.pt'),'frozen_parameters_sha256':frozen_hash,'teacher_sha256':sha(teacher_file),
            'test_inference':False,'recognizer_replaced':False,'elapsed_seconds':time.monotonic()-started}
        write(run/'CONCLUIDO.json',final);stage('concluido',selected_epoch=selected_epoch,eligible_gain=final['eligible_gain']);print(json.dumps(final),flush=True)
    except Exception as error:
        stage('falha',error=str(error));(run/'ERRO.txt').write_text(traceback.format_exc(),encoding='utf-8');raise

if __name__=='__main__':main()

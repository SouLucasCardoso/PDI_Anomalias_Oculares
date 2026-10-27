"""Ajuste completo dos kernels layer4; prefixo, BN e projecao congelados."""
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone
import argparse,csv,json,hashlib
import numpy as np
import torch
from torch.utils.data import Dataset,DataLoader
from ajuste_bloco_polar import FullTail
from encoder_polar_espacial import tail_vectors
from preparar_encoder_espacial import file_hash,prepare_cache
from treinar_adaptador_polar import CONDITIONS,monitor_scores
from treinar_adaptador_polar_original import eligible_clean,advancement
from perda_identidade_polar import selection_key
from perda_top3_polar import top3_hard_negative_loss
ROOT=Path(__file__).resolve().parent
NAME='ajuste_bloco_polar_treino_2026-10-23'

class FeaturePairs(Dataset):
    def __init__(self,features,mapping,teacher,indices,labels,queries):self.features=features;self.mapping=mapping;self.teacher=teacher;self.indices=indices;self.labels=labels;self.queries=queries
    def __len__(self):return len(self.indices)
    def __getitem__(self,k):
        i=self.indices[k];return torch.from_numpy(np.array(self.features[self.mapping[i]],copy=True)),torch.from_numpy(self.teacher[i].copy()),int(self.labels[k]),bool(self.queries[k])

def main():
    from avaliar_candidato_congelado import WEIGHTS
    from treinar_identidade_iris import IdentityEncoder
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args();out=a.output_root/NAME;source=a.output_root/'adaptador_polar_original_2026-10-23';previous=json.loads((source/'protocolo.json').read_text());encoder_relative=Path('outputs')/WEIGHTS['polar'][0]/'melhor_modelo.pt'
    if a.registrar:
        out.mkdir(parents=True,exist_ok=False)
        protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='OriginalTRAIN only167fit/16reusedmonitor people;encoderalready saw monitor historically. No VAL/test fitting/inference. Same6665fitphotos/480monitorqueries. Not independent generalization.',
            architecture='Start ORIGINALpolar encoder, NO rejectedweights. TrainALL5Convkernels inlayer4 includingdownsample1x1;8388608weights. Prefix/projection/ALLBatchNorm affine+stats frozen. SAMEglobalmean, no attention/newgeometry. Epoch0 exactlyoriginal. Not lowrank.',
            cache='REUSE original spatialpilot FP32layer3 cache12160maps bySHA256; no copy/newprefixinference. S1clean inALLviews. NativeS2gray128upper/lower10 with automatic U-Net/originalpolar. ReferenceONLYdefines intervention,notattentionweights.',
            training='Seed63,AdamW1e-5 wd1e-4,B16photos/3views,max8epochs,patience3after4;FP32. Teacher1-cosine weights4/1/1 plus.1top3hardnegative marginloss(margin.1,temp.1),plus1e-4sum mean-square displacementfromoriginalconvkernels. Noabsolutepenalty(previouspilotdidnotimprovejointoutcome),nohyperparametersearch.',
            enrollment_loss='OnlyFITcleanS1 validteacher photos,4955/334eyes. Refreshwithcurrenttail atSTARTofEACHepoch,freeze/no-gradientwithin epoch. top3mean per eye andhardestOTHERsame-sideeye,lossONLYS2FITqueries. S1fit photos participate in cleanteacher loss only. No monitor gallery/labels in gradients.',
            monitor='ALL960photos/480S2queries retained,onequeryphoto,suppliedside,16eyes. Gallery explicitlyCLEAN inALLconditions. ONEcleanFMR<=1%threshold per epoch unchangedforbothocclusions. No cleanquerycounterpartatinference. NewFP32zero-correctionbaseline comparedwithpreviousbaselinecounts.',
            selection='Epoch0included;eligiblecleanRank1/TAR>=epoch0,FMR<=1%. Prioritizefullmonitor gate,thenworstoccludedTAR,thenworstRank1,negativeworstFMR,meanoccludedteachercosine. Gateepoch>0,eligibleclean,BOTHocclusionsRank1/TARstrictgains,FMR<=1%. NoautomaticVAL/test/promotion/minimum.',
            fit_people=previous['fit_people'],monitor_people=previous['monitor_people'],rank=0,encoder_relative_path=encoder_relative.as_posix(),encoder_sha256=file_hash(ROOT/encoder_relative),unet_sha256=file_hash(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'),manifest_sha256=file_hash(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'),source_cache=str(source/'cache_features.npz'),source_cache_sha256=file_hash(source/'cache_features.npz'),source_rows_sha256=file_hash(source/'rows.json'),clean_polar_sha256=file_hash(ROOT/'data/cache_encoder_polar_2026-10-20/train_polar.npy'),script_sha256=file_hash(Path(__file__)),dependencies_sha256={n:file_hash(ROOT/n) for n in ['ajuste_bloco_polar.py','encoder_polar_espacial.py','preparar_encoder_espacial.py','perda_top3_polar.py','perda_identidade_polar.py','treinar_adaptador_polar.py','treinar_adaptador_polar_original.py']})
        cache_folder=a.output_root/'encoder_polar_espacial_2026-10-23'
        metadata=json.loads((cache_folder/'CACHE_CONCLUIDO.json').read_text())
        protocol.update(reused_cache_sha256=metadata['sha256'],reused_indices_sha256=metadata['indices_sha256'])
        assert protocol['encoder_sha256']==WEIGHTS['polar'][1]
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Ajuste espacial registrado antes do cache e treino.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert not (out/'CONCLUIDO.json').exists() and file_hash(Path(__file__))==protocol['script_sha256']
    for n,h in protocol['dependencies_sha256'].items():assert file_hash(ROOT/n)==h
    for file,key in [(ROOT/encoder_relative,'encoder_sha256'),(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt','unet_sha256'),(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json','manifest_sha256'),(source/'cache_features.npz','source_cache_sha256'),(source/'rows.json','source_rows_sha256'),(ROOT/'data/cache_encoder_polar_2026-10-20/train_polar.npy','clean_polar_sha256')]:assert file_hash(file)==protocol[key]
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;torch.manual_seed(63);device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    cache_folder=a.output_root/'encoder_polar_espacial_2026-10-23'
    cache_done=json.loads((cache_folder/'CACHE_CONCLUIDO.json').read_text());assert file_hash(cache_folder/'cache_layer3.npy')==cache_done['sha256'] and file_hash(cache_folder/'cache_indices.npz')==cache_done['indices_sha256']
    assert cache_done['sha256']==protocol['reused_cache_sha256'] and cache_done['indices_sha256']==protocol['reused_indices_sha256']
    features=np.load(cache_folder/'cache_layer3.npy',mmap_mode='r')
    with np.load(cache_folder/'cache_indices.npz') as z:mapping=z['mapping'];valid=z['valid']
    with np.load(source/'cache_features.npz') as z:teacher=z['teacher'];teacher_valid=z['teacher_valid'];fi=z['fit_indices'];mi=z['monitor_indices']
    rows=[SimpleNamespace(**r) for r in json.loads((source/'rows.json').read_text())];mr=[rows[i] for i in mi];fit=set(protocol['fit_people']);monitor=set(protocol['monitor_people']);assert not fit&monitor and {rows[i].subject for i in fi}<=fit and {rows[i].subject for i in mi}==monitor
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());assert not (fit|monitor)&{r['subject'] for r in manifest['val']+manifest['test']}
    eyes=sorted({(rows[i].subject,rows[i].side) for i in fi});eye_index={eye:j for j,eye in enumerate(eyes)};groups=[[i for i,r in enumerate(rows) if (r.subject,r.side)==eye and r.session==1 and teacher_valid[i]] for eye in eyes];assert all(groups) and len(eyes)==334
    gallery=np.array([i for g in groups for i in g]);assert all(rows[i].subject in fit for i in gallery) and not set(gallery)&set(mi)
    padded=np.full((len(eyes),max(map(len,groups))),-1,np.int64);positions=np.zeros_like(padded);local={i:j for j,i in enumerate(gallery)}
    for j,g in enumerate(groups):
        padded[j,:len(g)]=g;positions[j,:len(g)]=[local[i] for i in g]
    labels=np.array([eye_index[(rows[i].subject,rows[i].side)] for i in fi]);query_flags=np.array([rows[i].session==2 for i in fi]);sides=np.array([0 if side=='L' else 1 for _,side in eyes]);present=padded>=0
    np.savez_compressed(out/'cadastros_ajuste.npz',padded_indices=padded,eye_sides=sides,fit_indices=fi,fit_labels=labels,fit_query_flags=query_flags,gallery_indices=gallery,monitor_indices=mi)
    (out/'rows.json').write_bytes((source/'rows.json').read_bytes())
    encoder=IdentityEncoder();encoder.load_state_dict(torch.load(ROOT/encoder_relative,map_location='cpu',weights_only=True)['model']);torch.manual_seed(63);model=FullTail(encoder,protocol['rank']).to(device);del encoder
    frozen=model.frozen_digest();parameters=[p for p in model.parameters() if p.requires_grad];trainable=sum(p.numel() for p in parameters);assert trainable==8388608
    optimizer=torch.optim.AdamW(parameters,lr=1e-5,weight_decay=1e-4);loader=DataLoader(FeaturePairs(features,mapping,teacher,fi,labels,query_flags),batch_size=16,shuffle=True,num_workers=0,pin_memory=device.type=='cuda');gallery_present=torch.from_numpy(present).to(device);eye_sides=torch.from_numpy(sides).to(device)
    history=[];baseline=None;best=None;stale=0;best_epoch=0
    for epoch in range(9):
        model.eval();gallery_vectors=tail_vectors(model,features,mapping[gallery,0],device);gallery_hash=hashlib.sha256(gallery_vectors.tobytes()).hexdigest();gallery_features=torch.from_numpy(gallery_vectors[positions]).to(device);losses=[];model.train()
        if epoch:
            for x,t,eye,query in loader:
                x=x.to(device,non_blocking=True);t=t.to(device,non_blocking=True);optimizer.zero_grad();pred=model(x.flatten(0,1)).reshape(len(x),3,256)
                alignment=((1-(pred*t[:,None]).sum(-1))*pred.new_tensor([4.,1.,1.])).sum(1).mean()/6;metric=top3_hard_negative_loss(pred,eye.to(device),query.to(device),gallery_features,gallery_present,eye_sides);anchor=model.anchor_loss();loss=alignment+.1*metric+1e-4*anchor;assert torch.isfinite(loss)
                loss.backward();torch.nn.utils.clip_grad_norm_(parameters,5);optimizer.step();losses.append(float(loss.detach()))
        model.eval();vectors={tag:tail_vectors(model,features,mapping[mi,j],device) for j,(tag,_,_) in enumerate(CONDITIONS)};availability={tag:valid[mi,j] for j,(tag,_,_) in enumerate(CONDITIONS)};measured,scores=monitor_scores(vectors,availability,mr);cosines={}
        for tag in vectors:
            paired=availability[tag]&teacher_valid[mi];cosines[tag]=float(np.sum(vectors[tag][paired].astype(np.float64)*teacher[mi][paired].astype(np.float64),1).mean())
        if baseline is None:
            baseline=measured;old=json.loads((source/'CONCLUIDO.json').read_text())['baseline_monitor']
            for tag,s in scores.items():
                for k in ['rank1','tar','far','queries','extraction_failures']:assert measured[tag][k]==old[tag][k]
                np.savez_compressed(out/f'scores_baseline_{tag}.npz',**s)
        eligible=eligible_clean(measured,baseline);key=selection_key(measured,cosines,baseline,epoch);record=dict(epoch=epoch,gallery_sha256=gallery_hash,train_loss=float(np.mean(losses)) if losses else None,eligible=bool(eligible))
        for tag in measured:
            for k in ['rank1','tar','far']:record[tag+'_'+k]=measured[tag][k]
            record[tag+'_teacher_cosine']=cosines[tag]
        history.append(record);state=dict(adapters=model.adapters(),rank=protocol['rank'],epoch=epoch,monitor=measured,cosines=cosines,eligible=bool(eligible),configuration=protocol,frozen_sha256=frozen)
        if epoch==0 or eligible and (best is None or key>best):
            if eligible:best=key
            best_epoch=epoch;stale=0;torch.save(state,out/'melhor_modelo.pt')
            for tag,s in scores.items():np.savez_compressed(out/f'scores_selected_{tag}.npz',**s)
        elif epoch:stale+=1
        torch.save(state,out/'ultima_epoca.pt')
        for tag,s in scores.items():np.savez_compressed(out/f'scores_last_{tag}.npz',**s)
        with (out/'historico.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(record));w.writeheader();w.writerows(history)
        print(json.dumps(record),flush=True)
        if epoch>=4 and stale>=3:break
    assert model.frozen_digest()==frozen;chosen=torch.load(out/'melhor_modelo.pt',map_location='cpu',weights_only=True);gate=advancement(chosen['monitor'],baseline,best_epoch)
    final=dict(status='full_layer4_finetuning_completed',selected_epoch=best_epoch,epochs_trained=epoch,baseline_monitor=baseline,selected_monitor=chosen['monitor'],last_monitor=measured,selected_cosines=chosen['cosines'],recognition_validation_gate_passed=bool(gate),trainable_parameters=trainable,frozen_parameters_and_buffers_unchanged=True,frozen_sha256=frozen,checkpoint_sha256=file_hash(out/'melhor_modelo.pt'),last_checkpoint_sha256=file_hash(out/'ultima_epoca.pt'),fit_photos=len(fi),fit_people=len(fit),monitor_queries=480,monitor_people=len(monitor),cache=cache_done,validation_identity_inference=False,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)
if __name__=='__main__':main()

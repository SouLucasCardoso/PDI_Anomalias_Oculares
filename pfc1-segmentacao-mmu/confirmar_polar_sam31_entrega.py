"""Grade completa do candidato polar adaptado, somente se aprovado na validacao."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,time
import numpy as np
import torch
from PIL import Image
from geometria_polar_sam31 import Sam31OuterGeometry
from recorte_iris_sam31_alta_res import sha
from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
from treinar_identidade_iris import IdentityEncoder
from avaliar_dinov3_ubipr import masked_crop
from avaliar_candidato_congelado import extract,global_scores,fuse
from avaliar_robustez_reconhecimento import load_splits,identity,perturb,metrics
from validar_lateralidade_informada import subset
from confirmar_reconhecedor_entrega import SCHEDULE,load_components,measurements,report
from rodada_reconhecedor_entrega import write
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--training-run',type=Path,required=True);p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args();run=a.run_dir.resolve();run.mkdir(parents=True,exist_ok=False)
    training=json.loads((a.training_run/'CONCLUIDO.json').read_text());assert training['eligible_gain'] and training['selected_epoch'] is not None
    checkpoint=a.training_run/'melhor_modelo.pt';assert sha(checkpoint)==training['checkpoint_sha256']
    validation_file=a.training_run/'CANDIDATO_VALIDACAO.json';candidate=json.loads(validation_file.read_text());write(run/'CANDIDATO_CONGELADO.json',candidate)
    frozen_file=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json';frozen=json.loads(frozen_file.read_text());old_root=ROOT/'outputs/ensaio_oclusoes_2026-11-08'
    old_protocol=json.loads((old_root/'protocolo.json').read_text())
    for name,expected in old_protocol['source_sha256'].items():assert sha(ROOT/name)==expected
    assert str(torch.__version__)==old_protocol['versions']['torch']
    source_names=('confirmar_polar_sam31_entrega.py','geometria_polar_sam31.py','recorte_iris_sam31_alta_res.py','avaliar_candidato_congelado.py','avaliar_robustez_reconhecimento.py')
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Exploratory repeated-test comparison after validation-only selection; no independent confirmation or test-based adjustment',
        'candidate_sha256':sha(run/'CANDIDATO_CONGELADO.json'),'checkpoint_sha256':sha(checkpoint),'training_protocol_sha256':sha(a.training_run/'protocolo.json'),
        'source_file':Path(__file__).name,'source_sha256':sha(__file__),'sources_sha256':{n:sha(ROOT/n) for n in source_names},
        'frozen_calibration_sha256':sha(frozen_file),'threshold':frozen['frozen_threshold'],'schedule':SCHEDULE,
        'changes':'Only polar global descriptor gets adapted encoder and SAM3.1outergeometry; original U-Net support and pupil unchanged. Other8components cached from same-environment baseline.',
        'controls':'Reproduce baseline9fusion/decisions exactly. Recompute original-nearest support and assert128RGBcontrol byte-equal for all images. Enrollment SAMbands reused unchanged across conditions; changed queries inferred only from changed photo.',
        'comparison_gate':'CleanRank1/TAR no lower,cleanFMR<=1%;mean13joint higher,each13FMR no higher. No automatic replacement.',
        'deadline_utc':'2026-11-09T02:10:00+00:00','versions':{'torch':str(torch.__version__),'numpy':np.__version__}}
    write(run/'protocolo.json',protocol);(run/'source.py').write_bytes(Path(__file__).read_bytes());os.environ['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib');torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda')
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());rows=load_splits(manifest)['test'];ids=sorted({identity(r) for r in rows});subjects=np.array([r.subject for r in rows if r.session==2]);assert len(subjects)==486
    people=np.unique(subjects);draws=np.random.default_rng(20261108).integers(0,len(people),(5000,len(people)))
    sam=Sam31OuterGeometry();write(run/'SAM_ESTRITO.json',sam.audit);unet_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    assert sha(unet_file)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    unet=MulticlassUNet(8).to(device).eval();unet.load_state_dict(torch.load(unet_file,map_location='cpu',weights_only=True)['model'])
    saved=torch.load(checkpoint,map_location='cpu',weights_only=True);model=IdentityEncoder().to(device).eval();model.load_state_dict(saved['model']);del saved
    threshold=frozen['frozen_threshold'];records=[];original_bands=None;original_valid=None;started=time.monotonic();report(run,records)
    for condition,level in SCHEDULE:
        if datetime.now(timezone.utc)>=datetime.fromisoformat(protocol['deadline_utc']):write(run/'estado.json',{'stage':'limite_horario','completed':len(records),'total':13});return
        suffix='' if condition=='original' else f'_{condition}_{level}';folder=run/f'{condition}_{level}';folder.mkdir()
        old=old_root/'inferencia'/f'confirmacao_congelada_test{suffix}_2026-10-21';components=load_components(old);baseline_scores,bvalid=fuse(components,frozen['component_calibration_red_and_clahe']);y=components[0]['labels']
        with np.load(old/'scores_finais.npz',allow_pickle=False) as gold:
            np.testing.assert_allclose(baseline_scores,gold['scores'],atol=1e-10,rtol=0);np.testing.assert_array_equal(bvalid,gold['valid']);np.testing.assert_array_equal(y,gold['labels'])
            _,bc,ba=metrics(baseline_scores,y,threshold,bvalid);np.testing.assert_array_equal(bc,gold['correct']);np.testing.assert_array_equal(ba,gold['accepted'])
        control=np.load(old_root/f'cache_confirmacao_test{suffix}_2026-10-21'/'rgb.npy',mmap_mode='r')
        bands=np.lib.format.open_memmap(folder/'polar.npy',mode='w+',dtype=np.uint8,shape=(len(rows),64,512,3));valid=np.zeros(len(rows),bool);details=[]
        for start in range(0,len(rows),32):
            photos=[]
            for row in rows[start:start+32]:
                photo=Image.open(row.image).convert('RGB')
                if condition!='original' and row.session==2:photo=perturb(photo,decode_mask(Image.open(row.mask))==1,condition,level)[0]
                photos.append(photo)
            x=torch.from_numpy(np.stack([np.asarray(photo.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for photo in photos]).transpose(0,3,1,2).copy()).to(device)
            with torch.inference_mode():masks=unet(x).argmax(1).cpu().numpy()==1
            for offset,(photo,mask) in enumerate(zip(photos,masks)):
                i=start+offset;support=np.asarray(Image.fromarray(mask).resize(photo.size,Image.Resampling.NEAREST),bool)
                rgb_control=np.asarray(masked_crop(photo,support).resize((128,128),Image.Resampling.BILINEAR));np.testing.assert_array_equal(rgb_control,control[i])
                if condition!='original' and rows[i].session==1:
                    bands[i]=original_bands[i];valid[i]=original_valid[i];continue
                try:bands[i],_,detail=sam.polar(photo,support);valid[i]=True
                except ValueError as error:bands[i]=127;detail={'status':'invalid_original_support','reason':str(error)}
                details.append({'image':Path(rows[i].image).name,'detail':detail})
            write(run/'estado.json',{'stage':'preparando_geometria_teste','condition':condition,'level':level,'completed':len(records),'total':13,'prepared_rows':min(start+32,len(rows)),'rows_per_condition':len(rows),'pid':os.getpid()})
        bands.flush();np.save(folder/'valid.npy',valid);write(folder/'geometrias.json',details)
        if condition=='original':original_bands=bands;original_valid=valid.copy()
        full,qvalid=global_scores(extract(model,bands,device),valid,rows);scores,labels,_=subset(full,rows,ids);np.testing.assert_array_equal(labels,y);replacement={'scores':scores,'labels':y,'valid':qvalid};components[1]=replacement;np.savez_compressed(folder/'scores_polar_candidato.npz',**replacement)
        scores,fvalid=fuse(components,frozen['component_calibration_red_and_clahe']);b,bc,ba=measurements(baseline_scores,y,bvalid,threshold,subjects);c,cc,ca=measurements(scores,y,fvalid,threshold,subjects)
        np.savez_compressed(folder/'scores_candidato.npz',scores=scores,labels=y,valid=fvalid,correct=cc,accepted=ca)
        delta=np.column_stack((cc.astype(float)-bc,ca.astype(float)-ba,(cc&ca).astype(float)-(bc&ba)));totals=np.array([delta[subjects==person].sum(0) for person in people]);denom=np.array([(subjects==person).sum() for person in people]);ci=np.quantile(100*totals[draws].sum(1)/denom[draws].sum(1)[:,None],[.025,.975],axis=0)
        record={'condition':condition,'level':level,'baseline':b,'candidate':c,'paired_gain_pp':(100*delta.mean(0)).tolist(),'descriptive_interval95_pp':ci.tolist(),
            'audit':{'baseline_fusion_and_decisions_reproduced':True,'rgb_support_controls_byte_equal':True,'old_components_sha256':{f.name:sha(f) for f in old.glob('scores_*.npz')}}}
        records.append(record);write(folder/'resultado.json',record);report(run,records);print(json.dumps(record),flush=True)
    sam.close();clean=records[0];passed=all(clean['candidate']['metrics'][key]>=clean['baseline']['metrics'][key] for key in ('rank1','tar')) and clean['candidate']['metrics']['far']<=.01
    passed=passed and np.mean([r['candidate']['metrics']['joint_success'] for r in records])>np.mean([r['baseline']['metrics']['joint_success'] for r in records]) and all(r['candidate']['metrics']['far']<=r['baseline']['metrics']['far'] for r in records)
    assert sha(checkpoint)==protocol['checkpoint_sha256'];assert sha(run/'CANDIDATO_CONGELADO.json')==protocol['candidate_sha256']
    for name,expected in protocol['sources_sha256'].items():assert sha(ROOT/name)==expected
    final={'status':'concluido','selected':'sam31_polar_adapted','selected_epoch':training['selected_epoch'],'comparison_gate_passed':bool(passed),'records':records,'recognizer_replaced':False,'independent_confirmation':False,'universal_minimum':None,'elapsed_seconds':time.monotonic()-started}
    write(run/'CONCLUIDO.json',final);report(run,records,True);write(run/'estado.json',{'stage':'concluido','completed':13,'total':13,'comparison_gate_passed':bool(passed)})

if __name__=='__main__':main()

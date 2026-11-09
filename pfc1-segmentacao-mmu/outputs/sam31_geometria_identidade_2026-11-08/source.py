"""Avaliacao integrada val-only da geometria externaSAM3.1, com suporte antigo."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,os,time
import cv2,numpy as np,torch
from PIL import Image
from geometria_polar_sam31 import Sam31OuterGeometry
from recorte_iris_sam31_alta_res import sha
from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
from avaliar_robustez_reconhecimento import load_splits,identity,perturb,metrics
from avaliar_candidato_congelado import extract,global_scores,spatial,fuse,WEIGHTS
from validar_lateralidade_informada import subset
from treinar_identidade_iris import IdentityEncoder
from avaliar_dinov3_ubipr import masked_crop
from treinar_reconhecedor_entrega import ORDER,CONDITIONS,eligibility
from rodada_reconhecedor_entrega import result_path,write
import reconhecedor_transformer_polar
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--reference-root',type=Path,required=True);a=p.parse_args();out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_file.read_text());rows=load_splits(manifest)['val'];ids=sorted({identity(r) for r in rows});qi=[i for i,r in enumerate(rows) if r.session==2];gi=[i for i,r in enumerate(rows) if r.session==1]
    sources={name:sha(ROOT/name) for name in ('avaliar_geometria_sam31_identidade.py','geometria_polar_sam31.py','recorte_iris_sam31_alta_res.py','textura_polar.py','preparar_polar_vermelho.py','avaliar_candidato_congelado.py','avaliar_robustez_reconhecimento.py')}
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Validation development only, after repeated prior development; no test or clinical inference',
        'hypothesis':'SAM3.1 external contour may stabilize outer polar sampling under occlusion. Native RGB U-Net support and original inner geometry unchanged; no holefilling, inferred texture or oracle clean counterpart.',
        'sources_sha256':sources,'manifest_sha256':sha(manifest_file),'conditions':CONDITIONS,'input_images':len(rows),'queries':len(qi),'gallery_images':len(gi),
        'selection':'One fixed method; original ninth-component fusion weights,calibration,threshold unchanged. Eligible only cleanRank1/TAR no lower,cleanFMR<=1%,occludedFMR each no greater,meanjoint3 higher. All failures retained. Absolute all-conditionFMR<=1% separately.',
        'fallback':'Any inconsistent SAM ellipse uses original geometry; invalid original texture remains failure. No quality-based exclusion.',
        'official_versions_verified_2026_11_08':{'code':'f1647e8d0c1d280991f4d1b7d974c2704537fe66','checkpoint':'daa63191845a41281374e725f4c9e51c7a824460','github':'https://api.github.com/repos/facebookresearch/sam3/commits/main','huggingface':'https://huggingface.co/api/models/facebook/sam3.1'},
        'versions':{'torch':str(torch.__version__),'numpy':np.__version__}}
    write(out/'protocolo.json',protocol);(out/'source.py').write_bytes(Path(__file__).read_bytes());os.environ['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib')
    (out/'RELATORIO_ATUAL.md').write_text('# Geometria externa SAM3.1 — em execução\n\nPreparando faixas polares com o suporte visível anterior. Consulte estado.json para etapa e progresso. Ainda não há ganho de identidade medido nesta rodada.\n',encoding='utf-8')
    torch.set_num_threads(4);cv2.setNumThreads(1);torch.backends.cudnn.benchmark=False;device=torch.device('cuda');start=time.monotonic()
    def stage(name,**extra):write(out/'estado.json',{'stage':name,'utc':datetime.now(timezone.utc).isoformat(),'pid':os.getpid(),'elapsed_seconds':time.monotonic()-start,**extra})
    stage('carregando_sam31');sam=Sam31OuterGeometry();write(out/'SAM_ESTRITO.json',sam.audit)
    unet=MulticlassUNet(8).to(device).eval();unet_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';assert sha(unet_file)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    unet.load_state_dict(torch.load(unet_file,map_location='cpu',weights_only=True)['model']);prepared={};details=[];completed=0;total=len(rows)+2*len(qi)
    for condition,level in CONDITIONS:
        folder=out/condition;folder.mkdir();arrays={key:np.lib.format.open_memmap(folder/(key+'.npy'),mode='w+',dtype=np.uint8,shape=(len(rows),64,512,3)) for key in ('polar','red')};valid=np.zeros(len(rows),bool)
        suffix='' if condition=='original' else f'_{condition}_{level}'
        control_cache=a.reference_root/'nearest'/f'cache_confirmacao_val{suffix}_2026-10-21'
        control_rgb=np.load(control_cache/'rgb.npy',mmap_mode='r')
        indices=list(range(len(rows))) if condition=='original' else qi
        if condition!='original':
            original,pvalid=prepared['original']
            for key in arrays:arrays[key][gi]=original[key][gi]
            valid[gi]=pvalid[gi]
        for begin in range(0,len(indices),32):
            positions=indices[begin:begin+32];photos=[]
            for i in positions:
                row=rows[i];photo=Image.open(row.image).convert('RGB')
                if condition!='original':photo=perturb(photo,decode_mask(Image.open(row.mask))==1,condition,level)[0]
                photos.append(photo)
            x=torch.from_numpy(np.stack([np.asarray(photo.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for photo in photos]).transpose(0,3,1,2).copy()).to(device)
            with torch.inference_mode():masks=unet(x).argmax(1).cpu().numpy()==1
            for i,photo,mask in zip(positions,photos,masks):
                support=np.asarray(Image.fromarray(mask).resize(photo.size,Image.Resampling.NEAREST),bool)
                # Confirma que mudar o limbo nao mudou secretamente o suporte RGB.
                control=np.asarray(masked_crop(photo,support).resize((128,128),Image.Resampling.BILINEAR))
                np.testing.assert_array_equal(control,control_rgb[i],err_msg=f'Controle de suporte divergiu:{condition}/{i}')
                try:arrays['polar'][i],arrays['red'][i],detail=sam.polar(photo,support);valid[i]=True
                except ValueError as error:arrays['polar'][i]=127;arrays['red'][i]=127;detail={'status':'invalid_original_support','reason':str(error)}
                details.append({'image':Path(rows[i].image).name,'condition':condition,'detail':detail});completed+=1
            stage('preparando_geometria',condition=condition,completed=completed,total=total)
            if begin%160==0:print(f'SAM geometry {completed}/{total}',flush=True)
        for value in arrays.values():value.flush()
        np.save(folder/'valid.npy',valid);prepared[condition]=(arrays,valid);write(out/'geometrias.json',details)
    sam.close();del unet;torch.cuda.empty_cache()
    frozen=json.loads((ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json').read_text());threshold=frozen['frozen_threshold'];allcomponents={};baseline={}
    for condition,level in CONDITIONS:
        folder=result_path(a.reference_root,'nearest',condition,level);components=[]
        for name in ORDER:
            with np.load(folder/f'scores_{name}.npz',allow_pickle=False) as z:components.append({k:z[k].copy() for k in ('scores','valid','labels')})
        scores,valid=fuse(components,frozen['component_calibration_red_and_clahe']);m,c,accepted=metrics(scores,components[0]['labels'],threshold,valid);m.update(joint_success=float((c&accepted).mean()),threshold=threshold);baseline[condition]=m;allcomponents[condition]=components
    def save_component(name,condition,full,qvalid):
        scores,labels,_=subset(full,rows,ids);np.testing.assert_array_equal(labels,allcomponents[condition][0]['labels']);item={'scores':scores,'valid':qvalid,'labels':labels};allcomponents[condition][ORDER.index(name)]=item;np.savez_compressed(out/condition/f'scores_{name}.npz',**item)
    for name in ('polar','transformer'):
        file=ROOT/'outputs'/WEIGHTS[name][0]/'melhor_modelo.pt';assert sha(file)==WEIGHTS[name][1]
        if name=='polar':model=IdentityEncoder().to(device).eval();model.load_state_dict(torch.load(file,map_location='cpu',weights_only=True)['model'])
        else:model,_=reconhecedor_transformer_polar.load(file,device)
        for condition,(images,valid) in prepared.items():
            stage('extraindo_identidade',descriptor=name,condition=condition);save_component(name,condition,*global_scores(extract(model,images['polar'],device),valid,rows))
            if name=='polar':save_component('spatial',condition,*spatial(model,images['polar'],valid,rows,device))
        del model;torch.cuda.empty_cache()
    arc_base=ROOT/'data/modelos/cvrl_arciris';weights=next(arc_base.rglob('ResNet100_154000.pt'));assert sha(weights)=='466014be7723eb0b1a741dcff5a0c8ae51d1918818a6b021952f9c4ccd443f8f'
    assert sha(arc_base/'modules/network.py')=='de7f0cb796ebf4be02818c704d7e3afa0047dc09719b131b37cb8c26c42dd327'
    spec=importlib.util.spec_from_file_location('arciris_sam_geometry',arc_base/'modules/network.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);model=module.iresnet100();model.load_state_dict(torch.load(weights,map_location='cpu',weights_only=True));model.to(device).eval()
    for condition,(images,valid) in prepared.items():
        for name,key in (('arc_clahe','polar'),('arc_red','red')):
            stage('extraindo_identidade',descriptor=name,condition=condition);save_component(name,condition,*global_scores(extract(model,images[key],device,8,True),valid,rows,True))
    del model;torch.cuda.empty_cache();results={}
    for condition,components in allcomponents.items():
        scores,valid=fuse(components,frozen['component_calibration_red_and_clahe']);labels=components[0]['labels'];m,c,accepted=metrics(scores,labels,threshold,valid);m.update(joint_success=float((c&accepted).mean()),threshold=threshold);results[condition]=m
        np.savez_compressed(out/condition/'scores_fusion.npz',scores=scores,labels=labels,valid=valid,correct=c,accepted=accepted)
    final={'status':'concluido','baseline':baseline,'results':results,'eligible_gain':eligibility(results,baseline),'absolute_fmr_target_all_conditions':all(r['far']<=.01 for r in results.values()),
        'original_mask_and_inner_geometry_preserved':True,'sam_geometry_used':sum(r['detail']['status']=='sam_outer_geometry' for r in details),'original_geometry_fallbacks':sum(r['detail']['status']=='original_geometry_fallback' for r in details),
        'invalid_original_support':sum(r['detail']['status']=='invalid_original_support' for r in details),'test_inference':False,'recognizer_replaced':False,'elapsed_seconds':time.monotonic()-start}
    for name,expected in sources.items():assert sha(ROOT/name)==expected
    write(out/'CONCLUIDO.json',final);stage('concluido',eligible_gain=final['eligible_gain'])
    lines=['# Geometria externa SAM3.1 — validação de identidade','',f"Candidato elegível: {final['eligible_gain']}. Suporte U-Net e pupila preservados; altera apenas a amostragem externa polar. Todas as482consultas permanecem no denominador.",'',
        '| Versão | Condição | Rank-1 | TAR | FMR | Correto e aceito |','|---|---|---:|---:|---:|---:|']
    for name,r in (('baseline',baseline),('sam31_outer_geometry',results)):
        for condition,m in r.items():lines.append(f"| {name} | {condition} | {100*m['rank1']:.2f}% | {100*m['tar']:.2f}% | {100*m['far']:.3f}% | {100*m['joint_success']:.2f}% |")
    lines+=['','Validação reutilizada no desenvolvimento. Sem inferência de teste, reconstrução de textura, referência clínica ou substituição automática.']
    (out/'RELATORIO_ATUAL.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print(json.dumps(final),flush=True)

if __name__=='__main__':main()

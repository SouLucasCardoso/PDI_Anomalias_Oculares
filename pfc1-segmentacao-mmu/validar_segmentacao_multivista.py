"""Piloto de estabilização da segmentação por três vistas da mesma foto.

Somente validação de desenvolvimento. Não substitui o candidato congelado.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import importlib.util
import json
import numpy as np
import torch
from torch import nn

ROOT=Path(__file__).resolve().parent
ORDER=['rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red']
CONDITIONS=[('clean','original',0),('upper10','oclusao_superior',10),('lower10','oclusao_inferior',10)]

def contrast_tensor(x):
    from reconhecedor_convnext import contrast
    pixels=np.rint(x.detach().cpu().numpy().transpose(0,2,3,1)*255).clip(0,255).astype(np.uint8)
    adjusted=np.stack([contrast(p) for p in pixels])
    return torch.from_numpy(adjusted.transpose(0,3,1,2).copy()).to(x.device,dtype=x.dtype)/255

class SegmentTTA(nn.Module):
    def __init__(self,model):
        super().__init__();self.model=model
    def load_state_dict(self,state_dict,strict=True,assign=False):
        return self.model.load_state_dict(state_dict,strict=strict,assign=assign)
    def forward(self,x):
        p=self.model(x).softmax(1)
        p=p+self.model(x.flip(-1)).softmax(1).flip(-1)
        p=p+self.model(contrast_tensor(x)).softmax(1)
        return (p/3).clamp_min(1e-12).log()

def prepare_tta(rows,device,folder,condition,level):
    import treinar_segmentacao_ubipr as segmentation
    from avaliar_candidato_congelado import prepare
    factory=segmentation.MulticlassUNet
    try:
        segmentation.MulticlassUNet=lambda base:SegmentTTA(factory(base))
        return prepare(rows,device,folder,condition,level)
    finally:
        segmentation.MulticlassUNet=factory

def components(images,rv,pv,rows,device,folder):
    from avaliar_candidato_congelado import WEIGHTS,digest,extract,global_scores,spatial
    from avaliar_robustez_reconhecimento import identity
    from validar_lateralidade_informada import subset
    from treinar_identidade_iris import IdentityEncoder
    import reconhecedor_resnet50,reconhecedor_convnext,reconhecedor_transformer_polar
    ids=sorted({identity(r) for r in rows});result={}
    def save(name,full):
        values,valid=full;scores,labels,_=subset(values,rows,ids)
        result[name]=dict(scores=scores,labels=labels,valid=valid)
        np.savez_compressed(folder/f'scores_{name}.npz',**result[name])
        print(f'{folder.name}: {name} concluido',flush=True)
    for name in ['rgb','polar','r50','convnext','native','transformer']:
        weight=ROOT/'outputs'/WEIGHTS[name][0]/'melhor_modelo.pt';assert digest(weight)==WEIGHTS[name][1]
        if name in ['rgb','polar']:
            model=IdentityEncoder().to(device).eval();model.load_state_dict(torch.load(weight,map_location='cpu',weights_only=True)['model'])
        else:model,_={'r50':reconhecedor_resnet50,'native':reconhecedor_resnet50,'convnext':reconhecedor_convnext,'transformer':reconhecedor_transformer_polar}[name].load(weight,device)
        inputs=images['polar'] if name in ['polar','transformer'] else images['native'] if name=='native' else images['rgb']
        if name=='convnext':inputs=np.stack([reconhecedor_convnext.contrast(i) for i in inputs])
        valid=pv if name in ['polar','transformer'] else rv
        save(name,global_scores(extract(model,inputs,device),valid,rows))
        if name=='polar':save('spatial',spatial(model,inputs,valid,rows,device))
        del model
        if device.type=='cuda':torch.cuda.empty_cache()
    arc=ROOT/'data/modelos/cvrl_arciris';file=next(arc.rglob('ResNet100_154000.pt'))
    assert digest(file)=='466014be7723eb0b1a741dcff5a0c8ae51d1918818a6b021952f9c4ccd443f8f'
    assert digest(arc/'modules/network.py')=='de7f0cb796ebf4be02818c704d7e3afa0047dc09719b131b37cb8c26c42dd327'
    spec=importlib.util.spec_from_file_location('arc_tta_segmentation',arc/'modules/network.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    model=module.iresnet100();model.load_state_dict(torch.load(file,map_location='cpu',weights_only=True));model.to(device).eval()
    for name,key in [('arc_clahe','polar'),('arc_red','red')]:save(name,global_scores(extract(model,images[key],device,8,True),pv,rows,True))
    del model
    if device.type=='cuda':torch.cuda.empty_cache()
    return result

def main():
    from avaliar_candidato_congelado import digest,fuse,WEIGHTS
    from avaliar_robustez_reconhecimento import load_splits,metrics,operating_threshold
    from validar_fusao_identidade_adaptada import calibrate
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,required=True);args=parser.parse_args()
    out=args.output_root/'segmentacao_multivista_val_2026-10-23';out.mkdir(parents=True,exist_ok=False)
    manifest=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    rows=load_splits(json.loads(manifest.read_text()))['val']
    assert len(rows)==962 and sum(r.session==2 for r in rows)==482
    unet=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    assert digest(unet)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    frozen=json.loads((ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json').read_text())
    protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='One fixed exploratory development-validation pilot; no test images or selection on test; prior validation repeatedly used.',
        intervention='Only segmentation probabilities: equal mean of original, horizontal mirror with output unmirrored, LAB-L CLAHE clip2 grid8. Same original photo supplies recognition pixels. No clean counterpart, reconstructed texture, enrollment/query photo selection, or new identity weights.',
        transforms=3,query_photos=1,candidates_same_side=16,conditions=CONDITIONS,
        primary='New component means/stds and operating threshold calibrated once on CLEAN validation only. Unchanged equal8group fusion, apply same parameters to both occluded conditions. Secondary old fixed calibration is diagnostic only.',
        acceptance='Clean Rank1>=90%,TAR>=90%,FMR<=1%; both10% occlusions must improve Rank1 and TAR against original AND retain FMR<=1%. No automatic promotion or test evaluation even if passes.',
        stopping='Execute all three specified conditions once; no transform/weight search in this pilot.',
        failures='All482 queries and480 original enrollment images; failed extraction rejects and stays in denominators; annotations only determine simulated occlusion.',
        manifest_sha256=digest(manifest),unet_sha256=digest(unet),identity_sha256={k:h for k,(_,h) in WEIGHTS.items()},
        script_sha256=digest(Path(__file__)),dependencies_sha256={n:digest(ROOT/n) for n in ['avaliar_candidato_congelado.py','reconhecedor_convnext.py','validar_fusao_identidade_adaptada.py','avaliar_robustez_reconhecimento.py','textura_polar.py','normalizacao_eliptica.py']})
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    grouped={};baseline={};gallery=None;gi=[i for i,r in enumerate(rows) if r.session==1]
    for tag,condition,level in CONDITIONS:
        folder=out/tag;folder.mkdir();cache=out/f'cache_{tag}'
        images,rv,pv=prepare_tta(rows,device,cache,condition,level)
        if gallery is None:gallery={k:np.array(v[gi],copy=True) for k,v in images.items()}
        else:
            for k in images:np.testing.assert_array_equal(images[k][gi],gallery[k])
        grouped[tag]=components(images,rv,pv,rows,device,folder)
        suffix='' if tag=='clean' else '_'+condition+'_10'
        original=ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21'
        with np.load(original/'scores_finais.npz') as z:
            np.testing.assert_array_equal(z['labels'],grouped[tag]['rgb']['labels'])
            baseline[tag]=metrics(z['scores'],z['labels'],frozen['frozen_threshold'],z['valid'])[0]
    calibration=calibrate([grouped['clean'][n] for n in ORDER]);results=[];parameters={}
    for strategy,params in [('tta_clean_calibrated',calibration),('tta_fixed_diagnostic',frozen['component_calibration_red_and_clahe'])]:
        data={tag:dict(zip(['scores','valid'],fuse([c[n] for n in ORDER],params))) for tag,c in grouped.items()}
        labels=grouped['clean']['rgb']['labels'];clean=data['clean'];imp=np.ones_like(clean['scores'],bool);imp[np.arange(482),labels]=False
        threshold=operating_threshold(clean['scores'][imp&clean['valid'][:,None]&(clean['scores']>-2)]) if strategy=='tta_clean_calibrated' else frozen['frozen_threshold']
        parameters[strategy]=dict(calibration=params,threshold=threshold)
        for tag in grouped:
            d=data[tag];result,correct,accepted=metrics(d['scores'],labels,threshold,d['valid'])
            result.update(strategy=strategy,condition=tag,threshold=threshold,rank1_correct=int(correct.sum()),genuine_accepted=int(accepted.sum()))
            results.append(result);np.savez_compressed(out/f'{strategy}_{tag}.npz',**d,labels=labels,correct=correct,accepted=accepted)
            with (out/f'{strategy}_{tag}.csv').open('w',newline='',encoding='utf-8') as stream:
                writer=csv.writer(stream);writer.writerow(['query','label','valid','correct','accepted']+[f'score_{i}' for i in range(16)])
                for i in range(482):writer.writerow([i,int(labels[i]),bool(d['valid'][i]),bool(correct[i]),bool(accepted[i])]+d['scores'][i].tolist())
            print(json.dumps(result),flush=True)
    primary={r['condition']:r for r in results if r['strategy']=='tta_clean_calibrated'}
    passed=all(primary['clean'][m]>=.9 for m in ['rank1','tar']) and primary['clean']['far']<=.01
    passed=passed and all(primary[c][m]>baseline[c][m] for c in ['upper10','lower10'] for m in ['rank1','tar']) and all(primary[c]['far']<=.01 for c in ['upper10','lower10'])
    final=dict(status='single_photo_segmentation_tta_validation_completed',results=results,baseline=baseline,parameters=parameters,promotion_gate_passed=bool(passed),test_inference=False,frozen_candidate_replaced=False,minimum_area=None,enrollment_inputs_same_across_conditions=True)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)

if __name__=='__main__':main()

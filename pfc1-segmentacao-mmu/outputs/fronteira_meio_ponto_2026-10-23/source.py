"""Rodada final limitada a dois meios de intervalo, pipeline congelado integral."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,tempfile
import numpy as np
import torch
from avaliar_candidato_congelado import WEIGHTS,digest,prepare,extract,global_scores,spatial,fuse
ROOT=Path(__file__).resolve().parent
CONDITIONS=[('superior_0p5','oclusao_superior',.5),('inferior_1p5','oclusao_inferior',1.5)]

def main():
    from avaliar_robustez_reconhecimento import load_splits,identity,metrics
    from validar_lateralidade_informada import subset
    from treinar_identidade_iris import IdentityEncoder
    import reconhecedor_resnet50,reconhecedor_convnext,reconhecedor_transformer_polar
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'fronteira_meio_ponto_2026-10-23';out.mkdir(parents=True,exist_ok=False)
    frozen_path=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json';frozen=json.loads(frozen_path.read_text());manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_file.read_text());rows=load_splits(manifest)['test'];ids=sorted({identity(r) for r in rows});queries=[r for r in rows if r.session==2];assert len(queries)==486 and len(rows)==960
    assert not {r.subject for r in rows}&{r['subject'] for r in manifest['train']}
    weights={k:ROOT/'outputs'/folder/'melhor_modelo.pt' for k,(folder,_) in WEIGHTS.items()}
    for name,file in weights.items():assert digest(file)==WEIGHTS[name][1]
    unet=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';assert digest(unet)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    arc=ROOT/'data/modelos/cvrl_arciris';arc_file=next(arc.rglob('ResNet100_154000.pt'));assert digest(arc_file)=='466014be7723eb0b1a741dcff5a0c8ae51d1918818a6b021952f9c4ccd443f8f';assert digest(arc/'modules/network.py')=='de7f0cb796ebf4be02818c704d7e3afa0047dc09719b131b37cb8c26c42dd327'
    replay=json.loads((ROOT/'outputs/confirmacao_congelada_val_2026-10-21/CONCLUIDO.json').read_text())['result'];assert replay['replay_rank1_decisions_changed']==0 and replay['replay_acceptance_decisions_changed']==0
    protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Exactly two planned exploratory additions to previously exposed test: upper0.5% and lower1.5%; same frozen candidate,not new blind confirmation. No tuning/recalibration or further adaptive search.',
        conditions=CONDITIONS,threshold=frozen['frozen_threshold'],queries=486,defined_reference_queries=480,undefined_reference_queries=6,candidates=16,query_images=1,informed_side=True,
        intervention='Same original perturb:gray128on round(reference_pixels*level/100) lexicographic upper/lower selected pixels. References only define intervention. Rerun original segmentation/geometry; original enrollment and undefined-reference queries unchanged. Selected fraction not anatomical/disease extent.',
        precision='Reuse frozen prepare/extract/global_scores/spatial/fuse: CNN and Transformer BF16batch128,spatialFP32batch32,ArcFP32batch8. Same component and fusion weights/calibration; all failures retained.',
        criteria='Rank1>=90%,TAR>=90%,FMR<=1% fixed threshold. Determine prefix using all larger TESTED fractions on explicitly irregular grid: upperloss[0,.5,1,10],lower[0,1,1.5,2,10]. Lower0.5% NOT tested; no continuous monotonicity or uniform0.5pp-grid claim.',
        stopping='Run BOTH specified conditions regardless of outcomes; no additional points or model search in this closing round.',
        weights_sha256={k:digest(v) for k,v in weights.items()},unet_sha256=digest(unet),arc_weights_sha256=digest(arc_file),frozen_sha256=digest(frozen_path),manifest_sha256=digest(manifest_file),script_sha256=digest(Path(__file__)),dependencies_sha256={n:digest(ROOT/n) for n in ['avaliar_candidato_congelado.py','avaliar_robustez_reconhecimento.py','textura_polar.py','normalizacao_eliptica.py','preparar_polar_vermelho.py','validar_lateralidade_informada.py']},limits='Fixed-gallery16person test already examined,unknown ArcIris pretraining overlap; empirical point criterion and exploratory intervals,not clinical/anatomical universal minimum.')
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    old_cache=Path(tempfile.gettempdir())/'cache_confirmacao_test_2026-10-21'
    old_inputs={name:np.load(old_cache/(name+'.npy'),mmap_mode='r') for name in ['rgb','native','polar','red']}
    old_interventions=json.loads((ROOT/'outputs/confirmacao_congelada_test_oclusao_superior_1_2026-10-21/interventions.json').read_text());reference_sizes={r['image']:r['reference_pixels'] for r in old_interventions}
    unchanged=np.array([r.session==1 or reference_sizes.get(Path(r.image).name,-1)==0 for r in rows]);assert sum(r.session==1 for r in rows)==474 and unchanged.sum()==480
    results=[]
    for tag,condition,level in CONDITIONS:
        folder=out/tag;folder.mkdir();cache=a.output_root.parent/f'cache_fronteira_meio_ponto_{tag}_2026-10-23';images,rv,pv=prepare(rows,device,cache,condition,level)
        for name in images:np.testing.assert_array_equal(images[name][unchanged],old_inputs[name][unchanged])
        interventions=json.loads((cache/'interventions.json').read_text());assert len(interventions)==486
        for r in interventions:
            n=r['reference_pixels'];assert r['affected_fraction']==(round(n*level/100)/n if n else 0.)
        (folder/'interventions.json').write_text(json.dumps(interventions,indent=2),encoding='utf-8');components={}
        def save(name,result):
            full,valid=result;scores,labels,_=subset(full,rows,ids);components[name]=dict(scores=scores,labels=labels,valid=valid);np.savez_compressed(folder/f'scores_{name}.npz',**components[name]);print(f'{tag}:component {name}',flush=True)
        for name in ['rgb','polar','r50','convnext','native','transformer']:
            if name in ['rgb','polar']:
                model=IdentityEncoder().to(device).eval();model.load_state_dict(torch.load(weights[name],map_location='cpu',weights_only=True)['model'])
            else:model,_={'r50':reconhecedor_resnet50,'convnext':reconhecedor_convnext,'native':reconhecedor_resnet50,'transformer':reconhecedor_transformer_polar}[name].load(weights[name],device)
            inputs=images['polar'] if name in ['polar','transformer'] else images['native'] if name=='native' else images['rgb']
            if name=='convnext':inputs=np.stack([reconhecedor_convnext.contrast(i) for i in inputs])
            valid=pv if name in ['polar','transformer'] else rv;save(name,global_scores(extract(model,inputs,device),valid,rows))
            if name=='polar':save('spatial',spatial(model,inputs,valid,rows,device))
            del model
            if device.type=='cuda':torch.cuda.empty_cache()
        spec=importlib.util.spec_from_file_location('arciris_midpoint',arc/'modules/network.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);model=module.iresnet100();model.load_state_dict(torch.load(arc_file,map_location='cpu',weights_only=True));model.to(device).eval()
        for name,inputs in [('arc_clahe',images['polar']),('arc_red',images['red'])]:save(name,global_scores(extract(model,inputs,device,8,True),pv,rows,True))
        del model
        if device.type=='cuda':torch.cuda.empty_cache()
        order=['rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red'];scores,valid=fuse([components[k] for k in order],frozen['component_calibration_red_and_clahe']);labels=components['rgb']['labels']
        for c in components.values():np.testing.assert_array_equal(c['labels'],labels)
        measured,correct,accepted=metrics(scores,labels,frozen['frozen_threshold'],valid);np.savez_compressed(folder/'scores_finais.npz',scores=scores,labels=labels,valid=valid,correct=correct,accepted=accepted)
        record=dict(tag=tag,orientation=condition,occluded_percent=level,nominal_retained_percent=100-level,result=measured,rank1_correct=int(correct.sum()),genuine_accepted=int(accepted.sum()),passed=bool(measured['rank1']>=.9 and measured['tar']>=.9 and measured['far']<=.01),gallery_and_empty_reference_inputs_exact=True)
        (folder/'CONCLUIDO.json').write_text(json.dumps(record,indent=2),encoding='utf-8');results.append(record);print(json.dumps(record),flush=True)
    final=dict(status='bounded_midpoint_round_completed',records=results,threshold_unchanged=frozen['frozen_threshold'],new_conditions=2,training=False,threshold_recalibrated=False,independent_blind_test=False,anatomical_minimum=None,clinical_minimum=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()

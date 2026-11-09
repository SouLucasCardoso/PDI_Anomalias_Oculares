"""Recupera somente metadado TorchVersion de checkpoint local desta rodada.

Nao muda tensores, epoca escolhida, regra de selecao ou treinamento.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,shutil
import numpy as np
import torch
from torch.torch_version import TorchVersion
from treinar_reconhecedor_entrega import ROOT,ORDER,CONDITIONS,eligibility,frozen_digest
from recorte_iris_sam31_alta_res import sha
from rodada_reconhecedor_entrega import write,result_path
from avaliar_candidato_congelado import extract,global_scores,fuse
from avaliar_robustez_reconhecimento import load_splits,identity,metrics
from validar_lateralidade_informada import subset
from reconhecedor_resnet50 import Encoder

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args();run=a.run_dir.resolve()
    protocol=json.loads((run/'protocolo.json').read_text());reference=Path(protocol['reference_root'])
    for name,expected in protocol['sources_sha256'].items():assert sha(ROOT/name)==expected
    assert not (run/'CONCLUIDO.json').exists()
    best=run/'melhor_modelo.pt';before=sha(best)
    # Somente a subclasse conhecida de str, em arquivo produzido localmente e hash registrado.
    with torch.serialization.safe_globals([TorchVersion]):
        selected=torch.load(best,map_location='cpu',weights_only=True)
        last=torch.load(run/'ultima_epoca.pt',map_location='cpu',weights_only=True)
    assert last['epoch']==last['history'][-1]['epoch'] and last['stale']>=protocol['patience']
    assert selected['epoch']==last['selected_epoch']
    assert json.loads(json.dumps(selected['configuration']))==protocol
    selected['configuration']=json.loads(json.dumps(selected['configuration']))
    portable=run/'checkpoint_portavel.pt';torch.save(selected,portable)
    verification=torch.load(portable,map_location='cpu',weights_only=True)
    for part in ('model','training_head'):
        for name,value in selected[part].items():assert torch.equal(value,verification[part][name])
    backup=run/'melhor_modelo_metadado_torchversion.pt';assert not backup.exists();shutil.copy2(best,backup);portable.replace(best)
    repair={'utc':datetime.now(timezone.utc).isoformat(),'reason':'Local checkpoint configuration contained torch.torch_version.TorchVersion metadata; weights_only rejected this known str subclass.',
        'action':'Allowlist only TorchVersion to read own checkpoint; convert configuration through JSON to builtin types; verify every model/head tensor bitwise; preserve original checkpoint backup; recompute selected validation scores.',
        'original_checkpoint_sha256':before,'portable_checkpoint_sha256':sha(best),'backup_sha256':sha(backup),
        'all_model_and_head_tensors_bitwise_equal':True,'training_repeated':False,'selection_changed':False,'source_sha256':sha(__file__)}
    write(run/'RECUPERACAO_SERIALIZACAO.json',repair)
    os.environ['MPLCONFIGDIR']=str(Path(os.environ['TEMP'])/'pfc-matplotlib');torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda')
    model=Encoder().to(device).eval();model.load_state_dict(selected['model']);model.requires_grad_(False);model.backbone.layer4.requires_grad_(True);model.projection.requires_grad_(True)
    frozen_hash=frozen_digest(model)
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());rows=load_splits(manifest)['val'];ids=sorted({identity(r) for r in rows})
    frozen=json.loads((ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json').read_text());threshold=frozen['frozen_threshold'];results={}
    for condition,level in CONDITIONS:
        suffix='' if condition=='original' else f'_{condition}_{level}';folder=result_path(reference,'nearest',condition,level)
        cache=reference/'nearest'/f'cache_confirmacao_val{suffix}_2026-10-21'
        with np.load(cache/'valid.npz') as z:rv=z['rgb']
        images=np.load(cache/'native.npy',mmap_mode='r');components=[]
        for name in ORDER:
            with np.load(folder/f'scores_{name}.npz',allow_pickle=False) as z:components.append({k:z[k].copy() for k in ('scores','valid','labels')})
        full,qvalid=global_scores(extract(model,images,device),rv,rows);scores,y,_=subset(full,rows,ids);np.testing.assert_array_equal(y,components[0]['labels'])
        replacement={'scores':scores,'labels':y,'valid':qvalid};components[5]=replacement
        fused,valid=fuse(components,frozen['component_calibration_red_and_clahe']);m,c,accepted=metrics(fused,y,threshold,valid)
        m.update(joint_success=float((c&accepted).mean()),threshold=threshold);results[condition]=m
        for key in ('rank1','tar','far','joint_success'):assert abs(m[key]-selected['validation'][condition][key])<1e-12
        np.savez_compressed(run/f'scores_native_selected_{condition}.npz',**replacement)
        np.savez_compressed(run/f'scores_fusion_selected_{condition}.npz',scores=fused,labels=y,valid=valid,correct=c,accepted=accepted)
    final={'status':'concluido','selected_epoch':selected['epoch'],'epochs_completed':last['epoch'],'baseline':last['baseline'],'results':results,
        'eligible_gain':selected['epoch']>0 and eligibility(results,last['baseline']),'absolute_fmr_target_all_conditions':all(r['far']<=.01 for r in results.values()),
        'checkpoint_sha256':sha(best),'frozen_parameters_sha256':frozen_hash,'teacher_sha256':sha(run/'teacher.npy'),
        'test_inference':False,'recognizer_replaced':False,'elapsed_seconds':last['history'][-1]['elapsed_seconds'],
        'serialization_recovered_without_tensor_or_selection_change':True,'recovery_sha256':sha(run/'RECUPERACAO_SERIALIZACAO.json')}
    write(run/'CONCLUIDO.json',final);write(run/'estado.json',{'stage':'concluido','selected_epoch':selected['epoch'],'eligible_gain':final['eligible_gain'],'serialization_recovered':True})
    print(json.dumps({k:v for k,v in final.items() if k not in ('baseline','results')}),flush=True)

if __name__=='__main__':main()

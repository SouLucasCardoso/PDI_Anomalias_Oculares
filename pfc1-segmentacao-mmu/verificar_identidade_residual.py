"""Recarrega modelo e correcao e confere escores salvos, sem recalibracao."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
import torch
ROOT=Path(__file__).resolve().parent

def main():
    from treinar_identidade_iris import IdentityEncoder
    from treinar_segmentacao_ubipr import Sample
    from treinar_identidade_residual import features,correct
    from avaliar_candidato_congelado import global_scores
    from avaliar_robustez_reconhecimento import identity
    from validar_lateralidade_informada import subset
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();folder=a.output_root/'identidade_residual_oclusao_2026-10-21';destination=folder/'VERIFICACAO_RELOAD.json'
    if destination.exists():raise ValueError('Preserve verification')
    checkpoint=folder/'melhor_modelo.pt';state=torch.load(checkpoint,map_location='cpu',weights_only=True);parameters={k:v.numpy() for k,v in state['residual'].items()}
    with np.load(folder/'regressao_residual.npz') as saved:
        for k,v in parameters.items():np.testing.assert_array_equal(v,saved[k])
    reference=torch.load(ROOT/'outputs/identidade_arcface_ubipr_2026-10-20/melhor_modelo.pt',map_location='cpu',weights_only=True)['model'];assert state['model'].keys()==reference.keys();assert all(torch.equal(v,reference[k]) for k,v in state['model'].items())
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');model=IdentityEncoder().to(device).eval();model.load_state_dict(state['model'])
    rows=[Sample(**r) for r in json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text())['val']];eligible={identity(r) for r in rows if r.session==1}&{identity(r) for r in rows if r.session==2};rows=[r for r in rows if identity(r) in eligible];ids=sorted({identity(r) for r in rows});differences={}
    for name,prefix in [('clean',''),('upper10','_oclusao_superior_10'),('lower10','_oclusao_inferior_10')]:
        cache=a.output_root.parent/f'cache_confirmacao_val{prefix}_segmentador_8f126141f4dd_2026-10-21';images=np.load(cache/'rgb.npy',mmap_mode='r')
        with np.load(cache/'valid.npz') as z:valid=z['rgb']
        raw,base=features(model,images,device);full,qvalid=global_scores(correct(raw,base,parameters),valid,rows);scores,labels,_=subset(full,rows,ids)
        with np.load(folder/f'scores_melhor_{name}.npz') as z:
            np.testing.assert_array_equal(labels,z['labels']);np.testing.assert_array_equal(qvalid,z['valid']);np.testing.assert_allclose(scores,z['scores'],atol=1e-12,rtol=0);differences[name]=float(np.abs(scores-z['scores']).max())
    gradient=torch.load(a.output_root/'identidade_oclusao_segmentacao_2026-10-21/melhor_modelo.pt',map_location='cpu',weights_only=True);changed=sum(not torch.equal(v,reference[k]) for k,v in gradient['model'].items());assert gradient['epoch']==0 and changed==0
    result={'status':'residual_reload_verified','max_score_difference':differences,'residual_parameters_identical_npz_and_checkpoint':True,'residual_backbone_changed_tensors':0,'gradient_selected_epoch':0,'gradient_selected_encoder_changed_tensors':changed,'test_inference':False,'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    destination.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))

if __name__=='__main__':main()

"""Reproduz mascaras, prompts automaticos, metricas e CI sem redes/pesos externos."""
from pathlib import Path
import argparse,csv,json
import numpy as np
from PIL import Image
from avaliar_irissam_ubipr import ROOT,NAME,METHODS,CONDITIONS,mask_box,metrics,affected_support
from preparar_encoder_espacial import file_hash
from treinar_segmentacao_ubipr import decode_mask

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();folder=a.root/NAME;protocol=json.loads((folder/'protocolo.json').read_text());done=json.loads((folder/'CONCLUIDO.json').read_text());assert file_hash(folder/'source.py')==protocol['script_sha256'] and file_hash(folder/'mascaras_empacotadas.npz')==done['masks_sha256']
    assert len(protocol['sample'])==len({r['subject'] for r in protocol['sample']})==32
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());assert file_hash(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json')==protocol['manifest_sha256']
    val_images={Path(r['image']).name for r in manifest['val']};assert all(r['image'] in val_images for r in protocol['sample']);assert not {r['subject'] for r in protocol['sample']}&{r['subject'] for r in manifest['train']+manifest['test']}
    with (folder/'metricas_por_imagem.csv').open(encoding='utf-8',newline='') as f:records=list(csv.DictReader(f))
    prompts=json.loads((folder/'prompts.json').read_text());assert len(records)==384 and len(prompts)==96
    with np.load(folder/'mascaras_empacotadas.npz') as z:
        for i,row in enumerate(protocol['sample']):
            with Image.open(ROOT/'data/ubipr/single_eye'/row['mask']) as im:truth=decode_mask(im)==1
            for tag,_ in CONDITIONS:
                shape=tuple(z[f'{i:02}_{tag}_shape']);assert shape==truth.shape;visible=truth&~affected_support(truth,tag);predictions={}
                for method in METHODS:
                    pred=np.unpackbits(z[f'{i:02}_{tag}_{method}'],count=int(np.prod(shape))).reshape(shape).astype(bool);predictions[method]=pred
                    matched=[r for r in records if r['image']==row['image'] and r['condition']==tag and r['method']==method];assert len(matched)==1;r=matched[0]
                    assert int(r['subject'])==row['subject'] and int(r['reference_pixels'])==int(truth.sum()) and int(r['affected_pixels'])==int(affected_support(truth,tag).sum())
                    assert (r['empty_prediction']=='True')==(not bool(pred.any()))
                    for target,target_mask in [('full',truth),('visible',visible)]:
                        for key,value in metrics(pred,target_mask).items():assert value==float(r[target+'_'+key])
                saved=[v for v in prompts if v['image']==row['image'] and v['condition']==tag];assert len(saved)==1;assert saved[0]['automatic_box']==mask_box(predictions['unet'],.05);assert saved[0]['oracle_box']==mask_box(truth)
    for method,group in done['summary'].items():
        for tag,group_metrics in group.items():
            for key,value in group_metrics.items():assert float(np.mean([float(r[key]) for r in records if r['method']==method and r['condition']==tag]))==value
    rng=np.random.default_rng(63)
    for tag,_ in CONDITIONS:
        diff=np.array([float(r['visible_dice']) for r in records if r['method']=='irissam_auto_unet_box' and r['condition']==tag])-np.array([float(r['visible_dice']) for r in records if r['method']=='unet' and r['condition']==tag]);draws=rng.integers(0,32,size=(5000,32));ci=np.quantile(diff[draws].mean(1),[.025,.975]);saved=done['primary_paired_differences'][tag];assert float(diff.mean())==saved['mean_difference'];np.testing.assert_array_equal(ci,saved['bootstrap95'])
    u=done['summary']['unet'];s=done['summary']['irissam_auto_unet_box'];gate=s['clean']['full_dice']>=u['clean']['full_dice'] and all(s[t]['visible_dice']>=u[t]['visible_dice']+.01 for t in ['upper10','lower10']);assert bool(gate)==done['screen_passed'];assert not any(done[k] for k in ['biometric_inference','test_inference','frozen_candidate_replaced'])
    provenance=json.loads((folder/'PROVENIENCIA_CHECKPOINT.json').read_text());assert provenance['checkpoint']['sha256']==done['checkpoint_sha256']
    report=dict(status='irissam_masks_prompts_metrics_verified',people=32,paired_cases=96,records=384,automatic_prompts_reproduced=True,oracle_separated=True,all_dice_iou_exact=True,paired_bootstrap_exact=True,screen_gate_reproduced=bool(gate),new_model_inference=False)
    (folder/'AUDITORIA_REPRODUCAO.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

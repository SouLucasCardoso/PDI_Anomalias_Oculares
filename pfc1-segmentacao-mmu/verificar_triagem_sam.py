"""Reproduz Dice/IoU a partir das mascaras preservadas e referencias locais."""
from pathlib import Path
import argparse,csv,json
import numpy as np
from PIL import Image
from piloto_sam_guiado import ROOT,NAME,dice_iou,automatic_prompts
from avaliar_candidato_congelado import digest
from treinar_segmentacao_ubipr import decode_mask

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();folder=a.root/NAME
    protocol=json.loads((folder/'protocolo.json').read_text());done=json.loads((folder/'CONCLUIDO.json').read_text());assert digest(folder/'source.py')==protocol['script_sha256'];assert digest(folder/'mascaras_empacotadas.npz')==done['mask_file_sha256']
    with (folder/'metricas_por_imagem.csv').open(encoding='utf-8',newline='') as f:records=list(csv.DictReader(f))
    prompts=json.loads((folder/'prompts.json').read_text());assert len(records)==192 and len(prompts)==96
    with np.load(folder/'mascaras_empacotadas.npz') as z:
        for i,row in enumerate(protocol['sample']):
            with Image.open(ROOT/'data/ubipr/single_eye'/row['mask']) as im:truth=decode_mask(im)==1
            for tag in protocol['conditions']:
                shape=tuple(z[f'{i:02}_{tag}_shape']);assert shape==truth.shape;visible=truth.copy()
                if tag!='clean':
                    y,x=np.where(truth);order=np.lexsort((x,-y if tag=='lower10' else y));take=order[:round(len(x)*.1)];visible[y[take],x[take]]=False
                for suffix,method in [('unet','unet'),('sam','sam_guided')]:
                    pred=np.unpackbits(z[f'{i:02}_{tag}_{suffix}'],count=int(np.prod(shape))).reshape(shape).astype(bool)
                    matches=[r for r in records if r['image']==row['image'] and r['condition']==tag and r['method']==method];assert len(matches)==1;r=matches[0]
                    for target,target_mask in [('full',truth),('visible',visible)]:
                        for key,value in dice_iou(pred,target_mask).items():assert value==float(r[target+'_'+key])
                    if method=='unet':
                        saved=[v for v in prompts if v['image']==row['image'] and v['condition']==tag];assert len(saved)==1
                        try:expected=automatic_prompts(pred)
                        except ValueError:expected=None
                        assert expected==saved[0]['prompt']
    for method,group in done['summary'].items():
        for tag,metric in group.items():
            for key,value in metric.items():assert float(np.mean([float(r[key]) for r in records if r['method']==method and r['condition']==tag]))==value
    u=done['summary']['unet'];s=done['summary']['sam_guided'];gate=s['clean']['visible_dice']>=u['clean']['visible_dice'] and all(s[t]['visible_dice']>=u[t]['visible_dice']+.01 for t in ['upper10','lower10']) and np.mean([s[t]['full_dice'] for t in s])>=np.mean([u[t]['full_dice'] for t in u])
    assert bool(gate)==done['screen_passed'];assert not any(done[k] for k in ['biometric_inference','validation_identity_inference','test_inference','frozen_candidate_replaced'])
    report=dict(status='sam_guided_screen_masks_and_metrics_verified',paired_cases=96,metric_records=192,automatic_prompts_reproduced=True,all_dice_iou_exact=True,screen_gate_reproduced=bool(gate),new_model_inference=False)
    (folder/'AUDITORIA_REPRODUCAO.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

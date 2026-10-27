"""Treina somente8194parametros de forma; nao altera localizador circular ou identidade."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,hashlib,json,random
import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.utils.data import DataLoader,TensorDataset
from pupila_eliptica import EllipticShape,encode_shape
from localizador_pupila import PupilLocator
ROOT=Path(__file__).resolve().parent

def main():
    from auditar_alvos_pupila import ellipse_geometry
    from treinar_segmentacao_ubipr import decode_mask
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    out=a.output_root/'forma_pupila_2026-10-23';out.mkdir(parents=True,exist_ok=False)
    previous=ROOT/'outputs/localizador_pupila_2026-10-22';sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    original=json.loads((previous/'protocolo.json').read_text());completion=json.loads((previous/'CONCLUIDO.json').read_text())
    assert sha(previous/'melhor_modelo.pt')==completion['checkpoint_sha256']
    protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Fit only shape on same6282fit and879internal monitor inputs. No identity validation or test inference in training. Monitor reused, U-Net saw it; targets are annotation-hole proxies.',
        architecture='Frozen selected circle locator; its Conv features -> Linear4096x2 ->0.75tanh for trace-free log-axis vector (d*cos2theta,d*sin2theta),d=.5log(major/minor).8194trainable parameters. Circle center/equivalent radius EXACTLY unchanged.',
        training='Seed59,AdamW1e-3 wd1e-4,B64,max12epochs,patience3 after4;SmoothL1 shape;initial zero-shape epoch0 isotropic control;select minimum internal monitor loss. No augmentation to isolate shape fitting on cached inputs; no validation selection.',
        gate='Proceed to recognition only if selected monitor shape loss < isotropic epoch0. Recognition original frozen control, previously evaluated circle-fixed control,ellipse-fixed and ellipse-clean-recalibrated; all482queries and fixed side16candidates; clean parameters reused upper/lower10; no test or automatic promotion.',
        inference='Only legacy pupil fallback: same frozen learned circle; replace its shape if all512boundary samples contained in original outer ellipse and polar support nonempty,otherwise return learned circle. Ordinary holes,RGB crops,masks,identity/fusion weights unchanged. No quality filtering.',
        fit_people=original['fit_people'],monitor_people=original['monitor_people'],circle_checkpoint_sha256=sha(previous/'melhor_modelo.pt'),script_sha256=sha(Path(__file__)),shape_source_sha256=sha(ROOT/'pupila_eliptica.py'))
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());(out/'shape_source.py').write_bytes((ROOT/'pupila_eliptica.py').read_bytes())
    torch.set_num_threads(4);torch.manual_seed(59);np.random.seed(59);random.seed(59);torch.backends.cudnn.benchmark=False
    device='cuda' if torch.cuda.is_available() else 'cpu';circle=PupilLocator().to(device).eval();circle.load_state_dict(torch.load(previous/'melhor_modelo.pt',map_location='cpu',weights_only=True)['model'])
    for param in circle.parameters():param.requires_grad=False
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());mapping={Path(r['image']).name:r for r in manifest['train']}
    prepared={}
    for group in ['fit','monitor']:
        records=json.loads((previous/f'rows_{group}.json').read_text());targets=[]
        for row in records:
            with Image.open(ROOT/'data/ubipr/single_eye'/Path(mapping[row['image']]['mask']).name) as im:mask=decode_mask(im)==1
            _,inner=ellipse_geometry(mask);targets.append(encode_shape(inner))
        with np.load(previous/f'inputs_{group}.npz') as z:images=z['images']
        features=[]
        with torch.inference_mode():
            for start in range(0,len(images),128):
                batch=torch.from_numpy(images[start:start+128].transpose(0,3,1,2).copy()).to(device).float()/255
                features.append(circle.features(batch).flatten(1).cpu())
        prepared[group]=(torch.cat(features),torch.from_numpy(np.stack(targets)))
        print(json.dumps(dict(phase='prepare',group=group,images=len(records))),flush=True)
    fit=DataLoader(TensorDataset(*prepared['fit']),batch_size=64,shuffle=True)
    monitor_x,monitor_y=(v.to(device) for v in prepared['monitor']);model=EllipticShape().to(device);optimizer=torch.optim.AdamW(model.parameters(),lr=1e-3,weight_decay=1e-4)
    loss_fn=nn.SmoothL1Loss();history=[];best=float('inf');stale=0;best_epoch=None;zero_loss=float(loss_fn(torch.zeros_like(monitor_y),monitor_y))
    for epoch in range(13):
        model.train();losses=[]
        if epoch:
            for x,y in fit:
                optimizer.zero_grad();loss=loss_fn(model(x.to(device)),y.to(device));loss.backward();optimizer.step();losses.append(float(loss.detach()))
        model.eval()
        with torch.inference_mode():value=float(loss_fn(model(monitor_x),monitor_y))
        row=dict(epoch=epoch,train_loss=float(np.mean(losses)) if losses else None,monitor_loss=value,isotropic_monitor_loss=zero_loss);history.append(row)
        if value<best:
            best=value;best_epoch=epoch;stale=0
            (out/'melhor_forma.json').write_text(json.dumps(dict(state={k:v.detach().cpu().tolist() for k,v in model.state_dict().items()},epoch=epoch,monitor_loss=value)),encoding='utf-8')
        else:stale+=1
        with (out/'historico.csv').open('w',encoding='utf-8',newline='') as f:writer=csv.DictWriter(f,fieldnames=list(row));writer.writeheader();writer.writerows(history)
        print(json.dumps(row),flush=True)
        if epoch>=4 and stale>=3:break
    final=dict(status='pupil_shape_training_completed',best_epoch=best_epoch,epochs_trained=epoch,best_monitor_loss=best,isotropic_monitor_loss=zero_loss,recognition_validation_gate_passed=best<zero_loss,shape_sha256=sha(out/'melhor_forma.json'),circle_checkpoint_sha256=completion['checkpoint_sha256'],fit_images=len(prepared['fit'][0]),monitor_images=len(prepared['monitor'][0]),test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)

if __name__=='__main__':main()

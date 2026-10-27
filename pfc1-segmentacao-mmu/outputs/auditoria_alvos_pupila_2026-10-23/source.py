"""Auditoria descritiva no monitor interno; nao seleciona modelos ou limiares."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,hashlib,json
import cv2
import numpy as np
from PIL import Image
import torch
from localizador_pupila import PupilLocator,pupil_target
from normalizacao_eliptica import ellipse_endpoints

ROOT=Path(__file__).resolve().parent

def ellipse_geometry(mask):
    contours,h=cv2.findContours(mask.astype(np.uint8)*255,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_NONE)
    outer=[i for i,p in enumerate(h[0,:,3]) if p<0 and len(contours[i])>=5]
    oi=max(outer,key=lambda i:cv2.contourArea(contours[i]));outer_ellipse=cv2.fitEllipse(contours[oi])
    holes=[i for i,p in enumerate(h[0,:,3]) if p==oi and len(contours[i])>=5 and cv2.contourArea(contours[i])>=max(4,.01*cv2.contourArea(contours[oi]))]
    inner=cv2.fitEllipse(contours[max(holes,key=lambda i:cv2.contourArea(contours[i]))])
    return outer_ellipse,inner

def inside_fraction(inner,outer):
    theta=np.arange(512)*2*np.pi/512
    x,y=ellipse_endpoints(inner,theta)
    dx=x-outer[0][0];dy=y-outer[0][1];a=np.deg2rad(outer[2])
    u=np.cos(a)*dx+np.sin(a)*dy;v=-np.sin(a)*dx+np.cos(a)*dy
    return float(np.mean((u/(outer[1][0]/2))**2+(v/(outer[1][1]/2))**2<=1))

def main():
    from treinar_segmentacao_ubipr import decode_mask
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,default=ROOT/'outputs');args=parser.parse_args()
    out=args.output_root/'auditoria_alvos_pupila_2026-10-23';out.mkdir(parents=True,exist_ok=False)
    source=ROOT/'outputs/localizador_pupila_2026-10-22'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    protocol=json.loads((source/'protocolo.json').read_text());finished=json.loads((source/'CONCLUIDO.json').read_text())
    checkpoint=source/'melhor_modelo.pt';assert sha(checkpoint)==finished['checkpoint_sha256']
    registered=dict(registered_utc=datetime.now(timezone.utc).isoformat(),purpose='Descriptive audit of selected locator on internal training monitor only; original vs filled predicted-mask channel, RGB/targets unchanged. No new fitting, identity validation/test inference, threshold search or promotion.',
        limits='Monitor reused for checkpoint selection. Targets are proxies derived from iris annotation. Mask topology measured at64x64 is not native fallback classification. Filling holes is a channel intervention, NOT an ocular occlusion.',
        checkpoint_sha256=sha(checkpoint),inputs_sha256=sha(source/'inputs_monitor.npz'),script_sha256=sha(Path(__file__)),statistics='All879 retained; center error ROI normalized Euclidean, radius absolute normalized error; report original/filled mask and concentric baseline, per-person means and quantiles; native annotation ellipticity and512-angle inner/outer containment, no score-based selection.')
    (out/'protocolo.json').write_text(json.dumps(registered,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    records=json.loads((source/'rows_monitor.json').read_text());assert len(records)==879
    assert set(r['subject'] for r in records)==set(protocol['monitor_people'])
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());mapping={Path(r['image']).name:r for r in manifest['train']}
    with np.load(source/'inputs_monitor.npz') as z:images=z['images'];targets=z['targets'];baseline=z['baseline']
    filled=images.copy();hole_pixels=[]
    for i,image in enumerate(images):
        contours,_=cv2.findContours(image[:,:,3],cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        mask=np.zeros((64,64),np.uint8);cv2.drawContours(mask,contours,-1,255,cv2.FILLED)
        filled[i,:,:,3]=mask;hole_pixels.append(int(np.count_nonzero(mask!=image[:,:,3])))
    assert np.array_equal(images[:,:,:,:3],filled[:,:,:,:3])
    torch.set_num_threads(4);device='cuda' if torch.cuda.is_available() else 'cpu'
    model=PupilLocator().to(device).eval();model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
    predictions={}
    with torch.inference_mode():
        for condition,inputs in [('original',images),('filled_mask',filled)]:
            predictions[condition]=np.concatenate([model(torch.from_numpy(inputs[i:i+128].transpose(0,3,1,2).copy()).to(device).float()/255).cpu().numpy() for i in range(0,len(inputs),128)])
    predictions['concentric']=baseline
    rows=[]
    for i,record in enumerate(records):
        row=dict(record,filled_pixels=hole_pixels[i])
        for name,pred in predictions.items():
            row[name+'_center_error_roi']=float(np.linalg.norm(pred[i,:2]-targets[i,:2]))
            row[name+'_radius_error_roi']=float(abs(pred[i,2]-targets[i,2]))
        row['center_shift_roi']=float(np.linalg.norm(predictions['original'][i,:2]-predictions['filled_mask'][i,:2]))
        with Image.open(ROOT/'data/ubipr/single_eye'/Path(mapping[record['image']]['mask']).name) as im:mask=decode_mask(im)==1
        assert pupil_target(mask) is not None
        outer,inner=ellipse_geometry(mask);radius=np.sqrt(inner[1][0]*inner[1][1])/2
        circle=(inner[0],(2*radius,2*radius),0.)
        row['target_minor_major_ratio']=float(min(inner[1])/max(inner[1]))
        row['target_ellipse_inside_outer_fraction']=inside_fraction(inner,outer)
        row['target_circle_inside_outer_fraction']=inside_fraction(circle,outer)
        rows.append(row)
    with (out/'por_imagem.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    keys=[k for k in rows[0] if k not in ['image','subject','filled_pixels']]
    summary={k:dict(mean=float(np.mean([r[k] for r in rows])),median=float(np.median([r[k] for r in rows])),p90=float(np.quantile([r[k] for r in rows],.9))) for k in keys}
    people=[]
    for person in sorted(protocol['monitor_people']):
        subset=[r for r in rows if r['subject']==person]
        people.append(dict(subject=person,n=len(subset),**{k:float(np.mean([r[k] for r in subset])) for k in keys}))
    (out/'por_pessoa.json').write_text(json.dumps(people,indent=2),encoding='utf-8')
    loss=lambda x:float((torch.nn.functional.smooth_l1_loss(torch.from_numpy(x),torch.from_numpy(targets),reduction='none')*torch.tensor([1.,1.,4.])).mean())
    result=dict(status='pupil_proxy_audit_completed',images=len(rows),people=len(people),mask_channel_changed=sum(v>0 for v in hole_pixels),losses={k:loss(v) for k,v in predictions.items()},summary=summary,
        ellipse_not_fully_contained=sum(r['target_ellipse_inside_outer_fraction']<1 for r in rows),circle_not_fully_contained=sum(r['target_circle_inside_outer_fraction']<1 for r in rows),
        original_monitor_loss_recorded=finished['best_monitor_loss'],rgb_unchanged=True,new_training=False,identity_validation_inference=False,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    assert abs(result['losses']['original']-finished['best_monitor_loss'])<1e-9
    (out/'CONCLUIDO.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()

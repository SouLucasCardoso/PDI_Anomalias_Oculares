"""Comparador espacial ponderado: experimento fixo, apenas validacao."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, tempfile
import numpy as np
import torch
from torch import nn
ROOT = Path(__file__).resolve().parent


def reliability(images):
    """Entropia de 16 niveis em blocos16x16; proxy, nao mascara anatomica."""
    gray = np.asarray(images)[..., 0] // 16
    if gray.shape[1:] != (64, 512):
        raise ValueError('Expected64x512 polar images')
    patches = gray.reshape(-1, 4, 16, 32, 16).transpose(0, 1, 3, 2, 4)
    entropy = np.zeros(patches.shape[:3], dtype=np.float32)
    for value in range(16):
        p = (patches == value).mean(axis=(-1, -2))
        entropy -= (p * np.log2(np.maximum(p, 1e-12))).astype(np.float32)
    return (entropy / 4) ** 2


def weighted_scores(query, gallery, query_quality, gallery_quality):
    weights = torch.sqrt(query_quality[:, None] * gallery_quality[None])
    denominator = weights.sum((-1, -2))
    local = torch.einsum('bchw,gchw->bghw', query, gallery)
    scores = (local * weights).sum((-1, -2)) / denominator.clamp_min(1e-12)
    return torch.where(denominator > 0, scores, torch.full_like(scores, -2))


def main():
    from treinar_identidade_iris import IdentityEncoder
    from avaliar_robustez_reconhecimento import identity, metrics, operating_threshold, Sample
    from validar_lateralidade_informada import subset
    from validar_correspondencia_espacial import spatial_scores
    from validar_fusao_identidade_adaptada import ORDER, calibrate
    from avaliar_candidato_congelado import fuse
    p = argparse.ArgumentParser(); p.add_argument('--output-root', type=Path, required=True); a = p.parse_args()
    out = a.output_root / 'textura_local_val_2026-10-21'
    out.mkdir(parents=True, exist_ok=False)
    protocol = dict(registered_utc=datetime.now(timezone.utc).isoformat(),
        scope='Exploratory validation ONLY; no test inference, no candidate replacement',
        method='Frozen polar R18 layer3, constant127 feature subtraction, channel L2, shift0. Unchanged uniform S1 prototype. Local reliability=normalized16-bin entropy squared in16x16 input blocks. Pair weight=sqrt(query reliability * mean S1 reliability); weighted local cosine. No fill-value detector or ground truth mask.',
        controls='Uniform matching must reproduce cached spatial scores within2e-6. Two segmentation branches original/robust, each uniform/weighted. Standalone and same-branch fusion replacing spatial component only; fixed original fusion weights.',
        calibration='Each strategy calibrated once on CLEAN validation, impostor mean/std and empirical FMR<=1% threshold; same parameters for upper/lower10%. No parameter sweep.',
        counts='482 single-photo S2 queries,16 supplied-side candidates,15 impostors/query; all failures retained',
        limitations='Entropy is a texture proxy, not visible anatomical area. Repeated development validation, no independent confirmation or clinical minimum.',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'protocolo.json').write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text())
    rows=[Sample(**r) for r in manifest['val']]
    eligible={identity(r) for r in rows if r.session==1}&{identity(r) for r in rows if r.session==2}
    rows=[r for r in rows if identity(r) in eligible]; qi=[i for i,r in enumerate(rows) if r.session==2]
    assert len(rows)==962 and len(qi)==482
    ids=sorted({identity(r) for r in rows})
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    checkpoint=ROOT/'outputs/encoder_polar_2026-10-20/melhor_modelo.pt'
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()=='db93dfcca33b8a77cd3bfbaa66f07d1efae2e976414d67748ccf5eff4a5ebe5c'
    encoder=IdentityEncoder(); encoder.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
    extractor=nn.Sequential(*list(encoder.backbone.children())[:7]).to(device).eval()
    mean=torch.tensor([.485,.456,.406],device=device)[None,:,None,None]; std=torch.tensor([.229,.224,.225],device=device)[None,:,None,None]
    with torch.inference_mode(): background=extractor((torch.full((1,3,64,512),127/255,device=device)-mean)/std)
    conditions={'clean':'','upper10':'_oclusao_superior_10','lower10':'_oclusao_inferior_10'}
    results=[]; audits=[]; source_hashes={}
    def read(file):
        source_hashes[str(file)]=hashlib.sha256(file.read_bytes()).hexdigest()
        with np.load(file) as z:return {k:z[k] for k in ('scores','labels','valid')}
    for branch,tag in [('original',''),('robust','_segmentador_8f126141f4dd')]:
        data={}; originals={}
        for condition,suffix in conditions.items():
            cache=Path(tempfile.gettempdir())/f'cache_confirmacao_val{suffix}{tag}_2026-10-21'
            images=np.load(cache/'polar.npy',mmap_mode='r')
            with np.load(cache/'valid.npz') as z:valid=z['polar']
            quality=torch.from_numpy(reliability(images)); features=[]
            for start in range(0,len(images),32):
                x=torch.from_numpy(np.asarray(images[start:start+32]).transpose(0,3,1,2).copy()).to(device).float()/255
                with torch.inference_mode(): features.append(nn.functional.normalize(extractor((x-mean)/std)-background,dim=1).cpu())
            features=torch.cat(features); prototypes=[]; gallery_quality=[]; failed=[]
            for j,eye in enumerate(ids):
                gi=[i for i,r in enumerate(rows) if r.session==1 and identity(r)==eye and valid[i]]
                if gi:
                    prototypes.append(nn.functional.normalize(features[gi].mean(0),dim=0)); gallery_quality.append(quality[gi].mean(0))
                else:
                    prototypes.append(torch.zeros_like(features[0])); gallery_quality.append(torch.zeros_like(quality[0])); failed.append(j)
            gallery=torch.stack(prototypes).to(device); gquality=torch.stack(gallery_quality).to(device)
            folder=ROOT/'outputs'/f'confirmacao_congelada_val{suffix}{tag}_2026-10-21'
            originals[condition]=[read(folder/f'scores_{name}.npz') for name in ORDER]
            data[condition]={}
            for mode in ('uniform','weighted'):
                scores=[]
                for start in range(0,len(qi),32):
                    ii=qi[start:start+32]
                    with torch.inference_mode():
                        value=spatial_scores(features[ii].to(device),gallery,0) if mode=='uniform' else weighted_scores(features[ii].to(device),gallery,quality[ii].to(device),gquality)
                    scores.append(value.cpu().numpy())
                scores=np.concatenate(scores).astype(np.float64); scores[:,failed]=-2
                scores,labels,_=subset(scores,rows,ids); qvalid=valid[qi]&(scores>-2).any(1)
                c=dict(scores=scores,labels=labels,valid=qvalid); data[condition][mode]=c
                np.testing.assert_array_equal(labels,originals[condition][2]['labels'])
                if mode=='uniform':
                    error=float(np.max(np.abs(scores-originals[condition][2]['scores'])))
                    np.testing.assert_allclose(scores,originals[condition][2]['scores'],atol=2e-6,rtol=0)
                    np.testing.assert_array_equal(qvalid,originals[condition][2]['valid'])
                    audits.append(dict(branch=branch,condition=condition,uniform_max_difference=error))
            print(f'Extracted {branch}/{condition}; control verified',flush=True)
        for mode in ('uniform','weighted'):
            for kind in ('standalone','fusion'):
                grouped={}; parameters=None
                if kind=='fusion':
                    components=list(originals['clean']); components[2]=data['clean'][mode]; parameters=calibrate(components)
                for condition in conditions:
                    c=data[condition][mode]
                    if kind=='fusion':
                        components=list(originals[condition]); components[2]=c
                        scores,valid=fuse(components,parameters); c=dict(scores=scores,valid=valid,labels=c['labels'])
                    grouped[condition]=c
                clean=grouped['clean']; imp=np.ones_like(clean['scores'],bool); imp[np.arange(482),clean['labels']]=False
                threshold=operating_threshold(clean['scores'][imp&clean['valid'][:,None]&(clean['scores']>-2)])
                for condition,c in grouped.items():
                    measured,correct,accepted=metrics(c['scores'],c['labels'],threshold,c['valid'])
                    measured.update(branch=branch,mode=mode,kind=kind,condition=condition,threshold=threshold,joint_success=float((correct&accepted).mean()))
                    results.append(measured)
                    np.savez_compressed(out/f'scores_{branch}_{mode}_{kind}_{condition}.npz',**c,correct=correct,accepted=accepted)
                (out/f'parameters_{branch}_{mode}_{kind}.json').write_text(json.dumps(dict(threshold=threshold,parameters=parameters),indent=2),encoding='utf-8')
    final=dict(status='local_texture_validation_completed',results=results,audits=audits,source_sha256=source_hashes,test_inference=False,frozen_candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8'); print(json.dumps(results,indent=2),flush=True)


if __name__=='__main__':main()

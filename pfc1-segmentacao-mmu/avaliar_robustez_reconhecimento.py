"""Ensaio pareado UBIPr: identidade ocular, galeria fixa e perturbacoes nas consultas.

Nao simula diagnosticos. Niveis e metricas sao fixados antes da inferencia de teste.
Cache por condicao permite retomar sem reduzir a populacao experimental.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
import torch

from avaliar_dinov3_ubipr import MODEL_ID, masked_crop
from transformers import AutoImageProcessor, AutoModel
from treinar_segmentacao_ubipr import Sample, MulticlassUNet, decode_mask

ROOT = Path(__file__).resolve().parent
BRANCHES = ('inteira', 'iris_referencia', 'iris_unet')
CONDITIONS = [('original', 0)] + [(kind, level) for kind, levels in (
    ('oclusao_superior', (20, 40, 60)), ('oclusao_inferior', (20, 40, 60)),
    ('desfoque_iris', (1, 3, 5)), ('contraste_iris', (25, 50, 75))) for level in levels]


def identity(row):
    return f'{row.subject}_{row.side}'


def perturb(image, mask, kind, level):
    """Oclusao restrita a iris anotada; desfoque sigma em % da largura da iris.

    Contraste: mistura com cinza 128, alpha=level/100 dentro da referencia.
    Nenhum pixel periocular e modificado. Referencia original permanece fixa.
    """
    arr = np.asarray(image).copy()
    ys, xs = np.where(mask)
    meta = {'affected_fraction': 0., 'sigma_pixels': 0.}
    if kind == 'original' or len(xs) == 0:
        return image.copy(), meta
    if kind.startswith('oclusao'):
        # Exact pixel count, deterministic row-major boundary, no oversized black band.
        order = np.lexsort((xs, ys if kind.endswith('superior') else -ys))
        n = round(len(xs) * level / 100)
        take = order[:n]
        arr[ys[take], xs[take]] = 128
        meta['affected_fraction'] = n / len(xs)
    elif kind == 'desfoque_iris':
        sigma = float(max(0.1, (xs.max() - xs.min() + 1) * level / 100))
        blurred = np.asarray(image.filter(ImageFilter.GaussianBlur(sigma)))
        arr[mask] = blurred[mask]
        meta.update(affected_fraction=1., sigma_pixels=float(sigma))
    elif kind == 'contraste_iris':
        alpha = level / 100
        arr[mask] = np.rint((1 - alpha) * arr[mask].astype(float) + alpha * 128).astype(np.uint8)
        meta['affected_fraction'] = 1.
    else:
        raise ValueError(kind)
    return Image.fromarray(arr), meta


def quality(image, mask):
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return {'iris_pixels': 0, 'occupancy': None, 'sharpness': None, 'contrast': None}
    x0, x1, y0, y1 = xs.min(), xs.max()+1, ys.min(), ys.max()+1
    # Resize common ROI before gradients; exclude mask boundary from sharpness.
    gray = np.asarray(image.convert('L').crop((x0,y0,x1,y1)).resize((128,128)), dtype=float)
    region = np.asarray(Image.fromarray(mask[y0:y1,x0:x1]).resize((128,128), Image.Resampling.NEAREST))
    core = region[1:-1,1:-1] & region[:-2,1:-1] & region[2:,1:-1] & region[1:-1,:-2] & region[1:-1,2:]
    lap = gray[:-2,1:-1]+gray[2:,1:-1]+gray[1:-1,:-2]+gray[1:-1,2:]-4*gray[1:-1,1:-1]
    return {'iris_pixels': int(len(xs)), 'occupancy': float(mask.mean()),
            'sharpness': float(lap[core].var()) if core.any() else 0.,
            'contrast': float(np.asarray(image.convert('L'))[mask].std())}


def operating_threshold(impostor, target=.01):
    """Smallest observed/nextafter threshold with empirical FMR <= target (ties safe)."""
    values = np.sort(np.asarray(impostor, dtype=np.float64))
    candidates = np.unique(np.r_[values, np.nextafter(values, np.inf)])
    rates = (len(values)-np.searchsorted(values, candidates, side='left')) / len(values)
    return float(candidates[np.flatnonzero(rates <= target)[0]])


def metrics(scores, labels, threshold, valid):
    # NumPy weak-scalar promotion otherwise rounds nextafter(float64) back to float32.
    scores = np.asarray(scores, dtype=np.float64)
    n = len(labels)
    genuine = scores[np.arange(n), labels]
    mask = np.ones_like(scores, dtype=bool); mask[np.arange(n), labels] = False
    # Failed extraction is an explicit rejection. Finite floor keeps descriptive ROC computable.
    effective = scores.copy(); effective[~valid] = -2.
    g = effective[np.arange(n), labels]; imp = effective[mask]
    ts = np.unique(np.r_[g,imp,np.nextafter(np.max(effective),np.inf)])
    fmr = (len(imp)-np.searchsorted(np.sort(imp),ts,side='left'))/len(imp)
    fnmr = np.searchsorted(np.sort(g),ts,side='left')/len(g)
    pos = np.argmin(np.abs(fmr-fnmr))
    correct = (scores.argmax(1)==labels) & valid
    accepted = (genuine >= threshold) & valid
    impostor_accept = ((scores >= threshold) & valid[:,None])[mask]
    wrong = scores.copy(); wrong[np.arange(n),labels] = -np.inf
    return {'rank1': float(correct.mean()), 'tar':float(accepted.mean()),
            'fnmr':float(1-accepted.mean()), 'far':float(impostor_accept.mean()),
            'eer_descriptive':float((fmr[pos]+fnmr[pos])/2),
            'extraction_failures':int((~valid).sum()), 'queries':n,
            'genuine_mean_valid':float(genuine[valid].mean()) if valid.any() else None,
            'margin_mean_valid':float((genuine-wrong.max(1))[valid].mean()) if valid.any() else None}, correct, accepted


def paired_ci(base, altered, subjects, reps=5000):
    """Cluster bootstrap of query people, fixed enrolled gallery; positive means loss."""
    unique = np.unique(subjects)
    counts = np.array([(subjects==s).sum() for s in unique])
    sums = np.array([(base.astype(float)-altered.astype(float))[subjects==s].sum() for s in unique])
    draws = np.random.default_rng(20261001).integers(0,len(unique),(reps,len(unique)))
    losses = 100*sums[draws].sum(1)/counts[draws].sum(1)
    return [float(v) for v in np.quantile(losses,[.025,.975])]


def write_csv(path, rows):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def load_splits(manifest):
    splits={}
    for split in ('val','test'):
        rows=[]
        for r in manifest[split]:
            r=r.copy()
            for field in ('image','mask'):
                # Relocatable manifest: basename is authoritative after paired existence check.
                r[field]=str(ROOT/'data/ubipr/single_eye'/Path(r[field]).name)
                if not Path(r[field]).is_file(): raise FileNotFoundError(r[field])
            rows.append(Sample(**r))
        eligible={identity(r) for r in rows if r.session==1}&{identity(r) for r in rows if r.session==2}
        splits[split]=[r for r in rows if identity(r) in eligible]
    assert not {r.subject for r in splits['val']}&{r.subject for r in splits['test']}
    return splits


class Extractor:
    def __init__(self, cnn, batch):
        self.device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.batch=batch
        self.unet=MulticlassUNet(8).to(self.device).eval()
        self.unet.load_state_dict(torch.load(cnn/'melhor_modelo.pt',map_location=self.device,weights_only=True)['model'])
        self.processor=AutoImageProcessor.from_pretrained(MODEL_ID,local_files_only=True)
        self.model=AutoModel.from_pretrained(MODEL_ID,local_files_only=True,
            dtype=torch.bfloat16 if self.device.type=='cuda' else torch.float32).to(self.device).eval()

    def extract(self, rows, kind, level, dest):
        if dest.exists():
            print(f'Cache {dest.name}',flush=True)
            with np.load(dest) as z: return {k:z[k] for k in z.files}
        vectors={b:[] for b in BRANCHES}; validity={b:[] for b in BRANCHES}
        pending=[]; branches=[]; metadata=[]
        def flush():
            if not pending: return
            inputs=self.processor(images=pending,return_tensors='pt').to(self.device)
            with torch.inference_mode(),torch.autocast(device_type=self.device.type,dtype=torch.bfloat16,enabled=self.device.type=='cuda'):
                result=self.model(**inputs)
                features=result.pooler_output if result.pooler_output is not None else result.last_hidden_state[:,0]
            features=torch.nn.functional.normalize(features.float(),dim=1).cpu().numpy()
            if not np.isfinite(features).all(): raise FloatingPointError('Nonfinite embedding')
            for b,v in zip(branches,features): vectors[b].append(v)
            pending.clear(); branches.clear()
        start=time.time()
        for i,r in enumerate(rows):
            with Image.open(r.image) as im: original=im.convert('RGB')
            with Image.open(r.mask) as im: ref=decode_mask(im)==1
            altered,meta=perturb(original,ref,kind,level)
            small=np.asarray(altered.resize((320,240),Image.Resampling.BILINEAR),dtype=np.float32)/255
            tensor=torch.from_numpy(small.transpose(2,0,1).copy())[None].to(self.device)
            with torch.inference_mode(): pred=self.unet(tensor).argmax(1)[0].cpu().numpy()==1
            pred=np.asarray(Image.fromarray(pred).resize(original.size,Image.Resampling.NEAREST),dtype=bool)
            variants=(altered,masked_crop(altered,ref),masked_crop(altered,pred))
            for b,im,valid in zip(BRANCHES,variants,(True,ref.any(),pred.any())):
                pending.append(im); branches.append(b); validity[b].append(bool(valid))
                if len(pending)>=self.batch: flush()
            metadata.append(meta)
            if (i+1)%50==0: print(f'{dest.stem}: {i+1}/{len(rows)}, {time.time()-start:.0f}s',flush=True)
        flush()
        result={b:np.stack(vectors[b]) for b in BRANCHES}
        result.update({b+'_valid':np.array(validity[b]) for b in BRANCHES})
        result['coverage']=np.array([m['affected_fraction'] for m in metadata])
        np.savez_compressed(dest,**result)
        return result


def make_gallery(embeddings, valid, rows):
    ids=sorted({identity(r) for r in rows if r.session==1})
    gallery=[]; failed=[]
    for ident in ids:
        ix=[i for i,r in enumerate(rows) if identity(r)==ident and r.session==1 and valid[i]]
        if ix:
            v=embeddings[ix].mean(0); gallery.append(v/max(np.linalg.norm(v),1e-12))
        else:
            gallery.append(np.zeros(embeddings.shape[1])); failed.append(ident)
    return np.stack(gallery),ids,failed


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'outputs/robustez_reconhecimento_2026-10-01')
    parser.add_argument('--batch-size',type=int,default=6)
    args=parser.parse_args(); out=args.output_dir; out.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(4); torch.manual_seed(42)
    cnn=ROOT/'outputs/cnn/ubipr_multiclasse_30ep_batch32'
    manifest_bytes=(cnn/'manifesto.json').read_bytes()
    manifest=json.loads(manifest_bytes); splits=load_splits(manifest)
    # Audit exact duplicates across sessions/splits prior to measurement.
    seen={}; duplicates=[]; records=[]
    for split,rows in splits.items():
        for r in rows:
            digest=hashlib.sha256(Path(r.image).read_bytes()).hexdigest()
            if digest in seen: duplicates.append([seen[digest],r.image])
            seen[digest]=r.image
            with Image.open(r.image) as im: im=im.convert('RGB')
            with Image.open(r.mask) as m: mask=decode_mask(m)==1
            records.append({'split':split,**asdict(r),'sha256':digest,**quality(im,mask)})
    if duplicates: raise ValueError(f'Exact duplicates require audit: {duplicates[:3]}')
    config={'model':MODEL_ID,'conditions':CONDITIONS,'branches':BRANCHES,'seed':42,
       'identity':'subject+side','gallery':'session1 centroid','probe':'session2',
       'threshold':'validation original, empirical FAR <= 1%, ties rejected conservatively',
       'bootstrap':'5000 query-person cluster replicates; fixed gallery; percentile 95% CI',
       'manifest_sha256':hashlib.sha256(manifest_bytes).hexdigest(),
       'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
       'counts':{k:{'images':len(v),'people':len({r.subject for r in v}),'eyes':len({identity(r) for r in v}),
          'queries':sum(r.session==2 for r in v)} for k,v in splits.items()},
       'exact_duplicates':len(duplicates),'torch':torch.__version__,
       'clinical_labels':False,'development_subsample':False}
    config_path=out/'protocolo.json'
    if config_path.exists():
        old=json.loads(config_path.read_text(encoding='utf-8'))
        if old['script_sha256']!=config['script_sha256']: raise ValueError('Code changed: choose new output directory to avoid stale cache')
    config_path.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    write_csv(out/'manifesto_auditado.csv',records)
    print(json.dumps(config['counts']),flush=True)
    extractor=Extractor(cnn,args.batch_size)
    cache={k:extractor.extract(v,'original',0,out/f'embeddings_{k}_original.npz') for k,v in splits.items()}
    calibration={}; galleries={}; baseline={}; summaries=[]; per_query=[]; natural=[]
    queries=[r for r in splits['test'] if r.session==2]
    subjects=np.array([r.subject for r in queries]); labels=None
    for b in BRANCHES:
        val=cache['val']; vrows=splits['val']
        vg,vids,vfailed=make_gallery(val[b],val[b+'_valid'],vrows)
        vi=[i for i,r in enumerate(vrows) if r.session==2]
        vl=np.array([vids.index(identity(vrows[i])) for i in vi]); vs=val[b][vi]@vg.T
        valid=val[b+'_valid'][vi]; mask=np.ones_like(vs,dtype=bool); mask[np.arange(len(vi)),vl]=False
        thresh=operating_threshold(vs[mask & valid[:,None]])
        vm,_,_=metrics(vs,vl,thresh,valid)
        calibration[b]={'threshold':thresh,'validation':vm,'failed_enrollments':vfailed}
        test=cache['test']; rows=splits['test']; gallery,ids,failed=make_gallery(test[b],test[b+'_valid'],rows)
        if failed or vfailed: raise ValueError('Enrollment failure requires explicit gallery handling')
        galleries[b]=gallery
        qi=[i for i,r in enumerate(rows) if r.session==2]; labels=np.array([ids.index(identity(r)) for r in queries])
        scores=test[b][qi]@gallery.T
        mm,correct,accept=metrics(scores,labels,thresh,test[b+'_valid'][qi])
        baseline[b]=(mm,correct,accept)
        summaries.append({'branch':b,'condition':'original','level':0,**mm,'loss_rank1_pp':0.,'ci_low_pp':0.,'ci_high_pp':0.,'loss_tar_pp':0.,'tar_ci_low_pp':0.,'tar_ci_high_pp':0.,'coverage_mean':0.})
        np.savez_compressed(out/f'scores_{b}_original.npz',scores=scores,labels=labels,valid=test[b+'_valid'][qi])
        # Quality thresholds use validation only; original-image stratification is observational.
        val_rec=[r for r in records if r['split']=='val' and r['session']==2]
        test_rec=[r for r in records if r['split']=='test' and r['session']==2]
        for feature in ('sharpness','contrast','occupancy'):
            vals=np.array([r[feature] for r in val_rec if r[feature] is not None])
            edges=np.quantile(vals,[1/3,2/3])
            for group in range(3):
                selected=np.array([r[feature] is not None and np.searchsorted(edges,r[feature],side='right')==group for r in test_rec])
                natural.append({'branch':b,'feature':feature,'group':('baixo','medio','alto')[group],
                    'validation_cut1':float(edges[0]),'validation_cut2':float(edges[1]),'queries':int(selected.sum()),
                    'people':len(set(subjects[selected])), 'rank1':float(correct[selected].mean()) if selected.any() else None,
                    'tar':float(accept[selected].mean()) if selected.any() else None})
        for i,r in enumerate(queries):
            per_query.append({'branch':b,'condition':'original','level':0,'subject':r.subject,'side':r.side,'image':Path(r.image).name,
                'correct':int(correct[i]),'accepted':int(accept[i]),'valid':bool(test[b+'_valid'][qi][i]),'genuine_score':float(scores[i,labels[i]])})
    (out/'calibracao.json').write_text(json.dumps(calibration,indent=2),encoding='utf-8')
    write_csv(out/'qualidade_natural.csv',natural)
    write_csv(out/'resumo.csv',summaries)
    for kind,level in CONDITIONS[1:]:
        altered=extractor.extract(queries,kind,level,out/f'embeddings_test_{kind}_{level}.npz')
        for b in BRANCHES:
            scores=altered[b]@galleries[b].T
            mm,correct,accept=metrics(scores,labels,calibration[b]['threshold'],altered[b+'_valid'])
            bm,bc,ba=baseline[b]; ci=paired_ci(bc,correct,subjects); tci=paired_ci(ba,accept,subjects)
            summaries.append({'branch':b,'condition':kind,'level':level,**mm,
                'loss_rank1_pp':100*(bm['rank1']-mm['rank1']),'ci_low_pp':ci[0],'ci_high_pp':ci[1],
                'loss_tar_pp':100*(bm['tar']-mm['tar']),'tar_ci_low_pp':tci[0],'tar_ci_high_pp':tci[1],
                'coverage_mean':float(altered['coverage'].mean())})
            np.savez_compressed(out/f'scores_{b}_{kind}_{level}.npz',scores=scores,labels=labels,valid=altered[b+'_valid'])
            for i,r in enumerate(queries):
                per_query.append({'branch':b,'condition':kind,'level':level,'subject':r.subject,'side':r.side,'image':Path(r.image).name,
                    'correct':int(correct[i]),'accepted':int(accept[i]),'valid':bool(altered[b+'_valid'][i]),'genuine_score':float(scores[i,labels[i]])})
        write_csv(out/'resumo.csv',summaries); write_csv(out/'consultas.csv',per_query)
        print('RESULTADO '+json.dumps(summaries[-3:]),flush=True)
    (out/'CONCLUIDO.json').write_text(json.dumps({'conditions':len(CONDITIONS),'rows':len(summaries),'queries':len(queries)},indent=2),encoding='utf-8')
    print('CONCLUIDO',flush=True)


if __name__=='__main__': main()

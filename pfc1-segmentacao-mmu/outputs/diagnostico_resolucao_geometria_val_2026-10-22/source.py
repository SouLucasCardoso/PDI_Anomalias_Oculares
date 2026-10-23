"""Associacoes descritivas no reconhecimento congelado; validacao apenas."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,hashlib,json,tempfile
import numpy as np
from PIL import Image
import torch
ROOT=Path(__file__).resolve().parent


def shortside(mask):
    y,x=np.where(mask)
    return int(min(x.max()-x.min()+1,y.max()-y.min()+1)) if len(x) else None


def dice_reference(predicted,reference):
    # Empty annotations stay undefined rather than becoming perfect segmentations.
    if not reference.any():return None
    return float(2*(predicted&reference).sum()/(predicted.sum()+reference.sum()))


def bin_label(value,edges):
    if value is None:return 'undefined'
    for low,high in zip(edges[:-1],edges[1:]):
        if low<=value<high:return f'[{low},{high})'
    raise ValueError('Value outside registered bins')


def main():
    from treinar_segmentacao_ubipr import MulticlassUNet,decode_mask
    from avaliar_dinov3_ubipr import masked_crop
    from textura_polar import prepare_texture
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'outputs');a=p.parse_args()
    out=a.output_root/'diagnostico_resolucao_geometria_val_2026-10-22';out.mkdir(parents=True,exist_ok=False)
    checkpoint=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt';sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    assert sha(checkpoint)=='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
    protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Descriptive reused validation only, frozen recognition decisions and threshold. No new test inference, filtering, model selection or threshold fitting.',
        measures='Original-resolution predicted/reference visible-iris bbox short side; original-resolution iris Dice versus annotation, undefined for empty annotation; polar support fraction and pupil hole/fallback source. These are proxies, NOT anatomical iris diameter, clinical extent or quality standards.',
        bins=dict(native_shortside=[0,64,96,128,'infinity'],dice=[0,.8,.9,.95,1.000001],polar_support=[0,.5,.75,.9,1.000001]),
        analysis='Partition ALL482 queries by each registered diagnostic, retain undefined/failures. Report clean Rank1/TAR, upper/lower10% Rank1, and clean-to-occluded transitions. No optimal cutoff search, causal inference, population guarantees or minimum-area claim.',
        illustration='First2 clean errors and first2 clean successes by filename, distinct subjects within each group; no score/Dice/quality selection. Original photo, actual masked RGB crop, actual polar texture. Examples not prevalence estimates.',
        script_sha256=sha(Path(__file__)),segmenter_sha256=sha(checkpoint))
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';manifest=json.loads(manifest_file.read_text());raw=manifest['val'];key=lambda r:f"{r['subject']}_{r['side']}"
    eligible={key(r) for r in raw if r['session']==1}&{key(r) for r in raw if r['session']==2};rows=[r for r in raw if key(r) in eligible];qi=[i for i,r in enumerate(rows) if r['session']==2];assert len(qi)==482
    classes=sorted({r['subject'] for r in rows});labels=np.array([classes.index(rows[i]['subject']) for i in qi]);decisions={};source_hashes={str(manifest_file):sha(manifest_file)}
    for condition,suffix in [('clean',''),('upper10','_oclusao_superior_10'),('lower10','_oclusao_inferior_10')]:
        file=ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21/scores_finais.npz';source_hashes[str(file)]=sha(file)
        with np.load(file) as z:
            np.testing.assert_array_equal(z['labels'],labels);np.testing.assert_array_equal(z['correct'],z['valid']&(z['scores'].argmax(1)==labels));decisions[condition]={k:z[k] for k in ('correct','accepted','valid')}
    selected=[]
    for correct in [False,True]:
        people=set()
        for j in sorted(range(482),key=lambda j:Path(rows[qi[j]]['image']).name):
            r=rows[qi[j]]
            if decisions['clean']['correct'][j]==correct and r['subject'] not in people:
                selected.append(j);people.add(r['subject'])
                if len(people)==2:break
    cache=Path(tempfile.gettempdir())/'cache_confirmacao_val_2026-10-21';images=np.load(cache/'rgb.npy',mmap_mode='r');polars=np.load(cache/'polar.npy',mmap_mode='r')
    with np.load(cache/'valid.npz') as z:rv=z['rgb'];pv=z['polar']
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');model=MulticlassUNet(8).to(device).eval();model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True)['model'])
    records=[];illustrations={}
    for start in range(0,482,32):
        batch=[]
        for i in qi[start:start+32]:
            with Image.open(ROOT/'data/ubipr/single_eye'/Path(rows[i]['image']).name) as im:batch.append(im.convert('RGB'))
        x=torch.from_numpy(np.stack([np.asarray(im.resize((320,240),Image.Resampling.BILINEAR),np.float32)/255 for im in batch]).transpose(0,3,1,2).copy()).to(device)
        with torch.inference_mode():masks=model(x).argmax(1).cpu().numpy()==1
        for offset,(im,small) in enumerate(zip(batch,masks)):
            j=start+offset;i=qi[j];r=rows[i];pred=np.asarray(Image.fromarray(small).resize(im.size,Image.Resampling.NEAREST),bool)
            with Image.open(ROOT/'data/ubipr/single_eye'/Path(r['mask']).name) as annotation:reference=decode_mask(annotation)==1
            assert reference.shape==pred.shape;assert bool(pred.any())==bool(rv[i])
            crop=np.asarray(masked_crop(im,pred).resize((128,128),Image.Resampling.BILINEAR));np.testing.assert_array_equal(crop,images[i])
            geometry=None;polar=np.full((64,512,3),127,np.uint8)
            try:polar,geometry=prepare_texture(np.asarray(im),pred)
            except ValueError:pass
            assert (geometry is not None)==bool(pv[i]);np.testing.assert_array_equal(polar,polars[i])
            record=dict(image=Path(r['image']).name,subject=r['subject'],side=r['side'],correct=bool(decisions['clean']['correct'][j]),accepted=bool(decisions['clean']['accepted'][j]),valid=bool(decisions['clean']['valid'][j]),
                predicted_bbox_shortside=shortside(pred),reference_visible_bbox_shortside=shortside(reference),reference_pixels=int(reference.sum()),predicted_pixels=int(pred.sum()),iris_dice=dice_reference(pred,reference),
                polar_support=geometry['polar_mask_fraction'] if geometry else None,pupil_source=geometry['pupil_source'] if geometry else 'undefined')
            for condition in ['upper10','lower10']:
                altered=bool(decisions[condition]['correct'][j]);record[condition+'_correct']=altered;record[condition+'_lost']=record['correct'] and not altered;record[condition+'_recovered']=not record['correct'] and altered
            records.append(record)
            if j in selected:illustrations[j]=(np.asarray(im),crop,polar)
    with (out/'consultas.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    specifications={
        'predicted_bbox_shortside':[0,64,96,128,float('inf')],
        'reference_visible_bbox_shortside':[0,64,96,128,float('inf')],
        'iris_dice':[0,.8,.9,.95,1.000001],
        'polar_support':[0,.5,.75,.9,1.000001],
        'pupil_source':None}
    grouped=[]
    for field,edges in specifications.items():
        assignments=[bin_label(r[field],edges) if edges else r[field] for r in records]
        for group in sorted(set(assignments)):
            subset=[r for r,g in zip(records,assignments) if g==group];n=len(subset)
            row=dict(measure=field,group=group,queries=n,people=len({r['subject'] for r in subset}),clean_correct=sum(r['correct'] for r in subset),clean_accepted=sum(r['accepted'] for r in subset),failures=sum(not r['valid'] for r in subset))
            row.update(clean_rank1=row['clean_correct']/n,clean_tar=row['clean_accepted']/n)
            for condition in ['upper10','lower10']:
                row[condition+'_rank1']=sum(r[condition+'_correct'] for r in subset)/n;row[condition+'_lost_correct']=sum(r[condition+'_lost'] for r in subset);row[condition+'_recovered']=sum(r[condition+'_recovered'] for r in subset)
            grouped.append(row)
        assert sum(g['queries'] for g in grouped if g['measure']==field)==482
    with (out/'grupos.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(grouped[0]));writer.writeheader();writer.writerows(grouped)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(len(selected),3,figsize=(14,3*len(selected)),squeeze=False)
    for line,j in enumerate(selected):
        r=records[j]
        for col,(title,array) in enumerate(zip(['Foto original','Recorte RGB usado pelo modelo','Textura polar usada pelo modelo'],illustrations[j])):
            axes[line,col].imshow(array);axes[line,col].axis('off');axes[line,col].set_title(title,fontsize=10)
        axes[line,0].set_ylabel(r['image'],fontsize=8)
        dice='indefinido' if r['iris_dice'] is None else f"{r['iris_dice']:.3f}"
        axes[line,0].set_title(f"{r['image']} | {'ACERTO' if r['correct'] else 'ERRO'} | Dice={dice}",fontsize=9)
    fig.suptitle('Diagnostico na validacao: exemplos por ordem de arquivo, sem selecao por qualidade\nNenhuma imagem restaurada ou gerada; redimensionamento apenas para exibicao',fontsize=12)
    fig.tight_layout(rect=(0,0,1,.95));fig.savefig(out/'amostras_recortes_diagnostico.png',dpi=150);plt.close(fig)
    final=dict(status='validation_resolution_geometry_diagnostic_completed',queries=482,recognition_correct=int(decisions['clean']['correct'].sum()),groups=grouped,
        original_inputs_reproduced_exactly=True,reference_undefined=sum(r['iris_dice'] is None for r in records),illustrated_images=[records[j]['image'] for j in selected],
        source_sha256=source_hashes,test_inference=False,frozen_candidate_replaced=False,minimum_area=None,limits='Descriptive associations confounded by subject/session/acquisition and preprocessing; no optimal quality cutoff or deployment filter. Native bbox measures visible segmented support, not anatomical diameter. Group TAR uses frozen global threshold; no stratum FMR calibration or acceptance claim.')
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2))


if __name__=='__main__':main()

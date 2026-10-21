"""QC exploratorio apos diagnostico: suporte polar minimo, sem excluir consultas."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent
OLD=ROOT/'outputs/cadastro_multicaptura_val_v2_2026-10-20'
OUT=ROOT/'outputs/suporte_polar_val_2026-10-20'

def main():
    from avaliar_robustez_reconhecimento import load_splits,identity,metrics,operating_threshold
    from comparador_hdbif_lote import aggregate
    OUT.mkdir(exist_ok=True)
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'Post-hoc exploratory development follow-up after multicapture failure; validation only; not independent evidence',
        'purpose':'Reject HDBIF templates with tiny predicted polar support while retaining every query and eye',
        'primary_support_fraction':.10,'sensitivity_support_fraction':.20,
        'modes':['first','max','top3'],'gate':'Total nonzero polar-mask fraction must meet threshold in both query and enrollment; insufficient support score -2; no replacement of failed first photo',
        'calibration':'Each variant recalibrated validation original at empirical FMR<=1%; fixed people/queries; no test scoring',
        'critical_distinction':'10/20% here is a template quality gate after normalization, NOT minimum anatomical iris area or an occlusion result',
        'inputs_sha256':{name:hashlib.sha256((OLD/name).read_bytes()).hexdigest() for name in ['CONCLUIDO.json','scores_hdbif_capturas.npz','auditoria_hdbif.json']},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if (OUT/'protocolo.json').exists():raise ValueError('Preserve previous output')
    (OUT/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    (OUT/'source.py').write_bytes(Path(__file__).read_bytes())
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val']
    ids=sorted({identity(r) for r in rows})
    gallery=sorted([r for r in rows if r.session==1],key=lambda r:(identity(r),Path(r.image).name)); queries=[r for r in rows if r.session==2]; ng=len(gallery)
    groups=[[i for i,r in enumerate(gallery) if identity(r)==eye] for eye in ids]
    labels=np.array([ids.index(identity(r)) for r in queries])
    audits=json.loads((OLD/'auditoria_hdbif.json').read_text()); assert len(audits)==ng+len(queries)
    fractions=np.array([r['polar_valid_fraction'] for r in audits]); basevalid=np.array([r['valid'] for r in audits])
    with np.load(OLD/'scores_hdbif_capturas.npz') as z:raw=z['scores']
    results=[]
    for fraction in (.10,.20):
        gvalid=basevalid[:ng]&(fractions[:ng]>=fraction); qvalid=basevalid[ng:]&(fractions[ng:]>=fraction)
        gated=raw.copy(); gated[:,~gvalid]=-2; gated[~qvalid]=-2
        for mode in protocol['modes']:
            name=f'hdbif_support{int(fraction*100)}_{mode}'; scores=aggregate(gated,groups,mode); valid=qvalid&(scores>-2).any(1)
            imp=np.ones_like(scores,dtype=bool); imp[np.arange(len(labels)),labels]=False; usable=imp&valid[:,None]&(scores>-2)
            threshold=operating_threshold(scores[usable]) if usable.any() else 2.
            result,correct,accepted=metrics(scores,labels,threshold,valid)
            result.update(variant=name,threshold=threshold,joint_success=float((correct&accepted).mean()),rejected_enrollment_images=int((~gvalid).sum()),eyes_without_usable_enrollment=sum(not gvalid[positions].any() for positions in groups))
            results.append(result); np.savez_compressed(OUT/(name+'.npz'),scores=scores,labels=labels,valid=valid,correct=correct,accepted=accepted)
            print(json.dumps(result),flush=True)
    (OUT/'CONCLUIDO.json').write_text(json.dumps({'status':'post_hoc_development_validation_completed','scientific_final_result':False,'results':results},indent=2),encoding='utf-8')

if __name__=='__main__':main()

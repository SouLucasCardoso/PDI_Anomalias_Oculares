"""Duas entradas deterministicas da mesma foto; nao duas fotos de consulta."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent

def main():
    from validar_metrica_intra_classe import measure
    from normalizar_consulta import normalize
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'arciris_duas_vistas_2026-10-21';out.mkdir(parents=True,exist_ok=True)
    if (out/'protocolo.json').exists():raise ValueError('Preserve previous run')
    files=[a.output_root/n/'scores_fusion8.npz' for n in ['arciris_polar_2026-10-21','arciris_red_2026-10-21']]
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'method':'Mean of two pre-normalization fusion logits: identical seven components retained at1/8 each, ArcIris red/CLAHE score z-values averaged into remaining1/8. Fixed equal views of one original photo; no query label selection or weight search.',
              'scope':'Repeated development validation, supplied side16 candidates, all482queries and4 failures; same-side15impostors, FMR<=1%; external pretraining population unknown',
              'source_sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    components=[]
    for f in files:
        with np.load(f) as z:components.append({k:z[k] for k in ['scores','labels','valid']})
    np.testing.assert_array_equal(components[0]['labels'],components[1]['labels']);available=np.logical_and.reduce([c['scores']>-2 for c in components]);valid=np.logical_and.reduce([c['valid'] for c in components])&available.any(1)
    logits=[np.log(np.clip(c['scores'],1e-12,1-1e-12)/np.clip(1-c['scores'],1e-12,1)) for c in components]
    scores=1/(1+np.exp(-np.mean(logits,axis=0)));scores[~available]=-2;results=[]
    for name,s,v in [('equal_views',scores,valid),('equal_views_normalized',*normalize(scores,valid))]:
        data=dict(scores=s,labels=components[0]['labels'],valid=v);r=measure(data);r['variant']=name;results.append(r);np.savez_compressed(out/f'scores_{name}.npz',**data)
    final=dict(status='equal_same_photo_arciris_views_completed',results=results,test_inference=False,minimum_area=None,external_pretraining_overlap_unknown=True,development_90_reached=any(r['rank1']>=.9 and r['tar']>=.9 for r in results))
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)
if __name__=='__main__':main()

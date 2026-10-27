"""Preserva todos os vetores usados no ajuste e monitor, sem duplicar treino ordinario."""
from pathlib import Path
import argparse,json,shutil
import numpy as np
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'transporte_descritor_polar_2026-10-23'
    protocol=json.loads((out/'protocolo.json').read_text());rows=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text())['train'];monitor=set(protocol['monitor_people'])
    with np.load(out/'cache_embeddings.npz') as z:data={k:z[k] for k in z.files}
    positions=np.array([i for i,r in enumerate(rows) if data['changed'][i] or r['subject'] in monitor]);index={int(old):new for new,old in enumerate(positions)}
    changed=data['changed'][positions]
    np.savez_compressed(out/'evidencia_compacta.npz',original_indices=positions,teacher=data['teacher'][positions],student_changed=data['student'][positions][changed],transported_changed=data['transported'][positions][changed],changed=changed,valid=data['valid'][positions],fit_indices=np.array([index[int(i)] for i in data['fit_indices']]),monitor_changed_indices=np.array([index[int(i)] for i in data['monitor_changed_indices']]))
    statistics={}
    for role,key in [('fit','fit_indices'),('monitor','monitor_changed_indices')]:
        i=data[key];target=data['teacher'][i].astype(np.float64)
        statistics[role]=dict(images=len(i),cosine_before=float(np.sum(data['student'][i].astype(np.float64)*target,axis=1).mean()),cosine_after=float(np.sum(data['transported'][i].astype(np.float64)*target,axis=1).mean()))
    (out/'DIAGNOSTICO_AJUSTE.json').write_text(json.dumps(statistics,indent=2),encoding='utf-8')
    if not (out/'VERIFICACAO_COMPLETA.json').exists():shutil.copyfile(out/'VERIFICACAO_RELOAD.json',out/'VERIFICACAO_COMPLETA.json')
    print(json.dumps(dict(retained_images=len(positions),actual_changed=int(changed.sum()),monitor_images=sum(rows[int(i)]['subject'] in monitor for i in positions),statistics=statistics),indent=2))

if __name__=='__main__':main()

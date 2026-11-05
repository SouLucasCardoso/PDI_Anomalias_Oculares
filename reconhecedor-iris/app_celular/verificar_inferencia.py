"""Smoke real em VAL existente; sem misturar com o cadastro do celular."""
import hashlib
import json
import os
from pathlib import Path
import sys
APP_ROOT=Path(__file__).resolve().parents[1]
ROOT=APP_ROOT.parent/'pfc1-segmentacao-mmu'
sys.path.insert(0,str(APP_ROOT))
os.environ.setdefault('HF_HUB_OFFLINE','1')
os.environ.setdefault('TRANSFORMERS_OFFLINE','1')
os.environ.setdefault('HF_HOME',(ROOT/'data/hf-home.txt').read_text(encoding='utf-8-sig').strip())
from app_celular.motor import IrisEngine
import numpy as np


def main():
    out=APP_ROOT/'outputs/verificacao_reorganizacao_2026-11-05';out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text())['val']
    eligible={r['subject'] for r in manifest if r['side']=='L' and r['session']==1} & {r['subject'] for r in manifest if r['side']=='L' and r['session']==2}
    subject=min(eligible)
    rows=[next(r for r in manifest if r['subject']==subject and r['side']=='L' and r['session']==s) for s in (1,2)]
    other=min(eligible-{subject})
    rows.append(next(r for r in manifest if r['subject']==other and r['side']=='L' and r['session']==1))
    engine=IrisEngine();results=[]
    for i,row in enumerate(rows):
        print('IMAGE',i,Path(row['image']).name,flush=True)
        result=engine.analyze(row['image'],out/str(i),lambda stage,message:print(stage,message,flush=True))
        with np.load(out/str(i)/'features.npz',allow_pickle=False) as data:results.append({k:data[k] for k in data.files})
        print('RESULT',json.dumps(result),flush=True)
    groups=[dict(person_id=str(row['subject']),name='Participante VAL '+str(row['subject']),side='L',features=[features])
            for row,features in zip((rows[0],rows[2]),(results[0],results[2]))]
    ranking=engine.identify(results[1],groups)
    assert ranking['candidate_count']==2 and ranking['accepted'] is None
    record=dict(status='completed',scope='Integration smoke only, existing VAL, not phone or accuracy estimate',
        images=[dict(file=Path(r['image']).name,sha256=hashlib.sha256(Path(r['image']).read_bytes()).hexdigest()) for r in rows],
        shapes={k:list(v.shape) for k,v in results[0].items()},matching=ranking,
        expected=str(subject),top1_matches_expected=ranking['ranking'][0]['person_id']==str(subject),provenance=engine.provenance)
    (out/'VERIFICACAO.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('COMPLETED',json.dumps(ranking),flush=True)


if __name__=='__main__':main()

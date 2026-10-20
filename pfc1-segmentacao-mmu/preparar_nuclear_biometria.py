"""Registra dominio ainda nao avaliado: calibracao e teste por paciente."""
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import json
import random

ROOT=Path(__file__).resolve().parent

def main():
    source=ROOT/'data/nuclear/manifesto.json'
    rows=json.loads(source.read_text(encoding='utf-8'))
    groups=defaultdict(list)
    for row in rows: groups[row['patient_id'],row['side']].append(row)
    eligible={eye:rs for eye,rs in groups.items() if len({r['sha256'] for r in rs})>=2}
    people=sorted({eye[0] for eye in eligible}); random.Random(42).shuffle(people)
    calibration=set(people[:round(len(people)*.25)])
    splits={'calibration':[],'test':[]}
    for (person,side),photos in sorted(eligible.items()):
        split='calibration' if person in calibration else 'test'
        photos=sorted(photos,key=lambda r:(r['filename'],r['sha256']))
        for i,row in enumerate(photos):
            splits[split].append(dict(row,role='gallery' if i==0 else 'query'))
    assert not {r['patient_id'] for r in splits['calibration']}&{r['patient_id'] for r in splits['test']}
    if len({r['sha256'] for r in rows})!=len(rows): raise ValueError('Exact duplicate requires review')
    content=json.dumps(splits,ensure_ascii=False,indent=2).encode('utf-8')
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),
        'status':'registered_before_recognition_no_features_or_scores_examined',
        'source':'https://data.mendeley.com/datasets/6wv33nbcvv/2','license':'CC BY 4.0',
        'source_manifest_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'manifest_sha256':hashlib.sha256(content).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'identity':'published patient folder + DER/IZQ eye side',
        'split':'25% patients calibration, remaining test, shuffled seed42; both eyes same group',
        'gallery':'First lexicographic filename per eye; remaining distinct photographs queries',
        'threshold':'Frozen model; empirical FMR<=1% on calibration only, then fixed for test',
        'model_selection':'New ResNet18 angular-margin encoder selected on UBIPr validation only; no Nuclear model selection',
        'segmentation':'Frozen pretrained CVRL mask inference; predicted masks not reference annotations',
        'missing_masks':'Keep failed images and enrollments in denominators, explicit rejection',
        'area_follow_up':'Only after baseline; preserved predicted-mask pixels must be labeled estimated area, not true disease extent',
        'clinical_limitations':['Acquisition dates/sessions unestablished; no longitudinal or disease-progression claims',
            'No established healthy controls; no diagnosis from missing NC grade',
            'Published identities assumed; independence beyond released identifiers unverified',
            'Reference segmentation absent; masks require quality audit',
            'Supplementary grades apply only to matched selected images, not all captures of that eye'],
        'counts':{s:{'images':len(rs),'patients':len({r['patient_id'] for r in rs}),
                     'eyes':len({(r['patient_id'],r['side']) for r in rs}),
                     'queries':sum(r['role']=='query' for r in rs)} for s,rs in splits.items()}}
    out=ROOT/'outputs/nuclear_biometria_protocolo_2026-10-20'; out.mkdir(parents=True,exist_ok=True)
    if (out/'protocolo.json').exists(): raise ValueError('Preserve registration; choose a new version for changes')
    (out/'manifesto.json').write_bytes(content)
    (out/'protocolo.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(protocol['counts'],indent=2))

if __name__=='__main__': main()

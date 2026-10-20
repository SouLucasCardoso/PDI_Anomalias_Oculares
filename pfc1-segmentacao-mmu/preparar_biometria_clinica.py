"""Triagem conservadora de pares longitudinais SLP-VLD, sem inferencia clinica."""
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import hashlib
import json
import random
import re

from auditar_catscreen import records

ROOT=Path(__file__).resolve().parent

def capture_date(path):
    match=re.fullmatch(r'P\d+_(?:OD|OS)(\d{8})(?:\D.*)?',Path(path).stem,re.I)
    if not match: return None
    try: return datetime.strptime(match[1],'%Y%m%d').date().isoformat()
    except ValueError: return None

def main():
    source=ROOT/'data/slpvld/manifesto.json'
    rows=json.loads(source.read_text(encoding='utf-8'))
    workbook=next((ROOT/'data/slpvld/release').rglob('zhaohui_description.xlsx'))
    prefix_ids=defaultdict(set); id_prefixes=defaultdict(set)
    for row in records(workbook.read_bytes()):
        match=re.match(r'^(P\d+)_',Path(row['image_id']).stem,re.I)
        if match and row.get('ID'):
            prefix=match[1].upper(); metadata_id=str(row['ID'])
            prefix_ids[prefix].add(metadata_id); id_prefixes[metadata_id].add(prefix)
    ambiguous={p for p,ids in prefix_ids.items() if len(ids)>1}
    for prefixes in id_prefixes.values():
        if len(prefixes)>1: ambiguous.update(prefixes)
    hashes=defaultdict(list)
    for row in rows: hashes[row['sha256']].append(row)
    bad_hashes={h for h,rs in hashes.items() if len({(r['subject'],r['side']) for r in rs})>1}
    excluded=Counter(); grouped=defaultdict(list); seen=set()
    for row in sorted(rows,key=lambda r:r['image']):
        reason=None
        if row['source_split']!='development': reason='external_not_in_development_protocol'
        elif row['subject'] in ambiguous: reason='ambiguous_identity_metadata'
        elif row['sha256'] in bad_hashes: reason='duplicate_across_eye_identities'
        elif row['sha256'] in seen: reason='exact_duplicate_same_eye'
        date=capture_date(row['image'])
        if reason is None and date is None: reason='date_not_unambiguously_parsed'
        if reason:
            excluded[reason]+=1; continue
        seen.add(row['sha256'])
        grouped[(row['subject'],row['side'])].append(dict(row,capture_date=date))
    eligible={key:rs for key,rs in grouped.items() if len({r['capture_date'] for r in rs})>=2}
    people=sorted({key[0] for key in eligible}); random.Random(42).shuffle(people)
    if len(people)<4: raise ValueError('Pessoas insuficientes para particoes independentes')
    validation=set(people[:max(2,round(len(people)*.25))])
    splits={'val':[],'test':[]}; transitions=Counter()
    for (person,side),rs in sorted(eligible.items()):
        rs.sort(key=lambda r:(r['capture_date'],r['image']))
        first=rs[0]['capture_date']; gallery=[r for r in rs if r['capture_date']==first]
        queries=[r for r in rs if r['capture_date']>first]
        split='val' if person in validation else 'test'
        # Keep all captures on their original date; centroid gallery planned.
        splits[split].extend(dict(r,role='gallery') for r in gallery)
        splits[split].extend(dict(r,role='query') for r in queries)
        for r in queries:
            transitions[f"gallery_binary_{gallery[0]['label_binary']}_query_binary_{r['label_binary']}"]+=1
    counts={s:{'images':len(rs),'people':len({r['subject'] for r in rs}),
               'eyes':len({(r['subject'],r['side']) for r in rs}),
               'gallery':sum(r['role']=='gallery' for r in rs),'queries':sum(r['role']=='query' for r in rs)}
            for s,rs in splits.items()}
    assert not {r['subject'] for r in splits['val']}&{r['subject'] for r in splits['test']}
    out=ROOT/'outputs/biometria_clinica_triagem_2026-10-20'; out.mkdir(parents=True,exist_ok=True)
    content=json.dumps(splits,ensure_ascii=False,indent=2).encode('utf-8')
    report={'status':'eligibility_only_not_recognition_results','seed':42,'counts':counts,
            'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'manifest_sha256':hashlib.sha256(content).hexdigest(),
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'ambiguous_prefixes_excluded':len(ambiguous),'excluded_images':dict(excluded),
            'dated_eyes_without_distinct_dates':len(grouped)-len(eligible),
            'query_binary_transitions':dict(transitions),
            'date_rule':'Strict filename YYYYMMDD, earliest date gallery; strictly later dates queries',
            'split_rule':'Subject-disjoint 25% validation, remaining test, seed42; no clinical training',
            'pending':['Near-duplicate inspection','Visual verification of eye side and mask quality',
                       'Confirm filename dates represent acquisition dates',
                       'Freeze clinical protocol before inference; diagnostic transitions are observational'],
            'nuclear_limitation':'Multiple captures per eye, but no unambiguous dates established; not longitudinal evidence.'}
    destination=out/'protocolo_triagem.json'
    if destination.exists() and json.loads(destination.read_text(encoding='utf-8'))!=report:
        raise ValueError('Protocolo alterado: use nova pasta de saida')
    (out/'manifesto.json').write_bytes(content)
    destination.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()

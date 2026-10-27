"""Inventario de rotulos clinicos locais; nao diagnostica imagens."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True)
    source=ROOT/'data/slpvld/manifesto.json';rows=json.loads(source.read_text(encoding='utf-8'))
    # Explicit iris names are separate from other anterior-segment findings.
    direct=[r for r in rows if any(t in r['diagnosis_raw'].lower() for t in ['iris','irido'])]
    synechiae=[r for r in rows if 'synechia' in r['diagnosis_raw'].lower() and r not in direct]
    def summary(selected):
        return dict(images=len(selected),unique_image_hashes=len({r['sha256'] for r in selected}),files_present=sum(Path(r['image']).is_file() for r in selected),diagnosis_counts=dict(Counter(r['diagnosis_raw'] for r in selected)),source_splits=dict(Counter(r['source_split'] for r in selected)),coded_people=len({r['subject'] for r in selected}),coded_eyes=len({(r['subject'],r['side']) for r in selected}))
    report=dict(date='2026-10-27',method='Literal clinical labels in existing SLP-VLD manifesto, NOT image diagnosis. Direct: iris or irido substring. Other synechiae reported separately. Not exhaustive taxonomy or clinical confirmation.',manifest_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),slpvld_total=summary(rows),explicit_iris_labels=summary(direct),other_synechiae_labels=summary(synechiae),limitations=['No pixelwise mask quantifying anatomical iris loss.','Coded people/eyes not clinically validated independent identities.','No inference of absence of disease from absence of a matching label.','Clinical impact on recognition not established by counts.'],examples=[dict(filename=Path(r['image']).name,diagnosis_raw=r['diagnosis_raw'],sha256=r['sha256'],file_present=Path(r['image']).is_file(),source_split=r['source_split']) for r in direct+synechiae],other_datasets={})
    for name in ['slid','catscreen','nuclear']:
        f=ROOT/'data'/name/'auditoria.json';audit=json.loads(f.read_text(encoding='utf-8'))
        if name=='slid':report['other_datasets'][name]={k:audit[k] for k in ['images','with_annotated_lesion','normal_no_annotated_lesion','labels_per_image','patient_ids_in_release','iris_reference_in_release']}
        elif name=='nuclear':report['other_datasets'][name]={k:audit[k] for k in ['images','patients','matched_labeled_images','matched_patients','warning']}
        else:
            counts=Counter()
            for k in ['train','val','test']:counts.update(audit['tables'][k]['diagnosis_counts_raw'])
            report['other_datasets'][name]=dict(release=audit['release'],clean_diagnoses=dict(counts),clean_images=sum(counts.values()))
    (a.output_dir/'INVENTARIO_ANOMALIAS.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps({k:report[k] for k in ['explicit_iris_labels','other_synechiae_labels']},ensure_ascii=False))

if __name__=='__main__':main()

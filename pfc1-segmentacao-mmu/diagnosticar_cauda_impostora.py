"""Resume erros ja calculados, sem treinar, recalibrar ou abrir validacao/teste."""
from pathlib import Path
import argparse,json,math
import numpy as np
from treinar_adaptador_polar_fmr import NAME

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/NAME;report={}
    for name in ['adaptador_polar_original_2026-10-23','adaptador_polar_top3_2026-10-23',NAME]:
        folder=a.output_root/name;done=json.loads((folder/'CONCLUIDO.json').read_text());group=done['selected_monitor'];rows=json.loads((folder/'rows.json').read_text());people=set(json.loads((folder/'protocolo.json').read_text())['monitor_people']);queries=[r for r in rows if r['subject'] in people and r['session']==2];assert len(queries)==480
        report[name]={}
        for tag,r in group.items():
            with np.load(folder/f'scores_selected_{tag}.npz') as z:
                scores=z['scores'];labels=z['labels'];valid=z['valid'];correct=z['correct'];accepted=z['accepted']
            mask=np.ones_like(scores,bool);mask[np.arange(480),labels]=False;fp=(scores>=r['threshold'])&valid[:,None]&mask;counts=fp.sum(1);total=int(counts.sum());assert total/7200==r['far'];assert int(correct.sum())==r['correct']
            order=np.argsort(-counts,kind='stable');cumulative=np.cumsum(counts[order]);n80=int(np.searchsorted(cumulative,.8*total)+1) if total else 0
            summary=dict(false_acceptances=total,maximum_allowed_at_one_percent=72,excess=max(0,total-72),queries_with_any_false_acceptance=int((counts>0).sum()),queries_accounting_for_80_percent=n80,false_acceptances_on_correctly_identified_queries=int(counts[correct].sum()),false_acceptances_on_genuine_rejected_queries=int(counts[~accepted].sum()),top_queries=[dict(image=queries[i]['image'],subject=queries[i]['subject'],side=queries[i]['side'],false_acceptances=int(counts[i]),correct=bool(correct[i]),genuine_accepted=bool(accepted[i])) for i in order[:10] if counts[i]>0])
            report[name][tag]=summary
    result=dict(status='saved_monitor_false_acceptances_described',scope='Reused originalTRAINmonitor ONLY; thresholds unchanged, no diagnosis-based promotion or filtering. Descriptive concentration, not causal evidence.',methods=report,new_inference=False)
    (out/'DIAGNOSTICO_IMPOSTORES.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({n:{t:{k:v for k,v in r.items() if k!='top_queries'} for t,r in group.items()} for n,group in report.items()},indent=2))
if __name__=='__main__':main()

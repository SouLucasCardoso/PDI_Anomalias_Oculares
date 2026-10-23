"""Confere populacao, limiar, cadastro fixo e orcamento de pixels nas oclusoes."""
from pathlib import Path
import argparse,hashlib,json,math
import numpy as np
ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_robustez_reconhecimento import load_splits,metrics,paired_ci
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'auditoria_oclusao_congelada_2026-10-21';out.mkdir(parents=True,exist_ok=False)
    refined=json.loads((a.output_root/'refinamento_oclusao_congelada_2026-10-21/CONCLUIDO.json').read_text());coarse=json.loads((a.output_root/'curva_oclusao_congelada_2026-10-21/CONCLUIDO.json').read_text())
    source=a.output_root/'confirmacao_congelada_test_2026-10-21';baseline=json.loads((source/'CONCLUIDO.json').read_text());threshold=baseline['result']['threshold']
    with np.load(source/'scores_finais.npz') as z:b={k:z[k] for k in z.files}
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['test'];subjects=np.array([r.subject for r in rows if r.session==2]);gi=np.array([i for i,r in enumerate(rows) if r.session==1]);qi=np.array([i for i,r in enumerate(rows) if r.session==2]);records=[]
    cache=a.output_root.parent/'cache_confirmacao_test_2026-10-21';original={k:np.load(cache/(k+'.npy'),mmap_mode='r') for k in ['rgb','native','polar','red']}
    conditions=sorted({(r['orientation'],r['occluded_percent']) for r in coarse['records']+refined['records'] if r['orientation']!='original'})
    for orientation,loss in conditions:
        folder=a.output_root/f'confirmacao_congelada_test_{orientation}_{loss}_2026-10-21';completion=json.loads((folder/'CONCLUIDO.json').read_text());assert completion['result']['threshold']==threshold
        with np.load(folder/'scores_finais.npz') as z:c={k:z[k] for k in z.files}
        np.testing.assert_array_equal(c['labels'],b['labels']);assert c['scores'].shape==(486,16)
        measured,correct,accepted=metrics(c['scores'],c['labels'],threshold,c['valid']);np.testing.assert_array_equal(correct,c['correct']);np.testing.assert_array_equal(accepted,c['accepted'])
        for key in ['rank1','tar','far']:assert measured[key]==completion['result'][key]
        interventions=json.loads((folder/'interventions.json').read_text());defined=np.array([r['fraction_defined'] for r in interventions]);assert len(interventions)==486 and defined.sum()==480
        fractions=np.array([r['affected_fraction'] for r in interventions])[defined]
        for r in interventions:
            if r['fraction_defined']:assert r['affected_fraction']==round(r['reference_pixels']*loss/100)/r['reference_pixels']
        altered_cache=a.output_root.parent/f'cache_confirmacao_test_{orientation}_{loss}_2026-10-21'
        for key,base in original.items():
            current=np.load(altered_cache/(key+'.npy'),mmap_mode='r')
            unchanged=np.r_[gi,qi[~defined]]
            for start in range(0,len(unchanged),32):np.testing.assert_array_equal(base[unchanged[start:start+32]],current[unchanged[start:start+32]])
        sensitivity,_,_=metrics(c['scores'][defined],c['labels'][defined],threshold,c['valid'][defined])
        records.append(dict(orientation=orientation,occluded_percent=loss,nominal_preserved_percent=100-loss,metrics=measured,counts=dict(correct=int(correct.sum()),accepted=int(accepted.sum()),joint=int((correct&accepted).sum()),rank1_additional_correct_needed=max(0,math.ceil(.9*486)-int(correct.sum()))),paired_loss_rank1_pp_ci95=paired_ci(b['correct'],correct,subjects),paired_loss_tar_pp_ci95=paired_ci(b['accepted'],accepted,subjects),defined_area_queries=480,undefined_area_queries_retained_unchanged=6,actual_occluded_fraction_mean=float(fractions.mean()),actual_occluded_fraction_min=float(fractions.min()),actual_occluded_fraction_max=float(fractions.max()),gallery_and_empty_reference_inputs_exactly_unchanged=True,defined_reference_only_sensitivity=sensitivity,scores_sha256=hashlib.sha256((folder/'scores_finais.npz').read_bytes()).hexdigest()))
    final=dict(status='frozen_occlusion_audited',findings=refined['findings'],records=records,all486_queries_retained=True,unchanged_threshold=threshold,annotation_used_only_for_intervention=True,universal_or_clinical_minimum=None,interpretation='Smallest passing nominal retained annotated visible pixel fraction on1pp tested prefix; not complete anatomy, not proof every pixel is needed, not disease extent. Six queries lack defined area and remain unchanged; sensitivity over480 defined references reported separately without replacing primary denominator.',script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'AUDITORIA.json').write_text(json.dumps(final,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()

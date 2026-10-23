"""Comparacao pareada do controle de mascara/caixa/elipses originais."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_robustez_reconhecimento import load_splits,paired_ci,metrics
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'diagnostico_geometria_fixa_2026-10-21';out.mkdir(parents=True,exist_ok=False)
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['test'];subjects=np.array([r.subject for r in rows if r.session==2]);gi=np.array([i for i,r in enumerate(rows) if r.session==1]);qi=np.array([i for i,r in enumerate(rows) if r.session==2]);records=[]
    baseline_cache=a.output_root.parent/'cache_confirmacao_test_2026-10-21'
    for orientation in ['oclusao_superior','oclusao_inferior']:
        original=a.output_root/f'confirmacao_congelada_test_{orientation}_10_2026-10-21';fixed=a.output_root/f'confirmacao_congelada_test_{orientation}_10_geometria_fixa_2026-10-21'
        results=[json.loads((folder/'CONCLUIDO.json').read_text())['result'] for folder in [original,fixed]];assert results[0]['threshold']==results[1]['threshold']==0.8581747485460748
        arrays=[]
        for folder in [original,fixed]:
            with np.load(folder/'scores_finais.npz') as z:arrays.append({k:z[k] for k in z.files})
        dynamic,control=arrays;np.testing.assert_array_equal(dynamic['labels'],control['labels']);assert len(control['labels'])==486
        for data,result in zip(arrays,results):
            measured,correct,accepted=metrics(data['scores'],data['labels'],result['threshold'],data['valid']);np.testing.assert_array_equal(correct,data['correct']);np.testing.assert_array_equal(accepted,data['accepted'])
            for key in ['rank1','tar','far']:assert measured[key]==result[key]
        interventions=json.loads((fixed/'interventions.json').read_text());np.testing.assert_equal(interventions,json.loads((original/'interventions.json').read_text()));defined=np.array([r['fraction_defined'] for r in interventions]);assert defined.sum()==480
        cache=a.output_root.parent/f'cache_confirmacao_test_{orientation}_10_geometria_fixa_2026-10-21'
        with np.load(baseline_cache/'valid.npz') as z:rv=z['rgb'];pv=z['polar']
        with np.load(cache/'valid.npz') as z:np.testing.assert_array_equal(z['rgb'],rv);np.testing.assert_array_equal(z['polar'],pv)
        unchanged=np.r_[gi,qi[~defined]]
        for key in ['rgb','native','polar','red']:
            base=np.load(baseline_cache/(key+'.npy'),mmap_mode='r');current=np.load(cache/(key+'.npy'),mmap_mode='r')
            for start in range(0,len(unchanged),32):np.testing.assert_array_equal(base[unchanged[start:start+32]],current[unchanged[start:start+32]])
        records.append({'orientation':orientation,'loss_percent':10,'dynamic':results[0],'fixed_original_geometry':results[1],
          'rank1_gain_pp':100*(results[1]['rank1']-results[0]['rank1']),'tar_gain_pp':100*(results[1]['tar']-results[0]['tar']),
          'rank1_gain_pp_ci95':paired_ci(control['correct'],dynamic['correct'],subjects),'tar_gain_pp_ci95':paired_ci(control['accepted'],dynamic['accepted'],subjects),
          'additional_correct':int(control['correct'].sum()-dynamic['correct'].sum()),'additional_genuine_accepts':int(control['accepted'].sum()-dynamic['accepted'].sum()),
          'fixed_validity_matches_baseline':True,'gallery_and_undefined_area_inputs_unchanged':True,'all_queries_retained':486,'defined_area_queries':480,
          'source_scores_sha256':{str(folder.name):hashlib.sha256((folder/'scores_finais.npz').read_bytes()).hexdigest() for folder in [original,fixed]}})
    final={'status':'paired_original_geometry_diagnostic_completed','records':records,'threshold_recalibrated':False,'operational_minimum_changed':False,
      'scope':'Posthoc test diagnostic only; fixed support,bbox,ellipses require original unoccluded counterpart, not deployable one-photo improvement. Pixel texture and CLAHE still altered. No selection of model/threshold on these scores.',
      'uncertainty':'5000 person-cluster paired bootstrap, fixed gallery/threshold, pointwise; no multiple-comparison correction or population guarantee',
      'next':'Develop segmentation/normalization stability and occlusion-aware descriptors only on train/validation; preserve operational benchmark and limits',
      'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()

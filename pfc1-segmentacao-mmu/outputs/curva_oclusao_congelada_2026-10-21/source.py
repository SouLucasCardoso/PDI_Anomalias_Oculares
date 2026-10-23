"""Minimo na grade de10pp, interrompendo cada orientacao na primeira falha."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();out=a.output_root/'curva_oclusao_congelada_2026-10-21';out.mkdir(parents=True,exist_ok=False)
    baseline_file=a.output_root/'confirmacao_congelada_test_2026-10-21/CONCLUIDO.json';baseline=json.loads(baseline_file.read_text());assert baseline['target_reached']
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Exploratory frozen candidate, previously exposed UBIPr test; external pretraining overlap unknown',
      'conditions':'Original and upper/lower exact annotated iris pixel occlusion, levels10,20,...90%; one original query photo; all486 queries',
      'extraction':'Rerun frozen U-Net, geometry and all recognition components on each altered query; enrollment original. Annotation used ONLY to define intervention, never extraction; gray128 within reference iris, exterior unchanged; empty references unchanged and marked undefined area, retained in metrics.',
      'criterion':'Rank1>=90%,TAR>=90%,FMR<=1% at frozen validation threshold0.8581747485460748; minimum must pass all larger tested retained fractions',
      'stopping':'Evaluate increasing loss sequentially for each orientation; stop at FIRST failing condition. Lower retained fractions cannot satisfy all-larger-pass criterion after that failure, even if accuracy recovers. Unevaluated conditions are not plotted or imputed.',
      'interpretation':'Smallest approved retained fraction on10percentage-point grid, NOT precise anatomical, universal or clinical minimum; partial curve with justified early stopping, not complete19-condition curve',
      'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['avaliar_oclusao_congelada.py','avaliar_candidato_congelado.py','avaliar_robustez_reconhecimento.py']},
      'baseline_sha256':hashlib.sha256(baseline_file.read_bytes()).hexdigest()}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    records=[dict(orientation='original',occluded_percent=0,preserved_percent=100,passed=True,**baseline['result'])];findings=[]
    for orientation in ['oclusao_superior','oclusao_inferior']:
        minimum=100;first_failure=None;evaluated=[]
        for level in range(10,100,10):
            subprocess.run([sys.executable,str(ROOT/'avaliar_candidato_congelado.py'),'--split','test','--output-root',str(a.output_root),'--condition',orientation,'--level',str(level)],check=True)
            folder=a.output_root/f'confirmacao_congelada_test_{orientation}_{level}_2026-10-21';current=json.loads((folder/'CONCLUIDO.json').read_text());passed=current['target_reached'];evaluated.append(level)
            records.append(dict(orientation=orientation,occluded_percent=level,preserved_percent=100-level,passed=passed,**current['result']))
            (out/'progresso.json').write_text(json.dumps({'records':records,'completed_orientations':findings},indent=2),encoding='utf-8')
            if not passed:first_failure=100-level;break
            minimum=100-level
        findings.append({'orientation':orientation,'smallest_passing_retained_percent_on10pp_grid':minimum,'first_failing_retained_percent':first_failure,'evaluated_occluded_percent':evaluated,'stopped_at_first_failure':first_failure is not None})
    with (out/'resumo.csv').open('w',newline='',encoding='utf-8-sig') as stream:
        fields=sorted(set().union(*(r.keys() for r in records)));writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(records)
    final={'status':'coarse_grid_minimum_search_completed','findings':findings,'records':records,'threshold_recalibrated':False,'all_queries_retained':486,'independent_blind_test':False,'external_pretraining_overlap_unknown':True,'clinical_minimum':None,'anatomical_minimum':None,'limitations':protocol['interpretation']}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()

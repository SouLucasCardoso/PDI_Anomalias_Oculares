"""Refina a fronteira da grade inicial mantendo modelo/criterio congelados."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parent

def prefix_minimum(records):
    minimum=100
    for expected,(loss,passed) in enumerate(sorted(records),start=1):
        if loss!=expected:raise ValueError('Missing larger-area condition in1pp grid')
        if not passed:return minimum
        minimum=100-loss
    return minimum

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    coarse_file=a.output_root/'curva_oclusao_congelada_2026-10-21/CONCLUIDO.json';coarse=json.loads(coarse_file.read_text())
    out=a.output_root/'refinamento_oclusao_congelada_2026-10-21';out.mkdir(parents=True,exist_ok=False)
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Exploratory follow-up refining tested loss boundary after10pp scan, NOT independent confirmation; no changes to recognizer, calibration, threshold or criteria',
              'grid':'Each orientation, test loss1,2,... until first failing condition at frozen Rank1>=90%,TAR>=90%,FMR<=1%. Reuse already completed coarse conditions, no reevaluation or selection of better runs.',
              'stopping':'All larger retained fractions on1pp grid must pass; stop at first failure. Untested smaller fractions cannot satisfy this rule. No monotonicity assumed beyond this prefix criterion.',
              'population':'All486 queries retained,6 empty reference annotations unchanged and area undefined;480 queries have defined controlled pixel loss. One query image, supplied side, unchanged original enrollment.',
              'limitations':'Retained annotated visible iris pixel fraction, not anatomical iris or disease extent; artificial gray occlusion with resegmentation; point-estimate criterion, prior test exposure, unknown external-pretraining identities. Refinement chosen after coarse data; report as exploratory.',
              'coarse_sha256':hashlib.sha256(coarse_file.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'evaluator_sha256':hashlib.sha256((ROOT/'avaliar_candidato_congelado.py').read_bytes()).hexdigest()}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes())
    records=[];findings=[]
    for finding in coarse['findings']:
        orientation=finding['orientation'];failure=finding['first_failing_retained_percent'];upper=100-failure if failure is not None else 90;series=[]
        for loss in range(1,upper+1):
            folder=a.output_root/f'confirmacao_congelada_test_{orientation}_{loss}_2026-10-21';completion=folder/'CONCLUIDO.json'
            if not completion.exists():subprocess.run([sys.executable,str(ROOT/'avaliar_candidato_congelado.py'),'--split','test','--output-root',str(a.output_root),'--condition',orientation,'--level',str(loss)],check=True)
            current=json.loads(completion.read_text());passed=current['target_reached'];series.append((loss,passed));records.append(dict(orientation=orientation,occluded_percent=loss,preserved_percent=100-loss,passed=passed,**current['result']))
            (out/'progresso.json').write_text(json.dumps({'records':records,'completed_orientations':findings},indent=2),encoding='utf-8')
            if not passed:break
        findings.append({'orientation':orientation,'smallest_passing_retained_percent_on1pp_grid':prefix_minimum(series),'first_failing_retained_percent':100-series[-1][0] if not series[-1][1] else None,'evaluated_loss_levels':[i for i,_ in series],'all_larger_grid_fractions_pass':True})
    with (out/'resumo.csv').open('w',newline='',encoding='utf-8-sig') as stream:
        fields=sorted(set().union(*(r.keys() for r in records)));writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(records)
    final=dict(status='exploratory1pp_boundary_search_completed',findings=findings,records=records,threshold_recalibrated=False,all_queries_retained=486,defined_area_queries=480,undefined_area_queries_retained_unchanged=6,minimum_scope=protocol['limitations'],clinical_minimum=None,anatomical_minimum=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()

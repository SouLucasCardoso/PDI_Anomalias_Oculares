"""Ablacao operacional na validacao; checkpoint selecionado so por segmentacao."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);a=p.parse_args();trained=a.output_root/'segmentacao_oclusao_2026-10-21';completion=json.loads((trained/'CONCLUIDO.json').read_text());checkpoint=trained/'melhor_modelo.pt';digest=hashlib.sha256(checkpoint.read_bytes()).hexdigest();assert digest==completion['checkpoint_sha256']
    out=a.output_root/'validacao_segmentacao_oclusao_identidade_2026-10-21';out.mkdir(parents=True,exist_ok=False)
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'scope':'Recognition validation ONLY, paired preprocessing comparison; all482 queries including failures; checkpoint selected solely on segmentation Dice, never these identity results',
      'variants':'Original and robust segmenters, clean and upper/lower10% native reference iris gray occlusion. Reuse original clean completed validation. No weight/threshold or parameter search; all other identity components/frozen calibration unchanged.',
      'limitations':'Repeated development validation; new segmenter may change score distribution. Do not infer new test performance, minimum area, disease extent or automatic replacement. Future calibration/release must be separately frozen using validation only.',
      'checkpoint_sha256':digest,'best_epoch':completion['best_epoch'],'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'evaluator_sha256':hashlib.sha256((ROOT/'avaliar_candidato_congelado.py').read_bytes()).hexdigest()}
    (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());records=[]
    for robust in [False,True]:
        for condition in ['original','oclusao_superior','oclusao_inferior']:
            level=0 if condition=='original' else 10;suffix='' if level==0 else f'_{condition}_{level}'
            if robust:suffix+='_segmentador_'+digest[:12]
            folder=a.output_root/f'confirmacao_congelada_val{suffix}_2026-10-21'
            if not (folder/'CONCLUIDO.json').exists():
                cmd=[sys.executable,str(ROOT/'avaliar_candidato_congelado.py'),'--split','val','--condition',condition,'--level',str(level),'--output-root',str(a.output_root)]
                if robust:cmd+=['--segmenter',str(checkpoint)]
                subprocess.run(cmd,check=True)
            current=json.loads((folder/'CONCLUIDO.json').read_text());records.append(dict(segmenter='robust' if robust else 'original',condition=condition,occluded_percent=level,result=current['result'],source=str(folder)))
            (out/'progresso.json').write_text(json.dumps({'records':records},indent=2),encoding='utf-8')
    final={'status':'segmentation_recognition_validation_completed','records':records,'test_inference':False,'minimum_area':None,'frozen_candidate_replaced':False,'threshold_recalibrated':False}
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final,indent=2),flush=True)

if __name__=='__main__':main()

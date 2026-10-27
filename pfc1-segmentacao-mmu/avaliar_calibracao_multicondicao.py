"""Calibracao global interna aumentada; nenhum ajuste nos casos do monitor."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json
import numpy as np
from calibracao_multicondicao import calibrate_robust
from treinar_bloco_fmr_separado import ROOT,measured
from preparar_encoder_espacial import file_hash
NAME='calibracao_multicondicao_treino_2026-10-24'
TAGS=['clean','upper10','lower10']

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args();out=a.root/NAME;source=a.root/'fundo_consulta_treino_2026-10-23';sd=json.loads((source/'CONCLUIDO.json').read_text())
    if a.registrar:
        out.mkdir(exist_ok=False);protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='New TRAIN calibration hypothesis after clean-only transfer failed. Same fixed151FITnetwork,120queries/16INTERNALpeople for calibration,480queries/16OLDmonitor for assessment. Reused development populations,NOTindependent confirmation. No retraining/VAL/test.',
            method='Fixed background-normalized9componentfusion unchanged. Compute internal impostor0.5%FMRthreshold in each of CLEAN/upper10/lower10; ONEglobal threshold=max of these3, usedforALLconditions/ALLpeople. Condition labels ONLYdefine calibrationdomains,NEVERswitchthreshold at inference. No monitor cases/labels in threshold selection.',
            difference='Unlike earlier experiments, INTERNAL synthetic occlusions now legitimately enter calibration in NEWprotocol,not retroactive change. No condition-specific evaluation threshold, percentile search, model/fusionweight changes, query filtering or monitor-based threshold adjustment.',
            gate='Reportjoint90%Rank1/TAR andFMR<=1%percondition. Onlyif ALLmonitorFMR<=1%andcleanRank1/TAR>=90% consider separatelyregistered fixed5%occlusion feasibility. No automaticVAL/test/promotion/minimum; 10%ranking cannot change from monotonicthreshold.',
            target_internal_fmr=.005,source_completion_sha256=file_hash(source/'CONCLUIDO.json'),source_protocol_sha256=file_hash(source/'protocolo.json'),script_sha256=file_hash(Path(__file__)),calibrator_sha256=file_hash(ROOT/'calibracao_multicondicao.py'),score_files_sha256={f'scores_{split}_{tag}.npz':file_hash(source/f'scores_{split}_{tag}.npz') for split in ['internal','monitor'] for tag in TAGS})
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Calibracao global multicondicao registrada antes da avaliacao.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert not (out/'CONCLUIDO.json').exists() and file_hash(Path(__file__))==protocol['script_sha256'] and file_hash(ROOT/'calibracao_multicondicao.py')==protocol['calibrator_sha256'];assert file_hash(source/'CONCLUIDO.json')==protocol['source_completion_sha256'] and file_hash(source/'protocolo.json')==protocol['source_protocol_sha256']
    for n,h in protocol['score_files_sha256'].items():assert file_hash(source/n)==h
    internal={}
    for tag in TAGS:
        with np.load(source/f'scores_internal_{tag}.npz') as z:internal[tag]={k:z[k] for k in ['scores','labels','valid']}
    threshold,parts=calibrate_robust(internal,protocol['target_internal_fmr']);results={}
    for split in ['internal','monitor']:
        for tag in TAGS:
            with np.load(source/f'scores_{split}_{tag}.npz') as z:data={k:z[k] for k in ['scores','labels','valid']}
            m,d=measured(data,threshold);results.setdefault(split,{})[tag]=m;np.savez_compressed(out/f'scores_{split}_{tag}.npz',**d)
    r=results['monitor'];fmr=all(r[t]['far']<=.01 for t in TAGS);absolute=all(r[t]['rank1']>=.9 and r[t]['tar']>=.9 and r[t]['far']<=.01 for t in TAGS);eligible=fmr and all(r['clean'][k]>=.9 for k in ['rank1','tar'])
    done=dict(status='global_internal_multidomain_threshold_evaluated',results=results,clean_only_control=sd['results'],threshold=threshold,internal_domain_thresholds=parts,all_monitor_fmr_at_most_one_percent=bool(fmr),absolute_target_reached=bool(absolute),five_percent_feasibility_eligible=bool(eligible),monitor_used_for_calibration=False,condition_specific_inference_threshold=False,new_training=False,new_image_inference=False,validation_inference=False,test_inference=False,candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(done,indent=2),encoding='utf-8');print(json.dumps(done),flush=True)
if __name__=='__main__':main()

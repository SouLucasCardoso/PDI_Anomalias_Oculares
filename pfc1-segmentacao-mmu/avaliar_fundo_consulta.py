"""Alternativa fixa de normalizacao, sem rede nova ou limiar nas oclusoes."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json
import numpy as np
from avaliar_fusao_treino_separado import ROOT,ORDER,CONDITIONS
from normalizacao_fundo_consulta import fuse_background
from preparar_encoder_espacial import file_hash
from treinar_bloco_fmr_separado import calibrate,measured
NAME='fundo_consulta_treino_2026-10-23'

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args();out=a.root/NAME;source=a.root/'fusao_treino_calibracao_separada_2026-10-23';previous=json.loads((source/'CONCLUIDO.json').read_text())
    if a.registrar:
        out.mkdir(exist_ok=False);protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='TRAIN development only, same120INTERNALclean calibration queries and480OLDmonitorqueries. Hypothesis AFTERfusionFMRshift,not independent confirmation. NO training/VAL/test.',
            primary='ADAPTEDfixed9componentfusion,originalfixedcomponentmeans/stds from INTERNALCLEAN. Beforelogistic estimate querymean/std over available candidateRAWfusedlogits EXCLUDINGmaxONE. Apply toALLcandidatevalues inclmax,thenlogistic. No labels/GT/condition/threshold search. Atleast3candidates and nonzero backgroundstd required;otherwise rejection/allqueriesretained.',
            calibration='ONEnew INTERNALCLEAN0.5%FMRthreshold; unchanged forupper/lower10andOLDmonitorinclclean. OriginalADAPTEDnormalization as fixedcontrol. Rankcannotimprove fornonfailedqueries becauseperquerymonotonic.',
            gate='OLDmonitor cleanRank1/TAR>=controlclean, FMR<=1%ALLconditions;occludedTAR>=90%,Rank1>=90%forabsolutegoal. No replacingcandidateoropeningVAL/test automatically.',
            source_completion_sha256=file_hash(source/'CONCLUIDO.json'),source_protocol_sha256=file_hash(source/'protocolo.json'),script_sha256=file_hash(Path(__file__)),normalizer_sha256=file_hash(ROOT/'normalizacao_fundo_consulta.py'),component_files_sha256={f.name:file_hash(f) for f in source.glob('component_*.npz')},polar_files_sha256={f.name:file_hash(f) for f in source.glob('dependency_polar_selected_*.npz')})
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Normalizacao de fundo registrada antes dos resultados.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert not (out/'CONCLUIDO.json').exists() and file_hash(Path(__file__))==protocol['script_sha256'] and file_hash(ROOT/'normalizacao_fundo_consulta.py')==protocol['normalizer_sha256'];assert file_hash(source/'CONCLUIDO.json')==protocol['source_completion_sha256'] and file_hash(source/'protocolo.json')==protocol['source_protocol_sha256']
    for group in ['component_files_sha256','polar_files_sha256']:
        for n,h in protocol[group].items():assert file_hash(source/n)==h
    calibration=previous['parameters']['adapted']['calibration'];results={};threshold=None
    for split in ['internal','monitor']:
        for tag,_,_ in CONDITIONS:
            components=[]
            for name in ORDER:
                file=source/f'dependency_polar_selected_{split}_{tag}.npz' if name=='polar' else source/f'component_{split}_{tag}_{name}.npz'
                with np.load(file) as z:components.append({k:z[k] for k in ['scores','labels','valid']})
            scores,valid=fuse_background(components,calibration);data=dict(scores=scores,labels=components[0]['labels'],valid=valid)
            if split=='internal' and tag=='clean':threshold=calibrate(data)
            m,d=measured(data,threshold);results.setdefault(split,{})[tag]=m;np.savez_compressed(out/f'scores_{split}_{tag}.npz',**d)
    r=results['monitor'];control=previous['results']['adapted']['monitor'];absolute=all(r[t]['rank1']>=.9 and r[t]['tar']>=.9 and r[t]['far']<=.01 for t,_,_ in CONDITIONS);fmr=all(r[t]['far']<=.01 for t,_,_ in CONDITIONS)
    final=dict(status='background_normalization_evaluated',results=results,control=previous['results']['adapted'],threshold=threshold,component_calibration=calibration,all_monitor_fmr_at_most_one_percent=bool(fmr),absolute_target_reached=bool(absolute),validation_inference=False,test_inference=False,candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(final,indent=2),encoding='utf-8');print(json.dumps(final),flush=True)
if __name__=='__main__':main()

"""Auditoria temporaria da normalizacao de fundo; projeto protegido pelo Defender."""
from pathlib import Path
import argparse,json
import numpy as np
from avaliar_fundo_consulta import ROOT,NAME,ORDER,CONDITIONS
from normalizacao_fundo_consulta import fuse_background
from treinar_bloco_fmr_separado import calibrate,measured
from preparar_encoder_espacial import file_hash

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();out=a.root/NAME;done=json.loads((out/'CONCLUIDO.json').read_text());protocol=json.loads((out/'protocolo.json').read_text());source=a.root/'fusao_treino_calibracao_separada_2026-10-23'
    assert file_hash(out/'source.py')==protocol['script_sha256']==file_hash(ROOT/'avaliar_fundo_consulta.py') and file_hash(ROOT/'normalizacao_fundo_consulta.py')==protocol['normalizer_sha256']
    assert file_hash(source/'CONCLUIDO.json')==protocol['source_completion_sha256'] and file_hash(source/'protocolo.json')==protocol['source_protocol_sha256']
    for group in ['component_files_sha256','polar_files_sha256']:
        for name,h in protocol[group].items():assert file_hash(source/name)==h
    for split in ['internal','monitor']:
        for tag,_,_ in CONDITIONS:
            components=[]
            for name in ORDER:
                file=source/f'dependency_polar_selected_{split}_{tag}.npz' if name=='polar' else source/f'component_{split}_{tag}_{name}.npz'
                with np.load(file) as z:components.append({k:z[k] for k in ['scores','labels','valid']})
            scores,valid=fuse_background(components,done['component_calibration']);data=dict(scores=scores,labels=components[0]['labels'],valid=valid)
            if split=='internal' and tag=='clean':assert calibrate(data)==done['threshold']
            m,saved=measured(data,done['threshold']);assert m==done['results'][split][tag]
            with np.load(out/f'scores_{split}_{tag}.npz') as z:
                for key,value in saved.items():np.testing.assert_array_equal(value,z[key])
    r=done['results']['monitor'];fmr=all(r[t]['far']<=.01 for t,_,_ in CONDITIONS);absolute=all(r[t]['rank1']>=.9 and r[t]['tar']>=.9 and r[t]['far']<=.01 for t,_,_ in CONDITIONS)
    assert bool(fmr)==done['all_monitor_fmr_at_most_one_percent'] and bool(absolute)==done['absolute_target_reached'];assert not any(done[k] for k in ['validation_inference','test_inference','candidate_replaced'])
    audit=dict(status='background_normalization_audited',all_scores_exact=True,calibration_internal_clean_only=True,shared_threshold_verified=True,all_monitor_fmr_at_most_one_percent=bool(fmr),absolute_target_reached=bool(absolute),new_image_inference=False)
    (out/'AUDITORIA_REPRODUCAO.json').write_text(json.dumps(audit,indent=2),encoding='utf-8');print(json.dumps(audit))
if __name__=='__main__':main()
